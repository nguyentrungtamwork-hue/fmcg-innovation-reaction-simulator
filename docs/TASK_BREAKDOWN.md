# TASK_BREAKDOWN.md

Work is sliced into 9 phases. Each phase ends with a runnable artifact and a checklist item in `CURRENT_STATUS.md`.

## Phase 1 — Research & Design *(this phase)*
- [x] Study MiroFish repo (architecture only).
- [x] `ARCHITECTURE_RESEARCH.md`
- [x] `FMCG_SIMULATION_PRINCIPLES.md`
- [x] `MVP_SPEC.md`
- [x] `TASK_BREAKDOWN.md`
- [x] `SCORING_LOGIC.md`
- [x] `API_SPEC.md`
- [x] `CURRENT_STATUS.md`

## Phase 2 — Backend Skeleton
- Scaffold FastAPI app, `main.py`, settings (env-driven).
- SQLAlchemy models: `Project`, `Brief`, `Ontology`, `Agent`, `Event`, `Report`.
- SQLite migration via Alembic (or simple `create_all` for MVP).
- Endpoints: `POST /projects`, `GET /projects/{id}`, `POST /projects/{id}/brief`.
- `pytest` smoke test for create-project flow.

## Phase 3 — Ontology Extraction
- `services/ontology_service.py`: prompt-driven extractor.
- Strict Pydantic schema for 26 entity types, 18 relationship types.
- Captures `assumptions[]` and `missing_information[]`.
- Endpoint: `POST /projects/{id}/analyze`.
- Persist ontology as JSON blob + NetworkX graph file.

## Phase 4 — Agent Generation
- `services/agent_generation_service.py`.
- Segment template library (8 segments, MVP uses 5).
- Generate 50 consumers + 5 market actors, deterministic seeding.
- Validate no protected attributes / no PII.
- Endpoint: `POST /projects/{id}/agents/generate`, `GET /projects/{id}/agents`.

## Phase 5 — Simulation Engine
- `services/simulation_service.py`.
- Round loop: for each round, for each agent → retrieve memory → score → choose action → log event → update memory.
- Action schema enforced via Pydantic.
- Market-actor pass per round (retailer/competitor/etc.).
- Endpoint: `POST /projects/{id}/simulate`, `GET /projects/{id}/events`.
- Token-cost telemetry written to stdout.

## Phase 6 — Report Agent
- `services/report_service.py`.
- 14-section report generator. Each section receives only the slice of events it needs.
- Every claim tagged with event ids.
- Markdown + HTML export.
- Endpoint: `GET /projects/{id}/report?format=md|html`.

## Phase 7 — Deep Q&A & Scenarios
- `services/qa_service.py` — retrieval over brief + ontology + agents + events + report.
- `services/scenario_service.py` — re-runs Rounds 4–6 with a tweak (price/claim/promo).
- Endpoints: `POST /projects/{id}/ask`, `POST /projects/{id}/scenario`.

## Phase 8 — Frontend Dashboard
- Next.js app, 7 screens (Setup, Ontology, Agents, Timeline, Insights, Report, Q&A).
- API client in `src/services/`.
- Polling for long-running simulation.
- Export buttons for report.

## Phase 9 — Sample Data, Tests, Docs
- `samples/sample_innovation_brief.md` (FreshPlus).
- `samples/sample_ontology.json`, `samples/sample_agents.json`, `samples/sample_events.json`, `samples/sample_report.md`.
- Integration test running the full flow against a mocked LLM.
- README install + run instructions.
- Update `CURRENT_STATUS.md` with "next recommended prompt".

## Dependencies between phases
- Phase 3 needs Phase 2 (project model).
- Phase 4 needs Phase 3 (ontology grounds personas).
- Phase 5 needs Phase 4 (agents) and Phase 3 (ontology).
- Phase 6 needs Phase 5 (events).
- Phase 7 needs Phase 6 (report context for Q&A).
- Phase 8 can begin in parallel after Phase 2 with mocked data.
- Phase 9 is continuous; finalize last.
