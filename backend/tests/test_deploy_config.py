"""Phase 17 — demo project filter + deploy-config check tests."""
from fastapi.testclient import TestClient


def test_projects_demo_filter(client: TestClient) -> None:
    client.post("/api/v1/projects", json={"name": "Regular Concept"})
    client.post("/api/v1/projects", json={"name": "FreshPlus Demo — 2026-01-01"})

    all_projects = client.get("/api/v1/projects").json()
    assert len(all_projects) >= 2

    demo = client.get("/api/v1/projects?demo=true").json()
    assert len(demo) == 1
    assert demo[0]["name"].startswith("FreshPlus Demo")


def test_deploy_config_check_passes() -> None:
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    import check_deploy_config  # type: ignore

    checks = check_deploy_config.run_checks()
    failed = [name for name, ok, _ in checks if not ok]
    assert not failed, f"deploy-config checks failed: {failed}"
