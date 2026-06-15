"""Snapshot diff (Phase 13).

Deterministic, explainable comparison of two report versions — either the active
report or a saved snapshot — across scorecard dimensions, report sections, risks,
recommendations, and segments. No LLM is used; everything is structured-field diff.

Preconditions (ValueError → mapped by the endpoint):
    report_required | snapshot_not_found | invalid_diff_request
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.schemas.history import (
    DiffRequest,
    DiffSide,
    DiffSideInfo,
    DimensionChange,
    NumericDelta,
    RecommendationChange,
    RiskChanges,
    SectionChange,
    SegmentChange,
    SnapshotDiffOut,
)
from app.schemas.portfolio import Scorecard
from app.services import report_service, scorecard_service, snapshot_service

_EXPLORATORY = "Differences reflect changes in simulated, deterministic output — not validated market movements."

# (field, is_risk, epsilon, label)
_DIMS: list[tuple[str, bool, float, str]] = [
    ("overall_score", False, 0.5, "overall score"),
    ("trial_potential_score", False, 0.5, "trial potential"),
    ("repeat_potential_score", False, 0.5, "repeat potential"),
    ("sentiment_score", False, 0.5, "sentiment"),
    ("advocacy_score", False, 0.5, "advocacy"),
    ("claim_credibility_score", False, 0.5, "claim credibility"),
    ("price_value_score", False, 0.5, "price/value"),
    ("channel_fit_score", False, 0.5, "channel fit"),
    ("risk_score", True, 0.5, "risk"),
    ("assumption_risk_score", True, 0.5, "assumption risk"),
    ("sensitivity_risk_score", True, 0.5, "sensitivity risk"),
    ("confidence_score", False, 0.02, "confidence"),
]

_SCORE_FIELDS = [d[0] for d in _DIMS]

_SECTIONS = [
    "executive_summary",
    "segment_reaction_map",
    "purchase_trigger_analysis",
    "adoption_barrier_analysis",
    "innovation_risk_matrix",
    "strategic_recommendations",
    "recommended_ab_tests",
]

_SEV_RANK = {"high": 3, "medium": 2, "low": 1}


# --- helpers ----------------------------------------------------------------


def calculate_numeric_delta(left: float, right: float) -> float:
    return round(right - left, 3)


def classify_delta_direction(delta: float, *, risk: bool, eps: float) -> str:
    adj = -delta if risk else delta
    if adj > eps:
        return "improved"
    if adj < -eps:
        return "declined"
    return "unchanged"


def summarize_section_change(section: str, left: object, right: object) -> SectionChange:
    changed = json.dumps(left, sort_keys=True, default=str) != json.dumps(right, sort_keys=True, default=str)
    label = section.replace("_", " ")
    if not changed:
        return SectionChange(section=section, change_type="unchanged", summary=f"{label}: no change.")
    if isinstance(left, list) and isinstance(right, list) and len(left) != len(right):
        summary = f"{label}: changed ({len(left)} → {len(right)} items)."
    else:
        summary = f"{label}: content changed."
    return SectionChange(section=section, change_type="changed", summary=summary)


def compare_recommendations(left: Scorecard, right: Scorecard) -> RecommendationChange:
    changed = left.recommended_next_step != right.recommended_next_step
    interp = (
        "The recommended next step changed — the most pressing weakness shifted between versions."
        if changed
        else "The recommended next step is unchanged."
    )
    return RecommendationChange(
        left_recommendation=left.recommended_next_step,
        right_recommendation=right.recommended_next_step,
        changed=changed,
        interpretation=interp,
    )


def compare_risks(left_payload: dict, right_payload: dict) -> RiskChanges:
    def _map(p: dict) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in p.get("innovation_risk_matrix", []) or []:
            out[r.get("risk_type", "?")] = _SEV_RANK.get(str(r.get("severity", "")).lower(), 2)
        return out

    lm, rm = _map(left_payload), _map(right_payload)
    reduced, increased, unchanged = [], [], []
    for risk in set(lm) | set(rm):
        ls = lm.get(risk)
        rs = rm.get(risk)
        if ls is not None and rs is None:
            reduced.append(f"{risk} (removed)")
        elif rs is not None and ls is None:
            increased.append(f"{risk} (new)")
        elif ls is not None and rs is not None:
            if rs < ls:
                reduced.append(f"{risk} (severity ↓)")
            elif rs > ls:
                increased.append(f"{risk} (severity ↑)")
            else:
                unchanged.append(risk)
    return RiskChanges(
        reduced_risks=sorted(reduced),
        new_or_increased_risks=sorted(increased),
        unchanged_risks=sorted(unchanged),
    )


def compare_segments(left_payload: dict, right_payload: dict) -> list[SegmentChange]:
    def _map(p: dict) -> dict[str, dict]:
        return {s.get("segment_name", "?"): s for s in p.get("segment_reaction_map", []) or []}

    lm, rm = _map(left_payload), _map(right_payload)
    out: list[SegmentChange] = []
    for name in lm.keys() & rm.keys():
        a, b = lm[name], rm[name]
        td = round(b.get("average_trial_probability", 0) - a.get("average_trial_probability", 0), 3)
        rd = round(b.get("average_repeat_probability", 0) - a.get("average_repeat_probability", 0), 3)
        sd = round(b.get("average_sentiment_score", 0) - a.get("average_sentiment_score", 0), 3)
        if abs(td) < 0.005 and abs(rd) < 0.005 and abs(sd) < 0.005:
            interp = "Largely unchanged."
        elif td > 0.005:
            interp = f"Improved trial ({td:+.3f})."
        elif td < -0.005:
            interp = f"Declined trial ({td:+.3f})."
        else:
            interp = f"Repeat/sentiment shifted (repeat {rd:+.3f}, sentiment {sd:+.3f})."
        out.append(SegmentChange(segment_name=name, trial_delta=td, repeat_delta=rd, sentiment_delta=sd, interpretation=interp))
    return sorted(out, key=lambda s: -s.trial_delta)


def build_plain_english_diff_summary(
    left: DiffSideInfo, right: DiffSideInfo, dim_changes: list[DimensionChange], overall_delta: float
) -> str:
    movers = sorted([d for d in dim_changes if d.direction != "unchanged"], key=lambda d: -abs(d.delta))
    if overall_delta > 0.5:
        head = f"'{right.name}' is stronger than '{left.name}' (overall {overall_delta:+.1f})."
    elif overall_delta < -0.5:
        head = f"'{right.name}' is weaker than '{left.name}' (overall {overall_delta:+.1f})."
    else:
        head = f"'{right.name}' is about the same as '{left.name}' (overall {overall_delta:+.1f})."
    if movers:
        top = "; ".join(f"{m.dimension.replace('_score','').replace('_',' ')} {m.direction} ({m.delta:+.1f})" for m in movers[:3])
        head += f" Biggest movements: {top}."
    return head


# --- side resolution --------------------------------------------------------


def _resolve(db: Session, project_id: str, side: DiffSide, project_name: str) -> tuple[DiffSideInfo, Scorecard, dict]:
    if side.type == "active_report":
        report = report_service.get_report_row(db, project_id)
        if report is None:
            raise ValueError("report_required")
        sc = scorecard_service.build_for_project(db, project_id, project_name)
        payload = json.loads(report.payload_json or "{}")
        return DiffSideInfo(type="active_report", name="Active report", created_at=report.updated_at), sc, payload
    if side.type == "snapshot":
        if not side.snapshot_id:
            raise ValueError("invalid_diff_request")
        snap = snapshot_service.get_snapshot(db, project_id, side.snapshot_id)
        if snap is None:
            raise ValueError("snapshot_not_found")
        sc = snapshot_service.scorecard_of(snap)
        payload = json.loads(snap.report_payload_json or "{}")
        return DiffSideInfo(type="snapshot", name=snap.snapshot_name, created_at=snap.created_at), sc, payload
    raise ValueError("invalid_diff_request")


# --- public API -------------------------------------------------------------


def diff(db: Session, project_id: str, project_name: str, req: DiffRequest) -> SnapshotDiffOut:
    left_info, left_sc, left_payload = _resolve(db, project_id, req.left, project_name)
    right_info, right_sc, right_payload = _resolve(db, project_id, req.right, project_name)

    scorecard_delta: dict[str, NumericDelta] = {}
    dimension_changes: list[DimensionChange] = []
    for field, risk, eps, label in _DIMS:
        lv = float(getattr(left_sc, field))
        rv = float(getattr(right_sc, field))
        d = calculate_numeric_delta(lv, rv)
        scorecard_delta[field] = NumericDelta(left=lv, right=rv, delta=d)
        direction = classify_delta_direction(d, risk=risk, eps=eps)
        if direction == "unchanged":
            interp = f"{label} unchanged."
        else:
            note = " (lower is better)" if risk else ""
            interp = f"{label} {direction} by {abs(d):.2f}{note}."
        dimension_changes.append(DimensionChange(dimension=field, delta=d, direction=direction, interpretation=interp))

    changed_sections = [
        summarize_section_change(s, left_payload.get(s), right_payload.get(s)) for s in _SECTIONS
    ]
    rec_changes = compare_recommendations(left_sc, right_sc)
    risk_changes = compare_risks(left_payload, right_payload)
    segment_changes = compare_segments(left_payload, right_payload)

    overall_delta = scorecard_delta["overall_score"].delta
    plain = build_plain_english_diff_summary(left_info, right_info, dimension_changes, overall_delta)

    if overall_delta > 0.5:
        implication = f"The change appears to improve the concept; '{right_info.name}' is the stronger version to carry forward."
    elif overall_delta < -0.5:
        implication = f"The change appears to weaken the concept; revisit before adopting '{right_info.name}'."
    else:
        implication = "No material net change; decide on qualitative factors and validate with real research."
    if risk_changes.new_or_increased_risks:
        implication += f" Note newly raised risks: {', '.join(risk_changes.new_or_increased_risks[:2])}."

    return SnapshotDiffOut(
        project_id=project_id,
        left=left_info,
        right=right_info,
        scorecard_delta=scorecard_delta,
        dimension_changes=dimension_changes,
        changed_sections=changed_sections,
        recommendation_changes=rec_changes,
        risk_changes=risk_changes,
        segment_changes=segment_changes,
        plain_english_summary=plain,
        decision_implication=implication,
        limitations=[
            _EXPLORATORY,
            "Diff is a structured comparison of deterministic outputs; it does not prove real-world improvement.",
        ],
    )
