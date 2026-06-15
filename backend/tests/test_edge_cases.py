"""Phase 20 — backend edge-case / robustness tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "x",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "price": "Slightly premium",
        "channels": ["Convenience stores"],
        "launch_market": "Vietnam",
    }


def test_overview_handles_brief_only_project(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "BriefOnly"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    body = client.get(f"/api/v1/projects/{pid}/overview").json()
    assert body["pipeline_status"]["has_brief"] is True
    assert body["pipeline_status"]["has_ontology"] is False
    assert body["next_recommended_action"]["action"] == "analyze_ontology"
    assert body["latest_scorecard"] is None


def test_studio_state_handles_no_events(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "NoEvents"}).json()["id"]
    body = client.get(f"/api/v1/projects/{pid}/studio/state").json()
    assert body["events"] == []
    assert body["graph"]["nodes"] == []
    assert body["graph"]["edges"] == []


def test_scorecard_409_when_report_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.get(f"/api/v1/projects/{pid}/scorecard")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_briefing_get_409_when_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.get(f"/api/v1/projects/{pid}/briefing")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "briefing_required"


def test_portfolio_compare_empty_list(client: TestClient) -> None:
    r = client.post("/api/v1/portfolio/compare", json={"project_ids": []})
    assert r.status_code == 200
    body = r.json()
    assert body["items"] == []
    assert "No report-ready" in body["recommendation"]


def test_live_cancel_idempotent_on_finished(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    out = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"event_delay_ms": 0}).json()
    # consume the stream to completion
    client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/stream")
    # cancel a completed run is safe and keeps its status
    r1 = client.post(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/cancel")
    assert r1.status_code == 200
    assert r1.json()["status"] == "completed"
    r2 = client.post(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/cancel")
    assert r2.status_code == 200
    assert r2.json()["status"] == "completed"


def test_live_custom_stale_after_seconds_not_stale(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    # a generous TTL => a freshly-started run is NOT stale
    out = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"stale_after_seconds": 3600}).json()
    run = client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}").json()
    assert run["is_stale"] is False
    assert run["stale_after_seconds"] == 3600
