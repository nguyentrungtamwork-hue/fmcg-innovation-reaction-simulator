"""Executive narrative briefing (Phase 14).

Assembles a concise, evidence-grounded launch briefing entirely from data the
system already produced — report payload + scorecard + confidence + assumptions
(+ optional snapshot diff / decision timeline). Deterministic and offline by
default; an optional LLM pass may polish prose only and never invents findings.

No core scoring formula is changed. Recommendation-status logic is documented in
docs/SCORING_LOGIC.md.

Preconditions (ValueError → mapped by the endpoint):
    events_required | report_required | scorecard_required
"""
from __future__ import annotations

import json
import logging
import re

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import BriefingDoc, Event, Project, ScenarioRun
from app.schemas.briefing import (
    BriefingGenerateIn,
    BriefingHeader,
    BriefingPayload,
    BriefingRisk,
    BriefingSummary,
    DecisionRecommendation,
    EvidencePack,
    Finding,
    NextBestAction,
    ReadinessAssessment,
    Situation,
    ValidationItem,
    WhatChangedRecently,
)
from app.schemas.history import DiffRequest, DiffSide
from app.schemas.report import EvidenceRef, ReportPayload
from app.services import (
    app_log_service,
    assumptions_service,
    confidence_service,
    diff_service,
    report_service,
    scorecard_service,
    snapshot_service,
    timeline_service,
)
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_LIMITATIONS = [
    "This briefing is exploratory decision support, not a guaranteed market forecast.",
    "Reactions come from a deterministic simulation, not fitted to historical launch outcomes.",
    "No real sales / scan / POS data informs the analysis.",
    "No real social-listening data informs diffusion or WOM signals.",
    "Consumer 'interviews' are simulated personas, not real people.",
    "Confidence is a heuristic data-coverage score, not external validation.",
    "Real consumer validation (surveys, sensory tests, in-market A/B tests) is required before launch decisions.",
]


# --- small helpers ----------------------------------------------------------


def _owner_for(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("taste", "sensory", "formula", "ingredient", "reformulat")):
        return "R&D"
    if any(k in t for k in ("price", "promo", "promotion", "value-per", "bogo")):
        return "Trade Marketing"
    if any(k in t for k in ("shelf", "facing", "findability", "retail", "distribution")):
        return "Trade Marketing"
    if any(k in t for k in ("claim", "rtb", "reason to believe", "credib", "message", "positioning")):
        return "Brand"
    if any(k in t for k in ("kol", "koc", "creator", "tiktok", "media", "awareness")):
        return "Media"
    if any(k in t for k in ("creative", "content", "asset")):
        return "Creative"
    if any(k in t for k in ("e-commerce", "ecommerce", "pdp", "cart", "online")):
        return "E-commerce"
    if any(k in t for k in ("survey", "test", "validate", "research", "panel", "focus group")):
        return "Consumer Insight"
    return "Brand"


def _method_for(text: str) -> str:
    t = text.lower()
    if any(k in t for k in ("taste", "sensory", "medicinal", "flavour", "flavor")):
        return "sensory test"
    if any(k in t for k in ("price", "promo", "value")):
        return "e-commerce A/B test"
    if any(k in t for k in ("shelf", "retail", "findability", "distribution")):
        return "retail pilot"
    if any(k in t for k in ("claim", "credib", "believe", "message")):
        return "survey"
    if any(k in t for k in ("social", "wom", "advoc", "share")):
        return "social listening"
    if any(k in t for k in ("trial", "sampling", "try")):
        return "sampling booth"
    return "focus group"


def _dedup_key(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", "", text.lower())[:45]


def _refs(items, limit: int) -> list[EvidenceRef]:
    out: list[EvidenceRef] = []
    seen: set[str] = set()
    for it in items:
        for ev in it.evidence_events:
            if ev.event_id in seen:
                continue
            seen.add(ev.event_id)
            out.append(ev)
            if len(out) >= limit:
                return out
    return out


# --- recommendation status --------------------------------------------------


def decide_recommendation_status(sc) -> str:
    overall = sc.overall_score
    conf = sc.confidence_label
    risk = sc.risk_score
    repeat = sc.repeat_potential_score
    claim = sc.claim_credibility_score
    trial = sc.trial_potential_score
    assumption_risk = sc.assumption_risk_score

    if overall < 35 or (risk >= 70 and conf == "low") or (trial < 25 and overall < 45):
        return "hold"
    if risk >= 65 or claim < 40 or (repeat < 20 and assumption_risk >= 70):
        return "revise_and_retest"
    if overall >= 60 and conf in ("medium", "high") and risk < 60 and repeat >= 35:
        return "move_forward"
    return "validate_before_move_forward"


_STATUS_DECISION = {
    "move_forward": "Move forward to consumer validation / pilot.",
    "validate_before_move_forward": "Validate the key risks before moving forward.",
    "revise_and_retest": "Revise the concept and re-test before progressing.",
    "hold": "Hold — the concept is not ready without significant rework.",
}


# --- builders ---------------------------------------------------------------


def _situation(project: Project, rp: ReportPayload, ont, status: str) -> Situation:
    es = rp.executive_summary
    brand = next((e.name for e in ont.entities if e.type == "Brand"), None)
    category = next((e.name for e in ont.entities if e.type in ("Category", "SubCategory")), None)
    market = next((e.name for e in ont.entities if e.type == "RetailEnvironment"), None)
    ctx_bits = [b for b in (brand, category) if b]
    cat_ctx = (
        f"{' · '.join(ctx_bits)}" + (f" in {market}" if market else "")
        if ctx_bits
        else "FMCG innovation launch"
    )
    return Situation(
        one_paragraph_context=(
            f"{es.overall_market_reaction} The biggest opportunity is {es.top_opportunity} "
            f"The biggest risk is {es.top_risk}"
        ),
        category_or_market_context=cat_ctx,
        concept_summary=f"{project.name}: {es.estimated_trial_potential} {es.estimated_repeat_potential}",
        current_decision_point=_STATUS_DECISION[status],
    )


def _top_findings(rp: ReportPayload, sc, include_evidence: bool) -> list[Finding]:
    findings: list[Finding] = []
    segs = rp.segment_reaction_map
    if segs:
        top = segs[0]
        findings.append(
            Finding(
                finding_title=f"{top.segment_name} is the strongest beachhead",
                explanation=f"It leads on simulated trial probability ({top.average_trial_probability}).",
                supporting_metric=f"trial {top.average_trial_probability}, intent {top.average_purchase_intent_score}",
                supporting_evidence=_refs(rp.purchase_trigger_analysis[:1], 2) if include_evidence else [],
                affected_segments=[top.segment_name],
                confidence_level=sc.confidence_label,
                business_implication=top.recommended_message_angle,
            )
        )
    if rp.purchase_trigger_analysis:
        t = rp.purchase_trigger_analysis[0]
        findings.append(
            Finding(
                finding_title=f"Lead trigger: {t.trigger}",
                explanation=t.strategic_implication,
                supporting_metric=f"detected ×{t.frequency}",
                supporting_evidence=_refs([t], 2) if include_evidence else [],
                affected_segments=t.affected_segments,
                confidence_level=sc.confidence_label,
                business_implication="Anchor creative and the converting touchpoint on this trigger.",
            )
        )
    f = rp.trial_repeat_forecast
    findings.append(
        Finding(
            finding_title="Repeat is the tightest funnel constraint",
            explanation=f"{f.likely_repeaters} {f.one_time_trial_risk}",
            supporting_metric=f"repeat potential {sc.repeat_potential_score}/100",
            supporting_evidence=_refs(rp.adoption_barrier_analysis[:1], 2) if include_evidence else [],
            affected_segments=[s.segment_name for s in segs[:2]],
            confidence_level=sc.confidence_label,
            business_implication="Trial without repeat is one-and-done; protect repeat with sampling/sensory proof.",
        )
    )
    return findings


def _biggest_risks(rp: ReportPayload, include_evidence: bool) -> list[BriefingRisk]:
    risks: list[BriefingRisk] = []
    for b in rp.adoption_barrier_analysis[:2]:
        risks.append(
            BriefingRisk(
                risk_title=b.barrier,
                severity=b.severity_level,
                why_it_matters=f"Detected ×{b.frequency}; blocks adoption in {', '.join(b.affected_segments) or 'multiple segments'}.",
                affected_segments=b.affected_segments,
                supporting_evidence=_refs([b], 2) if include_evidence else [],
                mitigation=b.recommended_fix,
            )
        )
    for r in rp.innovation_risk_matrix:
        if r.severity.lower() == "high" and len(risks) < 4:
            risks.append(
                BriefingRisk(
                    risk_title=r.risk_type,
                    severity=r.severity,
                    why_it_matters=r.evidence,
                    affected_segments=r.affected_segments,
                    supporting_evidence=[],
                    mitigation=r.mitigation,
                )
            )
    return risks


def _readiness_assessment(sc, status: str) -> ReadinessAssessment:
    return ReadinessAssessment(
        trial_readiness=_rd(sc.trial_potential_score, 35, 55),
        repeat_readiness=_rd(sc.repeat_potential_score, 20, 40),
        claim_readiness=_rd(sc.claim_credibility_score, 40, 60),
        channel_readiness=_rd(sc.channel_fit_score, 45, 60),
        confidence_readiness="ready" if sc.confidence_label == "high" else "caution" if sc.confidence_label == "medium" else "not_ready",
        overall_readiness={"move_forward": "ready", "validate_before_move_forward": "caution", "revise_and_retest": "not_ready", "hold": "not_ready"}[status],
        readiness_reasoning=(
            f"Trial {sc.trial_potential_score:.0f}/100, repeat {sc.repeat_potential_score:.0f}/100, "
            f"claim credibility {sc.claim_credibility_score:.0f}/100, risk {sc.risk_score:.0f}/100, "
            f"confidence {sc.confidence_label}."
        ),
    )


def _rd(score: float, caution_below: float, ready_at: float) -> str:
    if score >= ready_at:
        return "ready"
    if score >= caution_below:
        return "caution"
    return "not_ready"


def _what_changed(db: Session, project_id: str, project_name: str, include_history: bool) -> WhatChangedRecently:
    snaps = snapshot_service.list_snapshots(db, project_id)
    if not include_history or not snaps:
        return WhatChangedRecently(
            has_history=False,
            latest_snapshot_comparison="No prior snapshot exists yet — this is the first recorded version.",
            scorecard_drift="n/a",
            changed_recommendation="n/a",
            major_timeline_events=[],
        )
    latest = snaps[0]
    try:
        d = diff_service.diff(
            db, project_id, project_name,
            DiffRequest(left=DiffSide(type="snapshot", snapshot_id=latest.id), right=DiffSide(type="active_report")),
        )
        drift = f"overall {d.scorecard_delta['overall_score'].delta:+.1f} vs '{latest.snapshot_name}'"
        rec = d.recommendation_changes.interpretation
        summary = d.plain_english_summary
    except ValueError:
        drift, rec, summary = "n/a", "n/a", f"Compared against snapshot '{latest.snapshot_name}'."
    tl = timeline_service.build_timeline(db, db.get(Project, project_id))
    events = [f"{t.title} ({t.timestamp:%Y-%m-%d})" for t in tl.timeline[-5:]]
    return WhatChangedRecently(
        has_history=True,
        latest_snapshot_comparison=summary,
        scorecard_drift=drift,
        changed_recommendation=rec,
        major_timeline_events=events,
    )


def _decision_recommendation(sc, status: str, rp: ReportPayload) -> DecisionRecommendation:
    conditions: list[str] = []
    if sc.claim_credibility_score < 60:
        conditions.append("Substantiate and validate the riskiest claim before launch.")
    if sc.repeat_potential_score < 40:
        conditions.append("Confirm repeat via a sensory/taste test with real consumers.")
    if sc.price_value_score < 55:
        conditions.append("Validate price/value (sampling or promo mechanic) before committing pricing.")
    if not conditions:
        conditions.append("Confirm the headline findings with a quick concept test in the beachhead segment.")
    return DecisionRecommendation(
        recommended_decision=_STATUS_DECISION[status],
        rationale=(
            f"Heuristic scorecard {sc.overall_score:.1f}/100 with {sc.confidence_label} confidence; "
            f"risk {sc.risk_score:.0f}/100, repeat {sc.repeat_potential_score:.0f}/100."
        ),
        conditions_before_launch=conditions,
        decision_caveats=[
            "Scores are simulated decision-support, not validated demand.",
            "Confidence is capped because no real market data informs the model.",
        ],
    )


def _next_best_actions(rp: ReportPayload, sc, confidence, assumptions, include: bool) -> list[NextBestAction]:
    if not include:
        return []
    candidates: list[tuple[int, NextBestAction]] = []
    seen: set[str] = set()

    def _add(rank: int, action: str, owner: str, effort: str, impact: str, basis: str, timing: str, method: str):
        key = _dedup_key(action)
        if not action.strip() or key in seen:
            return
        seen.add(key)
        candidates.append((rank, NextBestAction(
            priority="", action=action, owner_team=owner, effort=effort, expected_impact=impact,
            evidence_basis=basis, suggested_timing=timing, validation_method=method,
        )))

    # 1) high/medium barriers
    for b in rp.adoption_barrier_analysis[:3]:
        sev = b.severity_level.lower()
        rank = 0 if sev == "high" else 1
        segs = ", ".join(b.affected_segments) or "key segments"
        _add(
            rank,
            f"Address '{b.barrier}' for {segs}: {b.recommended_fix}",
            _owner_for(b.barrier + " " + b.recommended_fix),
            "medium",
            "Unblocks adoption / protects trial-to-repeat conversion.",
            f"Barrier detected ×{b.frequency} in the event log.",
            "Before launch",
            _method_for(b.barrier),
        )

    # 2) report strategic recommendations
    for r in rp.strategic_recommendations[:4]:
        rank = 0 if r.priority.upper().startswith("P0") else 1 if r.priority.upper().startswith("P1") else 2
        _add(
            rank, r.recommendation, r.owner_team if r.owner_team else _owner_for(r.recommendation),
            "medium", r.expected_impact, r.supporting_evidence, "Pre-launch", _method_for(r.recommendation),
        )

    # 3) weakest scorecard dimension -> test first
    dims = {
        "repeat": sc.repeat_potential_score,
        "claim credibility": sc.claim_credibility_score,
        "price/value": sc.price_value_score,
        "trial": sc.trial_potential_score,
    }
    weakest = min(dims, key=dims.get)
    _add(
        0,
        f"Run a targeted test of the weakest dimension ('{weakest}', {dims[weakest]:.0f}/100) with the beachhead segment.",
        "Consumer Insight", "medium",
        "Closes the largest gap to a confident launch decision.",
        f"Scorecard: {weakest} = {dims[weakest]:.0f}/100.",
        "Next sprint", _method_for(weakest),
    )

    # 4) confidence improvement
    for imp in confidence.how_to_improve_confidence[:2]:
        _add(1, imp, "Consumer Insight", "low", "Raises decision confidence.", "Confidence calibration.", "Next sprint", _method_for(imp))

    # 5) top high-impact assumption
    for a in assumptions.assumptions:
        if a.impact == "high":
            _add(1, f"Validate assumption: {a.assumption}", "Consumer Insight", "low", "Reduces assumption risk.", a.source, "Before launch", "survey")
            break

    candidates.sort(key=lambda x: x[0])
    out: list[NextBestAction] = []
    for rank, action in candidates[:10]:
        action.priority = "P0" if rank == 0 else "P1" if rank == 1 else "P2"
        out.append(action)
    return out[:10] if len(out) >= 5 else out


def _validation_plan(rp: ReportPayload) -> list[ValidationItem]:
    out: list[ValidationItem] = []
    for i, q in enumerate(rp.human_validation_questions[:6]):
        out.append(
            ValidationItem(
                question=q,
                recommended_method=_method_for(q),
                success_metric="Pre-registered threshold met vs control / norm.",
                priority="P0" if i < 2 else "P1",
            )
        )
    if not out:
        out.append(ValidationItem(question="Validate taste acceptance and repeat intent.", recommended_method="sensory test", success_metric="≥ category norm repeat intent.", priority="P0"))
    return out


def _evidence_pack(db, project_id, rp, sc, assumptions, include_history) -> EvidencePack:
    ev = _refs(list(rp.purchase_trigger_analysis) + list(rp.adoption_barrier_analysis), 6)
    seg_ev = [
        f"{s.segment_name}: trial {s.average_trial_probability}, repeat {s.average_repeat_probability}"
        for s in rp.segment_reaction_map[:3]
    ]
    sc_ev = [
        f"Overall {sc.overall_score}/100", f"Trial {sc.trial_potential_score}/100",
        f"Repeat {sc.repeat_potential_score}/100", f"Risk {sc.risk_score}/100",
        f"Confidence {sc.confidence_score:.2f} ({sc.confidence_label})",
    ]
    asm_ev = [a.assumption for a in assumptions.assumptions if a.impact == "high"][:3]
    scenarios = db.execute(select(ScenarioRun).where(ScenarioRun.project_id == project_id)).scalars().all()
    scen_ev = [f"Scenario: {s.scenario_name}" for s in scenarios] or ["No scenarios/sensitivity runs recorded yet."]
    hist_ev: list[str] = []
    if include_history:
        snaps = snapshot_service.list_snapshots(db, project_id)
        hist_ev = [f"Snapshot: {s.snapshot_name} ({s.created_at:%Y-%m-%d})" for s in snaps[:3]]
    return EvidencePack(
        event_evidence=ev,
        segment_evidence=seg_ev,
        scorecard_evidence=sc_ev,
        assumption_evidence=asm_ev,
        scenario_or_sensitivity_evidence=scen_ev,
        decision_history_evidence=hist_ev or ["No decision history recorded yet."],
    )


# --- assembly ---------------------------------------------------------------


def _load(db: Session, project_id: str):
    from app.services import ontology_service
    from app.schemas.ontology import OntologyPayload

    events = db.execute(
        select(func.count(Event.id)).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalar_one()
    if not events:
        raise ValueError("events_required")
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise ValueError("report_required")
    rp = report_service.get_payload(report)
    project = db.get(Project, project_id)
    try:
        sc = scorecard_service.build_for_project(db, project_id, project.name)
    except ValueError:
        raise ValueError("scorecard_required")
    conf = confidence_service.compute(db, project_id)
    assumptions = assumptions_service.build(db, project_id)
    ont_row = ontology_service.get_ontology(db, project_id)
    ont = OntologyPayload.model_validate(json.loads(ont_row.data_json or "{}")) if ont_row else OntologyPayload()
    return project, rp, sc, conf, assumptions, ont


def build_payload(db: Session, project_id: str, params: BriefingGenerateIn) -> BriefingPayload:
    from datetime import datetime, timezone

    project, rp, sc, conf, assumptions, ont = _load(db, project_id)
    status = decide_recommendation_status(sc)
    product_name = next((e.name for e in ont.entities if e.type == "ProductInnovation"), project.name)

    header = BriefingHeader(
        project_name=project.name,
        product_or_concept_name=product_name,
        generated_at=datetime.now(timezone.utc),
        audience=params.audience,
        confidence_label=sc.confidence_label,
        overall_score=sc.overall_score,
        recommendation_status=status,
    )
    return BriefingPayload(
        briefing_header=header,
        situation=_situation(project, rp, ont, status),
        top_findings=_top_findings(rp, sc, params.include_evidence),
        biggest_risks=_biggest_risks(rp, params.include_evidence),
        readiness_assessment=_readiness_assessment(sc, status),
        what_changed_recently=_what_changed(db, project_id, project.name, params.include_decision_history),
        decision_recommendation=_decision_recommendation(sc, status, rp),
        next_best_actions=_next_best_actions(rp, sc, conf, assumptions, params.include_next_actions),
        validation_plan=_validation_plan(rp),
        evidence_pack=_evidence_pack(db, project_id, rp, sc, assumptions, params.include_decision_history),
        limitations=_LIMITATIONS,
    )


# --- markdown ---------------------------------------------------------------


def render_markdown(p: BriefingPayload) -> str:
    h = p.briefing_header
    lines = [
        "# Executive Launch Briefing",
        f"_{h.project_name} · {h.product_or_concept_name} · audience: {h.audience} · {h.generated_at:%Y-%m-%d}_",
        "",
        "## Recommendation",
        f"**{h.recommendation_status.replace('_', ' ').title()}** — {p.decision_recommendation.recommended_decision}",
        f"Overall score {h.overall_score}/100 · confidence {h.confidence_label}.",
        f"{p.decision_recommendation.rationale}",
        "",
        "## Situation",
        p.situation.one_paragraph_context,
        f"Context: {p.situation.category_or_market_context}. {p.situation.concept_summary}",
        f"Decision point: {p.situation.current_decision_point}",
        "",
        "## Top Findings",
    ]
    for f in p.top_findings:
        lines.append(f"- **{f.finding_title}** — {f.explanation} ({f.supporting_metric}). {f.business_implication}")
    lines += ["", "## Biggest Risks"]
    for r in p.biggest_risks:
        lines.append(f"- **{r.risk_title}** ({r.severity}) — {r.why_it_matters} _Mitigation:_ {r.mitigation}")
    ra = p.readiness_assessment
    lines += [
        "", "## Readiness Assessment",
        f"- Trial: {ra.trial_readiness} | Repeat: {ra.repeat_readiness} | Claim: {ra.claim_readiness} | Channel: {ra.channel_readiness} | Confidence: {ra.confidence_readiness}",
        f"- **Overall readiness: {ra.overall_readiness}** — {ra.readiness_reasoning}",
        "", "## What Changed Recently",
    ]
    wc = p.what_changed_recently
    if wc.has_history:
        lines += [f"- {wc.latest_snapshot_comparison}", f"- Drift: {wc.scorecard_drift}", f"- {wc.changed_recommendation}"]
        lines += [f"- {e}" for e in wc.major_timeline_events]
    else:
        lines.append(f"- {wc.latest_snapshot_comparison}")
    lines += ["", "## Decision Recommendation", f"{p.decision_recommendation.recommended_decision}", "", "Conditions before launch:"]
    lines += [f"- {c}" for c in p.decision_recommendation.conditions_before_launch]
    lines += ["", "## Next Best Actions"]
    for a in p.next_best_actions:
        lines.append(f"- [{a.priority}] **{a.action}** _(owner: {a.owner_team}, effort: {a.effort}, validate via {a.validation_method})_")
    lines += ["", "## Validation Plan"]
    for v in p.validation_plan:
        lines.append(f"- [{v.priority}] {v.question} → {v.recommended_method} (success: {v.success_metric})")
    lines += ["", "## Evidence Pack"]
    lines += [f"- {s}" for s in p.evidence_pack.scorecard_evidence]
    lines += [f"- Segment: {s}" for s in p.evidence_pack.segment_evidence]
    if p.evidence_pack.event_evidence:
        lines.append(f"- Event evidence: {len(p.evidence_pack.event_evidence)} referenced reactions (see Event Explorer).")
    lines += ["", "## Limitations"]
    lines += [f"- {l}" for l in p.limitations]
    lines += ["", "> Exploratory decision support — validate with real consumer research before launch decisions."]
    return "\n".join(lines)


# --- LLM polish (optional) --------------------------------------------------

_LLM_SYSTEM = (
    "You are an FMCG insights lead. Polish this executive briefing Markdown for clarity and flow. "
    "You MUST NOT add facts, numbers, segments, risks, or actions — only rephrase what is present. "
    "Preserve all headings, figures, and the limitations. Return strict JSON: {\"markdown\": \"...\"}."
)


def _maybe_llm(markdown: str, use_llm: bool, llm_client: LLMClient | None) -> tuple[str, str]:
    if not use_llm:
        return markdown, "deterministic"
    client = llm_client or LLMClient()
    if not client.configured:
        return markdown, "deterministic"
    try:
        data = client.chat_json(_LLM_SYSTEM, json.dumps({"markdown": markdown}))
        new = data.get("markdown")
        if isinstance(new, str) and len(new.strip()) > 0.5 * len(markdown):
            return new.strip(), "llm_enhanced"
    except Exception as e:  # noqa: BLE001
        logger.warning("Briefing LLM rewrite failed; using deterministic. error=%s", e)
    return markdown, "deterministic"


# --- public API -------------------------------------------------------------


def generate(db: Session, project_id: str, params: BriefingGenerateIn, llm_client: LLMClient | None = None) -> BriefingDoc:
    payload = build_payload(db, project_id, params)
    markdown = render_markdown(payload)
    markdown, source_mode = _maybe_llm(markdown, params.use_llm_rewrite, llm_client)

    for existing in db.execute(select(BriefingDoc).where(BriefingDoc.project_id == project_id)).scalars().all():
        db.delete(existing)
    doc = BriefingDoc(
        project_id=project_id,
        audience=params.audience,
        tone=params.tone,
        source_mode=source_mode,
        payload_json=payload.model_dump_json(),
        markdown=markdown,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    app_log_service.log_briefing_generated(db, project_id=project_id, message=f"Executive briefing generated ({params.audience})")
    return doc


def get_briefing_row(db: Session, project_id: str) -> BriefingDoc | None:
    return db.execute(
        select(BriefingDoc).where(BriefingDoc.project_id == project_id).order_by(BriefingDoc.updated_at.desc())
    ).scalars().first()


def get_payload(doc: BriefingDoc) -> BriefingPayload:
    return BriefingPayload.model_validate(json.loads(doc.payload_json or "{}"))


def get_summary(doc: BriefingDoc) -> BriefingSummary:
    p = get_payload(doc)
    h = p.briefing_header
    return BriefingSummary(
        recommendation_status=h.recommendation_status,
        overall_score=h.overall_score,
        confidence_label=h.confidence_label,
        headline=p.situation.current_decision_point,
        top_action=p.next_best_actions[0].action if p.next_best_actions else None,
    )
