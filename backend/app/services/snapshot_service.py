"""Report snapshots (Phase 12).

A snapshot is a read-only, named freeze of a project's current report + its
scorecard, so re-running the pipeline never loses a prior decision. Snapshots do
not replace the active report. SQLite-only.
"""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Project, ReportSnapshot
from app.schemas.portfolio import Scorecard, SnapshotCreate, SnapshotOut
from app.services import decision_service, project_service, report_service, scorecard_service


def create_snapshot(db: Session, project_id: str, payload: SnapshotCreate) -> ReportSnapshot:
    project: Project | None = project_service.get_project(db, project_id)
    if project is None:
        raise ValueError("project_not_found")  # mapped to 404 by the endpoint guard already
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise ValueError("report_required")

    scorecard = scorecard_service.build_for_project(db, project_id, project.name)

    snap = ReportSnapshot(
        project_id=project_id,
        snapshot_name=payload.snapshot_name,
        description=payload.description,
        source_report_id=report.id,
        source_project_status=project.status,
        report_payload_json=report.payload_json,
        markdown=report.markdown,
        scorecard_json=scorecard.model_dump_json(),
    )
    db.add(snap)
    db.commit()
    db.refresh(snap)

    # auto decision-log entry for traceability
    decision_service.add_auto_entry(
        db,
        project_id,
        entry_type="snapshot_created",
        title=f"Snapshot created: {snap.snapshot_name}",
        body=payload.description,
        related_snapshot_id=snap.id,
    )
    return snap


def list_snapshots(db: Session, project_id: str) -> list[ReportSnapshot]:
    return db.execute(
        select(ReportSnapshot).where(ReportSnapshot.project_id == project_id).order_by(ReportSnapshot.created_at.desc())
    ).scalars().all()


def get_snapshot(db: Session, project_id: str, snapshot_id: str) -> ReportSnapshot | None:
    return db.execute(
        select(ReportSnapshot).where(
            ReportSnapshot.project_id == project_id, ReportSnapshot.id == snapshot_id
        )
    ).scalars().first()


def delete_snapshot(db: Session, project_id: str, snapshot_id: str) -> bool:
    snap = get_snapshot(db, project_id, snapshot_id)
    if snap is None:
        return False
    db.delete(snap)
    db.commit()
    return True


def scorecard_of(snap: ReportSnapshot) -> Scorecard:
    return Scorecard.model_validate(json.loads(snap.scorecard_json or "{}"))


def to_out(snap: ReportSnapshot) -> SnapshotOut:
    return SnapshotOut(
        snapshot_id=snap.id,
        project_id=snap.project_id,
        snapshot_name=snap.snapshot_name,
        description=snap.description,
        source_report_id=snap.source_report_id,
        source_project_status=snap.source_project_status,
        report_payload=json.loads(snap.report_payload_json or "{}"),
        markdown=snap.markdown,
        scorecard=scorecard_of(snap),
        created_at=snap.created_at,
    )
