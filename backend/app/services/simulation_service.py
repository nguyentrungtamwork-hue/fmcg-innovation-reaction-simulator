"""Multi-round FMCG launch simulation engine (Phase 5).

Runs the 6-round launch funnel against persisted consumer + market-actor
agents and the project's ontology. Every consumer agent is scored each round
(via `simulation_scoring.score_round`), an action is chosen, and an `Event`
row is persisted with full reasoning + raw scores. Each market actor takes one
action per round grounded in the round's aggregated consumer signal.

LLM-first with deterministic fallback: the scoring is fully deterministic given
the seed, so tests are stable and offline. The LLM hook is reserved for a later
phase; for now every run is `source_mode="fallback"`.
"""
from __future__ import annotations

import json
import logging
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Brief, Event, Ontology
from app.schemas.ontology import OntologyPayload
from app.schemas.simulation import SimulationRunIn
from app.services import ontology_service
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


def _require(db: Session, project_id: str) -> tuple[OntologyPayload, list[Agent], list[Agent]]:
    brief = db.execute(
        select(Brief).where(Brief.project_id == project_id)
    ).scalars().first()
    if brief is None:
        raise ValueError("brief_required")

    ontology_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    if ontology_row is None:
        raise ValueError("ontology_required")
    ontology = OntologyPayload.model_validate(json.loads(ontology_row.data_json or "{}"))

    agents = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
    consumers = [a for a in agents if a.agent_type == "consumer"]
    market = [a for a in agents if a.agent_type == "market_actor"]
    if not consumers:
        raise ValueError("agents_required")
    return ontology, consumers, market


def _reset_run_state(db: Session, project_id: str, agents: list[Agent]) -> None:
    """Delete prior *baseline* events and clear simulation memory / action history.

    Scenario events (run_type='scenario') are preserved — they are managed per
    scenario by the scenario service.
    """
    existing = db.execute(
        select(Event).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalars().all()
    for e in existing:
        db.delete(e)
    for a in agents:
        a.simulation_memory_json = "[]"
        a.action_history_json = "[]"
    db.flush()


def run_simulation(db: Session, project_id: str, params: SimulationRunIn) -> dict:
    ontology, consumers, market = _require(db, project_id)
    ctx = build_context(ontology)
    rounds = max(1, min(params.rounds, 6))

    if params.force_rerun:
        _reset_run_state(db, project_id, consumers + market)

    return run_rounds(
        db,
        project_id,
        ctx,
        consumers,
        market,
        rounds=rounds,
        seed=params.seed,
        include_actors=params.include_market_actors,
        run_type="baseline",
        scenario_id=None,
        persist_agent_state=True,
    )


def run_rounds(
    db: Session,
    project_id: str,
    ctx,
    consumers: list[Agent],
    market: list[Agent],
    *,
    rounds: int,
    seed: int,
    include_actors: bool,
    run_type: str = "baseline",
    scenario_id: str | None = None,
    persist_agent_state: bool = True,
) -> dict:
    """Core 6-round scoring loop, reusable for baseline and scenario runs.

    Events are tagged with `run_type` / `scenario_id`. When `persist_agent_state`
    is False (scenario runs) the agents' baseline memory / action history are left
    untouched, so a scenario never corrupts the baseline.
    """
    # stable agent ordering so seeded scoring is reproducible
    consumers = sorted(consumers, key=lambda a: a.id)
    market = sorted(market, key=lambda a: a.id)

    consumer_state: dict[str, dict] = {a.id: {} for a in consumers}
    consumer_profile: dict[str, dict] = {
        a.id: json.loads(a.profile_json or "{}") for a in consumers
    }
    action_history: dict[str, list] = {a.id: [] for a in consumers + market}
    sim_memory: dict[str, list] = {a.id: [] for a in consumers + market}

    all_actions: Counter[str] = Counter()
    barrier_counter: Counter[str] = Counter()
    trigger_counter: Counter[str] = Counter()
    segment_acc: dict[str, dict] = {}
    per_round: list[dict] = []
    total_events = consumer_events = market_events = 0

    for rnd in range(1, rounds + 1):
        stage = ROUND_STAGES[rnd]
        touchpoint_pool = ROUND_TOUCHPOINTS[rnd]
        round_actions: Counter[str] = Counter()
        sent_sum = trial_sum = interest_sum = 0.0
        positive = 0
        round_barriers: Counter[str] = Counter()
        round_triggers: Counter[str] = Counter()

        for idx, agent in enumerate(consumers):
            profile = consumer_profile[agent.id]
            state = consumer_state[agent.id]
            result = score_round(profile, agent.segment_name or "", ctx, rnd, state, idx, seed)
            touchpoint = choose_touchpoint(profile, touchpoint_pool, idx)

            event = Event(
                project_id=project_id,
                round_number=rnd,
                stage_name=stage,
                agent_id=agent.id,
                agent_type="consumer",
                segment_name=agent.segment_name,
                touchpoint=touchpoint,
                action_type=result["action_type"],
                content_seen=touchpoint,
                reasoning=result["reasoning"],
                generated_reaction=result["generated_reaction"],
                emotional_tone=result["emotional_tone"],
                confidence_score=result["confidence_score"],
                sentiment_score=result["sentiment_score"],
                trial_probability=result["trial_probability"],
                purchase_intent_score=result["purchase_intent_score"],
                repeat_probability=result["repeat_probability"],
                trust_change=result["trust_change"],
                barrier_detected=result["barrier_detected"],
                trigger_detected=result["trigger_detected"],
                run_type=run_type,
                scenario_id=scenario_id,
                scores_json=json.dumps(result["scores"], ensure_ascii=False),
            )
            db.add(event)
            consumer_events += 1
            total_events += 1

            act = result["action_type"]
            all_actions[act] += 1
            round_actions[act] += 1
            sent_sum += result["sentiment_score"]
            trial_sum += result["trial_probability"]
            interest_sum += result["scores"].get("interest", 0.0)
            if result["sentiment_score"] >= 0.55:
                positive += 1
            if result["barrier_detected"]:
                barrier_counter[result["barrier_detected"]] += 1
                round_barriers[result["barrier_detected"]] += 1
            if result["trigger_detected"]:
                trigger_counter[result["trigger_detected"]] += 1
                round_triggers[result["trigger_detected"]] += 1

            seg = agent.segment_name or "unknown"
            acc = segment_acc.setdefault(
                seg, {"n": 0, "trial_sum": 0.0, "sentiment_sum": 0.0, "purchases": 0, "actions": Counter()}
            )
            acc["n"] += 1
            acc["trial_sum"] += result["trial_probability"]
            acc["sentiment_sum"] += result["sentiment_score"]
            acc["actions"][act] += 1
            if act == "purchase_trial":
                acc["purchases"] += 1

            action_history[agent.id].append(
                {"round": rnd, "stage": stage, "action": act, "trial_probability": result["trial_probability"]}
            )
            sim_memory[agent.id].append(
                f"R{rnd} ({stage}): {act} — {result['generated_reaction']}"
            )

        n = max(1, len(consumers))
        aggregate = {
            "avg_interest": clamp(interest_sum / n),
            "avg_trial_prob": clamp(trial_sum / n),
            "avg_sentiment": clamp(sent_sum / n),
            "positive_share": clamp(positive / n),
            "top_barrier": round_barriers.most_common(1)[0][0] if round_barriers else None,
            "top_trigger": round_triggers.most_common(1)[0][0] if round_triggers else None,
            "n": len(consumers),
        }

        round_market_events = 0
        if include_actors:
            for midx, actor in enumerate(market):
                ma_profile = json.loads(actor.profile_json or "{}")
                ma = market_actor_action(
                    ma_profile, actor.role or "", ctx, rnd, aggregate, seed, midx
                )
                event = Event(
                    project_id=project_id,
                    round_number=rnd,
                    stage_name=stage,
                    agent_id=actor.id,
                    agent_type="market_actor",
                    segment_name=None,
                    touchpoint=actor.role,
                    action_type=ma["action_type"],
                    content_seen=f"aggregate consumer signal (round {rnd})",
                    reasoning=ma["reasoning"],
                    generated_reaction=ma["generated_reaction"],
                    emotional_tone=ma["emotional_tone"],
                    confidence_score=ma["confidence_score"],
                    sentiment_score=ma["sentiment_score"],
                    trust_change=ma["trust_change"],
                    barrier_detected=ma["barrier_detected"],
                    trigger_detected=ma["trigger_detected"],
                    run_type=run_type,
                    scenario_id=scenario_id,
                    scores_json=json.dumps(ma["scores"], ensure_ascii=False),
                )
                db.add(event)
                market_events += 1
                total_events += 1
                round_market_events += 1
                all_actions[ma["action_type"]] += 1
                action_history[actor.id].append(
                    {"round": rnd, "stage": stage, "action": ma["action_type"], "launch_impact": ma["trust_change"]}
                )
                sim_memory[actor.id].append(
                    f"R{rnd} ({stage}): {ma['action_type']} — {ma['generated_reaction']}"
                )

        per_round.append(
            {
                "round_number": rnd,
                "stage_name": stage,
                "consumer_events": len(consumers),
                "market_actor_events": round_market_events,
                "action_distribution": dict(round_actions),
                "avg_sentiment": aggregate["avg_sentiment"],
                "avg_trial_probability": aggregate["avg_trial_prob"],
            }
        )

    # persist per-agent memory + action history (baseline runs only)
    if persist_agent_state:
        for agent in consumers + market:
            agent.action_history_json = json.dumps(action_history[agent.id], ensure_ascii=False)
            agent.simulation_memory_json = json.dumps(sim_memory[agent.id], ensure_ascii=False)

    db.commit()

    segment_summary = {
        seg: {
            "n": acc["n"],
            "avg_trial_probability": round(acc["trial_sum"] / acc["n"], 3) if acc["n"] else 0.0,
            "avg_sentiment": round(acc["sentiment_sum"] / acc["n"], 3) if acc["n"] else 0.0,
            "trial_purchases": acc["purchases"],
            "top_action": acc["actions"].most_common(1)[0][0] if acc["actions"] else None,
        }
        for seg, acc in segment_acc.items()
    }

    return {
        "simulation_status": "completed",
        "source_mode": "fallback",
        "rounds_run": rounds,
        "total_events": total_events,
        "consumer_events": consumer_events,
        "market_actor_events": market_events,
        "action_distribution": dict(all_actions),
        "segment_summary": segment_summary,
        "top_barriers": barrier_counter.most_common(5),
        "top_triggers": trigger_counter.most_common(5),
        "per_round": per_round,
        "token_usage": None,
    }


# --- queries ----------------------------------------------------------------


def list_events(
    db: Session,
    project_id: str,
    limit: int = 100,
    offset: int = 0,
    round_number: int | None = None,
    action_type: str | None = None,
    agent_id: str | None = None,
    agent_type: str | None = None,
    segment_name: str | None = None,
) -> list[Event]:
    q = db.query(Event).filter(Event.project_id == project_id, Event.run_type == "baseline")
    if round_number is not None:
        q = q.filter(Event.round_number == round_number)
    if action_type:
        q = q.filter(Event.action_type == action_type)
    if agent_id:
        q = q.filter(Event.agent_id == agent_id)
    if agent_type:
        q = q.filter(Event.agent_type == agent_type)
    if segment_name:
        q = q.filter(Event.segment_name == segment_name)
    return (
        q.order_by(Event.round_number, Event.agent_type, Event.timestamp)
        .offset(offset)
        .limit(limit)
        .all()
    )


def get_event(db: Session, project_id: str, event_id: str) -> Event | None:
    return (
        db.query(Event)
        .filter(Event.project_id == project_id, Event.id == event_id)
        .first()
    )


def events_summary(db: Session, project_id: str) -> dict:
    events = (
        db.query(Event)
        .filter(Event.project_id == project_id, Event.run_type == "baseline")
        .order_by(Event.round_number)
        .all()
    )
    consumer = [e for e in events if e.agent_type == "consumer"]
    market = [e for e in events if e.agent_type == "market_actor"]
    rounds = sorted({e.round_number for e in events})

    all_actions: Counter[str] = Counter(e.action_type for e in events)
    barrier_counter: Counter[str] = Counter(e.barrier_detected for e in consumer if e.barrier_detected)
    trigger_counter: Counter[str] = Counter(e.trigger_detected for e in consumer if e.trigger_detected)

    per_round = []
    segment_acc: dict[str, dict] = {}
    for rnd in rounds:
        rc = [e for e in consumer if e.round_number == rnd]
        rm = [e for e in market if e.round_number == rnd]
        n = max(1, len(rc))
        per_round.append(
            {
                "round_number": rnd,
                "stage_name": ROUND_STAGES.get(rnd, ""),
                "consumer_events": len(rc),
                "market_actor_events": len(rm),
                "action_distribution": dict(Counter(e.action_type for e in rc)),
                "avg_sentiment": round(sum(e.sentiment_score or 0 for e in rc) / n, 3),
                "avg_trial_probability": round(sum(e.trial_probability or 0 for e in rc) / n, 3),
            }
        )

    for e in consumer:
        seg = e.segment_name or "unknown"
        acc = segment_acc.setdefault(
            seg, {"n": 0, "trial_sum": 0.0, "sentiment_sum": 0.0, "purchases": 0, "actions": Counter()}
        )
        acc["n"] += 1
        acc["trial_sum"] += e.trial_probability or 0.0
        acc["sentiment_sum"] += e.sentiment_score or 0.0
        acc["actions"][e.action_type] += 1
        if e.action_type == "purchase_trial":
            acc["purchases"] += 1

    segment_summary = {
        seg: {
            "n": acc["n"],
            "avg_trial_probability": round(acc["trial_sum"] / acc["n"], 3) if acc["n"] else 0.0,
            "avg_sentiment": round(acc["sentiment_sum"] / acc["n"], 3) if acc["n"] else 0.0,
            "trial_purchases": acc["purchases"],
            "top_action": acc["actions"].most_common(1)[0][0] if acc["actions"] else None,
        }
        for seg, acc in segment_acc.items()
    }

    return {
        "total_events": len(events),
        "consumer_events": len(consumer),
        "market_actor_events": len(market),
        "rounds_run": len(rounds),
        "action_distribution": dict(all_actions),
        "per_round": per_round,
        "segment_summary": segment_summary,
        "top_barriers": barrier_counter.most_common(5),
        "top_triggers": trigger_counter.most_common(5),
    }
