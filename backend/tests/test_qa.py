"""Phase 7 — Deep Q&A tests (deterministic, offline)."""
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
    """Project with brief + ontology + agents + simulation + report."""
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus QA"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 200, r.text
    return pid


def _ask(client: TestClient, pid: str, question: str, **extra) -> dict:
    body = {"question": question, **extra}
    r = client.post(f"/api/v1/projects/{pid}/ask", json=body)
    assert r.status_code == 200, r.text
    return r.json()


# --- preconditions ----------------------------------------------------------


def test_ask_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/ask", json={"question": "why is repeat low?"})
    assert r.status_code == 404


def test_ask_409_when_report_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    # events exist but no report yet
    r = client.post(f"/api/v1/projects/{pid}/ask", json={"question": "why is repeat low?"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_ask_409_when_events_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    r = client.post(f"/api/v1/projects/{pid}/ask", json={"question": "why is repeat low?"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "events_required"


# --- intent routing + content ----------------------------------------------


def test_ask_repeat_question(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Why is repeat purchase probability so low?")
    assert data["intent"] == "repeat_purchase"
    assert data["answer"]["direct_answer"]
    assert data["source_mode"] == "deterministic"


def test_ask_target_segment_question(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Which segment should we target first?")
    assert data["intent"] == "target_segment"
    assert data["answer"]["supporting_segments"]


def test_ask_claim_risk_question(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Which claim is the riskiest and least believable?")
    assert data["intent"] == "claim_risk"
    assert data["answer"]["direct_answer"]


def test_ask_pricing_question(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Is the premium price a problem and how should we handle promo?")
    assert data["intent"] == "pricing"
    assert data["answer"]["direct_answer"]


def test_ask_includes_evidence_references(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "What are the biggest adoption barriers?", include_evidence=True, max_evidence_events=5)
    refs = data["answer"]["supporting_events"]
    assert refs, "expected supporting events"
    for ref in refs:
        assert ref["event_id"]
        assert 1 <= ref["round_number"] <= 6
        assert ref["action_type"]


def test_ask_confidence_in_range(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Give me an overall summary in simple business language.")
    assert 0.0 <= data["answer"]["confidence_score"] <= 1.0


def test_ask_evidence_excluded_when_disabled(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "What are the biggest adoption barriers?", include_evidence=False)
    assert data["answer"]["supporting_events"] == []


def test_ask_interview_returns_selected_agents(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Interview 3 skeptical consumers about the claim.")
    assert data["intent"] == "interview_agents"
    ans = data["answer"]
    assert len(ans["selected_agents"]) == 3
    assert len(ans["simulated_interview_answers"]) == 3
    for iv in ans["simulated_interview_answers"]:
        assert iv["agent_id"]
        assert iv["answer"]
    # must be clearly flagged as simulated
    assert any("simulated" in lim.lower() for lim in ans["limitations"])


def test_ask_deterministic_fallback_without_llm(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _ask(client, pid, "Why is repeat low?", use_llm=True)
    # no API key configured in tests → must fall back gracefully
    assert data["source_mode"] == "deterministic"
    assert data["answer"]["direct_answer"]
