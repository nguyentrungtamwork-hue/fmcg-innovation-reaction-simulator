import io

from fastapi.testclient import TestClient


def _new_project(client: TestClient) -> str:
    r = client.post("/api/v1/projects", json={"name": "Test"})
    return r.json()["id"]


def test_submit_brief_json(client: TestClient) -> None:
    pid = _new_project(client)
    payload = {
        "raw_text": "Launch low-sugar tea for urban office workers.",
        "brand": "FreshPlus",
        "product_name": "FreshPlus Herbal Cool",
        "functional_claims": ["less sugar", "naturally cooling"],
        "channels": ["convenience store", "supermarket", "TikTok Shop"],
    }
    r = client.post(f"/api/v1/projects/{pid}/brief", json=payload)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["stored"] is True
    assert body["field_count"] >= 4

    envelope = client.get(f"/api/v1/projects/{pid}").json()
    assert envelope["has_brief"] is True


def test_submit_brief_upload(client: TestClient) -> None:
    pid = _new_project(client)
    file_bytes = b"# Sample Brief\nBrand: FreshPlus\nClaim: less sugar.\n"
    files = {"file": ("brief.md", io.BytesIO(file_bytes), "text/markdown")}
    r = client.post(f"/api/v1/projects/{pid}/brief/upload", files=files)
    assert r.status_code == 200, r.text
    assert r.json()["stored"] is True


def test_brief_on_missing_project(client: TestClient) -> None:
    r = client.post("/api/v1/projects/nope/brief", json={"raw_text": "x"})
    assert r.status_code == 404


def test_analyze_requires_brief(client: TestClient) -> None:
    pid = _new_project(client)
    r = client.post(f"/api/v1/projects/{pid}/analyze")
    assert r.status_code == 409
    assert r.json()["detail"]["code"] == "brief_required"


def test_analyze_returns_placeholder(client: TestClient) -> None:
    pid = _new_project(client)
    client.post(f"/api/v1/projects/{pid}/brief", json={"raw_text": "hello"})
    r = client.post(f"/api/v1/projects/{pid}/analyze")
    assert r.status_code == 200
    body = r.json()
    assert "ontology_id" in body
    assert isinstance(body["entities"], list)
    assert isinstance(body["missing_information"], list)
