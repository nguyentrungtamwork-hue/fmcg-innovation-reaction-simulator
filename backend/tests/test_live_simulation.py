"""Phase 18 — live simulation streaming (SSE) tests."""
import json
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
        "functional_claims": ["50% less sugar than leading RTD teas"],
        "packaging": "450ml PET",
        "price": "Slightly premium",
        "target_consumers": "Urban office workers 22-35",
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "competitors": ["Mainstream bottled teas"],
        "known_risks": ["Premium price may suppress trial"],
    }


def _prepare_agents(client: TestClient) -> str:
    """Project with brief + ontology + agents, but NO simulation yet."""
    pid = client.post("/api/v1/projects", json={"name": "Live"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    return pid


def _parse_sse(body: str) -> list[dict]:
    msgs = []
    for frame in body.split("\n\n"):
        for line in frame.splitlines():
            if line.startswith("data:"):
                raw = line[len("data:"):].strip()
                try:
                    msgs.append(json.loads(raw))
                except json.JSONDecodeError:
                    pass
    return msgs


def _start(client: TestClient, pid: str, **extra) -> dict:
    body = {"event_delay_ms": 0, **extra}
    r = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# --- preconditions ----------------------------------------------------------


def test_live_start_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/live-simulation/start", json={})
    assert r.status_code == 404


def test_live_start_409_when_agents_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    r = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "agents_required"


def test_live_start_succeeds_after_workflow(client: TestClient) -> None:
    pid = _prepare_agents(client)
    out = _start(client, pid)
    assert out["status"] == "running"
    assert out["run_id"]
    assert out["stream_url"].endswith(f"/{out['run_id']}/stream")


def test_live_prevents_concurrent_runs(client: TestClient) -> None:
    pid = _prepare_agents(client)
    _start(client, pid)
    r = client.post(f"/api/v1/projects/{pid}/live-simulation/start", json={"event_delay_ms": 0})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "live_run_already_running"


# --- stream -----------------------------------------------------------------


def test_live_stream_emits_lifecycle_and_persists(client: TestClient) -> None:
    pid = _prepare_agents(client)
    out = _start(client, pid, rounds=6)
    r = client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/stream")
    assert r.status_code == 200
    assert "text/event-stream" in r.headers["content-type"]
    msgs = _parse_sse(r.text)
    types = [m["type"] for m in msgs]
    assert "run_started" in types
    assert "round_started" in types
    assert "event_generated" in types
    assert "round_completed" in types
    assert "run_completed" in types

    # an event_generated payload carries a persisted event id + fields
    ev = next(m for m in msgs if m["type"] == "event_generated")
    assert ev["payload"]["event_id"]
    assert ev["payload"]["action_type"]
    assert ev["progress"]["rounds_total"] == 6

    # persisted exactly like a normal run -> 50 consumers + 5 actors over 6 rounds
    summary = client.get(f"/api/v1/projects/{pid}/events/summary").json()
    assert summary["total_events"] == 330
    assert summary["rounds_run"] == 6

    # run row is completed
    run = client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}").json()
    assert run["status"] == "completed"
    assert run["total_events_emitted"] == 330


def test_live_streamed_events_feed_report_and_studio(client: TestClient) -> None:
    pid = _prepare_agents(client)
    out = _start(client, pid)
    client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/stream")  # consume
    # report works on streamed events
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    # studio sees the events
    studio = client.get(f"/api/v1/projects/{pid}/studio/state").json()
    assert len(studio["events"]) == 330


def test_live_runs_list(client: TestClient) -> None:
    pid = _prepare_agents(client)
    out = _start(client, pid)
    client.get(f"/api/v1/projects/{pid}/live-simulation/{out['run_id']}/stream")
    runs = client.get(f"/api/v1/projects/{pid}/live-simulation/runs").json()
    assert any(r["run_id"] == out["run_id"] for r in runs)


def test_live_force_rerun_replaces_baseline(client: TestClient) -> None:
    pid = _prepare_agents(client)
    # first live run
    out1 = _start(client, pid)
    client.get(f"/api/v1/projects/{pid}/live-simulation/{out1['run_id']}/stream")
    before = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    # second live run with force_rerun replaces, not duplicates
    out2 = _start(client, pid, force_rerun=True)
    client.get(f"/api/v1/projects/{pid}/live-simulation/{out2['run_id']}/stream")
    after = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    assert before == after == 330
