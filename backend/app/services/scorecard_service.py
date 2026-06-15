"""Concept scorecard builder (Phase 12).

A transparent, deterministic decision-support heuristic derived entirely from
EXISTING data — the strategic report payload, the ontology, the confidence
calibration, and the assumptions ledger. It does NOT change any core scoring
formula and does NOT invent performance; every sub-score maps to data already
produced by earlier phases.

See docs/SCORING_LOGIC.md for the exact weighting.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Ontology
from app.schemas.ontology import OntologyPayload
from app.schemas.portfolio import Scorecard
from app.schemas.report import ReportPayload
from app.services import assumptions_service, confidence_service, ontology_service, report_service

# overall_score weights (documented in SCORING_LOGIC.md)
W_TRIAL = 0.20
W_REPEAT = 0.20
W_SENTIMENT = 0.15
W_ADVOCACY = 0.10
W_CLAIM = 0.10
W_CHANNEL = 0.10
W_CONFIDENCE = 0.15
W_RISK = 0.15
W_ASSUMPTION = 0.10
W_SENSITIVITY = 0.05

_RECOMMEND_ACTIONS = {"recommend", "share_with_friend"}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _kw_score(text: str | None, high: float, medium: float, low: float, default: float) -> float:
    t = (text or "").lower()
    if "high" in t:
        return high
    if "medium" in t or "moderate" in t:
        return medium
    if "low" in t:
        return low
    return default


def _seg_weighted(segments, attr: str) -> float:
    total = sum(s.number_of_agents for s in segments) or 1
    return sum(s.number_of_agents * getattr(s, attr) for s in segments) / total


def _build(
    rp: ReportPayload,
    ont: OntologyPayload,
    confidence_overall: float,
    confidence_label: str,
    high_assumptions: int,
    med_assumptions: int,
    low_assumptions: int,
    project_id: str,
    project_name: str,
    snapshot_id: str | None = None,
    snapshot_name: str | None = None,
) -> Scorecard:
    segs = rp.segment_reaction_map
    consumer_count = sum(s.number_of_agents for s in segs) or 1

    trial = _clamp(_seg_weighted(segs, "average_trial_probability") * 100) if segs else 0.0
    repeat = _clamp(_seg_weighted(segs, "average_repeat_probability") * 100) if segs else 0.0
    raw_sent = _seg_weighted(segs, "average_sentiment_score") if segs else 0.0
    sentiment = _clamp((raw_sent if raw_sent >= 0 else (raw_sent + 1) / 2) * 100)

    dist = rp.launch_funnel_summary.action_distribution or {}
    advocacy_rate = sum(dist.get(a, 0) for a in _RECOMMEND_ACTIONS) / consumer_count
    advocacy = _clamp(_clamp01(advocacy_rate) * 100)

    # claim credibility from ontology claim_analysis (believable/questionable/unbelievable)
    cred_map = {"believable": 1.0, "questionable": 0.5, "unbelievable": 0.0}
    creds = [cred_map.get(c.credibility, 0.6) for c in ont.claim_analysis]
    claim = _clamp((sum(creds) / len(creds)) * 100) if creds else 60.0

    # channel fit from ontology channel_analysis fit_score (0..1)
    fits = [c.fit_score for c in ont.channel_analysis]
    channel = _clamp((sum(fits) / len(fits)) * 100) if fits else 60.0

    # price/value from report packaging_price_perception (premium-price risk keyword)
    price_value = _kw_score(rp.packaging_price_perception.premium_price_risk, high=35, medium=60, low=82, default=60)

    # risk from the innovation risk matrix severities (higher = riskier)
    sev_map = {"high": 1.0, "medium": 0.6, "low": 0.3}
    sevs = [sev_map.get(r.severity.lower(), 0.5) for r in rp.innovation_risk_matrix]
    risk = _clamp((sum(sevs) / len(sevs)) * 100) if sevs else 50.0

    # assumption risk from the ledger (avg severity, higher = riskier)
    total_assumptions = max(1, high_assumptions + med_assumptions + low_assumptions)
    assumption_risk = _clamp(
        ((high_assumptions * 1.0 + med_assumptions * 0.5 + low_assumptions * 0.2) / total_assumptions) * 100
    )

    # sensitivity risk proxy: trial-vs-repeat gap + promotion dependency (NOT a full sweep)
    gap = _clamp01((trial - repeat) / 100.0)
    promo = _kw_score(rp.trial_repeat_forecast.dependency_on_promotion, high=0.8, medium=0.5, low=0.2, default=0.4)
    sensitivity_risk = _clamp((0.6 * gap + 0.4 * promo) * 100)

    overall = _clamp(
        W_TRIAL * trial
        + W_REPEAT * repeat
        + W_SENTIMENT * sentiment
        + W_ADVOCACY * advocacy
        + W_CLAIM * claim
        + W_CHANNEL * channel
        + W_CONFIDENCE * (confidence_overall * 100)
        - W_RISK * risk
        - W_ASSUMPTION * assumption_risk
        - W_SENSITIVITY * sensitivity_risk
    )

    sorted_segs = sorted(segs, key=lambda s: s.average_trial_probability, reverse=True)
    best_segment = sorted_segs[0].segment_name if sorted_segs else "—"
    weakest_segment = sorted_segs[-1].segment_name if sorted_segs else "—"
    strongest_trigger = rp.purchase_trigger_analysis[0].trigger if rp.purchase_trigger_analysis else "—"
    strongest_barrier = rp.adoption_barrier_analysis[0].barrier if rp.adoption_barrier_analysis else "—"

    # recommended next step: target the weakest dimension
    dims = {
        "repeat": repeat,
        "claim credibility": claim,
        "price/value": price_value,
        "trial": trial,
        "confidence": confidence_overall * 100,
    }
    weakest_dim = min(dims, key=dims.get)
    next_step_map = {
        "repeat": "De-risk repeat: run a sensory/taste test and pair launch with sampling before scaling.",
        "claim credibility": "Rewrite and substantiate the riskiest claim, then test believability with consumers.",
        "price/value": "Run pricing/promo work: make value-per-serve explicit and test a sampling/BOGO mechanic.",
        "trial": "Sharpen the trial proposition for the beachhead segment and test concept appeal.",
        "confidence": "Run consumer validation to close information gaps before committing.",
    }
    recommended = next_step_map[weakest_dim]

    ranking = (
        f"overall = 0.20·trial({trial:.0f}) + 0.20·repeat({repeat:.0f}) + 0.15·sentiment({sentiment:.0f}) "
        f"+ 0.10·advocacy({advocacy:.0f}) + 0.10·claim({claim:.0f}) + 0.10·channel({channel:.0f}) "
        f"+ 0.15·confidence({confidence_overall * 100:.0f}) − 0.15·risk({risk:.0f}) "
        f"− 0.10·assumption_risk({assumption_risk:.0f}) − 0.05·sensitivity_risk({sensitivity_risk:.0f}) "
        f"= {overall:.1f}/100."
    )

    return Scorecard(
        project_id=project_id,
        project_name=project_name,
        snapshot_id=snapshot_id,
        snapshot_name=snapshot_name,
        overall_score=round(overall, 1),
        confidence_score=round(confidence_overall, 3),
        trial_potential_score=round(trial, 1),
        repeat_potential_score=round(repeat, 1),
        sentiment_score=round(sentiment, 1),
        advocacy_score=round(advocacy, 1),
        risk_score=round(risk, 1),
        claim_credibility_score=round(claim, 1),
        price_value_score=round(price_value, 1),
        channel_fit_score=round(channel, 1),
        assumption_risk_score=round(assumption_risk, 1),
        sensitivity_risk_score=round(sensitivity_risk, 1),
        top_opportunity=rp.executive_summary.top_opportunity,
        top_risk=rp.executive_summary.top_risk,
        best_segment=best_segment,
        weakest_segment=weakest_segment,
        strongest_trigger=strongest_trigger,
        strongest_barrier=strongest_barrier,
        recommended_next_step=recommended,
        ranking_explanation=ranking,
        confidence_label=confidence_label,
    )


def build_for_project(db: Session, project_id: str, project_name: str) -> Scorecard:
    """Live scorecard from the project's current report + ontology + confidence + assumptions."""
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise ValueError("report_required")
    rp = report_service.get_payload(report)

    ont_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    ont = OntologyPayload.model_validate(json.loads(ont_row.data_json or "{}")) if ont_row else OntologyPayload()

    conf = confidence_service.compute(db, project_id)
    assumptions = assumptions_service.build(db, project_id)

    return _build(
        rp, ont, conf.overall_confidence, conf.confidence_label,
        assumptions.summary.high_impact_count,
        assumptions.summary.medium_impact_count,
        assumptions.summary.low_impact_count,
        project_id, project_name,
    )


def build_from_payload(
    rp_dict: dict,
    ont: OntologyPayload,
    confidence_overall: float,
    confidence_label: str,
    high: int, med: int, low: int,
    project_id: str, project_name: str,
    snapshot_id: str | None = None, snapshot_name: str | None = None,
) -> Scorecard:
    rp = ReportPayload.model_validate(rp_dict)
    return _build(rp, ont, confidence_overall, confidence_label, high, med, low, project_id, project_name, snapshot_id, snapshot_name)


def to_markdown(sc: Scorecard) -> str:
    rows = [
        ("Overall score", f"{sc.overall_score}/100"),
        ("Confidence", f"{sc.confidence_score:.2f} ({sc.confidence_label})"),
        ("Trial potential", f"{sc.trial_potential_score}/100"),
        ("Repeat potential", f"{sc.repeat_potential_score}/100"),
        ("Sentiment", f"{sc.sentiment_score}/100"),
        ("Advocacy", f"{sc.advocacy_score}/100"),
        ("Claim credibility", f"{sc.claim_credibility_score}/100"),
        ("Price/value", f"{sc.price_value_score}/100"),
        ("Channel fit", f"{sc.channel_fit_score}/100"),
        ("Risk (higher=worse)", f"{sc.risk_score}/100"),
        ("Assumption risk", f"{sc.assumption_risk_score}/100"),
        ("Sensitivity risk", f"{sc.sensitivity_risk_score}/100"),
    ]
    table = "\n".join(f"| {k} | {v} |" for k, v in rows)
    title = f"{sc.project_name}" + (f" — {sc.snapshot_name}" if sc.snapshot_name else "")
    return (
        f"# Concept Scorecard — {title}\n\n"
        f"| Metric | Score |\n| --- | --- |\n{table}\n\n"
        f"**Top opportunity:** {sc.top_opportunity}\n\n"
        f"**Top risk:** {sc.top_risk}\n\n"
        f"**Best segment:** {sc.best_segment}  |  **Weakest segment:** {sc.weakest_segment}\n\n"
        f"**Strongest trigger:** {sc.strongest_trigger}  |  **Strongest barrier:** {sc.strongest_barrier}\n\n"
        f"**Recommended next step:** {sc.recommended_next_step}\n\n"
        f"**Ranking:** {sc.ranking_explanation}\n\n"
        f"> {sc.disclaimer} Validate with real consumer research before launch decisions.\n"
    )
