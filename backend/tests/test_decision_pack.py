"""Phase 28 — Decision Pack aggregator tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"


def _brief() -> dict:
    return {
        "raw_text": SAMPLE_BRIEF_PATH.read_text(encoding="utf-8") if SAMPLE_BRIEF_PATH.exists() else "brief",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "category": "Ready-to-drink tea",
        "benefit": "Refreshes naturally with less sugar",
        "launch_market": "Vietnam",
    }


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "FreshPlus Pack"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/report/generate")
    assert r.status_code == 200, r.text
    return pid


def test_decision_pack_missing_project_404(client: TestClient) -> None:
    r = client.get("/api/v1/projects/nope/decision-pack")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "project_not_found"


def test_decision_pack_requires_report(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    r = client.get(f"/api/v1/projects/{pid}/decision-pack")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] in ("events_required", "report_required")


def test_decision_pack_succeeds_after_workflow(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/decision-pack")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["project_id"] == pid
    assert body["header"]["project_name"] == "FreshPlus Pack"
    assert "generated_at" in body


def test_decision_pack_includes_core_sections(client: TestClient) -> None:
    pid = _prepare_full(client)
    body = client.get(f"/api/v1/projects/{pid}/decision-pack").json()
    for key in (
        "header", "executive_summary", "scorecard", "top_findings", "biggest_risks",
        "next_best_actions", "scenario_summary", "sensitivity_summary", "assumptions_summary",
        "evidence_pack", "decision_history", "limitations",
    ):
        assert key in body
    assert body["scorecard"].get("overall_score") is not None
    assert len(body["top_findings"]) >= 1
    assert len(body["limitations"]) >= 1


def test_decision_pack_markdown_non_empty(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/decision-pack/markdown")
    assert r.status_code == 200
    text = r.text
    assert "# Decision Pack" in text
    assert "## Recommendation" in text
    assert "exploratory decision support" in text.lower()


def test_decision_pack_has_no_secrets(client: TestClient) -> None:
    pid = _prepare_full(client)
    raw = client.get(f"/api/v1/projects/{pid}/decision-pack").text.lower()
    for forbidden in ("openai_api_key", "api_key", "database_url", "secret_key", "password"):
        assert forbidden not in raw
