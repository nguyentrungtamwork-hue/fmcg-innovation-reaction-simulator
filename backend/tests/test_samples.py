"""Phase 26 — sample library tests."""
from fastapi.testclient import TestClient

# Real brands we must never ship in the fictional sample library.
_REAL_BRANDS = ["coca-cola", "pepsi", "nestle", "unilever", "lipton", "dove", "lay's", "lays", "danone"]


def test_list_samples_returns_library(client: TestClient) -> None:
    r = client.get("/api/v1/system/samples")
    assert r.status_code == 200
    samples = r.json()["samples"]
    assert len(samples) >= 5
    ids = {s["sample_id"] for s in samples}
    assert "ready_to_drink_tea" in ids
    for s in samples:
        assert s["name"] and s["category"] and s["short_description"]
        assert isinstance(s["recommended_demo_path"], list)


def test_get_sample_detail(client: TestClient) -> None:
    r = client.get("/api/v1/system/samples/healthy_snack")
    assert r.status_code == 200
    body = r.json()
    assert body["sample_id"] == "healthy_snack"
    assert "Baked" in body["sample_brief_text"] or len(body["sample_brief_text"]) > 50
    assert body["structured"].get("category")


def test_get_sample_unknown_404(client: TestClient) -> None:
    r = client.get("/api/v1/system/samples/not_a_sample")
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "sample_not_found"


def test_load_sample_creates_project_and_brief(client: TestClient) -> None:
    r = client.post("/api/v1/system/samples/ready_to_drink_tea/load", json={"project_name": "My Sample"})
    assert r.status_code == 200, r.text
    body = r.json()
    pid = body["project_id"]
    assert body["completed_steps"] == ["project_created", "brief_submitted"]
    env = client.get(f"/api/v1/projects/{pid}").json()
    assert env["project"]["name"] == "My Sample"
    assert env["has_brief"] is True


def test_load_sample_unknown_404(client: TestClient) -> None:
    r = client.post("/api/v1/system/samples/nope/load", json={})
    assert r.status_code == 404
    assert r.json()["detail"]["code"] == "sample_not_found"


def test_load_sample_run_pipeline(client: TestClient) -> None:
    r = client.post("/api/v1/system/samples/ready_to_drink_tea/load", json={"run_pipeline": True})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "report" in body["completed_steps"]
    pid = body["project_id"]
    assert client.get(f"/api/v1/projects/{pid}/report").status_code == 200


def test_samples_contain_no_real_brands(client: TestClient) -> None:
    raw = client.get("/api/v1/system/samples").text.lower()
    for sid in [s["sample_id"] for s in client.get("/api/v1/system/samples").json()["samples"]]:
        raw += client.get(f"/api/v1/system/samples/{sid}").text.lower()
    for brand in _REAL_BRANDS:
        assert brand not in raw
