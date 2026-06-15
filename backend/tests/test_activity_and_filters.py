"""Phase 31 — Portfolio activity feed + pipeline filters tests."""
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


def _full_project(client: TestClient, name: str) -> str:
    pid = client.post("/api/v1/projects", json={"name": name}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    client.post(f"/api/v1/projects/{pid}/report/generate")
    return pid


# --- activity ---------------------------------------------------------------


def test_activity_returns_stage_change_entries(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "Act-1"}).json()["id"]
    client.patch(
        f"/api/v1/projects/{pid}/pipeline-status",
        json={"pipeline_stage": "validate", "note": "Move to validation."},
    )
    body = client.get("/api/v1/portfolio/activity").json()
    assert body["total_returned"] >= 1
    types = {it["activity_type"] for it in body["items"]}
    assert "stage_change" in types
    item = next(it for it in body["items"] if it["activity_type"] == "stage_change")
    assert item["project_id"] == pid
    assert item["stage"] == "validate"
    assert "pipeline" in item["tags"]


def test_activity_project_id_filter(client: TestClient) -> None:
    a = client.post("/api/v1/projects", json={"name": "A"}).json()["id"]
    b = client.post("/api/v1/projects", json={"name": "B"}).json()["id"]
    client.patch(f"/api/v1/projects/{a}/pipeline-status", json={"pipeline_stage": "validate"})
    client.patch(f"/api/v1/projects/{b}/pipeline-status", json={"pipeline_stage": "revise"})
    body = client.get("/api/v1/portfolio/activity", params={"project_id": a}).json()
    assert all(it["project_id"] == a for it in body["items"])
    assert body["total_returned"] >= 1


def test_activity_stage_filter(client: TestClient) -> None:
    a = client.post("/api/v1/projects", json={"name": "A"}).json()["id"]
    b = client.post("/api/v1/projects", json={"name": "B"}).json()["id"]
    client.patch(f"/api/v1/projects/{a}/pipeline-status", json={"pipeline_stage": "validate"})
    client.patch(f"/api/v1/projects/{b}/pipeline-status", json={"pipeline_stage": "revise"})
    body = client.get("/api/v1/portfolio/activity", params={"stage": "validate"}).json()
    assert all(it["stage"] == "validate" for it in body["items"])


def test_activity_limit_respected(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "L"}).json()["id"]
    for stage in ("validate", "revise", "hold", "validate"):
        client.patch(f"/api/v1/projects/{pid}/pipeline-status", json={"pipeline_stage": stage})
    body = client.get("/api/v1/portfolio/activity", params={"limit": 2}).json()
    assert body["total_returned"] == 2


def test_activity_has_no_secrets(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "S"}).json()["id"]
    client.patch(f"/api/v1/projects/{pid}/pipeline-status", json={"pipeline_stage": "validate"})
    raw = client.get("/api/v1/portfolio/activity").text.lower()
    for forbidden in ("openai_api_key", "api_key", "database_url", "secret_key", "password"):
        assert forbidden not in raw


# --- pipeline filters -------------------------------------------------------


def test_pipeline_stage_filter(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "S"}).json()["id"]
    client.patch(f"/api/v1/projects/{pid}/pipeline-status", json={"pipeline_stage": "validate"})
    client.post("/api/v1/projects", json={"name": "Empty"})
    body = client.get("/api/v1/portfolio/pipeline", params={"stage": "validate"}).json()
    assert body["summary"]["total_projects"] == 1
    items_in_col = next(c for c in body["columns"] if c["stage"] == "validate")["items"]
    assert len(items_in_col) == 1


def test_pipeline_decision_label_filter(client: TestClient) -> None:
    _full_project(client, "DL-A")
    client.post("/api/v1/projects", json={"name": "Bare"})
    body = client.get("/api/v1/portfolio/pipeline", params={"decision_label": "validate"}).json()
    for col in body["columns"]:
        for it in col["items"]:
            assert it["decision_board_label"] == "validate"


def test_pipeline_search_filter(client: TestClient) -> None:
    a = client.post("/api/v1/projects", json={"name": "Alpha Concept"}).json()["id"]
    client.post("/api/v1/projects", json={"name": "Bravo Concept"})
    body = client.get("/api/v1/portfolio/pipeline", params={"search": "alpha"}).json()
    assert body["summary"]["total_projects"] == 1
    flat = [it for c in body["columns"] for it in c["items"]]
    assert flat[0]["project_id"] == a


def test_pipeline_include_archived_false(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "Old"}).json()["id"]
    client.post("/api/v1/projects", json={"name": "Live"})
    client.patch(f"/api/v1/projects/{pid}/pipeline-status", json={"pipeline_stage": "archived"})
    body = client.get("/api/v1/portfolio/pipeline", params={"include_archived": False}).json()
    archived_col = next(c for c in body["columns"] if c["stage"] == "archived")
    assert len(archived_col["items"]) == 0
    assert body["summary"]["total_projects"] == 1
