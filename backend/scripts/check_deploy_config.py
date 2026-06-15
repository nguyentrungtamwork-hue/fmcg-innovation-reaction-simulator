"""Deployment config sanity check (Phase 17).

Verifies the packaging/config artifacts and env conventions are present so a
developer can confidently deploy (Railway/Render + Vercel/Cloudflare, or VPS
Docker). Read-only — no network, no secrets. Run from the repo root or backend:

    cd backend && python scripts/check_deploy_config.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _exists(rel: str) -> bool:
    return (ROOT / rel).exists()


def _contains(rel: str, needle: str) -> bool:
    p = ROOT / rel
    return p.exists() and needle in p.read_text(encoding="utf-8", errors="ignore")


def run_checks() -> list[tuple[str, bool, str]]:
    checks: list[tuple[str, bool, str]] = []

    checks.append(("docker-compose.yml exists", _exists("docker-compose.yml"), "root compose file"))
    checks.append(("backend Dockerfile exists", _exists("backend/Dockerfile"), ""))
    checks.append(("frontend Dockerfile exists", _exists("frontend/Dockerfile"), ""))
    checks.append(("frontend nginx.conf exists", _exists("frontend/nginx.conf"), "SPA fallback"))

    checks.append((
        "frontend .env.example has VITE_API_BASE_URL",
        _contains("frontend/.env.example", "VITE_API_BASE_URL"),
        "frontend points at backend",
    ))
    checks.append((
        "compose passes VITE_API_BASE_URL build arg",
        _contains("docker-compose.yml", "VITE_API_BASE_URL"),
        "",
    ))
    checks.append((
        "compose sets FRONTEND_ORIGIN + DEMO_MODE",
        _contains("docker-compose.yml", "FRONTEND_ORIGIN") and _contains("docker-compose.yml", "DEMO_MODE"),
        "backend CORS + demo flag",
    ))

    # CORS reads env + status hides secrets — verified against the source.
    checks.append((
        "config exposes FRONTEND_ORIGIN + resolved_cors_origins()",
        _contains("backend/app/core/config.py", "frontend_origin")
        and _contains("backend/app/core/config.py", "resolved_cors_origins"),
        "env-driven CORS",
    ))
    # The key may be read as bool(settings.openai_api_key); it must never be an output field.
    checks.append((
        "system/status exposes llm_configured (bool) and never the key value",
        _contains("backend/app/api/v1/system.py", "llm_configured")
        and not _contains("backend/app/api/v1/system.py", '"openai_api_key"')
        and not _contains("backend/app/api/v1/system.py", "api_key="),
        "no secret leak",
    ))
    checks.append((
        "deployment docs exist",
        _exists("docs/DEPLOYMENT_OPTIONS.md") and _exists("docs/DEPLOYMENT_CHECKLIST.md"),
        "",
    ))

    return checks


def main() -> int:
    checks = run_checks()
    failed = 0
    for name, ok, note in checks:
        mark = "[OK]  " if ok else "[FAIL]"
        suffix = f"  ({note})" if note else ""
        print(f"{mark} {name}{suffix}")
        if not ok:
            failed += 1
    print("")
    if failed:
        print(f"{failed} check(s) failed.")
        return 1
    print(f"All {len(checks)} deploy-config checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
