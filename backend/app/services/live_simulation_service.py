"""Live (SSE) simulation streaming (Phase 18).

Streams the SAME deterministic simulation as `simulation_service` while it is
generated, persisting each `Event` (run_type='baseline') exactly like the sync
path. It reuses the scoring engine (`score_round`, `market_actor_action`) and the
same agent ordering/seed, so the persisted result is identical to a normal run —
guaranteeing replay / report / studio / briefing parity. The sync engine is
untouched; this is an additive streaming variant.
"""
from __future__ import annotations

import json
import logging
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Event, LiveSimulationRun
from app.schemas.live import LiveRunOut, LiveSimulationStartIn
from app.schemas.ontology import OntologyPayload
from app.services import app_log_service, ontology_service, simulation_service
from app.services.simulation_market_actors import market_actor_action
from app.services.simulation_scoring import (
    ROUND_STAGES,
    ROUND_TOUCHPOINTS,
    build_context,
    choose_touchpoint,
    clamp,
    score_round,
)

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def is_stale(run: LiveSimulationRun) -> bool:
    if run.status != "running":
        return False
    last = _as_utc(run.last_event_at) or _as_utc(run.last_heartbeat_at) or _as_utc(run.started_at) or _as_utc(run.created_at)
    if last is None:
        return False
    ttl = run.stale_after_seconds if run.stale_after_seconds is not None else 600
    return _now() - last > timedelta(seconds=ttl)


def reap_stale(db: Session, project_id: str) -> int:
    """Mark stale running runs as failed before starting a new one."""
    running = db.execute(
        select(LiveSimulationRun).where(
            LiveSimulationRun.project_id == project_id,
            LiveSimulationRun.status.in_(("pending", "running")),
        )
    ).scalars().all()
    reaped = 0
    for run in running:
        if is_stale(run):
            run.status = "failed"
            run.error_message = "Live run marked stale because no stream activity was detected."
            run.completed_at = _now()
            reaped += 1
    if reaped:
        db.commit()
    return reaped


def get_run(db: Session, project_id: str, run_id: str) -> LiveSimulationRun | None:
    return db.execute(
        select(LiveSimulationRun).where(
            LiveSimulationRun.project_id == project_id, LiveSimulationRun.id == run_id
        )
    ).scalars().first()


def list_runs(db: Session, project_id: str) -> list[LiveSimulationRun]:
    return db.execute(
        select(LiveSimulationRun).where(LiveSimulationRun.project_id == project_id).order_by(LiveSimulationRun.created_at.desc())
    ).scalars().all()


def to_out(run: LiveSimulationRun, *, has_events: bool | None = None) -> LiveRunOut:
    stale = is_stale(run)
    can_replay = has_events if has_events is not None else run.total_events_emitted > 0
    return LiveRunOut(
        run_id=run.id,
        project_id=run.project_id,
        status=run.status,
        rounds=run.rounds,
        seed=run.seed,
        deterministic=run.deterministic,
        include_market_actors=run.include_market_actors,
        force_rerun=run.force_rerun,
        event_delay_ms=run.event_delay_ms,
        total_events_expected=run.total_events_expected,
        total_events_emitted=run.total_events_emitted,
        current_round=run.current_round,
        stale_after_seconds=run.stale_after_seconds,
        error_message=run.error_message,
        started_at=run.started_at,
        last_heartbeat_at=run.last_heartbeat_at,
        last_event_at=run.last_event_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
        updated_at=run.updated_at,
        is_stale=stale,
        can_cancel=run.status in ("pending", "running"),
        can_replay_persisted_events=can_replay,
        stream_url=(f"/api/v1/projects/{run.project_id}/live-simulation/{run.id}/stream" if run.status == "running" and not stale else None),
    )


def start_run(db: Session, project_id: str, params: LiveSimulationStartIn) -> LiveSimulationRun:
    # preconditions (brief/ontology/agents) reuse the sync path's checks
    ontology, consumers, market = simulation_service._require(db, project_id)

    baseline_count = db.execute(
        select(func.count(Event.id)).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalar_one()
    if baseline_count > 0 and not params.force_rerun:
        raise ValueError("simulation_exists")

    # reap any stale running runs first, then block only on a genuinely-active run
    reap_stale(db, project_id)
    active = db.execute(
        select(LiveSimulationRun).where(
            LiveSimulationRun.project_id == project_id,
            LiveSimulationRun.status.in_(("pending", "running")),
        )
    ).scalars().first()
    if active is not None:
        raise ValueError("live_run_already_running")

    if params.force_rerun:
        simulation_service._reset_run_state(db, project_id, consumers + market)
        db.commit()

    rounds = max(1, min(params.rounds, 6))
    expected = rounds * (len(consumers) + (len(market) if params.include_market_actors else 0))

    run = LiveSimulationRun(
        project_id=project_id,
        status="running",
        rounds=rounds,
        seed=params.seed,
        deterministic=params.deterministic,
        include_market_actors=params.include_market_actors,
        force_rerun=params.force_rerun,
        event_delay_ms=params.event_delay_ms,
        stale_after_seconds=params.stale_after_seconds,
        total_events_expected=expected,
        total_events_emitted=0,
        current_round=0,
        started_at=_now(),
        last_heartbeat_at=_now(),
    )
    db.add(run)
    db.commit()
    db.refresh(run)
    app_log_service.log_live_run_started(db, project_id=project_id, run_id=run.id)
    return run


def iter_stream(db: Session, project_id: str, run_id: str) -> Iterator[dict]:
    """Yield stream messages (dicts) while generating + persisting events."""
    run = get_run(db, project_id, run_id)
    if run is None:
        yield {"type": "run_failed", "run_id": run_id, "project_id": project_id, "payload": {"error": "run_not_found"}}
        return

    rounds = run.rounds
    seed = run.seed
    include_actors = run.include_market_actors
    delay = max(0, run.event_delay_ms) / 1000.0
    expected = run.total_events_expected
    seq = 0
    emitted = 0

    def msg(mtype: str, *, round_number: int = 0, stage: str = "", payload: dict | None = None) -> dict:
        nonlocal seq
        seq += 1
        return {
            "run_id": run_id,
            "project_id": project_id,
            "type": mtype,
            "timestamp": _now().isoformat(),
            "sequence": seq,
            "round_number": round_number,
            "stage_name": stage,
            "progress": {
                "round": round_number,
                "rounds_total": rounds,
                "events_emitted": emitted,
                "events_expected": expected,
                "percent": round(100.0 * emitted / expected, 1) if expected else 0.0,
            },
            "payload": payload or {},
        }

    try:
        ontology_row = ontology_service.get_ontology(db, project_id)
        ontology = OntologyPayload.model_validate(json.loads(ontology_row.data_json or "{}"))
        ctx = build_context(ontology)
        agents = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
        consumers = sorted([a for a in agents if a.agent_type == "consumer"], key=lambda a: a.id)
        market = sorted([a for a in agents if a.agent_type == "market_actor"], key=lambda a: a.id)
        if not consumers:
            raise ValueError("agents_required")

        consumer_state: dict[str, dict] = {a.id: {} for a in consumers}
        consumer_profile: dict[str, dict] = {a.id: json.loads(a.profile_json or "{}") for a in consumers}
        action_history: dict[str, list] = {a.id: [] for a in consumers + market}
        sim_memory: dict[str, list] = {a.id: [] for a in consumers + market}

        yield msg("run_started", payload={"rounds_total": rounds, "consumers": len(consumers), "market_actors": len(market) if include_actors else 0})

        for rnd in range(1, rounds + 1):
            stage = ROUND_STAGES[rnd]
            touchpoint_pool = ROUND_TOUCHPOINTS[rnd]
            run.current_round = rnd
            run.last_heartbeat_at = _now()
            db.commit()
            yield msg("round_started", round_number=rnd, stage=stage, payload={"round_number": rnd, "stage_name": stage})

            sent_sum = trial_sum = interest_sum = 0.0
            positive = 0
            round_barriers: Counter[str] = Counter()
            round_triggers: Counter[str] = Counter()

            for idx, agent in enumerate(consumers):
                yield msg("agent_started", round_number=rnd, stage=stage, payload={
                    "agent_id": agent.id, "agent_type": "consumer", "segment_name": agent.segment_name,
                    "message": f"{agent.segment_name or 'Consumer'} is evaluating {stage.lower()}.",
                })
                result = score_round(consumer_profile[agent.id], agent.segment_name or "", ctx, rnd, consumer_state[agent.id], idx, seed)
                touchpoint = choose_touchpoint(consumer_profile[agent.id], touchpoint_pool, idx)
                event = Event(
                    project_id=project_id, round_number=rnd, stage_name=stage, agent_id=agent.id,
                    agent_type="consumer", segment_name=agent.segment_name, touchpoint=touchpoint,
                    action_type=result["action_type"], content_seen=touchpoint, reasoning=result["reasoning"],
                    generated_reaction=result["generated_reaction"], emotional_tone=result["emotional_tone"],
                    confidence_score=result["confidence_score"], sentiment_score=result["sentiment_score"],
                    trial_probability=result["trial_probability"], purchase_intent_score=result["purchase_intent_score"],
                    repeat_probability=result["repeat_probability"], trust_change=result["trust_change"],
                    barrier_detected=result["barrier_detected"], trigger_detected=result["trigger_detected"],
                    run_type="baseline", scenario_id=None, scores_json=json.dumps(result["scores"], ensure_ascii=False),
                )
                db.add(event)
                db.flush()
                emitted += 1
                run.total_events_emitted = emitted
                run.last_event_at = _now()

                sent_sum += result["sentiment_score"]
                trial_sum += result["trial_probability"]
                interest_sum += result["scores"].get("interest", 0.0)
                if result["sentiment_score"] >= 0.55:
                    positive += 1
                if result["barrier_detected"]:
                    round_barriers[result["barrier_detected"]] += 1
                if result["trigger_detected"]:
                    round_triggers[result["trigger_detected"]] += 1
                action_history[agent.id].append({"round": rnd, "stage": stage, "action": result["action_type"], "trial_probability": result["trial_probability"]})
                mem_line = f"R{rnd} ({stage}): {result['action_type']} — {result['generated_reaction']}"
                sim_memory[agent.id].append(mem_line)

                yield msg("event_generated", round_number=rnd, stage=stage, payload={
                    "event_id": event.id, "agent_id": agent.id, "agent_type": "consumer", "segment_name": agent.segment_name,
                    "touchpoint": touchpoint, "action_type": result["action_type"], "reasoning": result["reasoning"],
                    "generated_reaction": result["generated_reaction"], "emotional_tone": result["emotional_tone"],
                    "sentiment_score": result["sentiment_score"], "trial_probability": result["trial_probability"],
                    "purchase_intent_score": result["purchase_intent_score"], "repeat_probability": result["repeat_probability"],
                    "barrier_detected": result["barrier_detected"], "trigger_detected": result["trigger_detected"],
                    "confidence_score": result["confidence_score"],
                })
                yield msg("agent_memory_updated", round_number=rnd, stage=stage, payload={"agent_id": agent.id, "latest_memory": mem_line})
                if delay:
                    time.sleep(delay)

            n = max(1, len(consumers))
            aggregate = {
                "avg_interest": clamp(interest_sum / n), "avg_trial_prob": clamp(trial_sum / n),
                "avg_sentiment": clamp(sent_sum / n), "positive_share": clamp(positive / n),
                "top_barrier": round_barriers.most_common(1)[0][0] if round_barriers else None,
                "top_trigger": round_triggers.most_common(1)[0][0] if round_triggers else None,
                "n": len(consumers),
            }

            round_market = 0
            if include_actors:
                for midx, actor in enumerate(market):
                    ma_profile = json.loads(actor.profile_json or "{}")
                    ma = market_actor_action(ma_profile, actor.role or "", ctx, rnd, aggregate, seed, midx)
                    event = Event(
                        project_id=project_id, round_number=rnd, stage_name=stage, agent_id=actor.id,
                        agent_type="market_actor", segment_name=None, touchpoint=actor.role,
                        action_type=ma["action_type"], content_seen=f"aggregate consumer signal (round {rnd})",
                        reasoning=ma["reasoning"], generated_reaction=ma["generated_reaction"], emotional_tone=ma["emotional_tone"],
                        confidence_score=ma["confidence_score"], sentiment_score=ma["sentiment_score"], trust_change=ma["trust_change"],
                        barrier_detected=ma["barrier_detected"], trigger_detected=ma["trigger_detected"],
                        run_type="baseline", scenario_id=None, scores_json=json.dumps(ma["scores"], ensure_ascii=False),
                    )
                    db.add(event)
                    db.flush()
                    emitted += 1
                    round_market += 1
                    run.total_events_emitted = emitted
                    run.last_event_at = _now()
                    action_history[actor.id].append({"round": rnd, "stage": stage, "action": ma["action_type"], "launch_impact": ma["trust_change"]})
                    sim_memory[actor.id].append(f"R{rnd} ({stage}): {ma['action_type']} — {ma['generated_reaction']}")
                    yield msg("market_actor_event_generated", round_number=rnd, stage=stage, payload={
                        "event_id": event.id, "agent_id": actor.id, "agent_type": "market_actor", "role": actor.role,
                        "action_type": ma["action_type"], "generated_reaction": ma["generated_reaction"], "trust_change": ma["trust_change"],
                    })
                    if delay:
                        time.sleep(delay)

            db.commit()
            yield msg("round_completed", round_number=rnd, stage=stage, payload={
                "round_number": rnd, "stage_name": stage,
                "summary": f"Round {rnd} ({stage}) complete — avg sentiment {aggregate['avg_sentiment']:.2f}, avg trial {aggregate['avg_trial_prob']:.2f}.",
                "consumer_events": len(consumers), "market_actor_events": round_market,
            })

        # persist agent memory + action history (parity with sync baseline run)
        for agent in consumers + market:
            agent.action_history_json = json.dumps(action_history[agent.id], ensure_ascii=False)
            agent.simulation_memory_json = json.dumps(sim_memory[agent.id], ensure_ascii=False)
        run.status = "completed"
        run.completed_at = _now()
        run.total_events_emitted = emitted
        db.commit()
        app_log_service.log_live_run_completed(db, project_id=project_id, run_id=run_id, total_events=emitted)
        yield msg("run_completed", round_number=rounds, payload={"total_events": emitted, "status": "completed"})

    except Exception as e:  # noqa: BLE001
        logger.exception("live simulation failed run_id=%s", run_id)
        try:
            run.status = "failed"
            run.error_message = str(e)
            run.completed_at = _now()
            db.commit()
        except Exception:  # noqa: BLE001
            db.rollback()
        app_log_service.log_live_run_failed(db, project_id=project_id, run_id=run_id, error=str(e))
        yield msg("run_failed", payload={"error": str(e)})
