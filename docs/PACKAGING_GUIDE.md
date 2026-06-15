# PACKAGING_GUIDE.md

_How the local demo is packaged (Phase 10)._

## Docker (shareable local demo)
```bash
docker compose up --build
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000   (health: /healthz, status: /api/v1/system/status)
```
- **backend** service: `backend/Dockerfile` (python:3.12-slim) runs `uvicorn app.main:app` on :8000.
  SQLite lives on the named volume `backend_data` mounted at `/data`
  (`DATABASE_URL=sqlite:////data/fmcg_sim.db`), so demo data survives restarts.
  `ENVIRONMENT=docker` and `DEMO_MODE=true` are set; pass `OPENAI_API_KEY` from your shell to
  enable LLM paths.
- **frontend** service: `frontend/Dockerfile` is a two-stage build (node:20-alpine → nginx:alpine).
  `VITE_API_BASE_URL` is baked in at build time (default `http://localhost:8000/api/v1`, i.e. the
  host-mapped backend port the browser can reach). nginx serves the static bundle on :80, mapped
  to host :3000, with SPA fallback (`nginx.conf`).
- **CORS:** the backend allowlist already includes `http://localhost:3000`, so the dockerised
  frontend origin is accepted out of the box.

### Seeding demo data in Docker
```bash
docker compose exec backend python scripts/seed_demo.py --reset-demo
```

### Validation status
- `docker-compose.yml` parses as valid YAML; both build contexts and referenced files
  (`backend/Dockerfile`, `frontend/Dockerfile`, `frontend/nginx.conf`) exist.
- A full `docker compose build` was **not** executed in the authoring environment because Docker
  was not installed there. Run `docker compose config` and `docker compose up --build` on a host
  with Docker to confirm image builds.

## Demo seed (no Docker required)
```bash
cd backend
python scripts/seed_demo.py             # new FreshPlus demo project each run
python scripts/seed_demo.py --reset-demo  # delete prior demo projects first
```
Deterministic + offline. Runs project → brief → ontology → agents → simulation → report, plus a
sample Q&A and a 10% price-reduction scenario, then prints the `project_id` and the frontend/
backend URLs. Demo projects are named `FreshPlus Demo — <timestamp>`.

## CI smoke
`.github/workflows/ci.yml` runs on push/PR:
- **backend:** `pip install -r requirements.txt` → `pytest`
- **frontend:** `npm ci` → `npm test` → `npm run build`

## Deployment options
Local Docker, VPS Docker, and split managed hosting (Render/Railway backend + Vercel/Cloudflare
frontend) with required env vars and CORS notes are documented in
[docs/DEPLOYMENT_OPTIONS.md](DEPLOYMENT_OPTIONS.md). Production (Postgres/auth/jobs) is deferred.

## Live streaming (SSE) note
Agent Studio Live Mode streams over SSE; reverse proxies must not buffer it (`proxy_buffering off;`
for nginx in front of the API). The bundled frontend nginx serves static files only and does not
proxy the API. Details: `docs/LIVE_STREAMING_GUIDE.md` + `docs/DEPLOYMENT_OPTIONS.md`.

## Not included (by design)
Authentication, multi-user, live cloud deployment, production DB migrations, billing, and real
sales/social-data connectors are intentionally out of scope for this local MVP.
