"""Aggregated project overview (Phase 19) for the Workspace Home.

Read-only assembly from existing services. Includes a deterministic
"next recommended action" derived from the pipeline state (and stale live runs).
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DecisionLogEntry, Event, Project, ReportSnapshot, ScenarioRun
from app.schemas.overview import (
    ActivityItem,
    NextAction,
    OverviewCounts,
    OverviewOut,
    PipelineStatus,
)
from app.services import (
    briefing_service,
    live_simulation_service,
    project_service,
    report_service,
    scorecard_service,
    timeline_service,
)


def _count(db: Session, model, project_id: str, *, baseline_only: bool = False) -> int:
    stmt = select(func.count(model.id)).where(model.project_id == project_id)
    if baseline_only:
        stmt = stmt.where(model.run_type == "baseline")
    return db.execute(stmt).scalar_one()


def _next_action(status: PipelineStatus, stale_live: bool) -> NextAction:
    if stale_live:
        return NextAction(action="resolve_stale_run", label="Resolve the stale live run", surface="studio",
                           reason="A live run is stuck in 'running' with no recent activity — cancel it and start again.")
    if not status.has_brief:
        return NextAction(action="submit_brief", label="Submit the innovation brief", surface="workflow",
                          reason="No brief yet — start by adding the product/concept brief.")
    if not status.has_ontology:
        return NextAction(action="analyze_ontology", label="Analyze the brief (ontology)", surface="workflow",
                          reason="Brief is in — extract the FMCG ontology next.")
    if not status.has_agents:
        return NextAction(action="generate_agents", label="Generate consumer + market agents", surface="workflow",
                          reason="Ontology is ready — generate the agent panel.")
    if not status.has_simulation:
        return NextAction(action="run_live_simulation", label="Run the simulation (try Live Mode)", surface="studio",
                          reason="Agents are ready — run the 6-round simulation and watch it live.")
    if not status.has_report:
        return NextAction(action="generate_report", label="Generate the strategic report", surface="report",
                          reason="Simulation is done — synthesize the 16-section report.")
    if not status.has_briefing:
        return NextAction(action="generate_briefing", label="Generate the executive briefing", surface="briefing",
                          reason="Report is ready — produce the stakeholder briefing.")
    return NextAction(action="explore", label="Explore scenarios, sensitivity, snapshots & compare", surface="scenarios",
                      reason="Everything is ready — stress-test and snapshot decisions, then compare concepts.")


def build_overview(db: Session, project_id: str) -> OverviewOut:
    project: Project | None = project_service.get_project(db, project_id)
    if project is None:
        raise ValueError("project_not_found")

    env = project_service.envelope_counts(db, project_id)
    report_row = report_service.get_report_row(db, project_id)
    briefing_row = briefing_service.get_briefing_row(db, project_id)

    status = PipelineStatus(
        has_brief=env["has_brief"],
        has_ontology=env["has_ontology"],
        has_agents=env["agents_count"] > 0,
        has_simulation=env["events_count"] > 0,
        has_report=env["has_report"],
        has_briefing=briefing_row is not None,
    )

    counts = OverviewCounts(
        agents=env["agents_count"],
        events=env["events_count"],
        snapshots=_count(db, ReportSnapshot, project_id),
        scenarios=_count(db, ScenarioRun, project_id),
        decisions=_count(db, DecisionLogEntry, project_id),
    )

    latest_scorecard = None
    if report_row is not None:
        try:
            latest_scorecard = scorecard_service.build_for_project(db, project_id, project.name).model_dump()
        except ValueError:
            latest_scorecard = None

    latest_briefing_summary = briefing_service.get_summary(briefing_row).model_dump() if briefing_row else None

    runs = live_simulation_service.list_runs(db, project_id)
    latest_live = runs[0] if runs else None
    stale_live = any(live_simulation_service.is_stale(r) for r in runs)
    latest_live_run = (
        live_simulation_service.to_out(latest_live, has_events=counts.events > 0).model_dump() if latest_live else None
    )

    timeline = timeline_service.build_timeline(db, project)
    recent = [
        ActivityItem(timestamp=t.timestamp.isoformat() if t.timestamp else None, type=t.type, title=t.title, description=t.description)
        for t in list(reversed(timeline.timeline))[:8]
    ]

    return OverviewOut(
        project={"id": project.id, "name": project.name, "category": project.category, "market": project.market, "status": project.status},
        pipeline_status=status,
        counts=counts,
        latest_scorecard=latest_scorecard,
        latest_briefing_summary=latest_briefing_summary,
        latest_live_run=latest_live_run,
        next_recommended_action=_next_action(status, stale_live),
        recent_activity=recent,
    )
