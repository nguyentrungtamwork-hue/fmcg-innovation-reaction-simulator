"""Phase 9 — request-id, error envelope, and logging hardening tests."""
from fastapi.testclient import TestClient


def test_request_id_header_on_success(client: TestClient) -> None:
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")


def test_request_id_echoed_when_provided(client: TestClient) -> None:
    r = client.get("/api/v1/projects", headers={"X-Request-ID": "trace-123"})
    assert r.headers.get("X-Request-ID") == "trace-123"


def test_404_error_envelope_has_code_and_request_id(client: TestClient) -> None:
    r = client.get("/api/v1/projects/does-not-exist")
    assert r.status_code == 404
    body = r.json()
    assert body["detail"]["code"] == "project_not_found"
    assert body["detail"]["request_id"]


def test_validation_error_envelope(client: TestClient) -> None:
    # name is required (min_length=1) -> validation error
    r = client.post("/api/v1/projects", json={})
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "validation_error"


def test_409_error_envelope_preserves_code(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    # analyze before a brief exists -> 409 brief_required
    r = client.post(f"/api/v1/projects/{pid}/analyze")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "brief_required"
