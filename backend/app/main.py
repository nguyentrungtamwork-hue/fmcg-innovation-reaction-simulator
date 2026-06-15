"""FastAPI entrypoint for the FMCG Innovation Reaction Simulator backend."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.middleware import install_middleware_and_handlers
from app.storage.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

settings = get_settings()

app = FastAPI(title=settings.app_name, version=__version__)

# Request-id + access logging + consistent error envelope. Installed before CORS
# so the CORS middleware stays the outermost layer (preflight + headers on errors).
install_middleware_and_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.resolved_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _on_startup() -> None:
    init_db()


@app.get("/healthz", tags=["meta"])
def healthz() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": __version__,
        "llm_configured": bool(settings.openai_api_key),
    }


@app.get("/readyz", tags=["meta"])
def readyz() -> dict:
    """Readiness: app up + DB reachable + core tables accessible. No secrets."""
    from sqlalchemy import func, select

    from app.models import Project
    from app.storage.database import SessionLocal

    checks: list[dict] = []
    connected = True
    db = SessionLocal()
    try:
        db.execute(select(1))
        checks.append({"name": "db_connect", "ok": True})
        db.execute(select(func.count(Project.id)))
        checks.append({"name": "tables_accessible", "ok": True})
    except Exception as e:  # noqa: BLE001
        connected = False
        checks.append({"name": "db_connect", "ok": False, "detail": type(e).__name__})
    finally:
        db.close()

    db_type = settings.database_url.split(":", 1)[0] if settings.database_url else "unknown"
    return {
        "status": "ready" if connected else "degraded",
        "database": {"connected": connected, "type": db_type, "checks": checks},
        "app": {
            "version": __version__,
            "environment": settings.environment,
            "demo_mode": settings.demo_mode,
        },
    }


app.include_router(api_router, prefix=settings.api_v1_prefix)
