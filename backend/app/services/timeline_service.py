"""Merged per-project timeline (Phase 13).

Combines lifecycle milestones (project/brief/ontology/agents/simulation/report),
snapshots, scenarios, and decision-log entries into one chronological view. Derived
from existing rows; read-only.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import (
    Agent,
    Brief,
    DecisionLogEntry,
    Event,
    Ontology,
    Project,
    Report,
    ReportSnapshot,
    ScenarioRun,
)
from app.schemas.history import TimelineItem, TimelineOut


def build_timeline(db: Session, project: Project) -> TimelineOut:
    pid = project.id
    items: list[TimelineItem] = []

    items.append(TimelineItem(timestamp=project.created_at, type="project_created", title="Project created", description=project.name))

    brief = db.execute(select(Brief).where(Brief.project_id == pid).order_by(Brief.created_at)).scalars().first()
    if brief:
        items.append(TimelineItem(timestamp=brief.created_at, type="brief_submitted", title="Brief submitted", related_id=brief.id))

    ont = db.execute(select(Ontology).where(Ontology.project_id == pid)).scalars().first()
    if ont:
        items.append(TimelineItem(timestamp=ont.created_at, type="ontology_generated", title="Ontology extracted", related_id=ont.id))

    first_agent = db.execute(
        select(func.min(Agent.created_at)).where(Agent.project_id == pid)
    ).scalar_one_or_none()
    if first_agent:
        n = db.execute(select(func.count(Agent.id)).where(Agent.project_id == pid)).scalar_one()
        items.append(TimelineItem(timestamp=first_agent, type="agents_generated", title="Agents generated", description=f"{n} agents"))

    first_event = db.execute(
        select(func.min(Event.timestamp)).where(Event.project_id == pid, Event.run_type == "baseline")
    ).scalar_one_or_none()
    if first_event:
        n = db.execute(
            select(func.count(Event.id)).where(Event.project_id == pid, Event.run_type == "baseline")
        ).scalar_one()
        items.append(TimelineItem(timestamp=first_event, type="simulation_run", title="Simulation run", description=f"{n} baseline events"))

    report = db.execute(select(Report).where(Report.project_id == pid)).scalars().first()
    if report:
        items.append(
            TimelineItem(
                timestamp=report.updated_at or report.created_at,
                type="report_generated",
                title="Report generated",
                description=f"confidence {report.confidence_score}",
                related_id=report.id,
            )
        )

    for sc in db.execute(select(ScenarioRun).where(ScenarioRun.project_id == pid)).scalars().all():
        items.append(
            TimelineItem(timestamp=sc.created_at, type="scenario_created", title=f"Scenario: {sc.scenario_name}", related_id=sc.id)
        )

    for snap in db.execute(select(ReportSnapshot).where(ReportSnapshot.project_id == pid)).scalars().all():
        items.append(
            TimelineItem(
                timestamp=snap.created_at,
                type="snapshot_created",
                title=f"Snapshot: {snap.snapshot_name}",
                description=snap.description,
                related_id=snap.id,
            )
        )

    for d in db.execute(select(DecisionLogEntry).where(DecisionLogEntry.project_id == pid)).scalars().all():
        items.append(
            TimelineItem(
                timestamp=d.created_at,
                type=f"decision:{d.entry_type}",
                title=d.title,
                description=d.body,
                related_id=d.id,
                metadata={"entry_type": d.entry_type},
            )
        )

    items.sort(key=lambda i: i.timestamp)
    return TimelineOut(project_id=pid, timeline=items)
