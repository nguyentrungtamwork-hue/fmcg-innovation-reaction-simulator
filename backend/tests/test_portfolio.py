"""Phase 12 — snapshots, scorecard, portfolio, comparison tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _brief(brand: str = "FreshPlus") -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "",
        "brand": brand,
        "product_name": f"{brand} Herbal Cool",
        "category": "Ready-to-drink tea",
        "benefit": "Refreshes naturally with less sugar",
        "functional_claims": ["50% less sugar than leading RTD teas"],
        "emotional_claims": ["A calm reset"],
        "packaging": "450ml PET",
        "price": "Slightly premium",
        "pack_size": "450ml",
        "target_consumers": "Urban office workers 22-35",
        "usage_occasions": ["mid-afternoon at work"],
        "channels": ["Convenience stores", "Supermarkets", "TikTok Shop"],
        "launch_market": "Vietnam",
        "competitors": ["Mainstream bottled teas"],
        "known_risks": ["Premium price may suppress trial"],
    }


def _prepare_full(client: TestClient, name: str = "Concept", brand: str = "FreshPlus") -> str:
    pid = client.post("/api/v1/projects", json={"name": name}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief(brand))
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    return pid


# --- snapshots --------------------------------------------------------------


def test_snapshot_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/snapshots", json={"snapshot_name": "x"})
    assert r.status_code == 404


def test_snapshot_409_when_report_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/snapshots", json={"snapshot_name": "x"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_snapshot_create_list_detail_delete(client: TestClient) -> None:
    pid = _prepare_full(client)
    created = client.post(f"/api/v1/projects/{pid}/snapshots", json={"snapshot_name": "v1", "description": "first"})
    assert created.status_code == 200, created.text
    sid = created.json()["snapshot_id"]
    assert created.json()["scorecard"]["overall_score"] is not None

    lst = client.get(f"/api/v1/projects/{pid}/snapshots").json()
    assert any(s["snapshot_id"] == sid for s in lst)

    detail = client.get(f"/api/v1/projects/{pid}/snapshots/{sid}")
    assert detail.status_code == 200
    assert detail.json()["markdown"]

    deleted = client.delete(f"/api/v1/projects/{pid}/snapshots/{sid}")
    assert deleted.status_code == 200
    assert client.get(f"/api/v1/projects/{pid}/snapshots/{sid}").status_code == 404


def test_snapshot_preserves_after_report_regenerate(client: TestClient) -> None:
    pid = _prepare_full(client)
    sid = client.post(f"/api/v1/projects/{pid}/snapshots", json={"snapshot_name": "v1"}).json()["snapshot_id"]
    before = client.get(f"/api/v1/projects/{pid}/snapshots/{sid}").json()["scorecard"]["overall_score"]
    client.post(f"/api/v1/projects/{pid}/report/generate")  # regenerate active report
    after = client.get(f"/api/v1/projects/{pid}/snapshots/{sid}").json()["scorecard"]["overall_score"]
    assert before == after, "snapshot must be immutable"


# --- scorecard --------------------------------------------------------------


def test_scorecard_success_after_report(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/scorecard")
    assert r.status_code == 200, r.text
    sc = r.json()
    assert 0.0 <= sc["overall_score"] <= 100.0
    assert sc["ranking_explanation"]
    assert sc["disclaimer"]


def test_scorecard_409_before_report(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.get(f"/api/v1/projects/{pid}/scorecard")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_scorecard_export_non_empty(client: TestClient) -> None:
    pid = _prepare_full(client)
    j = client.get(f"/api/v1/projects/{pid}/scorecard/export?format=json")
    assert j.status_code == 200 and len(j.content) > 50
    m = client.get(f"/api/v1/projects/{pid}/scorecard/export?format=markdown")
    assert m.status_code == 200
    assert "Concept Scorecard" in m.text


# --- portfolio + compare ----------------------------------------------------


def test_portfolio_returns_projects(client: TestClient) -> None:
    pid = _prepare_full(client, name="Alpha")
    r = client.get("/api/v1/portfolio")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["total_projects"] >= 1
    assert body["summary"]["report_ready_projects"] >= 1
    assert any(p["project_id"] == pid and p["has_report"] for p in body["projects"])


def test_portfolio_compare_two_projects(client: TestClient) -> None:
    pid1 = _prepare_full(client, name="Alpha", brand="FreshPlus")
    pid2 = _prepare_full(client, name="Beta", brand="GreenCo")
    r = client.post("/api/v1/portfolio/compare", json={"project_ids": [pid1, pid2]})
    assert r.status_code == 200, r.text
    body = r.json()
    assert len(body["items"]) == 2
    assert body["comparison_summary"]["best_overall"]
    assert "overall_score" in body["dimension_rankings"]
    assert body["recommendation"]


def test_scorecard_overall_in_range(client: TestClient) -> None:
    pid = _prepare_full(client)
    sc = client.get(f"/api/v1/projects/{pid}/scorecard").json()
    assert 0.0 <= sc["overall_score"] <= 100.0
    for key in ("trial_potential_score", "repeat_potential_score", "risk_score", "claim_credibility_score"):
        assert 0.0 <= sc[key] <= 100.0
