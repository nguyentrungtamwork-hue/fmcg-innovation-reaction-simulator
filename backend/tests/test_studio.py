"""Phase 16 — Agent Studio state tests (read-only aggregation)."""
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
        "known_risks": ["Premium price may suppress trial", "Herbal taste may feel medicinal"],
    }


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "Studio"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    return pid


def test_studio_state_404_when_project_missing(client: TestClient) -> None:
    r = client.get("/api/v1/projects/nope/studio/state")
    assert r.status_code == 404


def test_studio_state_works_after_full_workflow(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/studio/state")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project"]["id"] == pid
    assert len(body["agents"]) >= 50
    assert len(body["events"]) > 0
    assert body["events_summary"]["total_events"] == len(body["events"])
    assert len(body["rounds"]) == 6


def test_studio_graph_has_nodes_and_edges(client: TestClient) -> None:
    pid = _prepare_full(client)
    graph = client.get(f"/api/v1/projects/{pid}/studio/state").json()["graph"]
    assert len(graph["nodes"]) >= 50
    assert len(graph["edges"]) >= 1
    assert len(graph["edges"]) <= 160
    for n in graph["nodes"][:5]:
        assert n["id"] and n["type"] in {"consumer", "market_actor"} and n["group"]
    for e in graph["edges"][:5]:
        assert e["source"] and e["target"] and e["reason"]
    assert "not real direct conversations" in graph["note"]


def test_studio_state_does_not_change_baseline_events(client: TestClient) -> None:
    pid = _prepare_full(client)
    before = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    client.get(f"/api/v1/projects/{pid}/studio/state")
    after = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    assert before == after


def test_studio_empty_when_no_simulation(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.get(f"/api/v1/projects/{pid}/studio/state")
    assert r.status_code == 200
    body = r.json()
    assert body["events"] == []
    assert body["graph"]["nodes"] == []
