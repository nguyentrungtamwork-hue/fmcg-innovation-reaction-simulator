# FMCG Innovation Reaction Simulator

A local multi-agent simulator that predicts how target consumers will react when an FMCG brand launches a new product innovation. Inspired architecturally (not by code) by [MiroFish](https://github.com/666ghj/MiroFish), customized end-to-end for FMCG launch decisions.

> **Status:** Phase 23 — observability & operational polish. Added **`/readyz`** (DB + tables check), an enhanced non-secret **`/system/status`**, and a read-only **`/system/diagnostics`** (counts + feature flags + warnings + request_id). Frontend gains a footer **Diagnostics** drawer, a global **ErrorBoundary** (friendly fallback + retry/home), and **Reference ID** surfacing in errors (request-id captured from headers/body). No secrets exposed. Backend: **195 tests** passing. Frontend: **53 Vitest tests** + `vite build` green. Next: Phase 24.

## Repository layout

```
backend/             FastAPI service
  app/
    api/v1/          Endpoint routers
    core/            Settings
    models/          SQLAlchemy ORM
    schemas/         Pydantic request/response
    services/        Business logic (ontology, agents, simulation, report, qa, scenarios)
    storage/         Database engine + session
  tests/             pytest (102 tests)
frontend/            Vite + React + TypeScript dashboard (Phase 8)
  src/
    api/             Typed REST client
    components/      Layout, Stepper, MetricCard, EvidenceChip, …
    pages/           ProjectList, ProjectWorkflow, Report, QA, ScenarioLab
docs/                Design documents + guides (see FRONTEND_GUIDE.md)
samples/             Sample innovation brief and sample outputs
```

## Docker demo (shareable, one command)
```bash
docker compose up --build
# Frontend: http://localhost:3000   Backend: http://localhost:8000
```
Then optionally seed a complete demo project:
```bash
docker compose exec backend python scripts/seed_demo.py --reset-demo
```
See [docs/PACKAGING_GUIDE.md](docs/PACKAGING_GUIDE.md) and [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md).

## Demo seed (no Docker)
```bash
cd backend && python scripts/seed_demo.py --reset-demo
```
Deterministic, offline. Builds project → brief → ontology → agents → simulation → report (+ sample
Q&A + price-reduction scenario) and prints the project URL.

## Frontend — setup & run
The dashboard lives in `/frontend` and calls the backend over REST. See
[docs/FRONTEND_GUIDE.md](docs/FRONTEND_GUIDE.md) and [docs/DEV_RUNBOOK.md](docs/DEV_RUNBOOK.md).

**One command** (starts backend :8000 + frontend :5173):
```bash
# Windows
powershell -ExecutionPolicy Bypass -File scripts\dev.ps1
# macOS/Linux
bash scripts/dev.sh        # or: make dev
```

**Manual:**
```bash
# Terminal A — backend
cd backend && python -m uvicorn app.main:app --reload --port 8000

# Terminal B — frontend
cd frontend
npm install
cp .env.example .env       # optional; defaults to http://localhost:8000/api/v1
npm run dev                # http://localhost:5173
npm test                   # vitest smoke tests
npm run build              # tsc --noEmit && vite build
npm run test:e2e           # opt-in Playwright browser smoke (see docs/TESTING_GUIDE.md)
```

The backend CORS allowlist already includes `http://localhost:5173`. Set `FRONTEND_ORIGIN`
in the backend `.env` to allow an additional deployed origin. Every backend response carries
an `X-Request-ID` header; errors return `{"detail": {"code", "message?", "request_id"}}`.

## Backend — setup & run

### 1. Prerequisites
- Python 3.11+
- (Optional) `uv` or `virtualenv`

### 2. Install
```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
```
No API keys are needed for Phase 2 — the placeholder services do not call any LLM yet.

### 4. Run
```bash
uvicorn app.main:app --reload --port 8000
```
- Health check: http://localhost:8000/healthz
- Interactive docs: http://localhost:8000/docs

### 5. Try the API
```bash
# Create a project
curl -X POST http://localhost:8000/api/v1/projects \
  -H "Content-Type: application/json" \
  -d '{"name":"FreshPlus Launch","category":"RTD tea","market":"VN"}'

# Submit a brief (replace PROJECT_ID)
curl -X POST http://localhost:8000/api/v1/projects/PROJECT_ID/brief \
  -H "Content-Type: application/json" \
  -d @../samples/sample_innovation_brief.md  # or use the JSON shape from API_SPEC.md

# Extract FMCG ontology from the brief (LLM if OPENAI_API_KEY set; deterministic fallback otherwise)
curl -X POST http://localhost:8000/api/v1/projects/PROJECT_ID/analyze

# Fetch the persisted ontology
curl http://localhost:8000/api/v1/projects/PROJECT_ID/ontology
```

### Agent generation notes
- Requires that `POST /analyze` has been run first (returns 409 `ontology_required` otherwise).
- Default run produces **50 consumer agents across 8 segments + 5 market actors** (Retailer, Competitor, Influencer, SocialCommunity, CategoryExpert).
- Generation is **deterministic with a seed** (default 42) and runs in fallback mode without an LLM key.
- Re-running the endpoint replaces existing agents cleanly — no duplication.
- Sample output: [samples/sample_agents.json](samples/sample_agents.json).
- Protected attributes (race, religion, health diagnosis, etc.) are scrubbed from any payload before persistence.

### Simulation notes (Phase 5)
- Requires that agents have been generated first (`409 agents_required` otherwise; also `409 brief_required` / `ontology_required`).
- Runs a **6-round launch funnel** (Concept → Comms → Shelf/e-comm → Trial → Post-trial → Diffusion). 50 consumers + 5 market actors × 6 rounds = **330 events**.
- **Deterministic given a seed** (default 42) — re-running the same agents produces an identical action distribution. Full 330-event run completes in well under 5s in fallback.
- `force_rerun=true` (default) clears prior events and resets each agent's `action_history` / `simulation_memory` — no accumulation across reruns.
- Scoring is transparent and segment-weighted (see [docs/SCORING_LOGIC.md](docs/SCORING_LOGIC.md)); every event carries grounded `reasoning`, a first-person `generated_reaction`, `emotional_tone`, and the full raw `scores` dict.
- Sample trace: [samples/sample_events.json](samples/sample_events.json).

### Report notes (Phase 6)
- `POST /report/generate` synthesizes the persisted brief + ontology + agents + events into a **16-section** strategic launch report. Requires a completed simulation (`409 events_required` otherwise; also `409 brief_required` / `ontology_required` / `agents_required`).
- **Deterministic builder** grounds every quantitative claim in event aggregates and attaches compact evidence refs (event_id, round, agent, segment, action, excerpt). Optional LLM narrative enhancement (`use_llm_narrative=true`) only rewrites executive-summary prose and falls back gracefully — tests run offline.
- Regeneration **replaces** the prior report (no stale duplicates). Read it back via `GET /report`, `/report/markdown`, `/report/summary`, or `/report/export`.
- Output is **exploratory decision support, not a guaranteed forecast**; the report recommends validating findings with real consumer research.
- Sample report: [samples/sample_report.json](samples/sample_report.json) · [samples/sample_report.md](samples/sample_report.md).

### Deep Q&A + scenario notes (Phase 7)
- `POST /ask` answers natural-language questions **strictly from persisted data** (report payload, baseline events, agents + their simulation memory, ontology) — never generic marketing knowledge. A 12-intent classifier routes to deterministic, evidence-cited answers (`409 events_required` / `409 report_required`). Interview-style questions ("interview 3 skeptical consumers") return simulated persona answers, clearly flagged as simulated. Optional `use_llm=true` only rephrases prose and falls back gracefully.
- `POST /scenario` re-simulates the launch under 10 what-if levers (price, sampling, promotion, claim credibility, channel focus, packaging, social proof, sensory risk, retailer support, competitor pressure) **without touching the baseline** simulation, report, or agent memory. Scenario events are tagged `run_type="scenario"`+`scenario_id`; the response returns a baseline-vs-scenario delta (metrics, segments, actions, triggers, barriers, recommendations, conclusion). List/detail/delta/delete via `GET/DELETE /scenarios`.
- Both surfaces carry the **exploratory decision-support** disclaimer.
- Samples: [samples/sample_qa_answers.json](samples/sample_qa_answers.json) · [samples/sample_scenario_price_reduction.json](samples/sample_scenario_price_reduction.json).

### Observability notes (Phase 23–24)
- Every response carries `X-Request-ID`; errors use `{"detail":{"code","message?","request_id"}}`.
- Set **`LOG_JSON=true`** for single-line JSON access/exception logs (default: readable text).
- Notable events/errors are persisted to a **bounded** `app_log_entries` table (`APP_LOG_MAX_ENTRIES`,
  default 500) and exposed read-only via `GET /api/v1/system/logs` and `/system/logs/recent-errors`;
  `/system/diagnostics` reports `recent_error_count/recent_warning_count/last_error/log_retention_limit`.
  No secrets are ever logged or returned. See [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md).

### Innovation Pipeline Board (Phase 30)
- A lightweight Kanban-style board at `/portfolio/pipeline` tracking each project through 12 stages
  (new_concept → archived) with **Apply Decision Board** (maps go/validate/revise/hold onto stages,
  preserving manual stages by default) and an **Update Stage** modal. Every change writes a
  decision-history entry. Project Home shows a stage chip + Update Stage button.
- `GET/PATCH /projects/{id}/pipeline-status`, `GET /portfolio/pipeline`,
  `POST /portfolio/pipeline/apply-decision-board`. See [docs/PIPELINE_BOARD_GUIDE.md](docs/PIPELINE_BOARD_GUIDE.md).

### Portfolio Decision Board (Phase 29)
- A cross-project leadership roll-up at `/portfolio/decision-board` classifying every concept
  **go / validate / revise / hold / incomplete** (deterministic, reusing scorecard + briefing logic),
  with summary counts, rankings, a portfolio recommendation, and per-project Decision Pack links.
  Print/PDF-ready + Markdown/JSON. `GET /portfolio/decision-board[?project_ids=…][/markdown]`.
- See [docs/PORTFOLIO_DECISION_BOARD.md](docs/PORTFOLIO_DECISION_BOARD.md). Heuristic, not a forecast.

### Stakeholder Decision Pack (Phase 28)
- A print/PDF-ready, **read-only** decision document at `/projects/:id/decision-pack` composed from
  existing outputs (no new scoring, no LLM): recommendation, scorecard, findings, risks, actions,
  scenario snapshot, assumptions, evidence, decision history. Print/Save-as-PDF + Markdown/JSON
  downloads + copy local read-only link. `GET /projects/{id}/decision-pack[/markdown]`.
- See [docs/DECISION_PACK_GUIDE.md](docs/DECISION_PACK_GUIDE.md). Exploratory — not a market forecast.

### Guided tours & demo auto-play (Phase 27)
- **Demo Control Panel** (footer **Tours & Demo**, Samples page, empty Projects state): start the
  **First-Time** or **Agent Studio** tour, **Play Demo (Quick/Full)**, or reset onboarding/tour state.
- Lightweight custom coachmark/spotlight tours (no tour library); skippable, keyboard-navigable, and
  remembered in `localStorage`. **Play Demo** loads the RTD-tea sample and walks the key surfaces.
- Tours explain **simulated** outputs — not real-world forecasts. See [docs/GUIDED_TOURS.md](docs/GUIDED_TOURS.md).

### Onboarding & sample library (Phase 26)
- **Samples** nav → `/samples`: load a ready-made (fictional) FMCG concept as a new project (brief
  only, or full deterministic pipeline). `GET/POST /api/v1/system/samples…`.
- First-run **onboarding checklist** on the Projects page (dismissible, `localStorage`), guided
  empty-states, contextual **?** help popovers, and a searchable categorized **Glossary**.
- See [docs/SAMPLE_LIBRARY_GUIDE.md](docs/SAMPLE_LIBRARY_GUIDE.md) and
  [docs/ONBOARDING_GUIDE.md](docs/ONBOARDING_GUIDE.md). Samples are illustrative, not market validation.

### Data management notes (Phase 25)
- **Export/import a project** as a single no-secret JSON bundle: `GET /projects/{id}/export`
  (`format=json|zip`) and `POST /projects/import` (create-new, fresh IDs). Also in the UI **Data
  Tools** page and Project Home → **Export Project**.
- **Backup SQLite:** `python backend/scripts/backup_sqlite.py [--zip]` (or `make backup`).
- **Reset/prune:** `python backend/scripts/reset_demo_data.py`, `python backend/scripts/prune_app_logs.py`;
  `DELETE /projects/{id}` cascades to all related rows. See [docs/DATA_MANAGEMENT.md](docs/DATA_MANAGEMENT.md).

### Ontology extraction notes
- The extractor is **LLM-first with a deterministic fallback**, so tests and offline runs work without any API key.
- Set `OPENAI_API_KEY` (and optionally `OPENAI_BASE_URL`, `OPENAI_MODEL`) in `.env` to enable the LLM path. Any OpenAI-compatible endpoint that supports `response_format={"type": "json_object"}` works.
- Re-running `POST /analyze` **replaces** the existing ontology for that project.
- A reference output for the included FreshPlus brief lives at [samples/sample_ontology.json](samples/sample_ontology.json).

### 6. Tests
```bash
cd backend
pytest
```

## Endpoints (Phase 2)
| Method | Path | Status |
|---|---|---|
| GET | `/healthz` | live |
| POST | `/api/v1/projects` | live |
| GET | `/api/v1/projects` | live |
| GET | `/api/v1/projects/{id}` | live |
| POST | `/api/v1/projects/{id}/brief` | live |
| POST | `/api/v1/projects/{id}/brief/upload` | live |
| POST | `/api/v1/projects/{id}/analyze` | **live (Phase 3)** |
| GET | `/api/v1/projects/{id}/ontology` | **live (Phase 3)** |
| POST | `/api/v1/projects/{id}/agents/generate` | **live (Phase 4)** |
| GET | `/api/v1/projects/{id}/agents` | **live (Phase 4)** |
| GET | `/api/v1/projects/{id}/agents/summary` | **live (Phase 4)** |
| GET | `/api/v1/projects/{id}/agents/{agent_id}` | **live (Phase 4)** |
| POST | `/api/v1/projects/{id}/simulate` | **live (Phase 5)** |
| GET | `/api/v1/projects/{id}/simulate/status` | **live (Phase 5)** |
| GET | `/api/v1/projects/{id}/events` | **live (Phase 5)** |
| GET | `/api/v1/projects/{id}/events/summary` | **live (Phase 5)** |
| GET | `/api/v1/projects/{id}/events/{event_id}` | **live (Phase 5)** |
| POST | `/api/v1/projects/{id}/report/generate` | **live (Phase 6)** |
| GET | `/api/v1/projects/{id}/report` | **live (Phase 6)** |
| GET | `/api/v1/projects/{id}/report/markdown` | **live (Phase 6)** |
| GET | `/api/v1/projects/{id}/report/summary` | **live (Phase 6)** |
| GET | `/api/v1/projects/{id}/report/export` | **live (Phase 6)** |
| POST | `/api/v1/projects/{id}/ask` | **live (Phase 7)** |
| POST | `/api/v1/projects/{id}/scenario` | **live (Phase 7)** |
| GET | `/api/v1/projects/{id}/scenarios` | **live (Phase 7)** |
| GET | `/api/v1/projects/{id}/scenarios/{scenario_id}` | **live (Phase 7)** |
| GET | `/api/v1/projects/{id}/scenarios/{scenario_id}/delta` | **live (Phase 7)** |
| DELETE | `/api/v1/projects/{id}/scenarios/{scenario_id}` | **live (Phase 7)** |
| GET | `/api/v1/system/status` | **live (Phase 10/23)** |
| GET | `/readyz` | **live (Phase 23)** |
| GET | `/api/v1/system/diagnostics` | **live (Phase 23/24)** |
| GET | `/api/v1/system/logs` | **live (Phase 24)** |
| GET | `/api/v1/system/logs/recent-errors` | **live (Phase 24)** |
| GET | `/api/v1/projects/{id}/export` | **live (Phase 25)** |
| POST | `/api/v1/projects/import` | **live (Phase 25)** |
| DELETE | `/api/v1/projects/{id}` | **live (Phase 25)** |
| POST | `/api/v1/system/prune-logs` | **live (Phase 25)** |
| POST | `/api/v1/system/reset-demo` | **live (Phase 25, DEMO_MODE)** |
| GET | `/api/v1/system/samples` | **live (Phase 26)** |
| GET | `/api/v1/system/samples/{id}` | **live (Phase 26)** |
| POST | `/api/v1/system/samples/{id}/load` | **live (Phase 26)** |
| GET | `/api/v1/projects/{id}/decision-pack` | **live (Phase 28)** |
| GET | `/api/v1/projects/{id}/decision-pack/markdown` | **live (Phase 28)** |
| GET | `/api/v1/portfolio/decision-board` | **live (Phase 29)** |
| GET | `/api/v1/portfolio/decision-board/markdown` | **live (Phase 29)** |
| GET / PATCH | `/api/v1/projects/{id}/pipeline-status` | **live (Phase 30)** |
| GET | `/api/v1/portfolio/pipeline` | **live (Phase 30)** |
| POST | `/api/v1/portfolio/pipeline/apply-decision-board` | **live (Phase 30)** |
| GET | `/api/v1/portfolio/activity` | **live (Phase 31)** |
| POST | `/api/v1/projects/{id}/sensitivity` | **live (Phase 11)** |
| GET | `/api/v1/projects/{id}/confidence` | **live (Phase 11)** |
| GET | `/api/v1/projects/{id}/assumptions` | **live (Phase 11)** |
| GET | `/api/v1/projects/{id}/scorecard` (+ `/export`) | **live (Phase 12)** |
| POST/GET/DELETE | `/api/v1/projects/{id}/snapshots[/{sid}]` | **live (Phase 12)** |
| GET | `/api/v1/portfolio` | **live (Phase 12)** |
| POST | `/api/v1/portfolio/compare` | **live (Phase 12)** |
| POST | `/api/v1/projects/{id}/snapshots/diff` | **live (Phase 13)** |
| POST/GET/DELETE | `/api/v1/projects/{id}/decisions[/{id}]` | **live (Phase 13)** |
| GET | `/api/v1/projects/{id}/timeline` | **live (Phase 13)** |
| POST | `/api/v1/projects/{id}/briefing/generate` | **live (Phase 14)** |
| GET | `/api/v1/projects/{id}/briefing` (+ `/markdown`, `/summary`, `/export`) | **live (Phase 14)** |
| POST | `/api/v1/projects/{id}/briefing/ask` | **live (Phase 15)** |
| POST | `/api/v1/projects/{id}/briefing/tailor` | **live (Phase 15)** |
| POST/GET | `/api/v1/projects/{id}/briefing/board-summary` (+ `/export`) | **live (Phase 15)** |
| GET | `/api/v1/projects/{id}/studio/state` | **live (Phase 16)** |
| POST | `/api/v1/projects/{id}/live-simulation/start` | **live (Phase 18, SSE)** |
| GET | `/api/v1/projects/{id}/live-simulation/{run_id}/stream` | **live (Phase 18, SSE)** |
| GET | `/api/v1/projects/{id}/live-simulation/{run_id}` (+ `/runs`, `/cancel`) | **live (Phase 18/19)** |
| GET | `/api/v1/projects/{id}/overview` | **live (Phase 19)** |

Full schemas: see [docs/API_SPEC.md](docs/API_SPEC.md).

## Design documents
- [docs/ARCHITECTURE_RESEARCH.md](docs/ARCHITECTURE_RESEARCH.md)
- [docs/FMCG_SIMULATION_PRINCIPLES.md](docs/FMCG_SIMULATION_PRINCIPLES.md)
- [docs/MVP_SPEC.md](docs/MVP_SPEC.md)
- [docs/TASK_BREAKDOWN.md](docs/TASK_BREAKDOWN.md)
- [docs/SCORING_LOGIC.md](docs/SCORING_LOGIC.md)
- [docs/API_SPEC.md](docs/API_SPEC.md)
- [docs/CURRENT_STATUS.md](docs/CURRENT_STATUS.md)
- [docs/FRONTEND_GUIDE.md](docs/FRONTEND_GUIDE.md)
- [docs/DEV_RUNBOOK.md](docs/DEV_RUNBOOK.md)
- [docs/PACKAGING_GUIDE.md](docs/PACKAGING_GUIDE.md)
- [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md)
- [docs/EXPLAINABILITY_GUIDE.md](docs/EXPLAINABILITY_GUIDE.md)
- [docs/PORTFOLIO_GUIDE.md](docs/PORTFOLIO_GUIDE.md)
- [docs/DECISION_HISTORY_GUIDE.md](docs/DECISION_HISTORY_GUIDE.md)
- [docs/BRIEFING_GUIDE.md](docs/BRIEFING_GUIDE.md)
- [docs/AUDIENCE_TAILORING_GUIDE.md](docs/AUDIENCE_TAILORING_GUIDE.md)
- [docs/AGENT_STUDIO_GUIDE.md](docs/AGENT_STUDIO_GUIDE.md)
- [docs/DEPLOYMENT_OPTIONS.md](docs/DEPLOYMENT_OPTIONS.md)
- [docs/DEPLOYMENT_CHECKLIST.md](docs/DEPLOYMENT_CHECKLIST.md)
- [docs/LIVE_STREAMING_GUIDE.md](docs/LIVE_STREAMING_GUIDE.md)
- [docs/WORKSPACE_HOME_GUIDE.md](docs/WORKSPACE_HOME_GUIDE.md)
- [docs/GLOSSARY.md](docs/GLOSSARY.md)
- [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md)
- [docs/PERFORMANCE_NOTES.md](docs/PERFORMANCE_NOTES.md)
- [docs/TESTING_GUIDE.md](docs/TESTING_GUIDE.md)
- [docs/OBSERVABILITY.md](docs/OBSERVABILITY.md)

## License & attribution
This is an original implementation. MiroFish (AGPL-3.0) is referenced only at the architectural level; no MiroFish code, prompts, or templates are reused. See `docs/ARCHITECTURE_RESEARCH.md` for the license boundary.

The simulator produces **decision-support hypotheses, not forecasts**. Outputs must be validated by real consumer research before launch decisions.
