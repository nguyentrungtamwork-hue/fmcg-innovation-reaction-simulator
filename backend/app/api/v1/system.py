"""System status / diagnostics (Phase 10 + Phase 23).

Exposes only safe, non-secret configuration + read-only operational diagnostics.
Never returns API keys, raw env, or other secrets.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import __version__
from app.core.config import get_settings
from app.models import AppLogEntry, Event, LiveSimulationRun, Project
from app.services import app_log_service, data_export_service, sample_service
from app.storage.database import get_db

router = APIRouter(prefix="/system", tags=["system"])


class SystemStatusOut(BaseModel):
    app_name: str
    version: str
    environment: str
    llm_configured: bool
    database: str            # retained for back-compat (e.g. "sqlite")
    database_type: str
    demo_mode: bool
    frontend_origin_configured: bool
    live_streaming_supported: bool
    e2e_configured: bool


class DiagnosticsOut(BaseModel):
    status: str
    request_id: str | None = None
    app: dict
    database: dict
    features: dict
    warnings: list[str]
    recent_error_count: int = 0
    recent_warning_count: int = 0
    last_error: dict | None = None
    log_retention_limit: int = 0


class AppLogOut(BaseModel):
    id: str
    timestamp: str | None = None
    level: str
    event_type: str
    request_id: str | None = None
    project_id: str | None = None
    run_id: str | None = None
    scenario_id: str | None = None
    path: str | None = None
    method: str | None = None
    status_code: int | None = None
    code: str | None = None
    message: str
    metadata: dict = {}


class AppLogListOut(BaseModel):
    items: list[AppLogOut]
    total_returned: int
    limit: int


def _db_type(settings) -> str:
    return settings.database_url.split(":", 1)[0] if settings.database_url else "unknown"


@router.get("/status", response_model=SystemStatusOut)
def system_status() -> SystemStatusOut:
    settings = get_settings()
    db_type = _db_type(settings)
    return SystemStatusOut(
        app_name=settings.app_name,
        version=__version__,
        environment=settings.environment,
        llm_configured=bool(settings.openai_api_key),
        database=db_type,
        database_type=db_type,
        demo_mode=settings.demo_mode,
        frontend_origin_configured=bool(settings.frontend_origin),
        live_streaming_supported=True,
        e2e_configured=True,
    )


@router.get("/diagnostics", response_model=DiagnosticsOut)
def system_diagnostics(request: Request, db: Session = Depends(get_db)) -> DiagnosticsOut:
    settings = get_settings()
    warnings: list[str] = []
    connected = True
    project_count = event_count = live_run_count = app_log_count = 0
    try:
        project_count = db.execute(select(func.count(Project.id))).scalar_one()
        event_count = db.execute(
            select(func.count(Event.id)).where(Event.run_type == "baseline")
        ).scalar_one()
        live_run_count = db.execute(select(func.count(LiveSimulationRun.id))).scalar_one()
        app_log_count = db.execute(select(func.count(AppLogEntry.id))).scalar_one()
    except Exception:  # noqa: BLE001
        connected = False
        warnings.append("database_query_failed")

    if not settings.openai_api_key:
        warnings.append("llm_not_configured_using_deterministic_fallback")
    if not settings.frontend_origin and settings.environment not in ("local", "docker"):
        warnings.append("frontend_origin_not_set")

    log_counts = {"recent_error_count": 0, "recent_warning_count": 0, "last_error": None}
    try:
        log_counts = app_log_service.counts(db)
    except Exception:  # noqa: BLE001
        warnings.append("app_log_query_failed")

    return DiagnosticsOut(
        status="ok" if connected else "degraded",
        request_id=getattr(request.state, "request_id", None),
        app={
            "name": settings.app_name,
            "version": __version__,
            "environment": settings.environment,
            "demo_mode": settings.demo_mode,
            "database_type": _db_type(settings),
            "llm_configured": bool(settings.openai_api_key),
        },
        database={
            "connected": connected,
            "project_count": project_count,
            "event_count": event_count,
            "live_run_count": live_run_count,
            "app_log_count": app_log_count,
        },
        features={
            "simulation": True,
            "live_streaming": True,
            "briefing": True,
            "portfolio": True,
            "e2e_configured": True,
        },
        warnings=warnings,
        recent_error_count=log_counts.get("recent_error_count", 0),
        recent_warning_count=log_counts.get("recent_warning_count", 0),
        last_error=log_counts.get("last_error"),
        log_retention_limit=settings.app_log_max_entries,
    )


@router.get("/logs", response_model=AppLogListOut)
def system_logs(
    db: Session = Depends(get_db),
    level: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    request_id: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
) -> AppLogListOut:
    rows = app_log_service.list_logs(
        db,
        level=level,
        event_type=event_type,
        request_id=request_id,
        project_id=project_id,
        limit=limit,
    )
    items = [AppLogOut(**app_log_service.to_dict(r)) for r in rows]
    return AppLogListOut(items=items, total_returned=len(items), limit=limit)


@router.get("/logs/recent-errors", response_model=AppLogListOut)
def system_recent_errors(db: Session = Depends(get_db)) -> AppLogListOut:
    rows = app_log_service.recent_errors(db, limit=10)
    items = [AppLogOut(**app_log_service.to_dict(r)) for r in rows]
    return AppLogListOut(items=items, total_returned=len(items), limit=10)


class PruneLogsOut(BaseModel):
    status: str
    pruned: int
    retention_limit: int


class ResetDemoOut(BaseModel):
    status: str
    projects_deleted: int
    counts: dict


def _require_demo_mode() -> None:
    if not get_settings().demo_mode:
        raise HTTPException(status_code=403, detail={"code": "demo_mode_required"})


@router.post("/prune-logs", response_model=PruneLogsOut)
def prune_logs(db: Session = Depends(get_db)) -> PruneLogsOut:
    """Prune the bounded app-log trail down to APP_LOG_MAX_ENTRIES."""
    pruned = app_log_service.prune_old_logs(db)
    db.commit()
    return PruneLogsOut(status="pruned", pruned=pruned, retention_limit=get_settings().app_log_max_entries)


@router.post("/reset-demo", response_model=ResetDemoOut)
def reset_demo(db: Session = Depends(get_db)) -> ResetDemoOut:
    """Delete demo projects (name starts with 'FreshPlus Demo'). DEMO_MODE only."""
    _require_demo_mode()
    result = data_export_service.reset_demo_data(db)
    return ResetDemoOut(**result)


# --- sample library (Phase 26) ---------------------------------------------


class SampleSummaryOut(BaseModel):
    sample_id: str
    name: str
    category: str
    short_description: str
    target_consumer: str = ""
    key_claim: str = ""
    price_positioning: str = ""
    channels: list[str] = []
    known_risks: list[str] = []
    recommended_demo_path: list[str] = []
    what_to_observe: str = ""


class SampleDetailOut(SampleSummaryOut):
    sample_brief_text: str = ""
    structured: dict = {}


class SampleListOut(BaseModel):
    samples: list[SampleSummaryOut]


class SampleLoadIn(BaseModel):
    project_name: str | None = None
    run_pipeline: bool = False


class SampleLoadOut(BaseModel):
    project_id: str
    status: str
    completed_steps: list[str]
    next_url: str
    warnings: list[str] = []


@router.get("/samples", response_model=SampleListOut)
def list_samples() -> SampleListOut:
    return SampleListOut(samples=[SampleSummaryOut(**s) for s in sample_service.list_samples()])


@router.get("/samples/{sample_id}", response_model=SampleDetailOut)
def get_sample(sample_id: str) -> SampleDetailOut:
    try:
        return SampleDetailOut(**sample_service.get_sample(sample_id))
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": str(e)})


@router.post("/samples/{sample_id}/load", response_model=SampleLoadOut)
def load_sample(sample_id: str, payload: SampleLoadIn, db: Session = Depends(get_db)) -> SampleLoadOut:
    try:
        result = sample_service.load_sample(
            db, sample_id, project_name=payload.project_name, run_pipeline=payload.run_pipeline
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": str(e)})
    return SampleLoadOut(**result)
