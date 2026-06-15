from fastapi.testclient import TestClient


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_create_and_get_project(client: TestClient) -> None:
    r = client.post(
        "/api/v1/projects",
        json={"name": "FreshPlus Low-Sugar Tea", "category": "RTD tea", "market": "VN"},
    )
    assert r.status_code == 201, r.text
    pid = r.json()["id"]
    assert r.json()["status"] == "created"

    r2 = client.get(f"/api/v1/projects/{pid}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["project"]["id"] == pid
    assert body["has_brief"] is False
    assert body["agents_count"] == 0


def test_list_projects(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "A"})
    client.post("/api/v1/projects", json={"name": "B"})
    r = client.get("/api/v1/projects")
    assert r.status_code == 200
    names = [p["name"] for p in r.json()]
    assert {"A", "B"}.issubset(names)


def test_project_not_found(client: TestClient) -> None:
    r = client.get("/api/v1/projects/does-not-exist")
    assert r.status_code == 404
