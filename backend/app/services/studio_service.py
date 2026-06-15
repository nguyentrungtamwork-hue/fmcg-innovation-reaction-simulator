"""Agent Studio aggregated read-only state (Phase 16).

Assembles existing persisted data (project + agents + baseline events + summary)
into one payload for the visual studio, and derives a bounded, transparent
interaction graph. This is READ-ONLY — no simulation scoring is changed, no rows
are written, baseline events are untouched.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Event, Project
from app.schemas.studio import StudioEdge, StudioGraph, StudioNode, StudioStateOut
from app.services import project_service, simulation_service

_MAX_EDGES = 160


def _agent_dicts(db: Session, project_id: str) -> list[dict]:
    agents = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
    out = []
    for a in agents:
        out.append(
            {
                "id": a.id,
                "name": a.name,
                "agent_type": a.agent_type,
                "segment_name": a.segment_name,
                "role": a.role,
                "confidence_score": a.confidence_score,
            }
        )
    return out


def _event_dicts(db: Session, project_id: str) -> list[dict]:
    events = db.execute(
        select(Event)
        .where(Event.project_id == project_id, Event.run_type == "baseline")
        .order_by(Event.round_number, Event.id)
    ).scalars().all()
    out = []
    for e in events:
        out.append(
            {
                "id": e.id,
                "round_number": e.round_number,
                "stage_name": e.stage_name,
                "agent_id": e.agent_id,
                "agent_type": e.agent_type,
                "segment_name": e.segment_name,
                "touchpoint": e.touchpoint,
                "action_type": e.action_type,
                "generated_reaction": e.generated_reaction,
                "reasoning": e.reasoning,
                "emotional_tone": e.emotional_tone,
                "confidence_score": e.confidence_score,
                "sentiment_score": e.sentiment_score,
                "trial_probability": e.trial_probability,
                "purchase_intent_score": e.purchase_intent_score,
                "repeat_probability": e.repeat_probability,
                "barrier_detected": e.barrier_detected,
                "trigger_detected": e.trigger_detected,
            }
        )
    return out


def _build_graph(agents: list[dict], events: list[dict]) -> StudioGraph:
    # nodes: one per agent, with light aggregates
    by_agent_events: dict[str, list[dict]] = defaultdict(list)
    for e in events:
        by_agent_events[e["agent_id"]].append(e)

    nodes: list[StudioNode] = []
    for a in agents:
        evs = by_agent_events.get(a["id"], [])
        sentiments = [e["sentiment_score"] for e in evs if e["sentiment_score"] is not None]
        actions = Counter(e["action_type"] for e in evs)
        nodes.append(
            StudioNode(
                id=a["id"],
                label=a["name"],
                type=a["agent_type"],
                group=(a["segment_name"] or a["role"] or "Unknown"),
                event_count=len(evs),
                avg_sentiment=round(sum(sentiments) / len(sentiments), 3) if sentiments else 0.0,
                dominant_action=actions.most_common(1)[0][0] if actions else None,
            )
        )

    # edges: bounded, transparent heuristic links
    edges: list[StudioEdge] = []
    seen: set[tuple[str, str]] = set()

    def _add(src: str, tgt: str, reason: str, rnd: int) -> None:
        if len(edges) >= _MAX_EDGES or src == tgt:
            return
        key = tuple(sorted((src, tgt)))
        if key in seen:
            return
        seen.add(key)
        edges.append(StudioEdge(source=src, target=tgt, reason=reason, round_number=rnd))

    by_round: dict[int, list[dict]] = defaultdict(list)
    for e in events:
        by_round[e["round_number"]].append(e)

    for rnd in sorted(by_round):
        round_events = by_round[rnd]
        consumers = [e for e in round_events if e["agent_type"] == "consumer"]
        market = [e for e in round_events if e["agent_type"] == "market_actor"]

        # shared trigger / barrier -> star to the group hub
        for attr, label in (("trigger_detected", "shared trigger"), ("barrier_detected", "shared barrier")):
            groups: dict[str, list[str]] = defaultdict(list)
            for e in consumers:
                if e[attr]:
                    groups[e[attr]].append(e["agent_id"])
            for value, agent_ids in groups.items():
                uniq = sorted(set(agent_ids))
                hub = uniq[0]
                for other in uniq[1:6]:  # cap fan-out per group
                    _add(hub, other, f"{label}: {value} (round {rnd})", rnd)

        # market-actor round impact -> link to the round's first consumer hub
        if consumers and market:
            hub = sorted({e["agent_id"] for e in consumers})[0]
            for m in market:
                _add(m["agent_id"], hub, f"market-actor round impact (round {rnd})", rnd)

    return StudioGraph(nodes=nodes, edges=edges)


def build_state(db: Session, project_id: str) -> StudioStateOut:
    project: Project | None = project_service.get_project(db, project_id)
    if project is None:
        raise ValueError("project_not_found")

    agents = _agent_dicts(db, project_id)
    events = _event_dicts(db, project_id)
    summary = simulation_service.events_summary(db, project_id)
    rounds = summary.get("per_round", [])
    graph = _build_graph(agents, events)

    return StudioStateOut(
        project={
            "id": project.id,
            "name": project.name,
            "category": project.category,
            "market": project.market,
            "status": project.status,
        },
        agents=agents,
        events=events,
        events_summary=summary,
        rounds=rounds,
        graph=graph,
    )
