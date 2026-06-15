"""Phase 7 — Scenario testing tests (deterministic, offline)."""
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
        "functional_claims": ["50% less sugar than leading RTD teas", "Contains chrysanthemum"],
        "emotional_claims": ["A calm reset"],
        "packaging": "450ml PET, frosted look",
        "price": "Slightly premium",
        "pack_size": "450ml",
        "target_consumers": "Urban office workers 22-35",
        "usage_occasions": ["mid-afternoon at work", "after lunch", "commute"],
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "competitors": ["Mainstream bottled teas", "Zero-sugar teas"],
        "media_plan": "TikTok creators, 2 KOLs",
        "sampling_plan": "4-week sampling at office CVS",
        "promotion_plan": "BOGO at convenience chains",
        "known_risks": [
            "Consumers may not believe the natural cooling claim",
            "Premium price may suppress trial",
            "Herbal taste may feel medicinal",
        ],
    }


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus Scenario"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 200, r.text
    return pid


def _run_scenario(client: TestClient, pid: str, overrides: dict, name: str = "Scenario") -> dict:
    body = {"scenario_name": name, "description": "test", "overrides": overrides}
    r = client.post(f"/api/v1/projects/{pid}/scenario", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# --- preconditions ----------------------------------------------------------


def test_scenario_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/scenario", json={"overrides": {}})
    assert r.status_code == 404


def test_scenario_409_when_baseline_events_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    # agents exist but no simulation events yet
    r = client.post(f"/api/v1/projects/{pid}/scenario", json={"overrides": {}})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "baseline_events_required"


def test_scenario_409_when_baseline_report_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/scenario", json={"overrides": {}})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "baseline_report_required"


# --- run + delta ------------------------------------------------------------


def test_scenario_success_with_price_change(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _run_scenario(client, pid, {"price_change_pct": -10}, name="10% price cut")
    assert data["scenario_id"]
    assert data["scenario_name"] == "10% price cut"
    assert data["baseline_summary"]
    assert data["scenario_summary"]
    assert data["conclusion"]


def test_scenario_returns_delta_metrics(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _run_scenario(client, pid, {"price_change_pct": -10, "sampling_boost": 0.5})
    mc = data["key_metric_changes"]
    for key in (
        "trial_probability_delta",
        "purchase_intent_delta",
        "repeat_probability_delta",
        "sentiment_delta",
        "complaint_delta",
        "recommend_delta",
        "switch_delta",
        "trial_count_delta",
    ):
        assert key in mc
    assert isinstance(mc["top_segments_improved"], list)


def test_scenario_creates_unique_id(client: TestClient) -> None:
    pid = _prepare_full(client)
    a = _run_scenario(client, pid, {"price_change_pct": -10})
    b = _run_scenario(client, pid, {"promotion_boost": 0.5})
    assert a["scenario_id"] != b["scenario_id"]


def test_scenario_preserves_baseline_events(client: TestClient) -> None:
    pid = _prepare_full(client)
    before = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    _run_scenario(client, pid, {"price_change_pct": -10})
    after = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    assert before == after, "baseline events must be unchanged"


def test_scenario_preserves_baseline_report(client: TestClient) -> None:
    pid = _prepare_full(client)
    before = client.get(f"/api/v1/projects/{pid}/report").json()["report_id"]
    _run_scenario(client, pid, {"price_change_pct": -10})
    after = client.get(f"/api/v1/projects/{pid}/report").json()["report_id"]
    assert before == after, "baseline report must be unchanged"


# --- list / detail / delta endpoints ---------------------------------------


def test_scenario_list_and_detail(client: TestClient) -> None:
    pid = _prepare_full(client)
    created = _run_scenario(client, pid, {"price_change_pct": -10})
    sid = created["scenario_id"]

    lst = client.get(f"/api/v1/projects/{pid}/scenarios")
    assert lst.status_code == 200
    items = lst.json()
    assert any(i["scenario_id"] == sid for i in items)

    detail = client.get(f"/api/v1/projects/{pid}/scenarios/{sid}")
    assert detail.status_code == 200
    assert detail.json()["scenario_id"] == sid


def test_scenario_delta_endpoint(client: TestClient) -> None:
    pid = _prepare_full(client)
    sid = _run_scenario(client, pid, {"price_change_pct": -10})["scenario_id"]
    r = client.get(f"/api/v1/projects/{pid}/scenarios/{sid}/delta")
    assert r.status_code == 200
    delta = r.json()
    assert "key_metric_changes" in delta
    assert "conclusion" in delta


def test_scenario_detail_404_when_missing(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/scenarios/nonexistent")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "scenario_not_found"


def test_scenario_rerun_does_not_corrupt_baseline_report(client: TestClient) -> None:
    pid = _prepare_full(client)
    baseline_report = client.get(f"/api/v1/projects/{pid}/report").json()["report_id"]
    _run_scenario(client, pid, {"price_change_pct": -10})
    _run_scenario(client, pid, {"sampling_boost": 0.8})
    _run_scenario(client, pid, {"promotion_boost": 0.5})
    after = client.get(f"/api/v1/projects/{pid}/report").json()
    assert after["report_id"] == baseline_report
    # baseline report still has 6 funnel rounds intact
    funnel = after["report_payload"]["launch_funnel_summary"]
    assert len(funnel["round_summary"]) == 6


def test_scenario_delete(client: TestClient) -> None:
    pid = _prepare_full(client)
    sid = _run_scenario(client, pid, {"price_change_pct": -10})["scenario_id"]
    r = client.delete(f"/api/v1/projects/{pid}/scenarios/{sid}")
    assert r.status_code == 200
    assert client.get(f"/api/v1/projects/{pid}/scenarios/{sid}").status_code == 404
