"""Phase 30 — Innovation Pipeline Board tests."""
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


def test_pipeline_status_inferred_for_empty_project(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "Bare"}).json()["id"]
    body = client.get(f"/api/v1/projects/{pid}/pipeline-status").json()
    assert body["pipeline_stage"] == "new_concept"
    assert body["pipeline_stage_source"] == "inferred"
    assert body["inferred_stage"] == "new_concept"


def test_pipeline_status_ready_for_simulation(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    body = client.get(f"/api/v1/projects/{pid}/pipeline-status").json()
    assert body["pipeline_stage"] == "ready_for_simulation"
    assert body["inferred_stage"] == "ready_for_simulation"


def test_patch_pipeline_status_updates_stage(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
    r = client.patch(
        f"/api/v1/projects/{pid}/pipeline-status",
        json={"pipeline_stage": "validate", "note": "Needs sensory test", "source": "manual"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["pipeline_stage"] == "validate"
    assert body["pipeline_stage_source"] == "manual"
    assert body["pipeline_stage_note"] == "Needs sensory test"


def test_patch_creates_decision_log_entry(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
    client.patch(
        f"/api/v1/projects/{pid}/pipeline-status",
        json={"pipeline_stage": "validate", "note": "n", "source": "manual"},
    )
    log = client.get(f"/api/v1/projects/{pid}/decisions").json()
    titles = [e["title"] for e in log]
    assert any("Pipeline stage changed" in t for t in titles)
    entry = next(e for e in log if "Pipeline stage changed" in e["title"])
    assert "pipeline" in entry["tags"] and "validate" in entry["tags"]


def test_patch_invalid_stage_422(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "P"}).json()["id"]
    r = client.patch(
        f"/api/v1/projects/{pid}/pipeline-status",
        json={"pipeline_stage": "nope", "source": "manual"},
    )
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "invalid_stage"


def test_pipeline_status_missing_project_404(client: TestClient) -> None:
    r = client.get("/api/v1/projects/nope/pipeline-status")
    assert r.status_code == 404


def test_portfolio_pipeline_returns_columns(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "A"})
    client.post("/api/v1/projects", json={"name": "B"})
    body = client.get("/api/v1/portfolio/pipeline").json()
    stages = {c["stage"] for c in body["columns"]}
    for s in ("new_concept", "validate", "go", "hold", "archived"):
        assert s in stages
    assert body["summary"]["total_projects"] == 2
    assert body["summary"]["new_count"] == 2


def test_apply_decision_board_updates_eligible(client: TestClient) -> None:
    pid = _full_project(client, "Ready")
    r = client.post(
        "/api/v1/portfolio/pipeline/apply-decision-board",
        json={"only_if_not_manual": True},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["changed"] >= 1
    status = client.get(f"/api/v1/projects/{pid}/pipeline-status").json()
    assert status["pipeline_stage"] in ("go", "validate", "revise", "hold")
    assert status["pipeline_stage_source"] == "decision_board"


def test_apply_decision_board_does_not_overwrite_manual(client: TestClient) -> None:
    pid = _full_project(client, "Manual")
    client.patch(
        f"/api/v1/projects/{pid}/pipeline-status",
        json={"pipeline_stage": "leadership_review", "source": "manual"},
    )
    r = client.post(
        "/api/v1/portfolio/pipeline/apply-decision-board",
        json={"only_if_not_manual": True},
    )
    body = r.json()
    assert body["skipped_manual"] >= 1
    status = client.get(f"/api/v1/projects/{pid}/pipeline-status").json()
    assert status["pipeline_stage"] == "leadership_review"
    assert status["pipeline_stage_source"] == "manual"
