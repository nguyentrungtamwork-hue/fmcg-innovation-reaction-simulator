"""Phase 3 — ontology extraction tests (fallback mode)."""
from pathlib import Path

from fastapi.testclient import TestClient


SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _new_project(client: TestClient, name: str = "FreshPlus Test") -> str:
    r = client.post("/api/v1/projects", json={"name": name})
    return r.json()["id"]


def _structured_brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "category": "Ready-to-drink tea",
        "concept": "Low-sugar herbal tea with natural cooling ingredients",
        "benefit": "Refreshes naturally with less sugar",
        "functional_claims": ["50% less sugar than leading RTD teas", "Contains chrysanthemum and mulberry leaf"],
        "emotional_claims": ["A calm reset in the middle of a hot day"],
        "packaging": "450ml PET, frosted look, green+cream",
        "price": "Slightly premium",
        "pack_size": "450ml",
        "target_consumers": "Urban office workers 22-35",
        "usage_occasions": ["mid-afternoon at work", "after lunch"],
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


def test_analyze_fails_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/analyze")
    assert r.status_code == 404


def test_analyze_fails_when_brief_missing(client: TestClient) -> None:
    pid = _new_project(client)
    r = client.post(f"/api/v1/projects/{pid}/analyze")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "brief_required"


def test_analyze_succeeds_with_fallback(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    r = client.post(f"/api/v1/projects/{pid}/analyze")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_mode"] == "fallback"
    assert 0.0 <= body["confidence_score"] <= 1.0


def test_ontology_contains_entities_and_relationships(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    body = client.post(f"/api/v1/projects/{pid}/analyze").json()

    types = {e["type"] for e in body["entities"]}
    assert "Brand" in types
    assert "ProductInnovation" in types
    assert "FunctionalClaim" in types
    assert "Channel" in types
    assert "CompetitorBrand" in types
    assert "UsageOccasion" in types

    rel_types = {r["type"] for r in body["relationships"]}
    assert "CLAIMS_TO_SOLVE" in rel_types
    assert "COMPETES_WITH" in rel_types
    assert "IS_SOLD_THROUGH" in rel_types


def test_ontology_strategic_signals_present(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    body = client.post(f"/api/v1/projects/{pid}/analyze").json()

    assert isinstance(body["missing_information"], list)
    assert isinstance(body["purchase_triggers"], list) and body["purchase_triggers"]
    assert isinstance(body["adoption_barriers"], list) and body["adoption_barriers"]
    assert isinstance(body["claim_analysis"], list) and body["claim_analysis"]
    assert isinstance(body["channel_analysis"], list) and body["channel_analysis"]


def test_ontology_missing_information_flags_gaps(client: TestClient) -> None:
    pid = _new_project(client)
    minimal = {"raw_text": "Launching a new snack.", "brand": "X"}
    client.post(f"/api/v1/projects/{pid}/brief", json=minimal)
    body = client.post(f"/api/v1/projects/{pid}/analyze").json()
    missing = set(body["missing_information"])
    # Several gaps should be flagged
    assert "channel_plan_unclear" in missing
    assert "competitor_set_unclear" in missing
    assert "functional_claim_unclear" in missing
    assert "price_unclear" in missing


def test_get_ontology_returns_persisted_ontology(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    posted = client.post(f"/api/v1/projects/{pid}/analyze").json()
    fetched = client.get(f"/api/v1/projects/{pid}/ontology").json()
    assert fetched["ontology_id"] == posted["ontology_id"]
    assert len(fetched["entities"]) == len(posted["entities"])


def test_get_ontology_404_before_analyze(client: TestClient) -> None:
    pid = _new_project(client)
    r = client.get(f"/api/v1/projects/{pid}/ontology")
    assert r.status_code == 404


def test_rerun_analyze_replaces_ontology(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    first = client.post(f"/api/v1/projects/{pid}/analyze").json()
    second = client.post(f"/api/v1/projects/{pid}/analyze").json()
    assert first["ontology_id"] != second["ontology_id"]
    # Only one ontology should be persisted.
    fetched = client.get(f"/api/v1/projects/{pid}/ontology").json()
    assert fetched["ontology_id"] == second["ontology_id"]


def test_envelope_reflects_ontology_presence(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json=_structured_brief())
    assert client.get(f"/api/v1/projects/{pid}").json()["has_ontology"] is False
    client.post(f"/api/v1/projects/{pid}/analyze")
    assert client.get(f"/api/v1/projects/{pid}").json()["has_ontology"] is True
