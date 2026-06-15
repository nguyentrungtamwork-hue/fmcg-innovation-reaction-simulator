"""Portfolio listing + concept comparison (Phase 12).

Aggregates per-project scorecards (built from existing report/ontology/confidence/
assumptions data) into a portfolio view and a side-by-side comparison. Transparent
and deterministic; nothing about project performance is invented.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Event, Project
from app.schemas.portfolio import (
    CompareIn,
    CompareItem,
    CompareOut,
    ComparisonSummary,
    PortfolioOut,
    PortfolioProjectRow,
    PortfolioSummary,
    Scorecard,
)
from app.services import project_service, report_service, scorecard_service, snapshot_service


def _has_simulation(db: Session, project_id: str) -> bool:
    n = db.execute(
        select(func.count(Event.id)).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalar_one()
    return n > 0


def build_portfolio(db: Session, *, status_filter: str | None = None) -> PortfolioOut:
    projects = project_service.list_projects(db)
    rows: list[PortfolioProjectRow] = []
    cards: dict[str, Scorecard] = {}

    for p in projects:
        has_report = report_service.get_report_row(db, p.id) is not None
        row = PortfolioProjectRow(
            project_id=p.id,
            project_name=p.name,
            status=p.status,
            has_report=has_report,
            has_simulation=_has_simulation(db, p.id),
        )
        if has_report:
            try:
                sc = scorecard_service.build_for_project(db, p.id, p.name)
                cards[p.id] = sc
                row.overall_score = sc.overall_score
                row.confidence_score = sc.confidence_score
                row.trial_potential_score = sc.trial_potential_score
                row.repeat_potential_score = sc.repeat_potential_score
                row.risk_score = sc.risk_score
                row.top_opportunity = sc.top_opportunity
                row.top_risk = sc.top_risk
                row.recommended_next_step = sc.recommended_next_step
            except ValueError:
                pass
        rows.append(row)

    def _best(attr: str, *, maximize: bool) -> str | None:
        if not cards:
            return None
        chosen = (max if maximize else min)(cards.values(), key=lambda c: getattr(c, attr))
        return chosen.project_name

    summary = PortfolioSummary(
        total_projects=len(projects),
        report_ready_projects=len(cards),
        highest_score_project=_best("overall_score", maximize=True),
        highest_risk_project=_best("risk_score", maximize=True),
        best_trial_project=_best("trial_potential_score", maximize=True),
        best_repeat_project=_best("repeat_potential_score", maximize=True),
    )
    return PortfolioOut(projects=rows, summary=summary)


def compare(db: Session, payload: CompareIn) -> CompareOut:
    items: list[CompareItem] = []

    for pid in payload.project_ids:
        project: Project | None = project_service.get_project(db, pid)
        if project is None:
            continue
        try:
            sc = scorecard_service.build_for_project(db, pid, project.name)
        except ValueError:
            continue
        items.append(CompareItem(type="project", project_id=pid, name=project.name, scorecard=sc))

    if payload.include_snapshots or payload.snapshot_ids:
        for sid in payload.snapshot_ids:
            # snapshot ids are globally unique; find owning project via the row
            from app.models import ReportSnapshot

            snap = db.get(ReportSnapshot, sid)
            if snap is None:
                continue
            sc = snapshot_service.scorecard_of(snap)
            items.append(
                CompareItem(
                    type="snapshot",
                    project_id=snap.project_id,
                    snapshot_id=snap.id,
                    name=f"{sc.project_name} — {snap.snapshot_name}",
                    scorecard=sc,
                )
            )

    if not items:
        return CompareOut(
            items=[],
            comparison_summary=ComparisonSummary(),
            dimension_rankings={},
            recommendation="No report-ready projects/snapshots to compare.",
        )

    def _name(item: CompareItem) -> str:
        return item.name

    def _rank(attr: str, *, maximize: bool) -> list[str]:
        return [_name(i) for i in sorted(items, key=lambda i: getattr(i.scorecard, attr), reverse=maximize)]

    best_overall = _rank("overall_score", maximize=True)[0]
    best_trial = _rank("trial_potential_score", maximize=True)[0]
    best_repeat = _rank("repeat_potential_score", maximize=True)[0]
    lowest_risk = _rank("risk_score", maximize=False)[0]
    highest_conf = _rank("confidence_score", maximize=True)[0]
    # "most needs validation" = lowest confidence + highest assumption risk
    needs_validation = sorted(
        items, key=lambda i: (i.scorecard.confidence_score - i.scorecard.assumption_risk_score / 100.0)
    )[0].name

    summary = ComparisonSummary(
        best_overall=best_overall,
        best_trial=best_trial,
        best_repeat=best_repeat,
        lowest_risk=lowest_risk,
        highest_confidence=highest_conf,
        most_needs_validation=needs_validation,
    )

    dimension_rankings = {
        "overall_score": _rank("overall_score", maximize=True),
        "trial_potential_score": _rank("trial_potential_score", maximize=True),
        "repeat_potential_score": _rank("repeat_potential_score", maximize=True),
        "risk_score": _rank("risk_score", maximize=False),
        "confidence_score": _rank("confidence_score", maximize=True),
    }

    recommendation = (
        f"Move '{best_overall}' forward first (best overall heuristic score). "
        f"'{needs_validation}' needs the most validation before committing"
        + (f"; '{lowest_risk}' is the lowest-risk option." if lowest_risk != best_overall else ".")
        + " This is a decision-support heuristic, not a validated forecast — confirm with real consumer research."
    )

    return CompareOut(
        items=items,
        comparison_summary=summary,
        dimension_rankings=dimension_rankings,
        recommendation=recommendation,
    )
