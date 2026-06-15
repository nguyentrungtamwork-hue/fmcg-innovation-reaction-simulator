"""Phase 25 — data export / import / delete + maintenance tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "brief",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "category": "Ready-to-drink tea",
        "benefit": "Refreshes naturally with less sugar",
        "launch_market": "Vietnam",
    }


def _prepare_full(client: TestClient, name: str = "FreshPlus Export") -> str:
    pid = client.post("/api/v1/projects", json={"name": name}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 200, r.text
    return pid


def _export(client: TestClient, pid: str, **params) -> dict:
    r = client.get(f"/api/v1/projects/{pid}/export", params=params)
    assert r.status_code == 200, r.text
    return r.json()


# --- export -----------------------------------------------------------------


def test_export_missing_project_404(client: TestClient) -> None:
    r = client.get("/api/v1/projects/does-not-exist/export")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "project_not_found"


def test_export_succeeds_after_workflow(client: TestClient) -> None:
    pid = _prepare_full(client)
    bundle = _export(client, pid)
    assert bundle["export_version"] == "1.0"
    assert bundle["project_id"] == pid
    assert "checksums" in bundle and "_all" in bundle["checksums"]


def test_export_bundle_includes_core_sections(client: TestClient) -> None:
    pid = _prepare_full(client)
    bundle = _export(client, pid)
    data = bundle["data"]
    assert data["project"]["id"] == pid
    assert len(data["agents"]) > 0
    assert len(data["events"]) > 0
    assert len(data["reports"]) == 1


def test_export_has_no_secrets(client: TestClient) -> None:
    pid = _prepare_full(client)
    raw = client.get(f"/api/v1/projects/{pid}/export").text.lower()
    # key/env-shaped identifiers must never appear (prose may legitimately use words
    # like "secret"/"token", so we check the structured secret keys, not loose words).
    for forbidden in ("openai_api_key", "api_key", "database_url", "secret_key", "password"):
        assert forbidden not in raw


def test_export_zip_format(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/export", params={"format": "zip"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/zip"
    assert r.content[:2] == b"PK"


# --- import -----------------------------------------------------------------


def test_import_create_new_succeeds(client: TestClient) -> None:
    pid = _prepare_full(client)
    bundle = _export(client, pid)
    r = client.post("/api/v1/projects/import", json={"bundle": bundle, "new_project_name": "Imported Demo"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "imported"
    assert body["new_project_id"] != pid


def test_imported_project_round_trips_counts(client: TestClient) -> None:
    pid = _prepare_full(client)
    bundle = _export(client, pid)
    new_pid = client.post("/api/v1/projects/import", json={"bundle": bundle}).json()["new_project_id"]
    new_bundle = _export(client, new_pid)
    assert len(new_bundle["data"]["agents"]) == len(bundle["data"]["agents"])
    assert len(new_bundle["data"]["events"]) == len(bundle["data"]["events"])
    assert len(new_bundle["data"]["reports"]) == len(bundle["data"]["reports"])


def test_import_rejects_malformed_bundle(client: TestClient) -> None:
    r = client.post("/api/v1/projects/import", json={"bundle": {"nope": True}})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_bundle"


def test_import_overwrite_mode_deferred(client: TestClient) -> None:
    pid = _prepare_full(client)
    bundle = _export(client, pid)
    r = client.post("/api/v1/projects/import", json={"bundle": bundle, "mode": "overwrite_existing"})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "import_mode_not_supported"


# --- delete (cascade) -------------------------------------------------------


def test_delete_project_removes_related_data(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.delete(f"/api/v1/projects/{pid}")
    assert r.status_code == 200, r.text
    counts = r.json()["counts"]
    assert counts["agents"] > 0
    assert counts["events"] > 0
    assert counts["project"] == 1
    # project + related rows gone
    assert client.get(f"/api/v1/projects/{pid}").status_code == 404
    assert client.get(f"/api/v1/projects/{pid}/export").status_code == 404


# --- maintenance ------------------------------------------------------------


def test_prune_logs_endpoint(client: TestClient) -> None:
    # create some error logs first
    for _ in range(3):
        client.get("/api/v1/projects/missing")
    r = client.post("/api/v1/system/prune-logs")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pruned"
    assert "retention_limit" in body


def test_reset_demo_guarded_by_demo_mode(client: TestClient) -> None:
    from app.core.config import get_settings

    keep = client.post("/api/v1/projects", json={"name": "Real Project"}).json()["id"]
    # guarded when demo_mode is off
    assert client.post("/api/v1/system/reset-demo").status_code == 403

    settings = get_settings()
    settings.demo_mode = True
    try:
        demo = client.post("/api/v1/projects", json={"name": "FreshPlus Demo — test"}).json()["id"]
        r = client.post("/api/v1/system/reset-demo")
        assert r.status_code == 200, r.text
        assert r.json()["projects_deleted"] >= 1
        assert client.get(f"/api/v1/projects/{demo}").status_code == 404
        assert client.get(f"/api/v1/projects/{keep}").status_code == 200
    finally:
        settings.demo_mode = False
