"""Decision log (Phase 13) — simple, local, single-user per-project notes/decisions."""
from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DecisionLogEntry
from app.schemas.history import DecisionCreate, DecisionOut


def create_entry(db: Session, project_id: str, payload: DecisionCreate) -> DecisionLogEntry:
    entry = DecisionLogEntry(
        project_id=project_id,
        entry_type=payload.entry_type,
        title=payload.title,
        body=payload.body,
        related_snapshot_id=payload.related_snapshot_id,
        related_scenario_id=payload.related_scenario_id,
        related_report_id=payload.related_report_id,
        tags_json=json.dumps(payload.tags or []),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def add_auto_entry(
    db: Session,
    project_id: str,
    *,
    entry_type: str,
    title: str,
    body: str = "",
    related_snapshot_id: str | None = None,
    related_scenario_id: str | None = None,
    related_report_id: str | None = None,
    tags: list[str] | None = None,
) -> DecisionLogEntry:
    return create_entry(
        db,
        project_id,
        DecisionCreate(
            entry_type=entry_type,
            title=title,
            body=body,
            related_snapshot_id=related_snapshot_id,
            related_scenario_id=related_scenario_id,
            related_report_id=related_report_id,
            tags=tags or [],
        ),
    )


def list_entries(db: Session, project_id: str) -> list[DecisionLogEntry]:
    return db.execute(
        select(DecisionLogEntry).where(DecisionLogEntry.project_id == project_id).order_by(DecisionLogEntry.created_at.desc())
    ).scalars().all()


def get_entry(db: Session, project_id: str, entry_id: str) -> DecisionLogEntry | None:
    return db.execute(
        select(DecisionLogEntry).where(
            DecisionLogEntry.project_id == project_id, DecisionLogEntry.id == entry_id
        )
    ).scalars().first()


def delete_entry(db: Session, project_id: str, entry_id: str) -> bool:
    entry = get_entry(db, project_id, entry_id)
    if entry is None:
        return False
    db.delete(entry)
    db.commit()
    return True


def to_out(entry: DecisionLogEntry) -> DecisionOut:
    try:
        tags = json.loads(entry.tags_json or "[]")
    except json.JSONDecodeError:
        tags = []
    return DecisionOut(
        id=entry.id,
        project_id=entry.project_id,
        entry_type=entry.entry_type,
        title=entry.title,
        body=entry.body,
        related_snapshot_id=entry.related_snapshot_id,
        related_scenario_id=entry.related_scenario_id,
        related_report_id=entry.related_report_id,
        tags=tags if isinstance(tags, list) else [],
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )
