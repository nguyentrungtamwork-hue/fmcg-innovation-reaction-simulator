"""Phase 11 — sensitivity, confidence, assumptions tests."""
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
        "usage_occasions": ["mid-afternoon at work"],
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "competitors": ["Mainstream bottled teas"],
        "known_risks": ["Premium price may suppress trial", "Herbal taste may feel medicinal"],
    }


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "Insights"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    return pid


# --- sensitivity ------------------------------------------------------------


def test_sensitivity_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/sensitivity", json={})
    assert r.status_code == 404


def test_sensitivity_409_when_baseline_events_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    r = client.post(f"/api/v1/projects/{pid}/sensitivity", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "baseline_events_required"


def test_sensitivity_success_default_levers(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.post(f"/api/v1/projects/{pid}/sensitivity", json={"levers": {"price_change_pct": [0, -10]}})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["sweeps"]
    assert body["overall_recommendation"]
    assert body["baseline_summary"]


def test_sensitivity_returns_points_per_lever(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.post(f"/api/v1/projects/{pid}/sensitivity", json={"levers": {"sampling_boost": [0, 0.1, 0.15]}})
    sweep = r.json()["sweeps"][0]
    assert sweep["lever"] == "sampling_boost"
    assert len(sweep["points"]) == 3
    for p in sweep["points"]:
        assert 0.0 <= p["trial_probability"] <= 1.0
        assert "interpretation" in p


def test_sensitivity_preserves_baseline_events(client: TestClient) -> None:
    pid = _prepare_full(client)
    before = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    client.post(f"/api/v1/projects/{pid}/sensitivity", json={"levers": {"price_change_pct": [0, -5, -10]}})
    after = client.get(f"/api/v1/projects/{pid}/events/summary").json()["total_events"]
    assert before == after, "sweep events must not pollute baseline"
    # baseline report still intact
    assert client.get(f"/api/v1/projects/{pid}/report").status_code == 200


# --- confidence -------------------------------------------------------------


def test_confidence_success_after_report(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/confidence")
    assert r.status_code == 200, r.text
    body = r.json()
    assert 0.0 <= body["overall_confidence"] <= 1.0
    assert body["confidence_label"] in {"low", "medium", "high"}


def test_confidence_includes_drivers_and_risks(client: TestClient) -> None:
    pid = _prepare_full(client)
    body = client.get(f"/api/v1/projects/{pid}/confidence").json()
    assert len(body["drivers"]) >= 5
    for d in body["drivers"]:
        assert "factor" in d and "score" in d and "weight" in d and "explanation" in d
    assert body["confidence_risks"]
    assert body["how_to_improve_confidence"]


def test_confidence_409_before_report(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.get(f"/api/v1/projects/{pid}/confidence")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


# --- assumptions ------------------------------------------------------------


def test_assumptions_success(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/assumptions")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["assumptions"]
    assert body["summary"]["high_impact_count"] >= 1


def test_assumptions_includes_ontology_missing_information(client: TestClient) -> None:
    pid = _prepare_full(client)
    body = client.get(f"/api/v1/projects/{pid}/assumptions").json()
    sources = {a["source"] for a in body["assumptions"]}
    # static method/data caveats are always present
    assert "simulation_engine" in sources
    assert "system" in sources
