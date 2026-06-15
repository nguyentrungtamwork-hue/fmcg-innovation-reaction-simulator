"""Bounded persistent app-event / error trail (Phase 24).

Records only *notable* events (errors, exceptions, run lifecycle, generation
milestones) — never every request, never secrets/bodies. The table is capped
(`APP_LOG_MAX_ENTRIES`, default 500); oldest rows are pruned after each insert.
"""
from __future__ import annotations

import json
import logging

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import AppLogEntry
from app.storage import database

logger = logging.getLogger(__name__)

_LEVELS = {"info", "warning", "error"}


def prune_old_logs(db: Session, max_entries: int | None = None) -> int:
    cap = max_entries if max_entries is not None else get_settings().app_log_max_entries
    ids = db.execute(
        select(AppLogEntry.id).order_by(AppLogEntry.timestamp.desc(), AppLogEntry.id.desc())
    ).scalars().all()
    if len(ids) <= cap:
        return 0
    old = ids[cap:]
    db.execute(delete(AppLogEntry).where(AppLogEntry.id.in_(old)))
    return len(old)


def create_log_entry(
    db: Session,
    *,
    level: str,
    event_type: str,
    message: str,
    request_id: str | None = None,
    project_id: str | None = None,
    run_id: str | None = None,
    scenario_id: str | None = None,
    path: str | None = None,
    method: str | None = None,
    status_code: int | None = None,
    code: str | None = None,
    metadata: dict | None = None,
) -> AppLogEntry:
    entry = AppLogEntry(
        level=level if level in _LEVELS else "info",
        event_type=event_type,
        message=(message or "")[:2000],
        request_id=request_id,
        project_id=project_id,
        run_id=run_id,
        scenario_id=scenario_id,
        path=path,
        method=method,
        status_code=status_code,
        code=code,
        metadata_json=json.dumps(metadata or {}, ensure_ascii=False)[:4000],
    )
    db.add(entry)
    db.flush()
    prune_old_logs(db)
    db.commit()
    return entry


def record(**kwargs) -> None:
    """Fire-and-forget log using a fresh session (safe from middleware/handlers)."""
    db = database.SessionLocal()
    try:
        create_log_entry(db, **kwargs)
    except Exception as e:  # noqa: BLE001 — logging must never break the request
        db.rollback()
        logger.warning("app-log write failed: %s", e)
    finally:
        db.close()


# --- convenience wrappers ---------------------------------------------------


def log_error(db: Session | None = None, **kwargs) -> None:
    kwargs.setdefault("level", "error")
    kwargs.setdefault("event_type", "http_error")
    _emit(db, **kwargs)


def log_live_run_started(db: Session, project_id: str, run_id: str, message: str = "Live simulation started") -> None:
    _emit(db, level="info", event_type="live_run_started", message=message, project_id=project_id, run_id=run_id)


def log_live_run_completed(db: Session, project_id: str, run_id: str, total_events: int) -> None:
    _emit(db, level="info", event_type="live_run_completed", message=f"Live simulation completed ({total_events} events)", project_id=project_id, run_id=run_id, metadata={"total_events": total_events})


def log_live_run_failed(db: Session, project_id: str, run_id: str, error: str) -> None:
    _emit(db, level="error", event_type="live_run_failed", message=f"Live simulation failed: {error}", project_id=project_id, run_id=run_id, code="live_run_failed")


def log_report_generated(db: Session, project_id: str, message: str = "Strategic report generated") -> None:
    _emit(db, level="info", event_type="report_generated", message=message, project_id=project_id)


def log_briefing_generated(db: Session, project_id: str, message: str = "Executive briefing generated") -> None:
    _emit(db, level="info", event_type="briefing_generated", message=message, project_id=project_id)


def log_scenario_created(db: Session, project_id: str, scenario_id: str, name: str) -> None:
    _emit(db, level="info", event_type="scenario_created", message=f"Scenario created: {name}", project_id=project_id, scenario_id=scenario_id)


def _emit(db: Session | None, **kwargs) -> None:
    """Write via the given session if provided, else a fresh one. Never raises."""
    if db is None:
        record(**kwargs)
        return
    try:
        create_log_entry(db, **kwargs)
    except Exception as e:  # noqa: BLE001
        try:
            db.rollback()
        except Exception:  # noqa: BLE001
            pass
        logger.warning("app-log write failed: %s", e)


# --- queries ----------------------------------------------------------------


def list_logs(
    db: Session,
    *,
    level: str | None = None,
    event_type: str | None = None,
    request_id: str | None = None,
    project_id: str | None = None,
    limit: int = 50,
) -> list[AppLogEntry]:
    stmt = select(AppLogEntry).order_by(AppLogEntry.timestamp.desc(), AppLogEntry.id.desc())
    if level:
        stmt = stmt.where(AppLogEntry.level == level)
    if event_type:
        stmt = stmt.where(AppLogEntry.event_type == event_type)
    if request_id:
        stmt = stmt.where(AppLogEntry.request_id == request_id)
    if project_id:
        stmt = stmt.where(AppLogEntry.project_id == project_id)
    return db.execute(stmt.limit(max(1, min(limit, 200)))).scalars().all()


def recent_errors(db: Session, limit: int = 10) -> list[AppLogEntry]:
    return db.execute(
        select(AppLogEntry)
        .where(AppLogEntry.level.in_(("error", "warning")))
        .order_by(AppLogEntry.timestamp.desc(), AppLogEntry.id.desc())
        .limit(limit)
    ).scalars().all()


def counts(db: Session) -> dict:
    from sqlalchemy import func

    err = db.execute(select(func.count(AppLogEntry.id)).where(AppLogEntry.level == "error")).scalar_one()
    warn = db.execute(select(func.count(AppLogEntry.id)).where(AppLogEntry.level == "warning")).scalar_one()
    last = db.execute(
        select(AppLogEntry).where(AppLogEntry.level.in_(("error", "warning"))).order_by(AppLogEntry.timestamp.desc()).limit(1)
    ).scalars().first()
    return {"recent_error_count": err, "recent_warning_count": warn, "last_error": _to_dict(last) if last else None}


def _to_dict(e: AppLogEntry) -> dict:
    try:
        meta = json.loads(e.metadata_json or "{}")
    except json.JSONDecodeError:
        meta = {}
    return {
        "id": e.id,
        "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        "level": e.level,
        "event_type": e.event_type,
        "request_id": e.request_id,
        "project_id": e.project_id,
        "run_id": e.run_id,
        "scenario_id": e.scenario_id,
        "path": e.path,
        "method": e.method,
        "status_code": e.status_code,
        "code": e.code,
        "message": e.message,
        "metadata": meta,
    }


def to_dict(e: AppLogEntry) -> dict:
    return _to_dict(e)
