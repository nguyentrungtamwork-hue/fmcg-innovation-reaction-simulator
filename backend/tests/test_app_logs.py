"""Phase 24 — JSON structured logging + bounded persistent app-log trail."""
import json
import logging

from fastapi.testclient import TestClient

from app.core import middleware
from app.core.config import get_settings
from app.services import app_log_service
from app.storage import database


# --- JSON formatter ---------------------------------------------------------


def test_access_log_json_is_valid_one_line_json(client: TestClient, caplog) -> None:
    settings = get_settings()
    settings.log_json = True
    try:
        with caplog.at_level(logging.INFO, logger="app.access"):
            r = client.get("/api/v1/system/status")
        assert r.status_code == 200
        json_lines = []
        for rec in caplog.records:
            msg = rec.getMessage()
            if msg.startswith("{"):
                parsed = json.loads(msg)  # must not raise
                assert "\n" not in msg
                json_lines.append(parsed)
        assert any(p.get("event_type") == "http_request" for p in json_lines)
        hit = next(p for p in json_lines if p.get("event_type") == "http_request")
        for key in ("timestamp", "level", "request_id", "method", "path", "status_code", "duration_ms"):
            assert key in hit
    finally:
        settings.log_json = False


def test_plain_log_used_when_json_disabled(client: TestClient, caplog) -> None:
    settings = get_settings()
    settings.log_json = False
    with caplog.at_level(logging.INFO, logger="app.access"):
        client.get("/api/v1/system/status")
    assert any("request method=" in r.getMessage() for r in caplog.records)


# --- model + service --------------------------------------------------------


def test_create_log_entry_persists(client: TestClient) -> None:
    db = database.SessionLocal()
    try:
        entry = app_log_service.create_log_entry(
            db, level="info", event_type="system_warning", message="hello"
        )
        assert entry.id
        assert app_log_service.list_logs(db)[0].message == "hello"
    finally:
        db.close()


def test_pruning_respects_max(client: TestClient) -> None:
    db = database.SessionLocal()
    try:
        for i in range(12):
            app_log_service.create_log_entry(
                db, level="info", event_type="system_warning", message=f"m{i}"
            )
        app_log_service.prune_old_logs(db, max_entries=5)
        db.commit()
        remaining = app_log_service.list_logs(db, limit=200)
        assert len(remaining) == 5
    finally:
        db.close()


# --- middleware wiring ------------------------------------------------------


def test_error_response_creates_app_log_entry(client: TestClient) -> None:
    r = client.get("/api/v1/projects/does-not-exist")
    assert r.status_code == 404
    logs = client.get("/api/v1/system/logs", params={"event_type": "http_error"}).json()
    assert logs["total_returned"] >= 1
    assert any(item["status_code"] == 404 for item in logs["items"])


def test_live_run_lifecycle_creates_entries(client: TestClient) -> None:
    db = database.SessionLocal()
    try:
        app_log_service.log_live_run_started(db, project_id="p1", run_id="r1")
        app_log_service.log_live_run_completed(db, project_id="p1", run_id="r1", total_events=3)
        types = {e.event_type for e in app_log_service.list_logs(db, project_id="p1")}
        assert "live_run_started" in types
        assert "live_run_completed" in types
    finally:
        db.close()


# --- endpoints --------------------------------------------------------------


def test_system_logs_endpoint_returns_entries(client: TestClient) -> None:
    # generate an error so there is at least one entry
    client.get("/api/v1/projects/missing")
    body = client.get("/api/v1/system/logs", params={"limit": 10}).json()
    assert "items" in body and "total_returned" in body and "limit" in body
    assert body["limit"] == 10


def test_recent_errors_only_warnings_and_errors(client: TestClient) -> None:
    db = database.SessionLocal()
    try:
        app_log_service.create_log_entry(db, level="info", event_type="report_generated", message="ok")
        app_log_service.create_log_entry(db, level="error", event_type="http_error", message="boom")
    finally:
        db.close()
    body = client.get("/api/v1/system/logs/recent-errors").json()
    assert all(item["level"] in ("error", "warning") for item in body["items"])
    assert any(item["message"] == "boom" for item in body["items"])


def test_diagnostics_includes_recent_error_summary(client: TestClient) -> None:
    client.get("/api/v1/projects/missing")  # produce an error log
    body = client.get("/api/v1/system/diagnostics").json()
    for key in ("recent_error_count", "recent_warning_count", "last_error", "log_retention_limit"):
        assert key in body
    assert body["log_retention_limit"] == get_settings().app_log_max_entries


def test_logs_payloads_have_no_secrets(client: TestClient) -> None:
    client.get("/api/v1/projects/missing")
    raw = client.get("/api/v1/system/logs").text.lower()
    for forbidden in ("openai_api_key", "api_key", "secret", "password", "token", "database_url"):
        assert forbidden not in raw
