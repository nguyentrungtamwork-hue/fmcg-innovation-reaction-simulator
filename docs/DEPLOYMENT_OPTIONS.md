# DEPLOYMENT_OPTIONS.md

_How to run/share the FMCG Innovation Reaction Simulator. This is a local/internal MVP — no
production pipeline is implemented; this documents the realistic paths and the env vars needed._

## Option A — Local Docker demo (recommended for internal demos)
```bash
docker compose up --build
# Frontend: http://localhost:3000   Backend: http://localhost:8000
docker compose exec backend python scripts/seed_demo.py --reset-demo   # optional demo data
```
Single host, SQLite on a mounted volume. See `docs/PACKAGING_GUIDE.md`.

## Option B — VPS Docker (private company demo)
Copy the repo (or built images) to a VPS and run the same `docker compose up --build`.
- Put the backend behind a reverse proxy (nginx/Caddy) with TLS.
- Set `FRONTEND_ORIGIN` (backend env) to the public frontend URL so CORS allows it.
- Build the frontend with `VITE_API_BASE_URL` pointing at the public backend URL.
- Back up the SQLite volume (`backend_data`).

## Option C — Split hosting (managed)
- **Backend** → Render / Railway / Fly: deploy `backend/` (uvicorn). Set `OPENAI_API_KEY` (optional),
  `ENVIRONMENT=production`, `FRONTEND_ORIGIN=<frontend URL>`, and a persistent disk for the SQLite
  file (or move to Postgres — Option D).
- **Frontend** → Vercel / Cloudflare Pages / Netlify: build `frontend/` with
  `VITE_API_BASE_URL=https://<backend-host>/api/v1`. Static SPA (the included `nginx.conf` SPA
  fallback is for the Docker image; managed static hosts have their own SPA setting).
- **CORS:** add the frontend origin to the backend allowlist via `FRONTEND_ORIGIN`.

## Option D — Full production (future, not implemented)
- Replace SQLite with **Postgres** (`DATABASE_URL=postgresql://…`; SQLAlchemy already abstracts the
  engine, but migrations/connection pooling would need adding).
- Add **background jobs** for long simulations, **auth**, **object storage** for exports, and real
  **data connectors** (sales/scan/social). These are explicitly out of scope for the MVP.

## Environment variables
| Variable | Where | Purpose | Default |
|---|---|---|---|
| `VITE_API_BASE_URL` | frontend (build-time) | Backend API base | `http://localhost:8000/api/v1` |
| `DATABASE_URL` | backend | DB connection | `sqlite:///./fmcg_sim.db` (Docker: `/data/...`) |
| `ENVIRONMENT` | backend | Shown in `/system/status` | `local` |
| `DEMO_MODE` | backend | Demo badge flag | `false` (Docker: `true`) |
| `FRONTEND_ORIGIN` | backend | Extra CORS origin | `""` (5173/3000 already allowed) |
| `OPENAI_API_KEY` | backend | Enables optional LLM paths | `""` (deterministic fallback) |
| `OPENAI_BASE_URL`, `OPENAI_MODEL` | backend | LLM endpoint/model | OpenAI defaults |
| `LOG_JSON` | backend | Emit single-line JSON logs instead of readable text | `false` |
| `APP_LOG_MAX_ENTRIES` | backend | Max persisted app-log rows (bounded; oldest pruned) | `500` |

## CORS notes
The backend allows `localhost:5173` and `localhost:3000` by default; set `FRONTEND_ORIGIN` to add a
deployed origin. Every response carries `X-Request-ID`; errors use `{"detail":{"code",...}}`.

## SSE (live simulation) notes
Live Mode (Phase 18) streams over Server-Sent Events. Reverse proxies must **not buffer** the
stream. The backend already sets `Cache-Control: no-cache` and `X-Accel-Buffering: no`; for nginx in
front of the API add `proxy_buffering off;` on the API location. In split hosting the browser's
`EventSource` connects to the backend stream URL, so `FRONTEND_ORIGIN` must be in the backend CORS
allowlist. Managed platforms may cap long requests — keep `event_delay_ms` modest and rounds ≤6 for
demos. For production, move live runs to background jobs + Redis/pub-sub or a WebSocket gateway.
See `docs/LIVE_STREAMING_GUIDE.md`.

## Health checks & observability
Point your platform's health check at **`GET /healthz`** (liveness) and **`GET /readyz`**
(readiness: DB reachable + tables accessible). The UI's footer **Diagnostics** drawer reads
`/system/status`, `/readyz`, `/system/diagnostics`, and `/system/logs/recent-errors` (read-only, no
secrets). Every response has an `X-Request-ID` for log correlation. Set **`LOG_JSON=true`** for
single-line JSON logs; notable events/errors are also kept in a bounded `app_log_entries` table
(`APP_LOG_MAX_ENTRIES`, default 500) readable via `/system/logs`. Full details:
`docs/OBSERVABILITY.md`.

## Backup, restore & reset (Phase 25)
Local data management is JSON-bundle based and SQLite-friendly — full details in
`docs/DATA_MANAGEMENT.md`.
- **Per-project export/import:** `GET /api/v1/projects/{id}/export` (`format=json|zip`) →
  `POST /api/v1/projects/import` (create-new, fresh IDs). Also in the UI **Data Tools** page and the
  Project Home **Export Project** button. No secrets in bundles.
- **DB file backup:** `python backend/scripts/backup_sqlite.py [--zip]` (or `make backup`) copies the
  SQLite file to `backend/backups/` with a timestamp. For Postgres, use platform-native backups.
- **Reset/prune:** `python backend/scripts/reset_demo_data.py` (demo projects),
  `python backend/scripts/prune_app_logs.py`. API: `POST /api/v1/system/reset-demo` (DEMO_MODE only),
  `POST /api/v1/system/prune-logs`. `DELETE /api/v1/projects/{id}` cascades to all related rows.

## SQLite vs Postgres caveat
SQLite is perfect for a single-user local/VPS demo. For concurrent users or managed hosting with
ephemeral disks, move to Postgres (Option D) and add migrations — the ORM models are portable but
this work is intentionally deferred.
