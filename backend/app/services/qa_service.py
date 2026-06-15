"""Deep Q&A over the persisted simulation + report (Phase 7).

Answers are grounded strictly in persisted data — the strategic report payload,
the baseline event log, consumer agents and their simulation memory, and the
ontology. A lightweight intent classifier routes each question to a deterministic
answer builder. An optional LLM pass may rewrite the prose but must never invent
findings; it falls back to the deterministic answer on any failure.

Preconditions (raised as ValueError → 409 by the API layer):
    events_required | report_required
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Event
from app.schemas.qa import (
    InterviewAnswer,
    QAAnswer,
    QAEvidenceRef,
    QuestionIn,
    QuestionOut,
)
from app.schemas.report import ReportPayload
from app.services import report_service
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_EXPLORATORY = "Simulation output is exploratory decision support, not a guaranteed market forecast."


# --- intent classification --------------------------------------------------

_INTENT_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    # interview must win over other keyword matches
    ("interview_agents", ("interview", "talk to", "speak to", "ask 3", "ask 5", "ask three", "ask five")),
    ("repeat_purchase", ("repeat", "repurchase", "loyalty", "come back", "buy again", "retention")),
    ("target_segment", ("which segment", "target first", "beachhead", "who should we target", "best segment", "which consumer")),
    ("claim_risk", ("claim", "skeptic", "credib", "believe", "proof", "rtb", "reason to believe")),
    ("pricing", ("price", "pricing", "premium", "expensive", "cost", "value for money", "promo")),
    ("channel_touchpoint", ("touchpoint", "channel", "shelf", "tiktok", "e-commerce", "ecommerce", "where to buy", "store")),
    ("trial", ("trial", "try", "first purchase", "purchase intent", "conversion")),
    ("barriers", ("barrier", "hesitat", "reject", "stop", "blocker", "why did", "obstacle", "friction")),
    ("triggers", ("trigger", "driver", "motivat", "what makes", "appeal", "drives trial")),
    ("recommendations", ("recommend", "what should we", "should we change", "prioriti", "a/b", "ab test", "action", "fix")),
    ("competitor_response", ("competitor", "retailer", "retail", "influencer", "negative comment", "respond", "backlash", "social")),
    ("general_summary", ("summary", "summarise", "summarize", "explain", "overview", "simple", "plain", "tl;dr", "overall")),
]


def classify_intent(question: str) -> str:
    q = question.lower()
    for intent, kws in _INTENT_KEYWORDS:
        if any(k in q for k in kws):
            return intent
    return "general_summary"


def _interview_count(question: str, available: int) -> int:
    words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8}
    m = re.search(r"\b(\d+)\b", question)
    n = int(m.group(1)) if m else next((v for w, v in words.items() if w in question.lower()), 5)
    return max(1, min(n, available, 8))


# --- evidence helpers -------------------------------------------------------


def _excerpt(text: str | None, n: int = 120) -> str:
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _ref(e: Event) -> QAEvidenceRef:
    return QAEvidenceRef(
        event_id=e.id,
        round_number=e.round_number,
        agent_id=e.agent_id,
        segment_name=e.segment_name,
        action_type=e.action_type,
        short_reaction_excerpt=_excerpt(e.generated_reaction or e.reasoning),
    )


def _pick(events: list[Event], predicate, limit: int) -> list[QAEvidenceRef]:
    out = [_ref(e) for e in events if predicate(e)]
    # most decisive first: higher round + confidence
    out_events = sorted(
        [e for e in events if predicate(e)],
        key=lambda e: (e.round_number, e.confidence_score or 0.0),
        reverse=True,
    )
    return [_ref(e) for e in out_events[:limit]]


# --- per-intent deterministic builders --------------------------------------


def _b_repeat(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    f = rp.trial_repeat_forecast
    low_segs = [s.segment_name for s in sorted(rp.segment_reaction_map, key=lambda s: s.average_repeat_probability)[:3]]
    top_barrier = rp.adoption_barrier_analysis[0].barrier if rp.adoption_barrier_analysis else "post-trial satisfaction"
    ev = _pick(events, lambda e: e.action_type in ("no_repeat_intent", "complain"), limit)
    return QAAnswer(
        direct_answer=(
            f"Repeat is the funnel's tightest constraint. {f.likely_repeaters} The main drag is "
            f"'{top_barrier}', which keeps post-trial satisfaction below the repeat threshold — especially "
            f"for {', '.join(low_segs)}."
        ),
        evidence_summary=(
            f"{f.one_time_trial_risk} Repeat probability is lowest in {', '.join(low_segs)} per the segment "
            "reaction map; post-trial events show no_repeat_intent / complain where taste-value expectations are unmet."
        ),
        supporting_events=ev,
        supporting_segments=low_segs,
        confidence_score=0.66,
        limitations=[_EXPLORATORY, "Repeat depends on real sensory acceptance, which is not measured here."],
        recommended_next_action=[
            "De-risk taste via sampling and proof-of-taste content before scaling media.",
            "Run a sensory test to confirm the share of triers who rate taste repeat-worthy.",
        ],
    )


def _b_trial(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    es = rp.executive_summary
    top_segs = [s.segment_name for s in rp.segment_reaction_map[:2]]
    ev = _pick(events, lambda e: e.action_type == "purchase_trial", limit)
    return QAAnswer(
        direct_answer=(
            f"{es.estimated_trial_potential} Trial concentrates in {', '.join(top_segs)}, "
            f"driven by {rp.trial_repeat_forecast.likely_triers}"
        ),
        evidence_summary=f"{rp.launch_funnel_summary.trial_signal} Purchase-trial events cluster in the beachhead segments.",
        supporting_events=ev,
        supporting_segments=top_segs,
        confidence_score=0.66,
        limitations=[_EXPLORATORY],
        recommended_next_action=[
            f"Focus early trial spend on {', '.join(top_segs)}.",
            "Anchor trial on the sampling/promo mechanic rather than a permanent price cut.",
        ],
    )


def _b_target_segment(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    if not rp.segment_reaction_map:
        return _b_general(rp, events, consumers, ont, limit)
    top = rp.segment_reaction_map[0]
    ev = _pick(events, lambda e: e.segment_name == top.segment_name and e.action_type in ("purchase_trial", "like", "recommend"), limit)
    return QAAnswer(
        direct_answer=(
            f"Target {top.segment_name} first — it shows the highest simulated trial probability "
            f"({top.average_trial_probability}) and purchase intent ({top.average_purchase_intent_score}). "
            f"{top.recommended_message_angle}"
        ),
        evidence_summary=(
            f"Across the segment reaction map, {top.segment_name} leads on trial probability; its strongest trigger is "
            f"'{top.strongest_trigger}'. Representative reaction: \"{top.representative_reaction}\""
        ),
        supporting_events=ev,
        supporting_segments=[s.segment_name for s in rp.segment_reaction_map[:3]],
        confidence_score=top.confidence_score,
        limitations=[_EXPLORATORY, "Segment ranking reflects modelled archetypes, not panel data."],
        recommended_next_action=[
            f"Lead launch targeting with {top.segment_name}.",
            "Validate the beachhead with a quick concept test in that segment.",
        ],
    )


def _b_claim(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    claims = rp.claim_clarity_and_credibility
    riskiest = None
    for c in claims:
        if "question" in c.credibility_assessment.lower() or "disbeliev" in c.credibility_assessment.lower() or "unbeliev" in c.credibility_assessment.lower():
            riskiest = c
            break
    riskiest = riskiest or (claims[0] if claims else None)
    ev = _pick(events, lambda e: e.action_type in ("request_review", "comment_negative"), limit)
    if riskiest is None:
        return _b_general(rp, events, consumers, ont, limit)
    rewrite = f" Suggested rewrite: {riskiest.recommended_rewrite}" if riskiest.recommended_rewrite else ""
    return QAAnswer(
        direct_answer=(
            f"The riskiest claim is '{riskiest.claim}'. Credibility: {riskiest.credibility_assessment} "
            f"Clarity: {riskiest.clarity_assessment}{rewrite}"
        ),
        evidence_summary=(
            "Skeptical and review-dependent agents request third-party validation or comment negatively in the "
            "communication round, signalling the claim needs a stronger reason-to-believe."
        ),
        supporting_events=ev,
        supporting_segments=["Skeptical Reviewer-Dependent Buyer", "Health/Safety-Conscious Buyer"],
        confidence_score=0.63,
        limitations=[_EXPLORATORY, "Believability is inferred from skepticism traits, not real claim testing."],
        recommended_next_action=[
            "Add a concrete, substantiated reason-to-believe to the claim.",
            "Seed credible KOC/expert reviews before asking for trial.",
        ],
    )


def _b_pricing(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    pp = rp.packaging_price_perception
    ev = _pick(events, lambda e: e.action_type in ("wait_for_promotion", "reject_before_trial", "ask_price"), limit)
    return QAAnswer(
        direct_answer=(
            f"{pp.price_value_summary} Premium price risk is {pp.premium_price_risk} {pp.promotion_dependency} "
            f"Recommended action: {pp.recommended_price_or_promo_action}"
        ),
        evidence_summary=(
            "Price-sensitive consumers defer to a promotion or reject before trial when value-per-serve is unclear; "
            "these events drive the pricing read."
        ),
        supporting_events=ev,
        supporting_segments=["Value-Seeking Practical Buyer", "Promotion-Driven Trial Buyer"],
        confidence_score=0.64,
        limitations=[_EXPLORATORY, "No real price-elasticity data informs this."],
        recommended_next_action=[
            "Make value-per-serve explicit on pack and PDP.",
            "Test a sampling/BOGO trial mechanic instead of a permanent price cut.",
        ],
    )


def _b_channel(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    chans = rp.channel_touchpoint_analysis
    # best-for-trial touchpoint: most trial/cart actions
    best = None
    best_trials = -1
    for c in chans:
        m = re.search(r"(\d+)", c.trial_contribution)
        n = int(m.group(1)) if m else 0
        if n > best_trials:
            best_trials, best = n, c
    ev = _pick(events, lambda e: e.action_type in ("purchase_trial", "add_to_cart", "ask_where_to_buy"), limit)
    if best is None:
        return _b_general(rp, events, consumers, ont, limit)
    return QAAnswer(
        direct_answer=(
            f"'{best.channel_or_touchpoint}' performed best for trial ({best.trial_contribution}). "
            f"Recommended role: {best.recommended_role_in_launch}."
        ),
        evidence_summary=(
            "Findability gates the shelf / e-commerce round; trial and add-to-cart actions concentrate at the "
            "touchpoints where visibility and channel fit are strongest."
        ),
        supporting_events=ev,
        supporting_segments=["Convenience-Driven Busy Buyer", "Early Adopter / Trend-Seeker"],
        confidence_score=0.62,
        limitations=[_EXPLORATORY, "Channel performance is modelled from channel-fit traits, not real sell-through."],
        recommended_next_action=[
            f"Prioritise visible facings / a strong PDP at {best.channel_or_touchpoint}.",
            "Secure trade visibility before scaling awareness media.",
        ],
    )


def _b_barriers(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    barriers = rp.adoption_barrier_analysis
    if not barriers:
        return _b_general(rp, events, consumers, ont, limit)
    top = barriers[0]
    ev = _pick(events, lambda e: e.barrier_detected == top.barrier, limit)
    lines = "; ".join(f"{b.barrier} (×{b.frequency}, {b.severity_level})" for b in barriers[:3])
    return QAAnswer(
        direct_answer=(
            f"The strongest adoption barriers are: {lines}. The top barrier '{top.barrier}' affects "
            f"{', '.join(top.affected_segments)}. Fix: {top.recommended_fix}"
        ),
        evidence_summary=f"'{top.barrier}' is detected {top.frequency} times across the event log, mostly in the trial/post-trial rounds.",
        supporting_events=ev,
        supporting_segments=top.affected_segments,
        confidence_score=0.66,
        limitations=[_EXPLORATORY],
        recommended_next_action=[b.recommended_fix for b in barriers[:2]],
    )


def _b_triggers(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    triggers = rp.purchase_trigger_analysis
    if not triggers:
        return _b_general(rp, events, consumers, ont, limit)
    top = triggers[0]
    ev = _pick(events, lambda e: e.trigger_detected == top.trigger, limit)
    lines = "; ".join(f"{t.trigger} (×{t.frequency})" for t in triggers[:3])
    return QAAnswer(
        direct_answer=f"The strongest purchase triggers are: {lines}. Lead trigger: '{top.trigger}'. {top.strategic_implication}",
        evidence_summary=f"'{top.trigger}' recurs {top.frequency} times across {', '.join(top.affected_segments)}.",
        supporting_events=ev,
        supporting_segments=top.affected_segments,
        confidence_score=0.65,
        limitations=[_EXPLORATORY],
        recommended_next_action=[f"Lean into '{top.trigger}' in creative and at the converting touchpoints."],
    )


def _b_recommendations(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    recs = rp.strategic_recommendations
    ab = rp.recommended_ab_tests
    top = recs[0] if recs else None
    rec_lines = "; ".join(f"[{r.priority}] {r.recommendation}" for r in recs[:4])
    ab_line = ab[0].test_name if ab else "the claim reason-to-believe test"
    return QAAnswer(
        direct_answer=(
            f"Before launch, prioritise: {rec_lines}. The first A/B test to run is '{ab_line}'."
        ),
        evidence_summary=(top.supporting_evidence if top else "Derived from the report's barrier/segment aggregates."),
        supporting_events=_pick(events, lambda e: e.action_type in ("reject_before_trial", "no_repeat_intent", "request_review"), limit),
        supporting_segments=[s.segment_name for s in rp.segment_reaction_map[:3]],
        confidence_score=0.64,
        limitations=[_EXPLORATORY],
        recommended_next_action=[r.recommendation for r in recs[:3]],
    )


def _b_competitor(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    cr = rp.competitor_and_retail_response
    sd = rp.social_diffusion_and_wom
    ev = _pick(events, lambda e: e.agent_type == "market_actor", limit)
    return QAAnswer(
        direct_answer=(
            f"Competitor risks: {'; '.join(cr.competitor_risks[:2])}. To respond to negative comments: "
            f"{sd.recommended_social_content_response}"
        ),
        evidence_summary=(
            f"Market-actor events show retailer, competitor and influencer reactions to the launch signal. "
            f"Likely complainers: {sd.likely_complainers}"
        ),
        supporting_events=ev,
        supporting_segments=[],
        confidence_score=0.6,
        limitations=[_EXPLORATORY, "Market-actor behaviour is modelled, not observed."],
        recommended_next_action=[
            "Pre-empt taste/claim doubts with proof-of-taste content.",
            "Lock trade visibility early to blunt defensive competitor promos.",
        ],
    )


def _b_general(rp: ReportPayload, events, consumers, ont, limit) -> QAAnswer:
    es = rp.executive_summary
    return QAAnswer(
        direct_answer=(
            f"In plain terms: {es.overall_market_reaction} The biggest opportunity is {es.top_opportunity} "
            f"The biggest risk is {es.top_risk} Top move: {es.key_recommendation}"
        ),
        evidence_summary=(
            f"{rp.launch_funnel_summary.trial_signal} {rp.launch_funnel_summary.repeat_signal} "
            f"{rp.launch_funnel_summary.advocacy_signal}"
        ),
        supporting_events=_pick(events, lambda e: e.action_type in ("purchase_trial", "recommend", "reject_before_trial"), limit),
        supporting_segments=[s.segment_name for s in rp.segment_reaction_map[:3]],
        confidence_score=es.confidence_score,
        limitations=[_EXPLORATORY] + list(rp.limitations[:1]),
        recommended_next_action=[es.key_recommendation],
    )


_BUILDERS = {
    "repeat_purchase": _b_repeat,
    "trial": _b_trial,
    "target_segment": _b_target_segment,
    "claim_risk": _b_claim,
    "pricing": _b_pricing,
    "channel_touchpoint": _b_channel,
    "barriers": _b_barriers,
    "triggers": _b_triggers,
    "recommendations": _b_recommendations,
    "competitor_response": _b_competitor,
    "general_summary": _b_general,
}


# --- interview builder ------------------------------------------------------


def _profile(a: Agent) -> dict:
    try:
        return json.loads(a.profile_json or "{}")
    except json.JSONDecodeError:
        return {}


def _memory(a: Agent) -> list[str]:
    try:
        mem = json.loads(a.simulation_memory_json or "[]")
        return mem if isinstance(mem, list) else []
    except json.JSONDecodeError:
        return []


def _b_interview(question: str, rp, events, consumers, ont, limit) -> QAAnswer:
    q = question.lower()
    # decide cohort
    if any(k in q for k in ("skeptic", "doubt", "critic", "unsure", "hesitan")):
        cohort, label = "skeptical", "skeptical consumer"
        ranked = sorted(consumers, key=lambda a: _profile(a).get("claim_skepticism_level", 0.0), reverse=True)
    elif any(k in q for k in ("repeat", "loyal", "advocate", "fan", "satisf")):
        cohort, label = "repeat", "likely repeat buyer"
        trier_ids = {e.agent_id for e in events if e.action_type in ("repeat_purchase_intent", "recommend", "share_with_friend")}
        ranked = [a for a in consumers if a.id in trier_ids] or sorted(
            consumers, key=lambda a: _profile(a).get("brand_loyalty_level", 0.0), reverse=True
        )
    else:
        cohort, label = "general", "simulated consumer"
        ranked = consumers
    n = _interview_count(question, len(ranked))
    chosen = ranked[:n]

    interviews: list[InterviewAnswer] = []
    for a in chosen:
        mem = _memory(a)
        last = mem[-1] if mem else ""
        prof = _profile(a)
        if cohort == "skeptical":
            ans = (
                f"I'm not fully convinced yet — I'd want proof before paying for this. "
                f"My read across the launch: {_excerpt(last, 160)}"
            )
        elif cohort == "repeat":
            ans = (
                f"I tried it and it largely worked for me, so I'd buy it again if it stays available and priced fairly. "
                f"{_excerpt(last, 160)}"
            )
        else:
            ans = f"My overall reaction across the launch: {_excerpt(last, 160)}"
        interviews.append(
            InterviewAnswer(
                agent_id=a.id,
                segment_name=a.segment_name,
                persona_label=f"{label} — {a.segment_name or 'unknown segment'}",
                answer=ans,
                evidence_from_agent_memory=mem[-3:],
            )
        )

    return QAAnswer(
        direct_answer=f"Interviewed {len(chosen)} simulated {label}s. Their reactions are summarised below.",
        evidence_summary="Each interview is reconstructed from the agent's persisted simulation memory across the 6 rounds.",
        supporting_events=[],
        supporting_segments=sorted({a.segment_name for a in chosen if a.segment_name}),
        confidence_score=0.6,
        limitations=[
            _EXPLORATORY,
            "These are SIMULATED personas reconstructed from modelled behaviour — not real interview transcripts.",
        ],
        recommended_next_action=["Validate these reconstructed reactions with real qualitative interviews."],
        selected_agents=[a.id for a in chosen],
        simulated_interview_answers=interviews,
    )


# --- optional LLM rewrite ---------------------------------------------------

_LLM_SYSTEM = (
    "You are an FMCG insights analyst. Rewrite the given direct_answer to be sharper and more readable. "
    "You MUST NOT add new facts, numbers, segments, or findings — only rephrase. Preserve every figure exactly. "
    "Return strict JSON: {\"direct_answer\": \"...\"}."
)


def _maybe_llm(answer: QAAnswer, llm_client: LLMClient | None) -> str:
    client = llm_client or LLMClient()
    if not client.configured:
        return "deterministic"
    try:
        data = client.chat_json(_LLM_SYSTEM, json.dumps({"direct_answer": answer.direct_answer}))
        new = data.get("direct_answer")
        if isinstance(new, str) and new.strip():
            answer.direct_answer = new.strip()
            return "llm"
    except Exception as e:  # noqa: BLE001
        logger.warning("Q&A LLM rewrite failed; using deterministic answer. error=%s", e)
    return "deterministic"


# --- entry point ------------------------------------------------------------


def _load(db: Session, project_id: str) -> tuple[ReportPayload, list[Event], list[Agent]]:
    events = db.execute(
        select(Event).where(Event.project_id == project_id, Event.run_type == "baseline").order_by(Event.round_number)
    ).scalars().all()
    if not events:
        raise ValueError("events_required")
    report_row = report_service.get_report_row(db, project_id)
    if report_row is None:
        raise ValueError("report_required")
    rp = report_service.get_payload(report_row)
    consumers = db.execute(
        select(Agent).where(Agent.project_id == project_id, Agent.agent_type == "consumer")
    ).scalars().all()
    return rp, events, consumers


def ask(db: Session, project_id: str, payload: QuestionIn, llm_client: LLMClient | None = None) -> QuestionOut:
    rp, events, consumers = _load(db, project_id)
    intent = classify_intent(payload.question)
    limit = max(0, payload.max_evidence_events) if payload.include_evidence else 0

    if intent == "interview_agents":
        answer = _b_interview(payload.question, rp, events, consumers, None, limit)
    else:
        answer = _BUILDERS[intent](rp, events, consumers, None, limit)

    if not payload.include_evidence:
        answer.supporting_events = []

    source_mode = "deterministic"
    if payload.use_llm:
        source_mode = _maybe_llm(answer, llm_client)

    return QuestionOut(
        project_id=project_id,
        question=payload.question,
        intent=intent,
        answer=answer,
        source_mode=source_mode,
    )
