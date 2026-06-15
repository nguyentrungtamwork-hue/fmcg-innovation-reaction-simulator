"""Briefing Q&A, audience tailoring, and board summary (Phase 15).

Everything here is grounded strictly in the persisted briefing payload (which is
itself derived from the report + scorecard + confidence + assumptions + history).
Audience tailoring re-frames the SAME findings — it never re-runs the simulation
or invents data. Deterministic by default; optional LLM polishes prose only.

Preconditions (ValueError → mapped by the endpoint):
    report_required | briefing_required | board_summary_required
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import BriefingArtifact
from app.schemas.briefing import (
    BriefingAnswer,
    BriefingAskIn,
    BriefingAskOut,
    BriefingPayload,
    BoardSummaryIn,
    BoardSummaryOut,
    BoardSummaryPayload,
    TailorIn,
    TailoredPayload,
    TailorOut,
)
from app.schemas.report import EvidenceRef
from app.services import briefing_service, report_service
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_CONF = {"high": 0.8, "medium": 0.6, "low": 0.4}

_OWNERS = {
    "brand_team": {"Brand", "Creative", "Media"},
    "trade_sales": {"Trade Marketing", "Sales", "E-commerce"},
    "rd_product": {"R&D"},
    "consumer_insight": {"Consumer Insight"},
    "executive": {"Leadership", "Brand"},
}

_FRAMING = {
    "executive": "For leadership: focus on the decision, the validation gate, the headline risk, and confidence.",
    "brand_team": "For Brand: positioning, claim credibility, the lead message, and the beachhead segment.",
    "trade_sales": "For Trade/Sales: channel fit, trial drivers, promo/sampling, retailer objections, and the sell-in story.",
    "rd_product": "For R&D/Product: sensory/taste risk, the repeat constraint, and claim substantiation.",
    "consumer_insight": "For Consumer Insight: open assumptions, validation questions, methods, and confidence gaps.",
}

_AUDIENCE_PRIORITY = {
    "executive": "Make a confident go / validate / hold decision and set the next investment gate.",
    "brand_team": "Sharpen positioning and the claim, and lead with the strongest segment.",
    "trade_sales": "Win trial and distribution — nail channel fit, promo/sampling and the retailer story.",
    "rd_product": "De-risk the product experience: taste acceptance, repeat, and claim proof.",
    "consumer_insight": "Close the biggest knowledge gaps with the right research before launch.",
}


# --- intent classifier ------------------------------------------------------

_INTENTS: list[tuple[str, tuple[str, ...]]] = [
    ("one_page_summary", ("one page", "one-page", "1-page", "board summary", "board-summary", "slide")),
    ("brand_team_actions", ("brand team", "brand should", "positioning", "what should brand", "message angle")),
    ("trade_sales_actions", ("trade", "sales", "retailer", "channel", "promo", "sampling", "distribution")),
    ("rd_product_actions", ("r&d", "rnd", "product team", "sensory", "formulation", "reformulate", "taste")),
    ("consumer_insight_actions", ("consumer insight", "research", "validate assumption", "insight team", "survey plan")),
    ("leadership_risks", ("leadership", "board care", "biggest risk", "what risks", "risks should", "risk care")),
    ("evidence_for_recommendation", ("evidence", "proof", "supports", "support the recommendation", "back this up")),
    ("validate_before_launch", ("validate before", "before launch", "before we launch", "what to validate", "validation plan", "what should we validate")),
    ("explain_recommendation_status", ("recommendation", "status", "why is", "why should", "ready to move", "move forward", "hold")),
    ("summarize_for_executive", ("simpler", "simple", "executive", "plain language", "explain this briefing", "summari", "tl;dr")),
    ("limitations_and_caveats", ("limitation", "caveat", "overclaim", "not prove", "careful", "what not to")),
]


def classify_intent(question: str) -> str:
    q = question.lower()
    for intent, kws in _INTENTS:
        if any(k in q for k in kws):
            return intent
    return "general_briefing_question"


# --- helpers ----------------------------------------------------------------


def _evidence(p: BriefingPayload, limit: int) -> list[EvidenceRef]:
    out: list[EvidenceRef] = []
    seen: set[str] = set()
    for ev in list(p.evidence_pack.event_evidence) + [e for f in p.top_findings for e in f.supporting_evidence]:
        if ev.event_id in seen:
            continue
        seen.add(ev.event_id)
        out.append(ev)
        if len(out) >= limit:
            break
    return out


def _actions_for(p: BriefingPayload, audience: str) -> list[str]:
    owners = _OWNERS.get(audience, set())
    role = [a.action for a in p.next_best_actions if a.owner_team in owners]
    return role or [a.action for a in p.next_best_actions[:3]]


def _load(db: Session, project_id: str) -> BriefingPayload:
    if report_service.get_report_row(db, project_id) is None:
        raise ValueError("report_required")
    doc = briefing_service.get_briefing_row(db, project_id)
    if doc is None:
        raise ValueError("briefing_required")
    return briefing_service.get_payload(doc)


# --- Q&A builders -----------------------------------------------------------


def _ans(p: BriefingPayload, direct: str, audience: str, *, actions: list[str] | None = None,
         risks: list[str] | None = None, follow: list[str] | None = None, ev: list[EvidenceRef] | None = None) -> BriefingAnswer:
    return BriefingAnswer(
        direct_answer=direct,
        audience_framing=_FRAMING.get(audience, _FRAMING["executive"]),
        supporting_evidence=ev or [],
        related_next_actions=actions or [a.action for a in p.next_best_actions[:3]],
        related_risks=risks or [r.risk_title for r in p.biggest_risks[:3]],
        confidence_score=_CONF.get(p.briefing_header.confidence_label, 0.5),
        limitations=p.limitations[:3],
        recommended_follow_up=follow or ["What should we not overclaim?", "What evidence supports this?"],
    )


def _answer(p: BriefingPayload, intent: str, payload_in: BriefingAskIn) -> BriefingAnswer:
    h = p.briefing_header
    dr = p.decision_recommendation
    aud = payload_in.audience
    ev = _evidence(p, payload_in.max_evidence_items) if payload_in.include_evidence else []

    if intent == "explain_recommendation_status":
        direct = (
            f"The status is '{h.recommendation_status.replace('_', ' ')}' because the concept scores "
            f"{h.overall_score}/100 with {h.confidence_label} confidence. {dr.rationale} {dr.recommended_decision}"
        )
        return _ans(p, direct, aud, ev=ev, follow=["What must be true before launch?", "What evidence supports this?"])
    if intent == "summarize_for_executive":
        direct = (
            f"In plain terms: {p.situation.one_paragraph_context} Bottom line: {dr.recommended_decision} "
            f"(score {h.overall_score}/100, {h.confidence_label} confidence)."
        )
        return _ans(p, direct, "executive", ev=ev)
    if intent in ("brand_team_actions", "trade_sales_actions", "rd_product_actions", "consumer_insight_actions"):
        role = intent.replace("_actions", "")
        acts = _actions_for(p, role)
        direct = f"{_AUDIENCE_PRIORITY.get(role, '')} Priorities: " + "; ".join(acts[:3]) + "."
        return _ans(p, direct, role, actions=acts, ev=ev)
    if intent == "leadership_risks":
        risks = [f"{r.risk_title} ({r.severity}): {r.why_it_matters}" for r in p.biggest_risks[:3]]
        direct = "Risks leadership should weigh: " + " | ".join(risks) + f" {' '.join(dr.decision_caveats)}"
        return _ans(p, direct, "executive", risks=[r.risk_title for r in p.biggest_risks[:3]], ev=ev)
    if intent == "evidence_for_recommendation":
        sc_ev = "; ".join(p.evidence_pack.scorecard_evidence[:4])
        direct = (
            f"The recommendation rests on: {sc_ev}. Top finding: {p.top_findings[0].finding_title if p.top_findings else 'n/a'}. "
            f"Referenced reactions are linked as evidence."
        )
        return _ans(p, direct, aud, ev=ev, follow=["Which segment drives this?", "What should we validate?"])
    if intent == "validate_before_launch":
        conds = dr.conditions_before_launch
        vp = [v.question for v in p.validation_plan[:3]]
        direct = "Before launch, validate: " + "; ".join(conds) + ". Suggested studies: " + "; ".join(vp) + "."
        return _ans(p, direct, "consumer_insight", actions=conds, ev=ev)
    if intent == "one_page_summary":
        direct = (
            f"One line: {dr.recommended_decision} Concept {h.overall_score}/100, {h.confidence_label} confidence. "
            "Use the Board Summary for a printable one-pager."
        )
        return _ans(p, direct, aud, ev=ev, follow=["Generate the board summary."])
    if intent == "limitations_and_caveats":
        direct = "Do not overclaim: " + " ".join(p.limitations[:4])
        return _ans(p, direct, aud, ev=[], follow=["What would raise confidence?"])
    # general
    direct = f"{p.situation.one_paragraph_context} {dr.recommended_decision}"
    return _ans(p, direct, aud, ev=ev)


# --- optional LLM polish ----------------------------------------------------

_LLM_SYSTEM = (
    "You are an FMCG insights lead. Rewrite the provided text to be clearer for the stated audience. "
    "Rewrite only using the provided payload. Do not add new claims, metrics, risks, or recommendations. "
    "Return strict JSON: {\"text\": \"...\"}."
)


def _maybe_llm(text: str, use_llm: bool, llm_client: LLMClient | None) -> tuple[str, str]:
    if not use_llm:
        return text, "deterministic"
    client = llm_client or LLMClient()
    if not client.configured:
        return text, "deterministic"
    try:
        data = client.chat_json(_LLM_SYSTEM, json.dumps({"text": text}))
        new = data.get("text")
        if isinstance(new, str) and new.strip():
            return new.strip(), "llm_enhanced"
    except Exception as e:  # noqa: BLE001
        logger.warning("Briefing-Q&A LLM rewrite failed; using deterministic. error=%s", e)
    return text, "deterministic"


# --- public: ask ------------------------------------------------------------


def ask(db: Session, project_id: str, payload: BriefingAskIn, llm_client: LLMClient | None = None) -> BriefingAskOut:
    p = _load(db, project_id)
    intent = classify_intent(payload.question)
    answer = _answer(p, intent, payload)
    new_direct, source_mode = _maybe_llm(answer.direct_answer, payload.use_llm_rewrite, llm_client)
    answer.direct_answer = new_direct
    return BriefingAskOut(project_id=project_id, question=payload.question, intent=intent, answer=answer, source_mode=source_mode)


# --- public: audience tailoring ---------------------------------------------


def _tailored_payload(p: BriefingPayload, audience: str) -> TailoredPayload:
    h = p.briefing_header
    dr = p.decision_recommendation
    owners = _OWNERS.get(audience, set())
    role_actions = [a.action for a in p.next_best_actions if a.owner_team in owners] or [a.action for a in p.next_best_actions[:3]]

    needs: dict[str, list[str]] = {
        "executive": [
            f"Recommendation: {dr.recommended_decision}",
            f"Overall {h.overall_score}/100, {h.confidence_label} confidence.",
            f"Headline risk: {p.biggest_risks[0].risk_title if p.biggest_risks else 'n/a'}.",
            "Next gate: validate the key risks before further investment.",
        ],
        "brand_team": [
            f"Lead segment: {p.top_findings[0].affected_segments[0] if p.top_findings and p.top_findings[0].affected_segments else 'beachhead'}.",
            "Claim credibility is a gating dimension — substantiate the riskiest claim.",
            f"Top trigger to anchor creative: {p.top_findings[1].finding_title if len(p.top_findings) > 1 else 'lead benefit'}.",
        ],
        "trade_sales": [
            "Trial and distribution are the priority — secure visibility before scaling media.",
            "Pair launch with a sampling/promo mechanic rather than a permanent price cut.",
            f"Watch retailer objections tied to: {p.biggest_risks[0].risk_title if p.biggest_risks else 'price/value'}.",
        ],
        "rd_product": [
            "Repeat is the tightest constraint — protect it with sensory proof.",
            "Validate taste acceptance before scaling.",
            "Substantiate the claim with a concrete reason-to-believe.",
        ],
        "consumer_insight": [
            "Several assumptions remain open — design validation around them.",
            f"Confidence is {h.confidence_label}; close the largest data gaps first.",
            "Pre-register success metrics for each validation study.",
        ],
    }
    return TailoredPayload(
        headline=f"[{audience.replace('_', ' ').title()}] {dr.recommended_decision} (score {h.overall_score}/100, {h.confidence_label} confidence)",
        audience_priority=_AUDIENCE_PRIORITY.get(audience, _AUDIENCE_PRIORITY["executive"]),
        what_this_audience_needs_to_know=needs.get(audience, needs["executive"]),
        role_specific_risks=[f"{r.risk_title} ({r.severity})" for r in p.biggest_risks[:3]],
        role_specific_actions=role_actions[:4],
        evidence_to_show=p.evidence_pack.scorecard_evidence[:3] + p.evidence_pack.segment_evidence[:2],
        what_not_to_overclaim=p.limitations[:3],
        talk_track=[
            _FRAMING.get(audience, _FRAMING["executive"]),
            f"Decision point: {p.situation.current_decision_point}",
            "Frame as exploratory decision support — validate with real research.",
        ],
    )


def _tailor_markdown(t: TailoredPayload, audience: str, tone: str) -> str:
    lines = [
        f"# Briefing — {audience.replace('_', ' ').title()} ({tone})",
        f"**{t.headline}**",
        "", f"_Priority: {t.audience_priority}_", "",
        "## What this audience needs to know",
    ]
    lines += [f"- {x}" for x in t.what_this_audience_needs_to_know]
    lines += ["", "## Role-specific risks"] + [f"- {x}" for x in t.role_specific_risks]
    lines += ["", "## Role-specific actions"] + [f"- {x}" for x in t.role_specific_actions]
    lines += ["", "## Evidence to show"] + [f"- {x}" for x in t.evidence_to_show]
    lines += ["", "## What not to overclaim"] + [f"- {x}" for x in t.what_not_to_overclaim]
    lines += ["", "## Talk track"] + [f"- {x}" for x in t.talk_track]
    lines += ["", "> Exploratory decision support — framing changed for the audience; the underlying findings are unchanged."]
    return "\n".join(lines)


def tailor(db: Session, project_id: str, params: TailorIn, llm_client: LLMClient | None = None) -> TailorOut:
    p = _load(db, project_id)
    tp = _tailored_payload(p, params.audience)
    md = _tailor_markdown(tp, params.audience, params.tone)
    md, source_mode = _maybe_llm(md, params.use_llm_rewrite, llm_client)
    # persist as artifact (replace prior of same type+audience)
    _save_artifact(db, project_id, "tailored_briefing", params.audience, params.tone, tp.model_dump_json(), md, source_mode)
    return TailorOut(project_id=project_id, audience=params.audience, tone=params.tone, tailored_payload=tp, markdown=md, source_mode=source_mode)


# --- public: board summary --------------------------------------------------


def _board_payload(p: BriefingPayload) -> BoardSummaryPayload:
    h = p.briefing_header
    dr = p.decision_recommendation
    findings = [f"{f.finding_title} ({f.supporting_metric})" for f in p.top_findings[:3]]
    risks = [f"{r.risk_title} ({r.severity})" for r in p.biggest_risks[:3]]
    actions = [f"[{a.priority}] {a.action} — {a.owner_team}" for a in p.next_best_actions[:3]]
    validation = [v.question for v in p.validation_plan[:3]]
    gate = dr.conditions_before_launch[0] if dr.conditions_before_launch else "Validate the headline risk before further investment."
    return BoardSummaryPayload(
        headline_recommendation=dr.recommended_decision,
        decision_status=h.recommendation_status,
        one_sentence_concept=p.situation.concept_summary,
        three_key_findings=findings,
        top_three_risks=risks,
        decision_gate=gate,
        next_three_actions=actions,
        validation_needed=validation,
        confidence_and_caveat=f"Confidence {h.confidence_label} ({h.overall_score}/100). Exploratory decision support, not a validated forecast.",
        evidence_refs=[f"{e.action_type} · R{e.round_number}" for e in p.evidence_pack.event_evidence[:4]],
    )


def _board_markdown(s: BoardSummaryPayload) -> str:
    return "\n".join([
        "# Board Summary — One Page",
        f"**Recommendation: {s.headline_recommendation}** _(status: {s.decision_status.replace('_', ' ')})_",
        f"Concept: {s.one_sentence_concept}",
        "", "## 3 Key Findings", *[f"- {x}" for x in s.three_key_findings],
        "", "## Top 3 Risks", *[f"- {x}" for x in s.top_three_risks],
        "", f"## Decision Gate\n{s.decision_gate}",
        "", "## Next 3 Actions", *[f"- {x}" for x in s.next_three_actions],
        "", "## Validation Needed", *[f"- {x}" for x in s.validation_needed],
        "", f"_{s.confidence_and_caveat}_",
    ])


def _save_artifact(db: Session, project_id: str, artifact_type: str, audience: str, tone: str, payload_json: str, markdown: str, source_mode: str) -> BriefingArtifact:
    for existing in db.execute(
        select(BriefingArtifact).where(BriefingArtifact.project_id == project_id, BriefingArtifact.artifact_type == artifact_type)
    ).scalars().all():
        db.delete(existing)
    art = BriefingArtifact(
        project_id=project_id, artifact_type=artifact_type, audience=audience, tone=tone,
        payload_json=payload_json, markdown=markdown, source_mode=source_mode,
    )
    db.add(art)
    db.commit()
    db.refresh(art)
    return art


def generate_board_summary(db: Session, project_id: str, params: BoardSummaryIn, llm_client: LLMClient | None = None) -> BoardSummaryOut:
    p = _load(db, project_id)
    sp = _board_payload(p)
    md = _board_markdown(sp)
    md, source_mode = _maybe_llm(md, params.use_llm_rewrite, llm_client)
    _save_artifact(db, project_id, "board_summary", "", params.tone, sp.model_dump_json(), md, source_mode)
    return BoardSummaryOut(project_id=project_id, summary_payload=sp, markdown=md, source_mode=source_mode)


def get_board_summary(db: Session, project_id: str) -> BoardSummaryOut:
    art = db.execute(
        select(BriefingArtifact).where(BriefingArtifact.project_id == project_id, BriefingArtifact.artifact_type == "board_summary").order_by(BriefingArtifact.updated_at.desc())
    ).scalars().first()
    if art is None:
        raise ValueError("board_summary_required")
    return BoardSummaryOut(
        project_id=project_id,
        summary_payload=BoardSummaryPayload.model_validate(json.loads(art.payload_json or "{}")),
        markdown=art.markdown,
        source_mode=art.source_mode,
    )
