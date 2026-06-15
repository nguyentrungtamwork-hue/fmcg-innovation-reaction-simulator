# DEV_RUNBOOK.md

_One-stop local runbook for the FMCG Innovation Reaction Simulator (Phase 9)._

## Architecture (local)
```
┌─────────────────────────┐        REST/JSON        ┌──────────────────────────┐
│  Frontend (Vite + React) │  ───────────────────▶   │  Backend (FastAPI)        │
│  http://localhost:5173   │   VITE_API_BASE_URL      │  http://localhost:8000    │
│  pages/components/api     │  ◀───────────────────   │  /api/v1/...  + SQLite     │
└─────────────────────────┘   CORS: 5173 allowed     └──────────────────────────┘
```
Single-user, local SQLite (`backend/fmcg_sim.db`). No auth, no external data sources.

## Prerequisites
- Python 3.11+ (3.12 used in dev)
- Node 18+ (Node 24 / npm 11 used in dev)

## One-command dev
- **Windows:** `powershell -ExecutionPolicy Bypass -File scripts\dev.ps1`
- **macOS/Linux:** `bash scripts/dev.sh`  (or `make dev`)

Both launch the backend on `:8000` and the frontend on `:5173`. Open http://localhost:5173.

## Docker demo (one command)
```bash
docker compose up --build       # frontend :3000, backend :8000
docker compose exec backend python scripts/seed_demo.py --reset-demo   # optional demo data
```
Details + validation notes: [PACKAGING_GUIDE.md](PACKAGING_GUIDE.md).

## Demo seed (no Docker)
```bash
cd backend
python scripts/seed_demo.py             # new demo project each run
python scripts/seed_demo.py --reset-demo  # delete prior demo projects first
```
Deterministic + offline; prints the project id and frontend/backend URLs.

## Backend (manual)
```bash
cd backend
python -m venv .venv
# Windows: .\.venv\Scripts\Activate.ps1   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env                 # optional; no API key needed (LLM is optional)

python -m uvicorn app.main:app --reload --port 8000   # run API
python -m pytest -q                                   # run tests (109 passing)
python scripts/seed_demo.py --reset-demo              # seed a complete demo project
```
- SQLite schema is created automatically on startup (`init_db()`); no migrations to run.
- `GET /healthz` reports `{status, app, version, llm_configured}`.
- Every response carries an `X-Request-ID` header; errors return `{"detail": {"code", "message?", "request_id"}}`.
- Set `OPENAI_API_KEY` (+ optional `OPENAI_BASE_URL`, `OPENAI_MODEL`) to enable LLM paths.
  Set `FRONTEND_ORIGIN` to allow an extra CORS origin beyond `localhost:5173`.

## Frontend (manual)
```bash
cd frontend
npm install
cp .env.example .env          # optional; defaults to http://localhost:8000/api/v1
npm run dev                   # http://localhost:5173
npm run build                 # tsc --noEmit && vite build
npm test                      # vitest run (10 smoke tests)
npm run typecheck             # tsc --noEmit only
```

## Full local demo (happy path)
1. Start backend on `:8000`, frontend on `:5173`.
2. Open the dashboard → **Create project**.
3. **Workflow → Step 2:** click **Load sample brief** → **Submit brief**.
4. **Step 3:** Analyze ontology.
5. **Step 4:** Generate agents.
6. **Step 5:** Run simulation (6 rounds, seed 42).
7. **Step 6:** Generate report → **Open full report**.
8. **Events tab:** filter by round/segment/action; expand a row; click an agent to open the drawer.
9. **Q&A tab:** ask "Why is repeat purchase low?" → read the answer + evidence chips.
10. **Scenario Lab:** run a 10% price reduction → review the Baseline | Scenario | Δ table; optionally compare two scenarios.
11. Re-open the **Report** tab → baseline report is unchanged.

## Troubleshooting
- **Frontend shows "Cannot reach the backend"** — the API isn't running, or `VITE_API_BASE_URL` is wrong. Start the backend and reload.
- **CORS error in console** — the browser origin isn't in the allowlist. Dev origin `5173` is allowed by default; for another origin set `FRONTEND_ORIGIN` in `backend/.env`.
- **409 with a code** (e.g. `events_required`) — a pipeline step hasn't run yet. The UI shows a friendly hint; follow the workflow order.
- **Port already in use** — change `--port` (backend) / `server.port` in `vite.config.ts` (frontend) and `VITE_API_BASE_URL` accordingly.
- **`npm test` cannot find jsdom/vitest** — run `npm install` again in `frontend`.
