"""Scenario testing (Phase 7).

Re-simulates the launch under modified assumptions WITHOUT touching the baseline
simulation, report, or agent memory. Scenario events are tagged with
`run_type='scenario'` + `scenario_id`. The baseline-vs-scenario delta is computed
from event aggregates and persisted on the `ScenarioRun` row.

Preconditions (ValueError → 409):
    ontology_required | agents_required | baseline_events_required | baseline_report_required
"""
from __future__ import annotations

import json
import uuid
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Event, Ontology, ScenarioRun
from app.schemas.ontology import OntologyPayload
from app.schemas.scenario import (
    MetricChanges,
    ScenarioOverrides,
    ScenarioRunIn,
    ScenarioRunOut,
)
from app.services import app_log_service, ontology_service, report_service, simulation_service
from app.services.simulation_scoring import SimContext, build_context

_EXPLORATORY = (
    "Scenario outputs are exploratory decision-support hypotheses, not guaranteed market results."
)

COMPLAINT = {"complain", "comment_negative"}
RECOMMEND = {"recommend", "share_with_friend"}


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


# --- override application ----------------------------------------------------


def apply_overrides(ctx: SimContext, ov: ScenarioOverrides) -> SimContext:
    """Translate scenario levers into additive nudges on the simulation context."""
    if ov.price_change_pct:
        # a price cut (negative pct) raises perceived value-for-money
        ctx.price_value_adj += (-ov.price_change_pct / 100.0) * 0.5
    if ov.claim_credibility_boost:
        ctx.claim_credibility = _clamp01(ctx.claim_credibility + ov.claim_credibility_boost)
    if ov.sampling_boost > 0:
        ctx.has_sampling = True
        ctx.social_proof_adj += 0.4 * ov.sampling_boost
        ctx.risk_adj -= 0.12 * ov.sampling_boost
    if ov.promotion_boost > 0:
        ctx.has_promo = True
        ctx.price_value_adj += 0.12 * ov.promotion_boost
    if ov.channel_focus:
        focus = ov.channel_focus.lower()
        matched = [c for c in ctx.channels if focus in c or c in focus]
        ctx.channels = matched or [focus]
        ctx.channel_adj += 0.08
    if ov.competitor_pressure_boost > 0:
        ctx.risk_intensity = _clamp01(ctx.risk_intensity + 0.15 * ov.competitor_pressure_boost)
    if ov.packaging_appeal_boost > 0:
        ctx.pack_adj += 0.4 * ov.packaging_appeal_boost
    if ov.social_proof_boost > 0:
        ctx.social_proof_adj += 0.4 * ov.social_proof_boost
    if ov.sensory_risk_reduction > 0:
        ctx.risk_adj -= 0.2 * ov.sensory_risk_reduction
        if ov.sensory_risk_reduction >= 0.7:
            ctx.taste_risk = False
    if ov.retailer_support_boost > 0:
        ctx.channel_adj += 0.15 * ov.retailer_support_boost
    return ctx


# --- input loading -----------------------------------------------------------


def _require_baseline(db: Session, project_id: str) -> tuple[OntologyPayload, list[Agent], list[Agent], list[Event]]:
    ontology_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    if ontology_row is None:
        raise ValueError("ontology_required")
    ontology = OntologyPayload.model_validate(json.loads(ontology_row.data_json or "{}"))

    agents = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
    consumers = [a for a in agents if a.agent_type == "consumer"]
    market = [a for a in agents if a.agent_type == "market_actor"]
    if not consumers:
        raise ValueError("agents_required")

    baseline_events = db.execute(
        select(Event).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalars().all()
    if not baseline_events:
        raise ValueError("baseline_events_required")

    if report_service.get_report_row(db, project_id) is None:
        raise ValueError("baseline_report_required")

    return ontology, consumers, market, baseline_events


def _scenario_events(db: Session, project_id: str, scenario_id: str) -> list[Event]:
    return db.execute(
        select(Event).where(
            Event.project_id == project_id,
            Event.run_type == "scenario",
            Event.scenario_id == scenario_id,
        )
    ).scalars().all()


# --- aggregation + delta -----------------------------------------------------


def _aggregate(events: list[Event]) -> dict:
    consumer = [e for e in events if e.agent_type == "consumer"]
    n = max(1, len(consumer))
    actions = Counter(e.action_type for e in consumer)
    seg: dict[str, dict] = defaultdict(lambda: {"n": 0, "trial_sum": 0.0, "sentiment_sum": 0.0})
    for e in consumer:
        s = seg[e.segment_name or "Unknown"]
        s["n"] += 1
        s["trial_sum"] += e.trial_probability or 0.0
        s["sentiment_sum"] += e.sentiment_score or 0.0
    seg_metrics = {
        k: {
            "n": v["n"],
            "avg_trial_probability": round(v["trial_sum"] / v["n"], 3) if v["n"] else 0.0,
            "avg_sentiment": round(v["sentiment_sum"] / v["n"], 3) if v["n"] else 0.0,
        }
        for k, v in seg.items()
    }
    return {
        "trial_probability": round(sum(e.trial_probability or 0 for e in consumer) / n, 3),
        "purchase_intent": round(sum(e.purchase_intent_score or 0 for e in consumer) / n, 3),
        "repeat_probability": round(sum(e.repeat_probability or 0 for e in consumer) / n, 3),
        "sentiment": round(sum(e.sentiment_score or 0 for e in consumer) / n, 3),
        "trial_count": actions.get("purchase_trial", 0),
        "complaint_count": sum(actions.get(a, 0) for a in COMPLAINT),
        "recommend_count": sum(actions.get(a, 0) for a in RECOMMEND),
        "switch_count": actions.get("switch_brand", 0),
        "action_distribution": dict(actions),
        "triggers": dict(Counter(e.trigger_detected for e in consumer if e.trigger_detected)),
        "barriers": dict(Counter(e.barrier_detected for e in consumer if e.barrier_detected)),
        "segments": seg_metrics,
    }


def _diff_counts(base: dict, scen: dict) -> dict[str, int]:
    keys = set(base) | set(scen)
    out = {k: scen.get(k, 0) - base.get(k, 0) for k in keys}
    return {k: v for k, v in sorted(out.items(), key=lambda kv: -abs(kv[1])) if v != 0}


def _segment_changes(base: dict, scen: dict) -> list[dict]:
    out = []
    segs = set(base["segments"]) | set(scen["segments"])
    for s in segs:
        b = base["segments"].get(s, {"avg_trial_probability": 0.0, "avg_sentiment": 0.0})
        c = scen["segments"].get(s, {"avg_trial_probability": 0.0, "avg_sentiment": 0.0})
        out.append(
            {
                "segment_name": s,
                "baseline_trial_probability": b["avg_trial_probability"],
                "scenario_trial_probability": c["avg_trial_probability"],
                "trial_probability_delta": round(c["avg_trial_probability"] - b["avg_trial_probability"], 3),
                "sentiment_delta": round(c["avg_sentiment"] - b["avg_sentiment"], 3),
            }
        )
    return sorted(out, key=lambda d: -d["trial_probability_delta"])


def _metric_changes(base: dict, scen: dict, seg_changes: list[dict]) -> MetricChanges:
    improved = [d["segment_name"] for d in seg_changes if d["trial_probability_delta"] > 0.005][:3]
    declined = [d["segment_name"] for d in reversed(seg_changes) if d["trial_probability_delta"] < -0.005][:3]
    return MetricChanges(
        trial_probability_delta=round(scen["trial_probability"] - base["trial_probability"], 3),
        purchase_intent_delta=round(scen["purchase_intent"] - base["purchase_intent"], 3),
        repeat_probability_delta=round(scen["repeat_probability"] - base["repeat_probability"], 3),
        sentiment_delta=round(scen["sentiment"] - base["sentiment"], 3),
        complaint_delta=scen["complaint_count"] - base["complaint_count"],
        recommend_delta=scen["recommend_count"] - base["recommend_count"],
        switch_delta=scen["switch_count"] - base["switch_count"],
        trial_count_delta=scen["trial_count"] - base["trial_count"],
        top_segments_improved=improved,
        top_segments_declined=declined,
    )


def _recommendation_changes(mc: MetricChanges, ov: ScenarioOverrides) -> list[str]:
    recs: list[str] = []
    if mc.trial_count_delta > 0:
        recs.append(
            f"Trial improves by {mc.trial_count_delta} consumers under this scenario"
            + (f", strongest in {', '.join(mc.top_segments_improved)}" if mc.top_segments_improved else "")
            + " — worth pursuing if the lever is affordable."
        )
    elif mc.trial_count_delta < 0:
        recs.append(f"Trial falls by {abs(mc.trial_count_delta)} consumers — this lever hurts the funnel; avoid in isolation.")
    if mc.repeat_probability_delta <= 0.01 and mc.trial_probability_delta > 0.01:
        recs.append("Trial rises but repeat barely moves — pair this lever with sampling or sensory proof to protect repeat.")
    if mc.repeat_probability_delta > 0.01:
        recs.append("Repeat probability improves — this lever helps convert trial into loyalty.")
    if ov.price_change_pct < 0 and mc.trial_probability_delta > 0:
        recs.append("A price cut lifts trial but resets the price reference — prefer a temporary promo/sample mechanic.")
    if mc.complaint_delta < 0:
        recs.append(f"Complaints drop by {abs(mc.complaint_delta)} — sensory/credibility de-risking is working.")
    if not recs:
        recs.append("No material change vs baseline — this lever alone is unlikely to move the launch.")
    return recs


def _conclusion(mc: MetricChanges, ov: ScenarioOverrides, name: str) -> str:
    direction = "improves" if mc.trial_probability_delta > 0.005 else "does not materially improve" if abs(mc.trial_probability_delta) <= 0.005 else "weakens"
    repeat_note = (
        "and repeat improves alongside it" if mc.repeat_probability_delta > 0.01
        else "but repeat remains constrained" if mc.trial_probability_delta > 0.005
        else "with repeat largely flat"
    )
    seg_note = (
        f" Gains concentrate in {', '.join(mc.top_segments_improved)}." if mc.top_segments_improved else ""
    )
    combine = (
        " It should be combined with sampling or sensory proof rather than used as a standalone launch fix."
        if mc.trial_probability_delta > 0.005 and mc.repeat_probability_delta <= 0.01
        else ""
    )
    return (
        f"'{name}' {direction} trial (Δ trial probability {mc.trial_probability_delta:+.3f}, "
        f"Δ trials {mc.trial_count_delta:+d}) {repeat_note}.{seg_note}{combine} {_EXPLORATORY}"
    )


# --- public API --------------------------------------------------------------


def run_scenario(db: Session, project_id: str, params: ScenarioRunIn) -> ScenarioRun:
    ontology, consumers, market, baseline_events = _require_baseline(db, project_id)

    ctx = apply_overrides(build_context(ontology), params.overrides)
    scenario_id = str(uuid.uuid4())

    simulation_service.run_rounds(
        db,
        project_id,
        ctx,
        consumers,
        market,
        rounds=max(1, min(params.rounds, 6)),
        seed=params.seed,
        include_actors=True,
        run_type="scenario",
        scenario_id=scenario_id,
        persist_agent_state=False,
    )
    scenario_events = _scenario_events(db, project_id, scenario_id)

    base_agg = _aggregate(baseline_events)
    scen_agg = _aggregate(scenario_events)
    seg_changes = _segment_changes(base_agg, scen_agg)
    mc = _metric_changes(base_agg, scen_agg, seg_changes)
    rec_changes = _recommendation_changes(mc, params.overrides)
    conclusion = _conclusion(mc, params.overrides, params.scenario_name)

    delta_summary = (
        f"Trial probability {mc.trial_probability_delta:+.3f}, repeat {mc.repeat_probability_delta:+.3f}, "
        f"sentiment {mc.sentiment_delta:+.3f}, trials {mc.trial_count_delta:+d}, "
        f"recommends {mc.recommend_delta:+d}, complaints {mc.complaint_delta:+d}."
    )

    delta_payload = {
        "baseline_summary": base_agg,
        "scenario_summary": scen_agg,
        "delta_summary": delta_summary,
        "key_metric_changes": mc.model_dump(),
        "segment_changes": seg_changes,
        "action_distribution_changes": _diff_counts(base_agg["action_distribution"], scen_agg["action_distribution"]),
        "trigger_changes": _diff_counts(base_agg["triggers"], scen_agg["triggers"]),
        "barrier_changes": _diff_counts(base_agg["barriers"], scen_agg["barriers"]),
        "recommendation_changes": rec_changes,
        "conclusion": conclusion,
    }

    run = ScenarioRun(
        id=scenario_id,
        project_id=project_id,
        scenario_name=params.scenario_name,
        description=params.description,
        overrides_json=params.overrides.model_dump_json(),
        baseline_event_count=len(baseline_events),
        scenario_event_count=len(scenario_events),
        delta_payload_json=json.dumps(delta_payload, ensure_ascii=False),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    app_log_service.log_scenario_created(db, project_id=project_id, scenario_id=run.id, name=params.scenario_name)
    return run


def to_out(run: ScenarioRun) -> ScenarioRunOut:
    delta = json.loads(run.delta_payload_json or "{}")
    return ScenarioRunOut(
        scenario_id=run.id,
        project_id=run.project_id,
        scenario_name=run.scenario_name,
        description=run.description,
        overrides=ScenarioOverrides.model_validate(json.loads(run.overrides_json or "{}")),
        baseline_summary=delta.get("baseline_summary", {}),
        scenario_summary=delta.get("scenario_summary", {}),
        delta_summary=delta.get("delta_summary", ""),
        key_metric_changes=MetricChanges.model_validate(delta["key_metric_changes"]),
        segment_changes=delta.get("segment_changes", []),
        action_distribution_changes=delta.get("action_distribution_changes", {}),
        trigger_changes=delta.get("trigger_changes", {}),
        barrier_changes=delta.get("barrier_changes", {}),
        recommendation_changes=delta.get("recommendation_changes", []),
        conclusion=delta.get("conclusion", ""),
        created_at=run.created_at,
    )


def list_scenarios(db: Session, project_id: str) -> list[ScenarioRun]:
    return db.execute(
        select(ScenarioRun).where(ScenarioRun.project_id == project_id).order_by(ScenarioRun.created_at.desc())
    ).scalars().all()


def get_scenario(db: Session, project_id: str, scenario_id: str) -> ScenarioRun | None:
    return db.execute(
        select(ScenarioRun).where(ScenarioRun.project_id == project_id, ScenarioRun.id == scenario_id)
    ).scalars().first()


def delete_scenario(db: Session, project_id: str, scenario_id: str) -> bool:
    run = get_scenario(db, project_id, scenario_id)
    if run is None:
        return False
    # remove the scenario's events too
    for e in _scenario_events(db, project_id, scenario_id):
        db.delete(e)
    db.delete(run)
    db.commit()
    return True
