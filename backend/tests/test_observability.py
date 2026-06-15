"""Phase 23 — health/readiness, system status, diagnostics, request-id tests."""
from fastapi.testclient import TestClient

_SECRET_HINTS = ("openai_api_key", "api_key", "secret", "password", "token", "database_url")


def _assert_no_secrets(body: dict) -> None:
    import json

    blob = json.dumps(body).lower()
    for hint in _SECRET_HINTS:
        assert hint not in blob, f"diagnostics leaked '{hint}'"


def test_readyz_ready(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ready"
    assert body["database"]["connected"] is True
    assert body["database"]["type"] == "sqlite"
    assert any(c["name"] == "tables_accessible" and c["ok"] for c in body["database"]["checks"])


def test_status_no_secrets_and_new_fields(client: TestClient) -> None:
    r = client.get("/api/v1/system/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("database_type", "frontend_origin_configured", "live_streaming_supported", "e2e_configured"):
        assert key in body
    assert body["database"] == "sqlite"
    assert isinstance(body["llm_configured"], bool)
    _assert_no_secrets(body)


def test_diagnostics_counts_and_features(client: TestClient) -> None:
    # create a project so counts are non-trivial
    client.post("/api/v1/projects", json={"name": "Diag"})
    r = client.get("/api/v1/system/diagnostics")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["database"]["connected"] is True
    assert body["database"]["project_count"] >= 1
    assert "event_count" in body["database"] and "live_run_count" in body["database"]
    assert body["features"]["simulation"] is True
    assert body["features"]["live_streaming"] is True
    _assert_no_secrets(body)


def test_diagnostics_includes_request_id(client: TestClient) -> None:
    r = client.get("/api/v1/system/diagnostics")
    assert r.json()["request_id"]
    assert r.headers.get("X-Request-ID")


def test_error_response_includes_request_id(client: TestClient) -> None:
    r = client.get("/api/v1/projects/does-not-exist")
    assert r.status_code == 404
    assert r.json()["detail"]["request_id"]
    assert r.headers.get("X-Request-ID")
