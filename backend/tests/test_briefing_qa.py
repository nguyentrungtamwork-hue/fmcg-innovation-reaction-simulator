"""Phase 15 — briefing Q&A, audience tailoring, board summary tests."""
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


def _prepare_report(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "BQA"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    return pid


def _prepare_briefing(client: TestClient) -> str:
    pid = _prepare_report(client)
    assert client.post(f"/api/v1/projects/{pid}/briefing/generate", json={}).status_code == 200
    return pid


# --- ask --------------------------------------------------------------------


def test_ask_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/briefing/ask", json={"question": "why?"})
    assert r.status_code == 404


def test_ask_409_when_briefing_missing(client: TestClient) -> None:
    pid = _prepare_report(client)  # report but no briefing
    r = client.post(f"/api/v1/projects/{pid}/briefing/ask", json={"question": "why?"})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "briefing_required"


def test_ask_recommendation_status(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    r = client.post(f"/api/v1/projects/{pid}/briefing/ask", json={"question": "Why is the recommendation what it is?"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["intent"] == "explain_recommendation_status"
    assert body["answer"]["direct_answer"]
    assert body["source_mode"] == "deterministic"


def test_ask_includes_evidence_and_limitations(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    body = client.post(
        f"/api/v1/projects/{pid}/briefing/ask",
        json={"question": "What evidence supports the recommendation?", "include_evidence": True, "max_evidence_items": 5},
    ).json()
    a = body["answer"]
    assert a["limitations"]
    assert 0.0 <= a["confidence_score"] <= 1.0
    assert isinstance(a["supporting_evidence"], list)


# --- tailor -----------------------------------------------------------------


def test_tailor_executive(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    r = client.post(f"/api/v1/projects/{pid}/briefing/tailor", json={"audience": "executive"})
    assert r.status_code == 200, r.text
    assert r.json()["tailored_payload"]["headline"]
    assert r.json()["markdown"]


def test_tailor_trade_sales(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    r = client.post(f"/api/v1/projects/{pid}/briefing/tailor", json={"audience": "trade_sales"})
    assert r.status_code == 200, r.text
    assert "Trade Sales" in r.json()["tailored_payload"]["headline"] or "trade" in r.json()["markdown"].lower()


def test_tailor_differs_by_audience(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    ex = client.post(f"/api/v1/projects/{pid}/briefing/tailor", json={"audience": "executive"}).json()["tailored_payload"]
    rd = client.post(f"/api/v1/projects/{pid}/briefing/tailor", json={"audience": "rd_product"}).json()["tailored_payload"]
    assert ex["audience_priority"] != rd["audience_priority"]
    assert ex["what_this_audience_needs_to_know"] != rd["what_this_audience_needs_to_know"]


# --- board summary ----------------------------------------------------------


def test_board_summary_generate(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    r = client.post(f"/api/v1/projects/{pid}/briefing/board-summary", json={})
    assert r.status_code == 200, r.text
    assert r.json()["summary_payload"]["headline_recommendation"]


def test_board_summary_has_three_each(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    sp = client.post(f"/api/v1/projects/{pid}/briefing/board-summary", json={}).json()["summary_payload"]
    assert 1 <= len(sp["three_key_findings"]) <= 3
    assert 1 <= len(sp["top_three_risks"]) <= 3
    assert 1 <= len(sp["next_three_actions"]) <= 3
    assert sp["decision_gate"]


def test_board_summary_markdown_non_empty(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    md = client.post(f"/api/v1/projects/{pid}/briefing/board-summary", json={}).json()["markdown"]
    assert "Board Summary" in md
    assert len(md) > 100


def test_board_summary_get_and_export(client: TestClient) -> None:
    pid = _prepare_briefing(client)
    # before generation -> 409
    assert client.get(f"/api/v1/projects/{pid}/briefing/board-summary").status_code == 409
    client.post(f"/api/v1/projects/{pid}/briefing/board-summary", json={})
    assert client.get(f"/api/v1/projects/{pid}/briefing/board-summary").status_code == 200
    j = client.get(f"/api/v1/projects/{pid}/briefing/board-summary/export?format=json")
    assert j.status_code == 200 and len(j.content) > 50
    m = client.get(f"/api/v1/projects/{pid}/briefing/board-summary/export?format=markdown")
    assert m.status_code == 200 and "Board Summary" in m.text
