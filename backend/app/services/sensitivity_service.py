"""Deterministic sensitivity sweeps (Phase 11).

For each lever value we apply the override onto a fresh SimContext, re-run the
6-round simulation (reusing the scenario engine), aggregate the result, then
delete the sweep events. The baseline simulation, report, and agent memory are
never touched (sweeps run with run_type='scenario', persist_agent_state=False,
and their events are removed after aggregation — no ScenarioRun rows are created).

Core scoring formulas are NOT changed — this only exposes the existing engine's
response to lever changes.
"""
from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.schemas.insight import LeverSweep, SensitivityIn, SensitivityOut, SweepPoint
from app.schemas.scenario import ScenarioOverrides
from app.services import scenario_service, simulation_service
from app.services.simulation_scoring import build_context

DEFAULT_LEVERS: dict[str, list[float]] = {
    "price_change_pct": [0, -5, -10, -15],
    "sampling_boost": [0, 0.05, 0.10, 0.15],
    "social_proof_boost": [0, 0.05, 0.10, 0.15],
    "claim_credibility_boost": [0, 0.05, 0.10, 0.15],
}

VALID_LEVERS = {
    "price_change_pct",
    "claim_credibility_boost",
    "sampling_boost",
    "promotion_boost",
    "social_proof_boost",
    "packaging_appeal_boost",
    "sensory_risk_reduction",
    "retailer_support_boost",
    "competitor_pressure_boost",
}

_EXPLORATORY = "Sensitivity curves are exploratory decision-support, not calibrated demand elasticities."


def _fmt_value(lever: str, value: float) -> str:
    return f"{value:g}%" if lever == "price_change_pct" else f"+{value:g}"


def _point(lever: str, value: float, agg: dict, base_agg: dict, consumer_count: int) -> SweepPoint:
    n = max(1, consumer_count)
    base_segs = base_agg.get("segments", {})
    seg_deltas = []
    for seg, m in agg.get("segments", {}).items():
        b = base_segs.get(seg, {}).get("avg_trial_probability", 0.0)
        seg_deltas.append((seg, round(m.get("avg_trial_probability", 0.0) - b, 3)))
    improved = [s for s, d in sorted(seg_deltas, key=lambda x: -x[1]) if d > 0.005][:3]
    declined = [s for s, d in sorted(seg_deltas, key=lambda x: x[1]) if d < -0.005][:3]

    trial = agg["trial_probability"]
    base_trial = base_agg["trial_probability"]
    d_trial = trial - base_trial
    if abs(d_trial) <= 0.005:
        interp = f"{_fmt_value(lever, value)}: ~no change in trial vs baseline."
    elif d_trial > 0:
        interp = f"{_fmt_value(lever, value)}: trial {d_trial:+.3f} vs baseline" + (
            f", strongest in {', '.join(improved)}." if improved else "."
        )
    else:
        interp = f"{_fmt_value(lever, value)}: trial {d_trial:+.3f} vs baseline — this direction hurts the funnel."

    return SweepPoint(
        value=value,
        trial_probability=trial,
        repeat_probability=agg["repeat_probability"],
        purchase_intent=agg["purchase_intent"],
        sentiment=agg["sentiment"],
        recommend_rate=round(agg["recommend_count"] / n, 3),
        complaint_rate=round(agg["complaint_count"] / n, 3),
        top_improved_segments=improved,
        top_declined_segments=declined,
        interpretation=interp,
    )


def _run_point(db: Session, project_id: str, ontology, consumers, market, lever, value, *, rounds, seed) -> dict:
    overrides = ScenarioOverrides(**{lever: float(value)})
    ctx = scenario_service.apply_overrides(build_context(ontology), overrides)
    sweep_id = f"sweep-{uuid.uuid4()}"
    simulation_service.run_rounds(
        db, project_id, ctx, consumers, market,
        rounds=rounds, seed=seed, include_actors=True,
        run_type="scenario", scenario_id=sweep_id, persist_agent_state=False,
    )
    events = scenario_service._scenario_events(db, project_id, sweep_id)
    agg = scenario_service._aggregate(events)
    for e in events:
        db.delete(e)
    db.commit()
    return agg


def _sweep_reads(lever: str, points: list[SweepPoint]) -> tuple[SweepPoint | None, SweepPoint | None, str]:
    if not points:
        return None, None, "No data."
    best = max(points, key=lambda p: p.trial_probability)
    # diminishing return: first point where marginal trial gain drops below 1/3 of the first step's gain
    diminishing = None
    if len(points) >= 3:
        gains = [points[i].trial_probability - points[i - 1].trial_probability for i in range(1, len(points))]
        first_gain = gains[0] if gains else 0.0
        if first_gain > 0.005:
            for i, g in enumerate(gains[1:], start=2):
                if g < first_gain / 3:
                    diminishing = points[i - 1]
                    break
    lift = best.trial_probability - points[0].trial_probability
    if lift <= 0.005:
        read = f"'{lever}' shows little trial leverage in this range (max trial lift {lift:+.3f})."
    else:
        read = f"'{lever}' lifts trial by up to {lift:+.3f} at {_fmt_value(lever, best.value)}"
        if diminishing is not None:
            read += f"; returns flatten beyond {_fmt_value(lever, diminishing.value)}."
        else:
            read += "; gains keep rising across the tested range."
    return best, diminishing, read


def run_sensitivity(db: Session, project_id: str, params: SensitivityIn) -> SensitivityOut:
    ontology, consumers, market, baseline_events = scenario_service._require_baseline(db, project_id)
    base_agg = scenario_service._aggregate(baseline_events)
    consumer_count = len(consumers)

    requested = params.levers or DEFAULT_LEVERS
    levers = {k: v for k, v in requested.items() if k in VALID_LEVERS and v}
    if not levers:
        levers = DEFAULT_LEVERS

    sweeps: list[LeverSweep] = []
    for lever, values in levers.items():
        points = [
            _point(lever, float(v), _run_point(db, project_id, ontology, consumers, market, lever, v, rounds=params.rounds, seed=params.seed), base_agg, consumer_count)
            for v in values
        ]
        best, diminishing, read = _sweep_reads(lever, points)
        sweeps.append(LeverSweep(lever=lever, points=points, best_point=best, diminishing_return_point=diminishing, strategic_read=read))

    # overall recommendation: the lever with the largest trial lift
    ranked = sorted(
        sweeps,
        key=lambda s: (s.best_point.trial_probability - s.points[0].trial_probability) if s.best_point and s.points else 0.0,
        reverse=True,
    )
    if ranked and ranked[0].best_point and ranked[0].points:
        top = ranked[0]
        lift = top.best_point.trial_probability - top.points[0].trial_probability
        if lift > 0.005:
            overall = (
                f"'{top.lever}' is the most responsive lever (trial lift up to {lift:+.3f} at "
                f"{_fmt_value(top.lever, top.best_point.value)}). Test it first, and pair trial levers with "
                "repeat protection (sampling / sensory proof)."
            )
        else:
            overall = "No single lever moves trial much in the tested ranges — combine levers and validate with real research."
    else:
        overall = "No sweeps produced data."

    return SensitivityOut(
        project_id=project_id,
        baseline_summary=base_agg,
        sweeps=sweeps,
        overall_recommendation=overall,
        limitations=[
            _EXPLORATORY,
            "Levers are additive nudges on a deterministic rule engine, not fitted to real price/promo elasticities.",
            "Each point is a single deterministic run at the given seed; real markets are noisier.",
        ],
    )
