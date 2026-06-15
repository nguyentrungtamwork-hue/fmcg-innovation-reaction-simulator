"""Request logging + error hardening (Phase 9; JSON logging + persistent trail Phase 24).

Adds a per-request id, structured access logging (method, path, status_code,
duration_ms, request_id), and a catch-all exception handler so unhandled errors
return a consistent JSON envelope instead of leaking a stack trace.

When ``LOG_JSON=true`` the access/exception lines are emitted as single-line JSON
(safe for log shippers); otherwise the readable key=value format is kept. Notable
errors/exceptions are also persisted to the bounded ``AppLogEntry`` trail. Secrets,
request bodies, API keys and env values are never logged.

No business logic lives here — endpoints keep raising HTTPException as before.
"""
from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import get_settings

logger = logging.getLogger("app.access")


def _error_body(code: str, message: str | None = None, request_id: str | None = None) -> dict:
    detail: dict = {"code": code}
    if message:
        detail["message"] = message
    if request_id:
        detail["request_id"] = request_id
    return {"detail": detail}


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _log_access(request: Request, status_code: int, duration_ms: float, request_id: str, error_code: str | None = None) -> None:
    if get_settings().log_json:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": "info" if status_code < 500 else "error",
            "event_type": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "duration_ms": duration_ms,
            "client_ip": _client_ip(request),
            "user_agent": request.headers.get("user-agent"),
            "error_code": error_code,
        }
        logger.info(json.dumps(payload, ensure_ascii=False))
    else:
        logger.info(
            "request method=%s path=%s status_code=%s duration_ms=%s request_id=%s",
            request.method,
            request.url.path,
            status_code,
            duration_ms,
            request_id,
        )


def _log_exception(request: Request, request_id: str, exc: BaseException) -> None:
    if get_settings().log_json:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "level": "error",
            "event_type": "exception",
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
            "error_code": "internal_error",
            "error_message": str(exc)[:500],
            "exception_type": type(exc).__name__,
        }
        logger.error(json.dumps(payload, ensure_ascii=False))
    else:
        logger.exception(
            "request_failed method=%s path=%s status_code=500 request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )


def _persist(**kwargs) -> None:
    # Lazy import to avoid a circular import at module load.
    try:
        from app.services import app_log_service

        app_log_service.record(**kwargs)
    except Exception:  # noqa: BLE001 — logging must never break the request
        logger.warning("failed to persist app-log entry", exc_info=False)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 - handled centrally
            duration_ms = round((time.perf_counter() - start) * 1000, 1)
            _log_exception(request, request_id, exc)
            _persist(
                level="error",
                event_type="exception",
                message=f"{type(exc).__name__}: {exc}"[:500],
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                status_code=500,
                code="internal_error",
            )
            return JSONResponse(
                status_code=500,
                content=_error_body("internal_error", "An unexpected error occurred.", request_id),
                headers={"X-Request-ID": request_id},
            )
        duration_ms = round((time.perf_counter() - start) * 1000, 1)
        response.headers["X-Request-ID"] = request_id
        _log_access(request, response.status_code, duration_ms, request_id)
        return response


def install_middleware_and_handlers(app: FastAPI) -> None:
    app.add_middleware(RequestContextMiddleware)

    @app.exception_handler(StarletteHTTPException)
    async def _http_exc_handler(request: Request, exc: StarletteHTTPException):
        request_id = getattr(request.state, "request_id", None)
        detail = exc.detail
        # Preserve the existing {"code": ...} convention; normalise plain strings.
        if isinstance(detail, dict):
            body = {"detail": {**detail}}
            if request_id and "request_id" not in body["detail"]:
                body["detail"]["request_id"] = request_id
            code = body["detail"].get("code")
        else:
            code = str(detail) or f"http_{exc.status_code}"
            body = _error_body(code, None, request_id)
        if exc.status_code >= 400:
            _persist(
                level="error" if exc.status_code >= 500 else "warning",
                event_type="http_error",
                message=str(detail)[:500] if not isinstance(detail, dict) else str(detail.get("message") or detail.get("code") or "")[:500],
                request_id=request_id,
                path=request.url.path,
                method=request.method,
                status_code=exc.status_code,
                code=str(code) if code else None,
            )
        return JSONResponse(status_code=exc.status_code, content=body, headers={"X-Request-ID": request_id or ""})

    @app.exception_handler(RequestValidationError)
    async def _validation_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        _persist(
            level="warning",
            event_type="http_error",
            message="Request payload failed validation.",
            request_id=request_id,
            path=request.url.path,
            method=request.method,
            status_code=422,
            code="validation_error",
        )
        return JSONResponse(
            status_code=422,
            content=_error_body("validation_error", "Request payload failed validation.", request_id),
            headers={"X-Request-ID": request_id or ""},
        )
