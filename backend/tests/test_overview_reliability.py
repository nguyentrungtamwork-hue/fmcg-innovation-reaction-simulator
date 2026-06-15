"""Phase 19 — live-run reliability + project overview tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "category": "Ready-to-drink tea",
        "benefit": "Refreshes naturally with less sugar",
        "functional_claims": ["50% less sugar"],
        "price": "Slightly premium",
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "known_risks": ["Premium price may suppress trial"],
    }


def _agents(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "Rel"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    return pid


# --- live-run reliability ---------------------------------------------------


def test_stale_run_detected(client: TestClient) -> None:
    pid = _agents(client)
    out = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"stale_after_seconds": 0}).json()
    run = client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}").json()
    assert run["is_stale"] is True
    assert run["can_cancel"] is True


def test_new_run_reaps_stale(client: TestClient) -> None:
    pid = _agents(client)
    out1 = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"stale_after_seconds": 0}).json()
    # second start should succeed (reaps the stale one) rather than 409
    out2 = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"stale_after_seconds": 0, "event_delay_ms": 0})
    assert out2.status_code == 200, out2.text
    assert out2.json()["run_id"] != out1["run_id"]
    reaped = client.get(f"/api/v1/projects/{pid}/live-simulation/{out1['run_id']}").json()
    assert reaped["status"] == "failed"
    assert "stale" in (reaped["error_message"] or "").lower()


def test_cancel_marks_run_cancelled(client: TestClient) -> None:
    pid = _agents(client)
    out = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={}).json()
    r = client.post(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/cancel")
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    # cancel again is safe
    assert client.post(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/cancel").status_code == 200


def test_runs_list_includes_reliability_fields(client: TestClient) -> None:
    pid = _agents(client)
    client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={})
    runs = client.get(f"/api/v1/projects/{pid}/live-simulation/runs").json()
    assert runs
    r = runs[0]
    for key in ("status", "is_stale", "can_cancel", "total_events_emitted", "created_at"):
        assert key in r


# --- project overview -------------------------------------------------------


def test_overview_404_when_project_missing(client: TestClient) -> None:
    assert client.get("/api/v1/projects/nope/overview").status_code == 404


def test_overview_next_action_submit_brief_when_empty(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "Empty"}).json()["id"]
    body = client.get(f"/api/v1/projects/{pid}/overview").json()
    assert body["pipeline_status"]["has_brief"] is False
    assert body["next_recommended_action"]["action"] == "submit_brief"
    assert body["counts"]["agents"] == 0


def test_overview_next_action_run_live_simulation_after_agents(client: TestClient) -> None:
    pid = _agents(client)
    body = client.get(f"/api/v1/projects/{pid}/overview").json()
    assert body["pipeline_status"]["has_agents"] is True
    assert body["pipeline_status"]["has_simulation"] is False
    assert body["next_recommended_action"]["action"] == "run_live_simulation"
    assert body["counts"]["agents"] >= 50


def test_overview_full_project(client: TestClient) -> None:
    pid = _agents(client)
    client.post(f"/api/v1/projects/{pid}/simulate")
    client.post(f"/api/v1/projects/{pid}/report/generate")
    client.post(f"/api/v1/projects/{pid}/briefing/generate", json={})
    body = client.get(f"/api/v1/projects/{pid}/overview").json()
    assert body["pipeline_status"]["has_report"] is True
    assert body["pipeline_status"]["has_briefing"] is True
    assert body["latest_scorecard"] is not None
    assert body["latest_briefing_summary"] is not None
    assert body["next_recommended_action"]["action"] == "explore"
    assert isinstance(body["recent_activity"], list) and body["recent_activity"]
