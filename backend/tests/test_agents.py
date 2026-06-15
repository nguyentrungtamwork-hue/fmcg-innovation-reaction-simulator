"""Phase 4 — agent generation tests (fallback path)."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"

PROTECTED = (
    "race",
    "ethnicity",
    "religion",
    "political_affiliation",
    "sexual_orientation",
    "disability",
    "precise_address",
    "home_address",
    "health_diagnosis",
    "criminal_history",
)

NUMERIC_TRAITS = (
    "price_sensitivity",
    "novelty_seeking_level",
    "brand_loyalty_level",
    "claim_skepticism_level",
    "health_safety_concern_level",
    "convenience_need_level",
    "taste_or_sensory_importance",
    "packaging_sensitivity",
    "promotion_sensitivity",
    "social_influence_sensitivity",
    "review_dependency_level",
)


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


def _prepare_project(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus Agents"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    return pid


def test_generate_fails_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/agents/generate")
    assert r.status_code == 404


def test_generate_fails_when_ontology_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/agents/generate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ontology_required"


def test_default_generation_creates_50_consumers_and_5_market_actors(client: TestClient) -> None:
    pid = _prepare_project(client)
    r = client.post(f"/api/v1/projects/{pid}/agents/generate")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["consumer_agents"] == 50
    assert body["market_actor_agents"] == 5
    assert body["total_agents"] == 55
    assert body["source_mode"] == "fallback"


def test_segment_distribution_non_empty_and_matches_default(client: TestClient) -> None:
    pid = _prepare_project(client)
    body = client.post(f"/api/v1/projects/{pid}/agents/generate").json()
    dist = body["segment_distribution"]
    assert sum(dist.values()) == 50
    # 8 default segments should each be present at least once.
    assert len(dist) == 8


def test_consumer_payload_grounding_memory_traits(client: TestClient) -> None:
    pid = _prepare_project(client)
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    agents = client.get(f"/api/v1/projects/{pid}/agents?agent_type=consumer").json()
    assert len(agents) == 50
    for a in agents:
        prof = a["profile"]
        assert prof["grounding_sources"], f"missing grounding for {a['name']}"
        assert prof["initial_memory"], f"missing memory for {a['name']}"
        for t in NUMERIC_TRAITS:
            v = prof[t]
            assert isinstance(v, (int, float)), f"{t} not numeric for {a['name']}"
            assert 0.0 <= v <= 1.0, f"{t}={v} out of range for {a['name']}"


def test_market_actors_have_all_five_roles(client: TestClient) -> None:
    pid = _prepare_project(client)
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    agents = client.get(f"/api/v1/projects/{pid}/agents?agent_type=market_actor").json()
    roles = {a["role"] for a in agents}
    assert roles == {"Retailer", "Competitor", "Influencer", "SocialCommunity", "CategoryExpert"}
    for a in agents:
        prof = a["profile"]
        assert prof["evaluation_criteria"]
        assert 0.0 <= prof["influence_power"] <= 1.0
        assert 0.0 <= prof["trust_level"] <= 1.0


def test_get_agent_by_id(client: TestClient) -> None:
    pid = _prepare_project(client)
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    agents = client.get(f"/api/v1/projects/{pid}/agents").json()
    first = agents[0]
    r = client.get(f"/api/v1/projects/{pid}/agents/{first['id']}")
    assert r.status_code == 200
    assert r.json()["id"] == first["id"]

    r404 = client.get(f"/api/v1/projects/{pid}/agents/missing-id")
    assert r404.status_code == 404


def test_regeneration_replaces_old_agents(client: TestClient) -> None:
    pid = _prepare_project(client)
    first = client.post(f"/api/v1/projects/{pid}/agents/generate").json()
    second = client.post(f"/api/v1/projects/{pid}/agents/generate").json()
    assert first["total_agents"] == second["total_agents"] == 55
    after = client.get(f"/api/v1/projects/{pid}/agents").json()
    assert len(after) == 55  # no duplication


def test_protected_attributes_not_present(client: TestClient) -> None:
    pid = _prepare_project(client)
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    agents = client.get(f"/api/v1/projects/{pid}/agents").json()
    for a in agents:
        keys = {k.lower() for k in a["profile"].keys()}
        for p in PROTECTED:
            assert p not in keys, f"protected attr {p} found in agent {a['name']}"


def test_summary_endpoint(client: TestClient) -> None:
    pid = _prepare_project(client)
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    summary = client.get(f"/api/v1/projects/{pid}/agents/summary").json()
    assert summary["total_agents"] == 55
    assert summary["consumer_agents"] == 50
    assert summary["market_actor_agents"] == 5
    assert sum(summary["segment_distribution"].values()) == 50
    assert len(summary["average_trait_scores"]) == 11
    for v in summary["average_trait_scores"].values():
        assert 0.0 <= v <= 1.0


def test_filter_by_segment(client: TestClient) -> None:
    pid = _prepare_project(client)
    gen = client.post(f"/api/v1/projects/{pid}/agents/generate").json()
    seg = "Health/Safety-Conscious Buyer"
    expected = gen["segment_distribution"][seg]  # product-aware mix (Phase: per-product customization)
    agents = client.get(
        f"/api/v1/projects/{pid}/agents",
        params={"agent_type": "consumer", "segment_name": seg},
    ).json()
    assert len(agents) == expected and expected >= 1
    assert all(a["segment_name"] == seg for a in agents)
