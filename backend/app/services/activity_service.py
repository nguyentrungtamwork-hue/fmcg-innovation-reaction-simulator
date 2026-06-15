"""Cross-project portfolio activity feed (Phase 31).

Aggregates decision-log entries across all projects into a single chronological
feed, with optional filters. Read-only, deterministic, no secrets. Derives stage
hints from tags on `DecisionLogEntry` rows written by Phase 30.
"""
from __future__ import annotations

import json
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DecisionLogEntry, Project

# entry_type → activity_type
_TYPE_MAP = {
    "change": "stage_change",
    "decision": "decision",
    "snapshot": "snapshot",
    "scenario": "scenario",
    "report": "report",
    "briefing": "briefing",
}


def _related_url(entry: DecisionLogEntry, tags: list[str]) -> str:
    pid = entry.project_id
    if "pipeline" in tags or "stage-change" in tags:
        return f"/projects/{pid}/decisions"
    if entry.related_snapshot_id:
        return f"/projects/{pid}/snapshots/diff"
    if entry.related_scenario_id:
        return f"/projects/{pid}/scenarios"
    if entry.related_report_id:
        return f"/projects/{pid}/report"
    return f"/projects/{pid}/home"


def _stage_from(tags: list[str]) -> str | None:
    from app.services.pipeline_service import STAGES

    for t in tags:
        if t in STAGES:
            return t
    return None


def _activity_type(entry: DecisionLogEntry, tags: list[str]) -> str:
    if "stage-change" in tags:
        return "stage_change"
    if "decision-board" in tags:
        return "decision"
    return _TYPE_MAP.get(entry.entry_type, entry.entry_type or "decision")


def _to_item(entry: DecisionLogEntry, projects: dict[str, str]) -> dict:
    try:
        tags = json.loads(entry.tags_json or "[]")
        if not isinstance(tags, list):
            tags = []
    except json.JSONDecodeError:
        tags = []
    return {
        "id": entry.id,
        "timestamp": entry.created_at.isoformat() if entry.created_at else None,
        "project_id": entry.project_id,
        "project_name": projects.get(entry.project_id, ""),
        "activity_type": _activity_type(entry, tags),
        "title": entry.title or "",
        "description": (entry.body or "")[:500],
        "stage": _stage_from(tags),
        "tags": tags,
        "related_url": _related_url(entry, tags),
    }


def list_activity(
    db: Session,
    *,
    activity_type: str | None = None,
    project_id: str | None = None,
    stage: str | None = None,
    limit: int = 30,
) -> dict:
    limit = max(1, min(int(limit), 100))
    projects = {p.id: p.name for p in db.execute(select(Project)).scalars().all()}

    stmt = select(DecisionLogEntry).order_by(DecisionLogEntry.created_at.desc())
    if project_id:
        stmt = stmt.where(DecisionLogEntry.project_id == project_id)
    rows: Iterable[DecisionLogEntry] = db.execute(stmt).scalars().all()

    items: list[dict] = []
    for r in rows:
        item = _to_item(r, projects)
        if activity_type and item["activity_type"] != activity_type:
            continue
        if stage and item["stage"] != stage:
            continue
        items.append(item)
        if len(items) >= limit:
            break

    return {"items": items, "total_returned": len(items)}
