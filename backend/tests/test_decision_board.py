"""Phase 29 — Portfolio Decision Board tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"

_LABELS = {"go", "validate", "revise", "hold", "incomplete"}


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


def test_board_empty_state(client: TestClient) -> None:
    r = client.get("/api/v1/portfolio/decision-board")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_projects"] == 0
    assert body["items"] == []
    assert "No report-ready" in body["portfolio_recommendation"]


def test_board_includes_incomplete_project(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "Bare"}).json()["id"]
    body = client.get("/api/v1/portfolio/decision-board").json()
    item = next(it for it in body["items"] if it["project_id"] == pid)
    assert item["decision_label"] == "incomplete"
    assert item["has_decision_pack"] is False
    assert body["summary"]["incomplete_count"] >= 1


def test_board_includes_report_ready_project(client: TestClient) -> None:
    pid = _full_project(client, "Ready Concept")
    body = client.get("/api/v1/portfolio/decision-board").json()
    item = next(it for it in body["items"] if it["project_id"] == pid)
    assert item["decision_label"] in _LABELS - {"incomplete"}
    assert item["has_decision_pack"] is True
    assert item["decision_pack_url"] == f"/projects/{pid}/decision-pack"
    assert item["overall_score"] is not None
    assert body["summary"]["report_ready_projects"] >= 1
    assert len(body["rankings"]["best_overall"]) >= 1


def test_board_labels_are_allowed(client: TestClient) -> None:
    _full_project(client, "A")
    client.post("/api/v1/projects", json={"name": "B (incomplete)"})
    body = client.get("/api/v1/portfolio/decision-board").json()
    for it in body["items"]:
        assert it["decision_label"] in _LABELS


def test_board_markdown_non_empty(client: TestClient) -> None:
    _full_project(client, "MD Concept")
    r = client.get("/api/v1/portfolio/decision-board/markdown")
    assert r.status_code == 200
    assert "# Portfolio Decision Board" in r.text
    assert "heuristic decision-support" in r.text.lower()


def test_board_no_secrets(client: TestClient) -> None:
    _full_project(client, "Secret Check")
    raw = client.get("/api/v1/portfolio/decision-board").text.lower()
    for forbidden in ("openai_api_key", "api_key", "database_url", "secret_key", "password"):
        assert forbidden not in raw


def test_board_project_ids_filter(client: TestClient) -> None:
    keep = _full_project(client, "Keep")
    _full_project(client, "Drop")
    body = client.get("/api/v1/portfolio/decision-board", params={"project_ids": keep}).json()
    assert body["summary"]["total_projects"] == 1
    assert body["items"][0]["project_id"] == keep
