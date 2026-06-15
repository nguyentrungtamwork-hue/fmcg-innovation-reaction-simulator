"""Confidence calibration (Phase 11).

Explains *why* the simulation's confidence is high/medium/low by decomposing it
into weighted, deterministic drivers (data coverage + grounding quality), and is
explicit that the absence of real sales/social data caps confidence. This does
NOT modify the report's own confidence score — it is a separate explainability view.
"""
from __future__ import annotations

import json

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Event, Ontology
from app.schemas.insight import ConfidenceDriver, ConfidenceOut
from app.schemas.ontology import OntologyPayload
from app.services import ontology_service, report_service

_DISCLAIMER = (
    "Confidence reflects internal data coverage and grounding quality only. It is NOT validated "
    "against real launch outcomes — treat all output as exploratory decision support."
)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def _label(score: float) -> str:
    return "high" if score >= 0.75 else "medium" if score >= 0.5 else "low"


def compute(db: Session, project_id: str) -> ConfidenceOut:
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise ValueError("report_required")

    ont_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    payload = OntologyPayload.model_validate(json.loads(ont_row.data_json or "{}")) if ont_row else OntologyPayload()

    consumers = db.execute(
        select(Agent).where(Agent.project_id == project_id, Agent.agent_type == "consumer")
    ).scalars().all()
    consumer_count = len(consumers)
    segments = {a.segment_name for a in consumers if a.segment_name}

    event_count = db.execute(
        select(func.count(Event.id)).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalar_one()
    evidence_events = db.execute(
        select(func.count(Event.id)).where(
            Event.project_id == project_id,
            Event.run_type == "baseline",
            (Event.trigger_detected.isnot(None)) | (Event.barrier_detected.isnot(None)),
        )
    ).scalar_one()

    missing = len(payload.missing_information)
    claims = len(payload.claim_analysis)
    grounded_llm = report.source_mode == "llm_enhanced"

    drivers = [
        ConfidenceDriver(
            factor="ontology_completeness", weight=0.18,
            score=_clamp01(0.4 + 0.04 * len(payload.entities) + (0.2 if claims else 0)),
            explanation=f"{len(payload.entities)} ontology entities, {claims} analyzed claims.",
        ),
        ConfidenceDriver(
            factor="agent_coverage", weight=0.15,
            score=_clamp01(consumer_count / 50.0),
            explanation=f"{consumer_count} consumer agents simulated.",
        ),
        ConfidenceDriver(
            factor="event_volume", weight=0.12,
            score=_clamp01(event_count / 330.0),
            explanation=f"{event_count} baseline simulation events.",
        ),
        ConfidenceDriver(
            factor="segment_diversity", weight=0.12,
            score=_clamp01(len(segments) / 8.0),
            explanation=f"{len(segments)} distinct consumer segments represented.",
        ),
        ConfidenceDriver(
            factor="evidence_density", weight=0.13,
            score=_clamp01(evidence_events / event_count) if event_count else 0.0,
            explanation=f"{evidence_events}/{event_count} events carry a detected trigger or barrier.",
        ),
        ConfidenceDriver(
            factor="claim_richness", weight=0.10,
            score=_clamp01(claims / 3.0),
            explanation=f"{claims} claims have a clarity/credibility assessment.",
        ),
        ConfidenceDriver(
            factor="information_gaps", weight=0.10,
            score=_clamp01(1.0 - missing / 8.0),
            explanation=f"{missing} open 'missing information' items in the ontology.",
        ),
        ConfidenceDriver(
            factor="grounding_mode", weight=0.05,
            score=1.0 if grounded_llm else 0.6,
            explanation=("LLM-enhanced narrative." if grounded_llm else "Deterministic fallback (no LLM) — grounded but conservative."),
        ),
        ConfidenceDriver(
            factor="real_world_data", weight=0.05,
            score=0.3,
            explanation="No real sales/scan or social-listening data informs the model — this caps confidence.",
        ),
    ]

    overall = round(sum(d.score * d.weight for d in drivers), 3)

    risks: list[str] = ["No real sales/scan or social-listening data — results are simulated."]
    if not grounded_llm:
        risks.append("Running in deterministic fallback mode (no LLM narrative enrichment).")
    if missing:
        risks.append(f"{missing} unresolved 'missing information' items in the brief/ontology.")
    if consumer_count < 50:
        risks.append(f"Only {consumer_count} consumer agents — below the default cohort of 50.")
    if event_count and evidence_events / event_count < 0.3:
        risks.append("Low evidence density — few events carry an explicit trigger/barrier.")

    improve = [
        "Fill the ontology's 'missing information' gaps in the brief and re-analyze.",
        "Validate the top barriers and claims with real consumer research (surveys, sensory tests).",
        "Run in-market A/B tests for the highest-sensitivity levers before scaling.",
    ]
    if not grounded_llm:
        improve.append("Configure an LLM key to enrich the narrative (does not change the underlying scores).")

    return ConfidenceOut(
        project_id=project_id,
        overall_confidence=overall,
        confidence_label=_label(overall),
        drivers=drivers,
        confidence_risks=risks,
        how_to_improve_confidence=improve,
        disclaimer=_DISCLAIMER,
    )
