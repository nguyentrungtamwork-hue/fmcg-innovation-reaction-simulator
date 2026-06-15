"""Phase 10 — system status endpoint tests."""
from fastapi.testclient import TestClient


def test_system_status_shape(client: TestClient) -> None:
    r = client.get("/api/v1/system/status")
    assert r.status_code == 200
    body = r.json()
    for key in ("app_name", "version", "environment", "llm_configured", "database", "demo_mode"):
        assert key in body
    assert isinstance(body["llm_configured"], bool)
    assert isinstance(body["demo_mode"], bool)
    assert body["database"] == "sqlite"


def test_system_status_no_secrets(client: TestClient) -> None:
    r = client.get("/api/v1/system/status")
    body = r.json()
    # never expose secret-ish keys
    for forbidden in ("openai_api_key", "api_key", "secret", "password", "token"):
        assert forbidden not in body
