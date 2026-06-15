"""Strategic launch report orchestrator (Phase 6).

Reads the persisted brief + ontology + agents + simulation events, builds a
deterministic 16-section `ReportPayload` via `report_builder`, optionally
enhances the narrative with an LLM (graceful fallback), persists the `Report`
row (replacing any prior report for the project), and exposes query helpers.

Preconditions raised as `ValueError` (mapped to 409 by the API layer):
    brief_required | ontology_required | agents_required | events_required
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent, Brief, Event, Ontology, Report
from app.schemas.ontology import OntologyPayload
from app.schemas.report import ReportGenerateIn, ReportPayload, ReportSummaryOut
from app.services import app_log_service, ontology_service, report_builder
from app.services.llm_client import LLMClient
from app.services.simulation_scoring import build_context

logger = logging.getLogger(__name__)


# --- input loading ----------------------------------------------------------


def _latest_brief(db: Session, project_id: str) -> Brief | None:
    return db.execute(
        select(Brief).where(Brief.project_id == project_id).order_by(Brief.created_at.desc())
    ).scalars().first()


def _load_inputs(
    db: Session, project_id: str
) -> tuple[dict, OntologyPayload, list[Agent], list[Agent], list[Event]]:
    brief = _latest_brief(db, project_id)
    if brief is None:
        raise ValueError("brief_required")
    structured: dict = {}
    if brief.structured_json:
        try:
            structured = json.loads(brief.structured_json) or {}
        except json.JSONDecodeError:
            structured = {}

    ontology_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    if ontology_row is None:
        raise ValueError("ontology_required")
    ontology = OntologyPayload.model_validate(json.loads(ontology_row.data_json or "{}"))

    agents = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
    consumers = [a for a in agents if a.agent_type == "consumer"]
    market = [a for a in agents if a.agent_type == "market_actor"]
    if not consumers:
        raise ValueError("agents_required")

    events = db.execute(
        select(Event)
        .where(Event.project_id == project_id, Event.run_type == "baseline")
        .order_by(Event.round_number, Event.timestamp)
    ).scalars().all()
    if not events:
        raise ValueError("events_required")

    return structured, ontology, consumers, market, events


# --- summary ----------------------------------------------------------------


def _build_summary(payload: ReportPayload) -> ReportSummaryOut:
    es = payload.executive_summary
    top_segments = [
        {
            "segment_name": s.segment_name,
            "average_trial_probability": s.average_trial_probability,
            "average_repeat_probability": s.average_repeat_probability,
            "dominant_actions": s.dominant_actions,
        }
        for s in payload.segment_reaction_map[:3]
    ]
    top_triggers = [
        {"trigger": t.trigger, "frequency": t.frequency, "affected_segments": t.affected_segments}
        for t in payload.purchase_trigger_analysis[:3]
    ]
    top_barriers = [
        {"barrier": b.barrier, "frequency": b.frequency, "severity_level": b.severity_level}
        for b in payload.adoption_barrier_analysis[:3]
    ]
    key_recs = [r.recommendation for r in payload.strategic_recommendations[:5]]
    return ReportSummaryOut(
        overall_market_reaction=es.overall_market_reaction,
        top_opportunity=es.top_opportunity,
        top_risk=es.top_risk,
        top_segments=top_segments,
        top_triggers=top_triggers,
        top_barriers=top_barriers,
        key_recommendations=key_recs,
    )


# --- optional LLM narrative enhancement -------------------------------------

_NARRATIVE_SYSTEM = (
    "You are an FMCG launch strategist. Rewrite the provided executive-summary fields to be "
    "sharper and more board-ready. You MUST NOT invent any new facts, numbers, segments, or "
    "findings — only rephrase what is given. Preserve every quantitative figure exactly. "
    "Return strict JSON with keys: overall_market_reaction, top_opportunity, top_risk, "
    "key_recommendation."
)


def _maybe_enhance(payload: ReportPayload, llm_client: LLMClient | None) -> str:
    """Optionally rewrite the executive summary in place. Returns the source mode."""
    client = llm_client or LLMClient()
    if not client.configured:
        return "deterministic"
    es = payload.executive_summary
    user = json.dumps(
        {
            "overall_market_reaction": es.overall_market_reaction,
            "top_opportunity": es.top_opportunity,
            "top_risk": es.top_risk,
            "key_recommendation": es.key_recommendation,
        }
    )
    try:
        data = client.chat_json(_NARRATIVE_SYSTEM, user)
        for key in ("overall_market_reaction", "top_opportunity", "top_risk", "key_recommendation"):
            val = data.get(key)
            if isinstance(val, str) and val.strip():
                setattr(es, key, val.strip())
        return "llm_enhanced"
    except Exception as e:  # noqa: BLE001 — never let LLM failure break report generation
        logger.warning("LLM narrative enhancement failed; using deterministic report. error=%s", e)
        return "deterministic"


# --- generation -------------------------------------------------------------


def generate_report(
    db: Session,
    project_id: str,
    params: ReportGenerateIn | None = None,
    llm_client: LLMClient | None = None,
) -> Report:
    """Build, (optionally) enhance, and persist the strategic launch report.

    Replaces any existing report for the project so there are never stale
    duplicates. Returns the persisted `Report` row.
    """
    params = params or ReportGenerateIn()
    structured, ontology, consumers, market, events = _load_inputs(db, project_id)

    payload, confidence = report_builder.build_report(structured, ontology, consumers, market, events)

    source_mode = "deterministic"
    if params.use_llm_narrative:
        source_mode = _maybe_enhance(payload, llm_client)

    ctx = build_context(ontology)
    markdown = report_builder.render_markdown(payload, brand=ctx.brand, product=ctx.product)

    # Replace any existing report(s) for the project.
    existing = db.execute(
        select(Report).where(Report.project_id == project_id)
    ).scalars().all()
    for r in existing:
        db.delete(r)
    db.flush()

    report = Report(
        project_id=project_id,
        report_type="strategic_launch_report",
        payload_json=payload.model_dump_json(),
        markdown=markdown,
        source_mode=source_mode,
        confidence_score=confidence,
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    app_log_service.log_report_generated(db, project_id=project_id, message=f"Strategic report generated ({source_mode})")
    return report


# --- query helpers ----------------------------------------------------------


def get_report_row(db: Session, project_id: str) -> Report | None:
    return db.execute(
        select(Report).where(Report.project_id == project_id).order_by(Report.created_at.desc())
    ).scalars().first()


def get_payload(report: Report) -> ReportPayload:
    return ReportPayload.model_validate(json.loads(report.payload_json or "{}"))


def get_summary(report: Report) -> ReportSummaryOut:
    return _build_summary(get_payload(report))
