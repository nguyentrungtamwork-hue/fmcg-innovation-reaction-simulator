"""Phase 14 — executive briefing tests."""
from pathlib import Path

from fastapi.testclient import TestClient

SAMPLE_BRIEF_PATH = Path(__file__).resolve().parents[2] / "samples" / "sample_innovation_brief.md"

ALLOWED_STATUS = {"move_forward", "validate_before_move_forward", "revise_and_retest", "hold"}
SECTIONS = [
    "briefing_header",
    "situation",
    "top_findings",
    "biggest_risks",
    "readiness_assessment",
    "what_changed_recently",
    "decision_recommendation",
    "next_best_actions",
    "validation_plan",
    "evidence_pack",
    "limitations",
]


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


def _prepare_full(client: TestClient) -> str:
    pid = client.post("/api/v1/projects", json={"name": "Briefing"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    assert client.post(f"/api/v1/projects/{pid}/report/generate").status_code == 200
    return pid


def _generate(client: TestClient, pid: str) -> dict:
    r = client.post(f"/api/v1/projects/{pid}/briefing/generate", json={})
    assert r.status_code == 200, r.text
    return r.json()


# --- preconditions ----------------------------------------------------------


def test_briefing_404_when_project_missing(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/briefing/generate", json={})
    assert r.status_code == 404


def test_briefing_409_when_report_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    client.post(f"/api/v1/projects/{pid}/simulate")
    r = client.post(f"/api/v1/projects/{pid}/briefing/generate", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "report_required"


def test_briefing_409_when_events_missing(client: TestClient) -> None:
    pid = client.post("/api/v1/projects", json={"name": "x"}).json()["id"]
    client.post(f"/api/v1/projects/{pid}/brief", json=_brief())
    client.post(f"/api/v1/projects/{pid}/analyze")
    client.post(f"/api/v1/projects/{pid}/agents/generate")
    r = client.post(f"/api/v1/projects/{pid}/briefing/generate", json={})
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "events_required"


# --- generation -------------------------------------------------------------


def test_briefing_generate_succeeds(client: TestClient) -> None:
    pid = _prepare_full(client)
    data = _generate(client, pid)
    assert data["source_mode"] == "deterministic"
    assert data["briefing_id"]
    assert data["markdown"]


def test_briefing_payload_has_all_sections(client: TestClient) -> None:
    pid = _prepare_full(client)
    payload = _generate(client, pid)["briefing_payload"]
    for s in SECTIONS:
        assert s in payload, f"missing section {s}"


def test_briefing_includes_next_actions(client: TestClient) -> None:
    pid = _prepare_full(client)
    actions = _generate(client, pid)["briefing_payload"]["next_best_actions"]
    assert len(actions) >= 3
    for a in actions:
        assert a["owner_team"]
        assert a["effort"] in {"low", "medium", "high"}
        assert a["action"]


def test_briefing_includes_limitations(client: TestClient) -> None:
    pid = _prepare_full(client)
    lims = _generate(client, pid)["briefing_payload"]["limitations"]
    assert any("exploratory" in l.lower() for l in lims)
    assert any("real consumer validation" in l.lower() for l in lims)


def test_briefing_recommendation_status_allowed(client: TestClient) -> None:
    pid = _prepare_full(client)
    status = _generate(client, pid)["briefing_payload"]["briefing_header"]["recommendation_status"]
    assert status in ALLOWED_STATUS


def test_briefing_markdown_has_sections(client: TestClient) -> None:
    pid = _prepare_full(client)
    md = _generate(client, pid)["markdown"]
    assert "# Executive Launch Briefing" in md
    assert "## Next Best Actions" in md
    assert "## Limitations" in md


# --- get / export -----------------------------------------------------------


def test_get_briefing_after_generate(client: TestClient) -> None:
    pid = _prepare_full(client)
    _generate(client, pid)
    r = client.get(f"/api/v1/projects/{pid}/briefing")
    assert r.status_code == 200
    assert r.json()["briefing_id"]


def test_get_briefing_409_before_generate(client: TestClient) -> None:
    pid = _prepare_full(client)
    r = client.get(f"/api/v1/projects/{pid}/briefing")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "briefing_required"


def test_briefing_export(client: TestClient) -> None:
    pid = _prepare_full(client)
    _generate(client, pid)
    j = client.get(f"/api/v1/projects/{pid}/briefing/export?format=json")
    assert j.status_code == 200 and len(j.content) > 50
    m = client.get(f"/api/v1/projects/{pid}/briefing/export?format=markdown")
    assert m.status_code == 200
    assert "Executive Launch Briefing" in m.text
