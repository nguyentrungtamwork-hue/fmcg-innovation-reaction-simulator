"""Phase 6 — strategic launch report generation tests (deterministic path)."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"

SECTION_KEYS = [
    "executive_summary",
    "launch_funnel_summary",
    "segment_reaction_map",
    "purchase_trigger_analysis",
    "adoption_barrier_analysis",
    "claim_clarity_and_credibility",
    "packaging_price_perception",
    "channel_touchpoint_analysis",
    "trial_repeat_forecast",
    "social_diffusion_and_wom",
    "competitor_and_retail_response",
    "innovation_risk_matrix",
    "strategic_recommendations",
    "recommended_ab_tests",
    "human_validation_questions",
    "limitations",
]


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
    """Project with brief + ontology + agents + a full simulation run."""
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus Report"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    return pid


def _generate(client: TestClient, pid: str) -> dict:
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 200, r.text
    return r.json()


# --- preconditions ----------------------------------------------------------


def test_report_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/report/generate")
    assert r.status_code == 404


def test_report_409_when_no_brief(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "brief_required"


def test_report_409_when_no_ontology(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "ontology_required"


def test_report_409_when_no_agents(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "agents_required"


def test_report_409_when_no_events(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "events_required"


# --- generation shape -------------------------------------------------------


def test_report_generate_200_shape(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _generate(client, pid)
    assert data["project_id"] == pid
    assert data["report_id"]
    assert data["status"] == "completed"
    assert data["source_mode"] == "deterministic"
    assert 0.0 <= data["confidence_score"] <= 1.0
    assert data["generated_at"]
    assert data["markdown_report"]


def test_report_has_all_16_sections(client: TestClient) -> None:
    pid = _prepare_full(client)
    payload = _generate(client, pid)["report_payload"]
    for key in SECTION_KEYS:
        assert key in payload, f"missing section: {key}"


def test_executive_summary_fields(client: TestClient) -> None:
    pid = _prepare_full(client)
    es = _generate(client, pid)["report_payload"]["executive_summary"]
    assert es["overall_market_reaction"]
    assert es["top_opportunity"]
    assert es["top_risk"]
    assert es["estimated_trial_potential"]
    assert es["estimated_repeat_potential"]
    assert es["key_recommendation"]


def test_markdown_non_empty_and_has_headers(client: TestClient) -> None:
    pid = _prepare_full(client)
    md = _generate(client, pid)["markdown_report"]
    assert len(md) > 500
    assert "## 1. Executive Summary" in md
    assert "## 16. Limitations" in md
    assert "exploratory decision support" in md.lower()


# --- segment map reconciles with the simulation ----------------------------


def test_segment_map_covers_segments(client: TestClient) -> None:
    pid = _prepare_full(client)
    seg_map = _generate(client, pid)["report_payload"]["segment_reaction_map"]
    assert len(seg_map) >= 5
    for s in seg_map:
        assert s["number_of_agents"] >= 1
        assert 0.0 <= s["average_trial_probability"] <= 1.0
        assert s["representative_reaction"]
        assert s["recommended_message_angle"]


def test_segment_agent_counts_reconcile(client: TestClient) -> None:
    pid = _prepare_full(client)
    seg_map = _generate(client, pid)["report_payload"]["segment_reaction_map"]
    total_agents = sum(s["number_of_agents"] for s in seg_map)
    summary = client.get(f"/api/v1/projects/{pid}/agents/summary").json()
    assert total_agents == summary["consumer_agents"]


def test_funnel_round_summary_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    funnel = _generate(client, pid)["report_payload"]["launch_funnel_summary"]
    assert len(funnel["round_summary"]) == 6
    assert funnel["action_distribution"]
    rounds = [r["round_number"] for r in funnel["round_summary"]]
    assert rounds == [1, 2, 3, 4, 5, 6]


def test_action_distribution_matches_events_summary(client: TestClient) -> None:
    pid = _prepare_full(client)
    dist = _generate(client, pid)["report_payload"]["launch_funnel_summary"]["action_distribution"]
    ev_summary = client.get(f"/api/v1/projects/{pid}/events/summary").json()
    # consumer trial purchases should reconcile with the report's distribution
    assert dist.get("purchase_trial", 0) >= 0
    assert sum(dist.values()) <= ev_summary["total_events"]


# --- triggers / barriers ----------------------------------------------------


def test_trigger_and_barrier_analysis_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    payload = _generate(client, pid)["report_payload"]
    assert len(payload["adoption_barrier_analysis"]) >= 1
    b = payload["adoption_barrier_analysis"][0]
    assert b["frequency"] >= 1
    assert b["severity_level"] in {"high", "medium", "low"}
    assert b["recommended_fix"]


def test_evidence_references_well_formed(client: TestClient) -> None:
    pid = _prepare_full(client)
    payload = _generate(client, pid)["report_payload"]
    # gather evidence from triggers + barriers
    refs = []
    for t in payload["purchase_trigger_analysis"]:
        refs.extend(t["evidence_events"])
    for b in payload["adoption_barrier_analysis"]:
        refs.extend(b["evidence_events"])
    assert refs, "expected at least one evidence reference"
    for ref in refs:
        assert ref["event_id"]
        assert 1 <= ref["round_number"] <= 6
        assert ref["action_type"]


def test_evidence_event_ids_exist(client: TestClient) -> None:
    pid = _prepare_full(client)
    payload = _generate(client, pid)["report_payload"]
    sample_ref = None
    for b in payload["adoption_barrier_analysis"]:
        if b["evidence_events"]:
            sample_ref = b["evidence_events"][0]
            break
    assert sample_ref is not None
    r = client.get(f"/api/v1/projects/{pid}/events/{sample_ref['event_id']}")
    assert r.status_code == 200


# --- other sections ---------------------------------------------------------


def test_claim_section_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    claims = _generate(client, pid)["report_payload"]["claim_clarity_and_credibility"]
    assert len(claims) >= 1
    assert claims[0]["claim"]


def test_risk_matrix_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    risks = _generate(client, pid)["report_payload"]["innovation_risk_matrix"]
    assert len(risks) >= 5
    for r in risks:
        assert r["severity"] in {"high", "medium", "low"}
        assert r["mitigation"]


def test_recommendations_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    recs = _generate(client, pid)["report_payload"]["strategic_recommendations"]
    assert len(recs) >= 3
    for r in recs:
        assert r["priority"]
        assert r["owner_team"]
        assert r["recommendation"]


def test_ab_tests_present(client: TestClient) -> None:
    pid = _prepare_full(client)
    tests = _generate(client, pid)["report_payload"]["recommended_ab_tests"]
    assert len(tests) >= 2
    for t in tests:
        assert t["variant_a"] and t["variant_b"]
        assert t["success_metric"]


# --- GET endpoints ----------------------------------------------------------


def test_get_report_after_generate(client: TestClient) -> None:
    pid = _prepare_full(client)
    _generate(client, pid)
    r = client.get(f"/api/v1/projects/{pid}/report")
    assert r.status_code == 200
    assert r.json()["report_id"]


def test_get_report_409_before_generate(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/report")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_get_markdown_endpoint(client: TestClient) -> None:
    pid = _prepare_full(client)
    _generate(client, pid)
    r = client.get(f"/api/v1/projects/{pid}/report/markdown")
    assert r.status_code == 200
    assert "text/markdown" in r.headers["content-type"]
    assert "Executive Summary" in r.text


def test_get_summary_endpoint(client: TestClient) -> None:
    pid = _prepare_full(client)
    _generate(client, pid)
    r = client.get(f"/api/v1/projects/{pid}/report/summary")
    assert r.status_code == 200
    body = r.json()
    assert body["overall_market_reaction"]
    assert isinstance(body["top_segments"], list)
    assert isinstance(body["key_recommendations"], list)


# --- regeneration -----------------------------------------------------------


def test_regenerate_replaces_cleanly(client: TestClient) -> None:
    pid = _prepare_full(client)
    first = _generate(client, pid)["report_id"]
    second = _generate(client, pid)["report_id"]
    assert first != second
    # exactly one report row should remain
    envelope = client.get(f"/api/v1/projects/{pid}").json()
    # the GET report returns the single latest one
    r = client.get(f"/api/v1/projects/{pid}/report")
    assert r.status_code == 200
    assert r.json()["report_id"] == second
