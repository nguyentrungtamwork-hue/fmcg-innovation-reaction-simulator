"""Phase 13 — snapshot diff, decision log, timeline tests."""
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


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "History"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    return pid


def _snapshot(client: TestClient, pid: str, name: str) -> str:
    return client.post(f"/api/v1/projects/{pid}/snapshots", json={"snapshot_name": name}).json()["snapshot_id"]


# --- snapshot diff ----------------------------------------------------------


def test_diff_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/snapshots/diff", json={"left": {"type": "active_report"}, "right": {"type": "snapshot", "snapshot_id": "x"}})
    assert r.status_code == 404


def test_diff_404_when_snapshot_missing(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.post(f"/api/v1/projects/{pid}/snapshots/diff", json={"left": {"type": "active_report"}, "right": {"type": "snapshot", "snapshot_id": "nope"}})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "snapshot_not_found"


def test_diff_active_vs_snapshot(client: TestClient) -> None:
    pid = _prepare_full(client)
    sid = _snapshot(client, pid, "v1")
    r = client.post(f"/api/v1/projects/{pid}/snapshots/diff", json={"left": {"type": "snapshot", "snapshot_id": sid}, "right": {"type": "active_report"}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "overall_score" in body["scorecard_delta"]
    assert body["plain_english_summary"]
    assert body["decision_implication"]


def test_diff_snapshot_vs_snapshot(client: TestClient) -> None:
    pid = _prepare_full(client)
    a = _snapshot(client, pid, "A")
    b = _snapshot(client, pid, "B")
    r = client.post(f"/api/v1/projects/{pid}/snapshots/diff", json={"left": {"type": "snapshot", "snapshot_id": a}, "right": {"type": "snapshot", "snapshot_id": b}})
    assert r.status_code == 200, r.text
    body = r.json()
    # identical snapshots -> zero overall delta
    assert body["scorecard_delta"]["overall_score"]["delta"] == 0
    assert body["dimension_changes"]


def test_diff_invalid_request(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.post(f"/api/v1/projects/{pid}/snapshots/diff", json={"left": {"type": "snapshot"}, "right": {"type": "active_report"}})
    assert r.status_code == 400
    assert r.json()["detail"]["code"] == "invalid_diff_request"


# --- decision log -----------------------------------------------------------


def test_decision_create_list_detail_delete(client: TestClient) -> None:
    pid = _prepare_full(client)
    created = client.post(
        f"/api/v1/projects/{pid}/decisions",
        json={"entry_type": "decision", "title": "Proceed to validation", "body": "trial strong", "tags": ["validation"]},
    )
    assert created.status_code == 200, created.text
    eid = created.json()["id"]
    assert created.json()["tags"] == ["validation"]

    lst = client.get(f"/api/v1/projects/{pid}/decisions").json()
    assert any(e["id"] == eid for e in lst)

    detail = client.get(f"/api/v1/projects/{pid}/decisions/{eid}")
    assert detail.status_code == 200
    assert detail.json()["title"] == "Proceed to validation"

    assert client.delete(f"/api/v1/projects/{pid}/decisions/{eid}").status_code == 200
    assert client.get(f"/api/v1/projects/{pid}/decisions/{eid}").status_code == 404


def test_snapshot_creates_auto_decision_entry(client: TestClient) -> None:
    pid = _prepare_full(client)
    _snapshot(client, pid, "Baseline v1")
    entries = client.get(f"/api/v1/projects/{pid}/decisions").json()
    assert any(e["entry_type"] == "snapshot_created" for e in entries)


# --- timeline ---------------------------------------------------------------


def test_timeline_merged_entries(client: TestClient) -> None:
    pid = _prepare_full(client)
    _snapshot(client, pid, "v1")
    client.post(f"/api/v1/projects/{pid}/decisions", json={"entry_type": "note", "title": "Kickoff"})
    r = client.get(f"/api/v1/projects/{pid}/timeline")
    assert r.status_code == 200, r.text
    types = [t["type"] for t in r.json()["timeline"]]
    assert "project_created" in types
    assert "report_generated" in types
    assert "snapshot_created" in types
    # timeline is chronological
    ts = [t["timestamp"] for t in r.json()["timeline"]]
    assert ts == sorted(ts)
