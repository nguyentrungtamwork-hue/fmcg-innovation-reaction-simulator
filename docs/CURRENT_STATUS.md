# CURRENT_STATUS.md

_Last updated: 2026-06-06_

## Phase
**Phase 31 — Stage-Change Notifications, Activity Feed & Pipeline Filters: COMPLETE.**

### Enhancement — Per-product agent customization (3 levels)
Agents/reactions are now product-specific while **core scoring formulas are unchanged** (only
persona composition + text vary):
- **L2 — product-aware segment mix:** `agent_fallback.ontology_weighted_distribution()` tilts the
  8 canonical archetypes by ontology signals + inferred category (snack/beverage/dairy/skincare/
  personal-care/household). Keeps the 8 archetype keys (so `SEGMENT_WEIGHTS` lookups are identical),
  every segment ≥1, sums to consumer_count, deterministic. Each product → a different mix.
- **L3 — category/product-aware reactions:** `SimContext` gains text-only `category`/`unit_noun`/
  `benefit`; `build_context()` infers them; `_react()` renders product-specific phrasing (snack says
  "pack/crunch", beverage says "bottle/refreshes…") — no numeric scoring touched.
- **L1 — opt-in LLM persona enrichment:** `agent_generation_service._llm_enrich_consumers()` rewrites
  persona TEXT (description/barriers/trust-drivers) when `OPENAI_API_KEY` is set; graceful fallback to
  deterministic personas otherwise; never touches traits/scores (`source_mode="llm"`).
- Tests: `tests/test_product_customization.py` (11) + two distribution-agnostic test fixes →
  **266 backend passing**; frontend unchanged, build green.

## Completed
### Phases 1–5
- Design docs, FastAPI backend, models/schemas/services, FMCG ontology extraction (LLM-first + deterministic fallback), consumer + market-actor agent generation (50 consumers across 8 segments + 5 market actors), and the multi-round (6-round) simulation engine producing 330 grounded events with deterministic per-agent/per-round scoring.

### Phase 6
- Strategic Launch Report generation: deterministic 16-section report builder + markdown renderer, optional LLM narrative enhancement (exec-summary prose only, graceful fallback), report persistence + GET endpoints, `samples/sample_report.{json,md}`.

### Phase 7 (this phase)
- [x] **Event model** extended with `run_type` (`baseline`|`scenario`, indexed, default `baseline`) and `scenario_id` (nullable, indexed). All baseline queries (project envelope counts, report `_load_inputs`, simulation `list_events`/`events_summary`/`_reset_run_state`) filter `run_type == "baseline"`, so scenario events never leak into baseline outputs.
- [x] **`ScenarioRun` model** (`scenario_runs`): id, project_id, scenario_name, description, overrides_json, baseline_event_count, scenario_event_count, delta_payload_json, created_at/updated_at.
- [x] **Scoring engine** (`simulation_scoring.py`): added neutral-default additive adjustment fields to `SimContext` (`price_value_adj`, `social_proof_adj`, `pack_adj`, `channel_adj`, `risk_adj`, all `0.0`) applied inside `score_round`. Defaults keep baseline behaviour byte-for-byte identical.
- [x] **Simulation refactor** (`simulation_service.py`): extracted the 6-round loop into `run_rounds(..., run_type, scenario_id, persist_agent_state)`. `run_simulation` delegates with baseline defaults; scenario runs call it with `run_type="scenario"`, a fresh `scenario_id`, and `persist_agent_state=False` so baseline agent memory/action history is never overwritten.
- [x] **Deep Q&A** (`schemas/qa.py`, `services/qa_service.py`, `api/v1/qa.py`):
  - `POST /api/v1/projects/{id}/ask` — body `{question, use_llm=false, include_evidence=true, max_evidence_events=5}`.
  - 12-intent keyword classifier (`interview_agents`, `repeat_purchase`, `target_segment`, `claim_risk`, `pricing`, `channel_touchpoint`, `trial`, `barriers`, `triggers`, `recommendations`, `competitor_response`, `general_summary`); default `general_summary`.
  - Deterministic per-intent answer builders grounded strictly in the persisted `ReportPayload` + baseline event evidence + consumer agents/ontology — no invented findings. Each answer returns `direct_answer`, `evidence_summary`, `supporting_events` (event_id/round/agent/segment/action/excerpt), `supporting_segments`, `confidence_score` (0–1), `limitations`, `recommended_next_action`.
  - Interview intent selects a cohort (skeptical / repeat / general), parses the requested count, and reconstructs `simulated_interview_answers` from each agent's persisted simulation memory, with `selected_agents` and an explicit "these are SIMULATED personas" caveat.
  - Optional LLM rewrite of `direct_answer` only (never adds facts); falls back to `source_mode="deterministic"` when unconfigured or on error.
- [x] **Scenario testing** (`schemas/scenario.py`, `services/scenario_service.py`, `api/v1/scenarios.py`):
  - `apply_overrides` maps 10 what-if levers (price_change_pct, claim_credibility_boost, sampling_boost, promotion_boost, channel_focus, competitor_pressure_boost, packaging_appeal_boost, social_proof_boost, sensory_risk_reduction, retailer_support_boost) onto the SimContext adjustments + direct mutations. Neutral overrides → identical to baseline.
  - `run_scenario` re-simulates against existing agents, tags events `run_type="scenario"`+`scenario_id`, aggregates baseline vs scenario, computes metric/segment/action/trigger/barrier deltas + recommendation changes + a narrative conclusion, and persists a `ScenarioRun` with the full delta payload. Baseline events and report are never touched.
  - Endpoints: `POST /scenario`, `GET /scenarios`, `GET /scenarios/{id}`, `GET /scenarios/{id}/delta`, `DELETE /scenarios/{id}`.
- [x] `samples/sample_qa_answers.json` (why repeat low / which segment first / riskiest claim / interview 3 skeptical consumers) + `samples/sample_scenario_price_reduction.json` (−10% price, baseline vs scenario delta).
- [x] 25 new tests (12 Q&A + 13 scenario); **102 total passing**, fully offline.

### Phase 8 (this phase)
- [x] **Vite + React + TypeScript dashboard** in `/frontend`, talking to the existing backend over REST. No backend business logic changed.
- [x] **Backend touch (CORS only):** `config.py` `cors_origins` now includes `http://localhost:5173` + `127.0.0.1:5173`; added optional `frontend_origin` env and `resolved_cors_origins()`; `main.py` uses it. Verified: preflight from `localhost:5173` returns the allow-origin header; 102 backend tests still pass.
- [x] **Typed API client** (`src/api/`): `client.ts` (single `fetch` wrapper + `ApiError{status,code}`) plus per-domain modules exposing all required functions (createProject, getProjects, getProject, submitBrief, analyzeOntology, getOntology, generateAgents, getAgentsSummary, listAgents, runSimulation, getEventsSummary, generateReport, getReport, getReportSummary, getReportMarkdown, askQuestion, runScenario, listScenarios, getScenario, getScenarioDelta, deleteScenario).
- [x] **Pages:** `ProjectListPage` (list/create), `ProjectWorkflowPage` (8-step runner with live status read from the project envelope), `ReportPage` (exec summary, segment map table, triggers/barriers, risk matrix, recommendations, A/B tests, markdown panel, JSON export), `QAConsolePage` (presets + free text, evidence chips, simulated-interview view), `ScenarioLabPage` (10 override levers, run, saved-scenario list, delta cards + segment/action/trigger/barrier changes + conclusion).
- [x] **Components:** `Layout`, `Stepper`, `StatusBadge`, `MetricCard`, `EvidenceChip`, `LoadingState`, `ErrorState` (backend error codes → friendly copy).
- [x] **UX/disclaimers:** exploratory-decision-support banner on report + scenario pages + footer; scenario lab states baseline is preserved; simulated interviews badged as not-real.
- [x] **Build/typecheck green:** `npm run build` (`tsc --noEmit && vite build`) succeeds; 56 modules, ~212 kB JS (64 kB gzip).
- [x] `docs/FRONTEND_GUIDE.md` created; `README.md`, `docs/CURRENT_STATUS.md` updated.

### Phase 9 (this phase)
- [x] **Frontend tests:** Vitest + React Testing Library + jsdom. `src/test/setup.ts` + `src/test/smoke.test.tsx` (10 smoke tests, API modules mocked, no backend). `npm test` → 10 passed; `npm run build` still green (`tsc --noEmit && vite build`).
- [x] **Event Explorer** (`/projects/:id/events`, `EventExplorerPage`): filters (round / agent_type / segment / action) backed by `GET /events`; responsive table; expandable rows (stage, tone, confidence, reasoning, generated_reaction, event_id); clickable agent. Linked from Workflow + Report.
- [x] **Agent Detail Drawer** (`AgentDrawer`): fetches `GET /agents/{id}`; shows traits, grounding sources, initial memory, simulation memory, action history, trust drivers, trial barriers, repeat drivers, likely objections.
- [x] **Scenario side-by-side compare:** Baseline | Scenario | Δ table (trial/intent/repeat/sentiment/complaints/recommends/switches; complaint & switch deltas tone-inverted) + optional "compare with" second-scenario column.
- [x] **Backend hardening (no business-logic change):** `app/core/middleware.py` adds `RequestContextMiddleware` (per-request id + structured access log: method/path/status_code/duration_ms/request_id), a catch-all exception handler (`internal_error`, no stack traces leaked), HTTPException normaliser (preserves `{code}` + adds `request_id`), and a `validation_error` handler (422). Wired in `main.py` before CORS; `logging.basicConfig` added. Read-only `simulation_memory` + `action_history` added to `AgentOut`.
- [x] **Frontend error UX:** `ErrorState` maps `project_not_found`, `brief_required`, `ontology_required`, `agents_required`, `events_required`, `report_required`, `baseline_events_required`, `baseline_report_required`, `scenario_not_found`, `network_error` to friendly, actionable copy.
- [x] **A11y/responsiveness:** focus-visible rings on buttons/nav, `aria-label`s on drawer/range inputs, `htmlFor`/`id` on explorer filters, `role="dialog"`+`aria-modal` drawer, `overflow-x-auto` tables, responsive grids.
- [x] **Dev runbook:** `scripts/dev.ps1`, `scripts/dev.sh`, `Makefile`, `docs/DEV_RUNBOOK.md` (one-command dev, troubleshooting, architecture diagram, full demo).
- [x] **Backend tests:** `tests/test_hardening.py` (5: request-id header, echoed id, 404/409 envelope codes + request_id, 422 validation_error). **107 backend tests passing.**
- [x] End-to-end verified live (in-process TestClient): agent payload exposes `simulation_memory`/`action_history`; event filters (round/agent_type) correct (330 total / 55 round-3 / 300 consumer); `X-Request-ID` header present; structured access logs emitted.

### Phase 10 (this phase)
- [x] **Docker packaging:** root `docker-compose.yml` (backend :8000 + frontend :3000); `backend/Dockerfile` (python:3.12-slim → uvicorn, SQLite on named volume `backend_data` at `/data`); `frontend/Dockerfile` (node:20-alpine build → nginx:alpine serve) + `frontend/nginx.conf` (SPA fallback); `.dockerignore` for both. CORS already allows `localhost:3000`. Compose YAML validated (parses, build contexts/files present); full `docker build` not run here (Docker absent in authoring env — documented).
- [x] **Demo seed:** `backend/scripts/seed_demo.py` — deterministic, offline; builds project→brief→ontology→agents→simulation→report (+ sample Q&A + 10% price scenario); `--reset-demo` flag; prints `project_id` + frontend/backend URLs. Verified end-to-end (330 events, report confidence 0.745, scenario created).
- [x] **System status endpoint:** `GET /api/v1/system/status` (`app/api/v1/system.py`) → `{app_name, version, environment, llm_configured, database, demo_mode}`, no secrets. Settings gained `environment` + `demo_mode`. Tests: `tests/test_system.py` (shape + no-secrets).
- [x] **Report download/print:** Report page adds **Download Markdown**, **Download JSON**, **Print report** (+ `@media print` stylesheet hiding chrome). `downloadText` util added.
- [x] **System status footer + offline retry banner** in `Layout` (Backend connected/offline, LLM configured/fallback, Demo Mode, version) via `src/api/system.ts`.
- [x] **CI smoke:** `.github/workflows/ci.yml` — backend `pytest`; frontend `npm ci` + `npm test` + `npm run build`.
- [x] **Docs:** created `docs/DEMO_SCRIPT.md`, `docs/PACKAGING_GUIDE.md`; updated `README.md`, `docs/DEV_RUNBOOK.md`, `docs/FRONTEND_GUIDE.md`, `docs/API_SPEC.md`, `docs/CURRENT_STATUS.md`.
- [x] **Tests:** backend **109 passing** (+2 system); frontend **10 passing** (Vitest, system API mocked); `npm run build` green.

### Phase 11 (this phase)
- [x] **Sensitivity sweeps:** `POST /api/v1/projects/{id}/sensitivity` (`app/services/sensitivity_service.py`, `app/schemas/insight.py`). Reuses the scenario engine per lever-value, aggregates, then **deletes sweep events** (baseline untouched; no ScenarioRun rows). Returns per-lever response points + `best_point` + `diminishing_return_point` + `strategic_read` + `overall_recommendation`. Verified live: sampling_boost most responsive (trial 0.313→0.332), baseline 330 events PRESERVED.
- [x] **Confidence calibration:** `GET /confidence` (`confidence_service.py`) — 9 weighted drivers (ontology completeness, agent coverage, event volume, segment diversity, evidence density, claim richness, information gaps, grounding mode, real-world-data cap) → `overall_confidence` + label + risks + how-to-improve. Does NOT change report scoring. Verified: 0.651 (medium). Formula documented in `SCORING_LOGIC.md`.
- [x] **Assumptions ledger:** `GET /assumptions` (`assumptions_service.py`) — consolidates method/data caveats + simulated personas + scenario/sensitivity caveats + ontology `missing_information`/`market_assumptions` + report limitations, each with impact + recommended validation. Verified: 22 items (14 high / 3 med / 5 low).
- [x] **Endpoints** registered via `app/api/v1/insights.py`; preconditions map to 404/409 with the existing envelope.
- [x] **Frontend:** `SensitivityPage` (route `/projects/:id/sensitivity`); `ConfidencePanel` + `AssumptionsLedger` on the Report page; dependency-free SVG charts `MiniLineChart`/`MiniBarChart`/`ConfidenceGauge` (`components/charts.tsx`); `api/insights.ts`; nav + Report links added.
- [x] **Evidence drill-down:** `EvidenceChip` gains optional `projectId` → "Open event →"/"Open agent →" links; Event Explorer reads `event_id`/`agent_id`/`round_number`/`open_agent` query params to pre-filter + auto-open the Agent Drawer. Wired on Report (trigger/barrier chips), Q&A, and Workflow.
- [x] **Tests:** backend `tests/test_insights.py` (10) — **119 backend passing**; frontend smoke suite extended to **15 passing** (Sensitivity page, Confidence panel, Assumptions ledger, EvidenceChip drilldown, MiniLineChart). `npm run build` green.
- [x] **Docs:** created `docs/EXPLAINABILITY_GUIDE.md`; updated `SCORING_LOGIC.md`, `API_SPEC.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 12 (this phase)
- [x] **Concept scorecard** (`app/services/scorecard_service.py`, `app/schemas/portfolio.py`): transparent 0–100 heuristic from existing report + ontology + confidence + assumptions (weights documented in `SCORING_LOGIC.md`); `ranking_explanation` prints every term; carries a "decision-support heuristic, not a forecast" disclaimer. `GET /scorecard` (+ `/scorecard/export?format=json|markdown`). Verified live: overall computed, sub-scores in 0–100.
- [x] **Report snapshots** (`app/models/snapshot.py` `ReportSnapshot`, `snapshot_service.py`): immutable named freeze of report payload + markdown + scorecard. `POST/GET/DELETE /snapshots[/{sid}]` + `/snapshots/{sid}/scorecard[/export]`. Verified: snapshot unchanged after report regenerate.
- [x] **Portfolio + comparison** (`portfolio_service.py`, `app/api/v1/portfolio.py`): `GET /portfolio` (all projects + scorecard columns + summary) and `POST /portfolio/compare` (per-item scorecards, comparison_summary, dimension_rankings, recommendation). Verified: 2 projects compared, recommendation produced.
- [x] **Routers** `app/api/v1/snapshots.py` (under `/projects/{id}`) + `portfolio.py` (top-level `/portfolio`), registered.
- [x] **Frontend:** `PortfolioPage` (`/portfolio`, sort/filter), `ComparePage` (`/compare`, 2–5 select + dimension table + cards), `ScorecardCard` (+ `scorecardMarkdown`), `SnapshotPanel` on the Report page (scorecard + create/list/view/delete snapshots + Markdown/JSON downloads), `api/portfolio.ts`, nav links Portfolio + Compare.
- [x] **Tests:** backend `tests/test_portfolio.py` (10) → **129 backend passing**; frontend smoke suite extended to **19 passing** (Portfolio, Compare, ScorecardCard, SnapshotPanel). `npm run build` green.
- [x] **Docs:** created `docs/PORTFOLIO_GUIDE.md`; updated `SCORING_LOGIC.md` (scorecard formula), `API_SPEC.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 13 (this phase)
- [x] **Snapshot diff** (`app/services/diff_service.py`, `app/schemas/history.py`): deterministic, no-LLM comparison of two sides (active_report | snapshot) across scorecard dimensions (risk dims improve when they decrease), report sections, risks (reduced/new), recommendations, and segments + plain-English summary + decision implication. `POST /snapshots/diff` (404 project / 409 report_required / 404 snapshot_not_found / 400 invalid_diff_request). Verified: identical snapshots → zero overall delta.
- [x] **Decision log** (`app/models/decision.py`, `decision_service.py`): `POST/GET/DELETE /decisions[/{id}]`; tags; snapshot creation auto-logs a `snapshot_created` entry. **Merged timeline** (`timeline_service.py`) `GET /timeline` spanning project/brief/ontology/agents/simulation/report + scenarios + snapshots + decisions, chronological.
- [x] **Router** `app/api/v1/history.py` registered.
- [x] **Frontend:** `SnapshotDiffPage` (`/projects/:id/snapshots/diff`), `DecisionHistoryPage` (`/projects/:id/decisions`), `DriftIndicator` (active-vs-latest-snapshot banner on the Report page), `api/history.ts`, nav **History**, Report links to Snapshot diff + History. Reuses `MiniBarChart` for dimension-delta magnitudes.
- [x] **Tests:** backend `tests/test_history.py` (8) → **137 backend passing**; frontend smoke suite extended to **22 passing** (SnapshotDiffPage, DecisionHistoryPage, MiniBarChart deltas). `npm run build` green.
- [x] **Docs:** created `docs/DECISION_HISTORY_GUIDE.md`; updated `API_SPEC.md`, `FRONTEND_GUIDE.md`, `PORTFOLIO_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 14 (this phase)
- [x] **Executive briefing** (`app/schemas/briefing.py`, `app/models/briefing.py`, `app/services/briefing_service.py`, `app/api/v1/briefing.py`): deterministic, evidence-grounded narrative assembled from report + scorecard + confidence + assumptions (+ optional snapshot diff / timeline). 11-section payload (header, situation, top findings, biggest risks, readiness, what-changed, decision recommendation, next-best-actions, validation plan, evidence pack, limitations) + executive Markdown + summary. Optional LLM prose polish (`use_llm_rewrite`) with deterministic fallback; tests run offline.
- [x] **Recommendation status** (`move_forward`/`validate_before_move_forward`/`revise_and_retest`/`hold`) deterministic from scorecard, documented in `SCORING_LOGIC.md`. **Next-best-actions** engine: dedup + prioritized (severity→impact→confidence→effort→owner), owner team + effort, 5–10 specific actions.
- [x] **Endpoints:** `POST /briefing/generate`, `GET /briefing`, `/briefing/markdown`, `/briefing/summary`, `/briefing/export?format=json|markdown`. Preconditions 404 / 409 events_required / report_required / scorecard_required / briefing_required.
- [x] **Frontend:** `BriefingPage` (`/projects/:id/briefing`) with audience/tone selectors, evidence/history toggles, recommendation banner, all sections with evidence chips, Download MD/JSON + Print; `api/briefing.ts`; nav **Briefing**; links from Report + Portfolio (per row) + Decision History.
- [x] **Tests:** backend `tests/test_briefing.py` (12) → **149 backend passing**; frontend smoke suite extended to **24 passing** (BriefingPage render + post-generate actions/downloads). `npm run build` green.
- [x] **Docs:** created `docs/BRIEFING_GUIDE.md`; updated `SCORING_LOGIC.md`, `API_SPEC.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`.
- [x] Verified live: status logic (hold on a thin brief), 3 findings / 3 risks / 10 actions / 6 validations, what-changed history wired, 7.9 kB markdown, specific owner-tagged top action.

### Phase 15 (this phase)
- [x] **Briefing Q&A** (`app/services/briefing_qa_service.py`, schemas in `app/schemas/briefing.py`): `POST /briefing/ask` with a 12-intent classifier + deterministic, evidence-cited answer builders grounded only in the persisted briefing payload. Optional LLM prose polish; deterministic fallback.
- [x] **Audience tailoring:** `POST /briefing/tailor` re-frames the SAME findings per audience (executive/brand_team/trade_sales/rd_product/consumer_insight) — headline, priority, needs-to-know, role risks/actions, evidence-to-show, what-not-to-overclaim, talk track + Markdown. No re-simulation; verified that executive vs R&D outputs differ.
- [x] **One-page board summary:** `POST/GET /briefing/board-summary` (+ `/export`) — 3 findings / 3 risks / 3 actions + decision gate + validation + caveat; stored via new `BriefingArtifact` model (one per type+project).
- [x] **Router** additions in `app/api/v1/briefing.py`; preconditions 404 / 409 report_required / briefing_required / board_summary_required.
- [x] **Frontend:** `BriefingPage` gains tabs (Briefing / Ask Briefing / Tailor by Audience / Board Summary); components `AskBriefingTab`, `TailorTab`, `BoardSummaryTab`; `api/briefing.ts` (+ask/tailor/board); `ErrorState` maps new codes.
- [x] **Tests:** backend `tests/test_briefing_qa.py` (11) → **160 backend passing**; frontend smoke suite extended to **27 passing** (Ask/Tailor/Board tabs). `npm run build` green.
- [x] **Docs:** created `docs/AUDIENCE_TAILORING_GUIDE.md`; updated `API_SPEC.md`, `BRIEFING_GUIDE.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 16 (this phase)
- [x] **Read-only studio aggregator** (`app/schemas/studio.py`, `app/services/studio_service.py`, `app/api/v1/studio.py`): `GET /projects/{id}/studio/state` returns project + light agents + baseline events (sorted) + summary + rounds + a bounded (≤160) interaction graph (nodes per agent; edges from shared trigger/barrier within a round + market-actor round impact, with an explicit "not real conversations" note). No scoring change; baseline untouched.
- [x] **Frontend Agent Studio** (`/projects/:id/studio`, `AgentStudioPage`): animated playback of saved events — metric strip (trials/repeats/recommends/complaints/avg sentiment over revealed events), `PlaybackControls` (0.5x/1x/2x/instant, play/pause/reset/replay), `RoundTimeline`, filter bar (segment/agent-type/action/trigger/barrier/sentiment), `AgentNetworkCanvas` (dependency-free SVG, segment-clustered nodes, active highlight, heuristic edges + legend), `LiveEventStream` (capped 40, Open agent/event), and `AgentDrawer` inspector. Empty state → "Run simulation first" (one-click run). Reuses MetricCard/AgentDrawer/ErrorState/LoadingState.
- [x] **Links + nav:** Studio nav item; links from Workflow (sim step), Event Explorer, Report. `api/studio.ts`.
- [x] **Tests:** backend `tests/test_studio.py` (5) → **165 backend passing**; frontend smoke suite extended to **30 passing** (studio render, playback reveals cards, empty state). `npm run build` green (85 modules).
- [x] **Docs:** created `docs/AGENT_STUDIO_GUIDE.md` + `docs/DEPLOYMENT_OPTIONS.md`; updated `API_SPEC.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `PACKAGING_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.
- [x] No WebSocket/SSE (deferred); playback is client-side over persisted events; edges clearly labelled as visualization aids.

### Phase 17 (this phase)
- [x] **Deployment readiness:** `GET /projects?demo=true` filter (`project_service.list_projects(demo_only=)`); `backend/scripts/check_deploy_config.py` (10 checks — compose/Dockerfiles/nginx, env conventions, env-driven CORS, no secret leak in `/system/status`, docs present); `docker-compose.yml` gains `FRONTEND_ORIGIN`. Created `docs/DEPLOYMENT_CHECKLIST.md` (Railway/Render + Vercel/Cloudflare, VPS Docker, SQLite→Postgres caveats).
- [x] **Studio UX hardening:** control-room header (sim-ready badge + agent/event totals + mode + CTAs Run/Replay/Report/Briefing/Events); guided next-step empty state (submit brief → analyze → generate agents → run simulation, inline via existing APIs); keyboard shortcuts (Space play/pause, R reset, ←/→ round); consumer/market view toggles; live-stream **Copy evidence**; canvas legend explains filtered nodes + heuristic edges ("not a conversation"). Projects page shows "Open demo in Agent Studio" when a `FreshPlus Demo` project exists.
- [x] **Tests:** backend `tests/test_deploy_config.py` (2: demo filter + config check) → **167 backend passing**; frontend smoke suite extended to **33 passing** (studio header/keys/legend, guided empty state). `npm run build` green.
- [x] **Docs:** created `docs/DEPLOYMENT_CHECKLIST.md`; updated `AGENT_STUDIO_GUIDE.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`. No WebSocket/SSE; playback remains client-side over persisted events.

### Phase 18 (this phase)
- [x] **SSE live streaming:** `LiveSimulationRun` model; `app/services/live_simulation_service.py` (faithful streaming replay of the deterministic loop — reuses `score_round`/`market_actor_action`, same ordering/seed; persists each `Event` as `run_type="baseline"`, then agent memory at completion); `app/api/v1/live_simulation.py` (`POST /start`, `GET /{run_id}/stream` SSE, `GET /{run_id}`, `GET /runs`, `POST /{run_id}/cancel`). Sync `simulation_service` untouched.
- [x] **Stream message types:** run_started, round_started, agent_started, event_generated, agent_memory_updated, market_actor_event_generated, round_completed, run_completed, run_failed, heartbeat — each with progress + payload. Preconditions: 404 / 409 brief/ontology/agents_required, simulation_exists, live_run_already_running. `event_delay_ms` paces (0 in tests).
- [x] **Frontend Live Mode:** Studio gains a Replay/Live switch; `useLiveSimulation` hook (EventSource lifecycle, parse, derived metrics, completed/failed/disconnect, cleanup); components `LivePanel`, `LiveSimulationControls`, `LiveProgressBar`, `LiveStatusBadge`; live canvas highlight + event cards + metric strip + progress; completion actions (Report/Replay/Events). Replay mode preserved.
- [x] **Persistence parity:** streamed runs feed `/events`, `/studio/state`, report, briefing, scenarios identically to `POST /simulate` (verified: 330 events, report generates on streamed events).
- [x] **Tests:** backend `tests/test_live_simulation.py` (8) → **175 backend passing**; frontend smoke suite **35 passing** (mode switch + controls + mocked EventSource stream + completion actions). `npm run build` green.
- [x] **Docs:** created `docs/LIVE_STREAMING_GUIDE.md`; updated `API_SPEC.md`, `AGENT_STUDIO_GUIDE.md`, `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `DEPLOYMENT_OPTIONS.md`, `PACKAGING_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`. WebSocket deferred (one-way stream → SSE); cancel implemented.

### Phase 19 (this phase)
- [x] **Live-run reliability:** `LiveSimulationRun` gains `last_heartbeat_at`/`last_event_at`/`stale_after_seconds`; `live_simulation_service` adds `is_stale()`, `reap_stale()` (run on every `start`), timestamps updated during streaming, and `to_out()` now returns `is_stale`/`can_cancel`/`can_replay_persisted_events`/`stream_url`. Cancel marks pending/running `cancelled` (status-level; events kept). `start` accepts `stale_after_seconds`.
- [x] **Overview endpoint:** `GET /projects/{id}/overview` (`overview_service` + `app/api/v1/overview.py`) — pipeline_status, counts, latest scorecard, latest briefing summary, latest live run, deterministic `next_recommended_action` (submit_brief→…→explore, with resolve_stale_run priority), recent_activity.
- [x] **Frontend:** `ProjectHomePage` (`/projects/:id/home`) — status badges + counts + what-to-do-next + latest recommendation + quick links + recent activity; **global jump** (project+surface) and footer **Glossary** drawer (`GlossaryModal`) in Layout; **Home** nav; **Live Run History** panel in `LivePanel` (status/stale/cancel/open-replay + stale banner). New `api/overview.ts`, `api/liveSimulation.ts` (+listLiveRuns/cancelLiveRun).
- [x] **Tests:** backend `tests/test_overview_reliability.py` (8: stale detect, reap-on-start, cancel, runs reliability fields, overview 404 + next-action submit_brief/run_live_simulation/explore) → **183 backend passing**; frontend smoke suite **39 passing** (Home + next-step, Live Run History, global jump, glossary modal). `npm run build` green.
- [x] **Docs:** created `docs/GLOSSARY.md` + `docs/WORKSPACE_HOME_GUIDE.md`; updated `API_SPEC.md`, `AGENT_STUDIO_GUIDE.md`, `FRONTEND_GUIDE.md`, `LIVE_STREAMING_GUIDE.md`, `DEMO_SCRIPT.md`, `README.md`, `CURRENT_STATUS.md`. Cancel remains status-level (documented); no background queue/WebSocket added.

### Phase 20 (this phase)
- [x] **Accessibility:** Escape closes `AgentDrawer` + `GlossaryModal` (dialog roles/labels already present); `aria-live` on live status/progress; labelled filters/jump; focus rings; `prefers-reduced-motion` via new `usePrefersReducedMotion` hook + CSS (`studio-pulse` keyframe disabled under reduce). Playback shortcuts ignore typing (already). Created `docs/ACCESSIBILITY.md`.
- [x] **Performance:** Event Explorer client-side **pagination** (50/100/200, default 50; loads ≤1000 then slices); configurable **live-stream cap** (40/100/200, metrics use full revealed set); canvas **segment-aggregation** fallback when nodes > 150; **route code-splitting** (`React.lazy`+`Suspense`) for Report/Events/Portfolio/Compare/Briefing/Studio → main bundle 328→243 kB. Created `docs/PERFORMANCE_NOTES.md`.
- [x] **Robustness:** `ErrorState` gains optional **Retry** + clearer offline copy; wired on Project Home + Event Explorer; live disconnect/failure guidance preserved.
- [x] **Tests:** frontend smoke suite **46 passing** (+7: AgentDrawer Escape, Glossary open/close, global jump surface, Event Explorer pagination+filters, reduced-motion render, live disconnect guidance, Scenario Lab delta); backend `tests/test_edge_cases.py` (7: brief-only overview, no-event studio, scorecard/briefing 409s, empty compare, idempotent cancel, custom stale TTL) → **190 backend passing**. `npm run build` green.
- [x] **Docs:** created `ACCESSIBILITY.md`, `PERFORMANCE_NOTES.md`, `TESTING_GUIDE.md`; updated `FRONTEND_GUIDE.md`, `AGENT_STUDIO_GUIDE.md`, `LIVE_STREAMING_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`. Playwright deferred (E2E plan documented in `TESTING_GUIDE.md`).

### Phase 21 (this phase)
- [x] **Focus traps + restoration:** dependency-free `src/hooks/useFocusTrap.ts` applied to `AgentDrawer` + `GlossaryModal` (traps Tab/Shift+Tab, focuses into the dialog, restores focus to the trigger on close; containers `tabIndex={-1}`). Escape + backdrop close preserved.
- [x] **Skip to content:** Layout gains a focus-visible "Skip to content" link → `#main-content`; main is now `<main id="main-content" role="main" tabIndex={-1}>`.
- [x] **Playwright E2E (opt-in):** `frontend/playwright.config.ts` + `frontend/e2e/smoke.spec.ts` (app shell + Projects/Portfolio/Compare nav + skip link + Glossary open/Escape + Portfolio/Compare routes + best-effort seeded Workflow flow that skips gracefully). Scripts `test:e2e` / `:headed` / `:ui`; `@playwright/test` devDep; Vitest now excludes `e2e/**`; gitignore for `test-results`/`playwright-report`. **Not** in default CI.
- [x] **Tests:** frontend smoke suite **50 passing** (+4: AgentDrawer focus trap + restore, Glossary trap+restore, skip-link/main landmark). Backend unchanged → **190 passing**. `npm run build` green (e2e excluded from tsc/vite). E2E **not executed here** (no browser binaries in the authoring env) — config authored + validated; run locally per `TESTING_GUIDE.md`.
- [x] **Docs:** created none new beyond config; updated `ACCESSIBILITY.md`, `TESTING_GUIDE.md`, `FRONTEND_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`. axe automation evaluated and deferred (documented).

### Phase 22 (this phase)
- [x] **E2E depth + axe:** `e2e/smoke.spec.ts` extended — seeded page-load checks (Home → Studio → Events → Report, graceful skip) + **`@axe-core/playwright`** accessibility checks (wcag2a/aa, fail only on `serious`/`critical`) on app shell, Portfolio, open Glossary dialog, and seeded Home + Studio. Added `@axe-core/playwright` devDep.
- [x] **CI `e2e` job** (`.github/workflows/ci.yml`, `continue-on-error: true`, non-blocking): starts uvicorn + `seed_demo.py`, builds + `vite preview`s the frontend, installs Playwright chromium, runs `npm run test:e2e`, uploads the `playwright-report` artifact. backend/frontend jobs unchanged.
- [x] **A11y fixes:** added `aria-label`s to unlabeled `<select>`s (Agent Studio filter helper; Decision-history related-snapshot picker) so every control has an accessible name.
- [x] **Tests/build:** backend **190 passing**, frontend **50 passing**, `npm run build` green, CI YAML valid (3 jobs). E2E + axe **not executed in the authoring env** (no browser binaries / no live server) — authored, config validated, CI-wired; runs locally or in the CI e2e job.
- [x] **Docs:** updated `README.md`, `TESTING_GUIDE.md`, `ACCESSIBILITY.md`, `FRONTEND_GUIDE.md`, `CURRENT_STATUS.md`.

### Phase 23 (this phase)
- [x] **Health/readiness:** new `GET /readyz` (DB connect + tables-accessible checks → ready/degraded, no secrets) in `app/main.py`. Enhanced `GET /api/v1/system/status` with `database_type`, `frontend_origin_configured`, `live_streaming_supported`, `e2e_configured` (kept `database` for back-compat).
- [x] **Diagnostics:** `GET /api/v1/system/diagnostics` (read-only) — status, request_id, app info, DB counts (projects/baseline events/live runs), feature flags, warnings; asserts no secrets. (`app/api/v1/system.py`.)
- [x] **Request-id/logging:** already present (middleware) — verified every response has `X-Request-ID`, error envelopes + exception logs carry `request_id`.
- [x] **Frontend:** footer **Diagnostics** drawer (`DiagnosticsPanel`, `api/system.ts` +getReadyz/getDiagnostics); global **ErrorBoundary** wrapping routed content (friendly fallback + Retry/Go-home, dev-only stack); API client captures `request_id` → `ApiError.requestId`; `ErrorState` shows "Reference ID".
- [x] **Tests:** backend `tests/test_observability.py` (5: readyz ready, status no-secrets+new fields, diagnostics counts/features, diagnostics request_id, error request_id) → **195 backend passing**; frontend smoke suite **53 passing** (+3: Diagnostics panel, ErrorBoundary catch, ErrorState reference id). `npm run build` green.
- [x] **Docs:** created `docs/OBSERVABILITY.md`; updated `API_SPEC.md`, `TESTING_GUIDE.md`, `FRONTEND_GUIDE.md`, `DEPLOYMENT_OPTIONS.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 24 (this phase)
- [x] **JSON logging:** env toggle `LOG_JSON` (`app/core/config.py`, default `false`). `app/core/middleware.py` now emits single-line JSON access logs (`event_type:"http_request"` + timestamp/level/request_id/method/path/status_code/duration_ms/client_ip/user_agent/error_code) and exception logs (`event_type:"exception"` + request_id/path/method/error_code/error_message/exception_type) when enabled; readable `key=value` kept by default. No secrets/bodies logged.
- [x] **Persistent bounded trail:** `AppLogEntry` model (`app/models/app_log.py`, `app_log_entries`) with id/timestamp/level/event_type/request_id/project_id/run_id/scenario_id/path/method/status_code/code/message/metadata_json/created_at. Bounded by `APP_LOG_MAX_ENTRIES` (default 500); oldest pruned after each insert.
- [x] **Logging service:** `app/services/app_log_service.py` — `create_log_entry`, `record` (own session), `prune_old_logs`, `log_error`, `log_live_run_started/completed/failed`, `log_report_generated`, `log_briefing_generated`, `log_scenario_created`, `list_logs`, `recent_errors`, `counts`, `to_dict`. Logging never breaks a request (swallows + rolls back on failure).
- [x] **Wiring (lifecycle points only):** middleware exception/HTTPException/validation handlers persist `exception`/`http_error`; `live_simulation_service` (started/completed/failed); `report_service` (report_generated); `briefing_service` (briefing_generated); `scenario_service` (scenario_created).
- [x] **Endpoints:** `GET /api/v1/system/logs` (filters level/event_type/request_id/project_id, limit default 50/max 200 → `{items[], total_returned, limit}`) and `GET /api/v1/system/logs/recent-errors` (last 10 error/warning). Read-only, no secrets. `/system/diagnostics` now includes `recent_error_count/recent_warning_count/last_error/log_retention_limit`.
- [x] **Frontend:** `api/system.ts` `getSystemLogs`/`getRecentErrors` + `AppLogEntry`/`AppLogList` types; `DiagnosticsPanel` "Recent Errors" section with Refresh logs, per-entry Copy ID (request_id), and "No recent errors" empty state; `ErrorState` gains a Copy ID button (existing Reference ID kept).
- [x] **Tests:** backend `tests/test_app_logs.py` (10) → **205 backend passing**; frontend smoke **57 passing** (+4: recent errors render, empty state, copyable request-id button, clipboard write). `npm run build` green. `conftest.py` rebinds `database.SessionLocal` to the per-test DB so middleware-side log writes land in the test DB.
- [x] **Docs:** updated `OBSERVABILITY.md`, `TESTING_GUIDE.md`, `DEPLOYMENT_OPTIONS.md`, `FRONTEND_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 25 (this phase)
- [x] **Project export bundle:** `GET /api/v1/projects/{id}/export` (`format=json|zip`, `include_logs=false`, `include_events=true`, `include_artifacts=true`). Deterministic no-secret JSON bundle (`export_version`, `exported_at`, `app_version`, `project_id`, `data{project,brief,ontology,agents,events,reports,briefings,briefing_artifacts,scenarios,snapshots,decisions,live_runs[,app_logs]}`, `checksums` (sha256 per-section + `_all`), `limitations`). ZIP wraps the same JSON.
- [x] **Project import/restore:** `POST /api/v1/projects/import` (`create_new` only; fresh IDs; remaps event→agent/scenario, snapshot→report, decision→snapshot/scenario/report; datetime strings coerced back). `overwrite_existing` → `400 import_mode_not_supported`; malformed → `400 invalid_bundle`.
- [x] **Cascade delete:** `DELETE /api/v1/projects/{id}` removes all related rows (events/agents/reports/briefings/artifacts/scenarios/snapshots/decisions/live_runs/brief/ontology/app_logs) in one transaction, returns counts; verified no orphans (re-fetch + re-export 404).
- [x] **Maintenance endpoints:** `POST /api/v1/system/prune-logs` (prune to cap, returns count) and `POST /api/v1/system/reset-demo` (deletes `FreshPlus Demo*` projects; **DEMO_MODE-guarded**, else `403 demo_mode_required`). `/system/diagnostics` now reports `database.app_log_count`.
- [x] **Service:** `app/services/data_export_service.py` — `export_project`, `import_project`, `delete_project`, `reset_demo_data`, generic column serialiser + datetime coercion.
- [x] **Scripts:** `backend/scripts/backup_sqlite.py` (`--zip`, `--out`; safe if DB absent; never copies `.env`), `reset_demo_data.py` (`--prefix`, `--all --yes`), `prune_app_logs.py` (`--max`, `--older-than-days`). `make backup` / `reset-demo` / `prune-logs` added.
- [x] **Frontend:** `api/projects.ts` `exportProjectBundle`/`projectExportUrl`/`importProject`/`deleteProject`; new **Data Tools** page (`/data-tools`, nav item) with export (JSON/zip), import (file/paste), and backup/reset/prune instructions; Project Home **Export Project** button + Data Tools link; Diagnostics drawer app-log count + Download diagnostics snapshot + Data Tools link.
- [x] **Tests:** backend `tests/test_data_export.py` (12: export 404/success/sections/no-secrets/zip, import create-new/round-trip/malformed/overwrite-deferred, cascade delete, prune endpoint, reset-demo guard) → **217 backend passing**; frontend smoke **61 passing** (+4: Data Tools renders, export calls API, import success, Project Home export button). `npm run build` green.
- [x] **Docs:** created `docs/DATA_MANAGEMENT.md`; updated `DEPLOYMENT_OPTIONS.md`, `DEMO_SCRIPT.md`, `FRONTEND_GUIDE.md`, `OBSERVABILITY.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 26 (this phase)
- [x] **Sample library:** 6 fictional FMCG concepts under `samples/library/` (`*.md` briefs + `samples_index.json` metadata/structured fields). Categories: RTD beverage, healthy snack, personal care, household cleaning, dairy/nutrition, beauty/skincare. No real brand names.
- [x] **Backend service+endpoints:** `app/services/sample_service.py` (`list_samples`, `get_sample`, `load_sample`); `GET /api/v1/system/samples`, `GET /api/v1/system/samples/{id}` (404 `sample_not_found`), `POST /api/v1/system/samples/{id}/load` (`project_name`, `run_pipeline`). `run_pipeline=false` creates project+brief; `true` runs deterministic ontology→agents→simulation→report→briefing (no LLM). Returns project_id/status/completed_steps/next_url/warnings.
- [x] **Frontend:** `api/samples.ts`; `/samples` (`SampleLibraryPage`: cards, search, category filter, load + load-and-run) and `/samples/:id` (`SampleDetailPage`: full brief + load); **Samples** nav item.
- [x] **Onboarding:** `OnboardingPanel` (8-step dismissible checklist on empty Projects page; `localStorage onboarding_seen`/`last_sample_loaded`); guided empty-states on Project List (load sample / import / blank) and Project Home (no-brief hint). Samples links added to Project List, Project Home, Data Tools, Glossary.
- [x] **Contextual help:** `HelpTooltip` accessible **?** popover (Esc/outside-click close) with shared `HELP_TEXT` registry (ontology, agent, market actor, simulation event, live/replay, trial/repeat, confidence, assumptions, snapshot, scenario, briefing, export bundle); wired on Project Home.
- [x] **Glossary upgrade:** `GlossaryModal` now has search + category tabs (Simulation/Research/Reporting/Operations) + inline page links; `docs/GLOSSARY.md` updated.
- [x] **Tests:** backend `tests/test_samples.py` (7: list/detail/unknown-404/load create/load-unknown-404/run-pipeline/no-real-brands) → **224 backend passing**; frontend smoke **67 passing** (+6: sample cards, search filter, load shows links, onboarding render+dismiss, HelpTooltip content, glossary search). `npm run build` green.
- [x] **Docs:** created `docs/SAMPLE_LIBRARY_GUIDE.md`, `docs/ONBOARDING_GUIDE.md`; updated `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `DATA_MANAGEMENT.md`, `GLOSSARY.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 27 (this phase)
- [x] **Tour system** (`frontend/src/tours/`): `tours.ts` (TourStep/Tour types + `FIRST_TIME_TOUR`, `STUDIO_TOUR`, `TOURS` registry, `TOUR_DISCLAIMER`), `TourProvider.tsx` (context + `useTour` + route navigation + localStorage persistence/resume; no-op fallback when used outside a provider), `TourOverlay.tsx` (spotlight ring around `data-tour` targets, centered-modal fallback, step card, keyboard →/←/Esc).
- [x] **Two tours:** First-Time Product Tour (Projects/Samples → Home → Studio → Report/Briefing → Scenario Lab → Data Tools) and Agent Studio Tour (Live/Replay, canvas, timeline, stream, **heuristic-edge disclaimer**). Studio tour launches from a **Tour** button in the Studio header.
- [x] **Demo auto-play:** `DemoControlPanel.tsx` — Start First-Time/Studio tour, **Play Demo (Quick)** (load RTD-tea sample, brief only) / **Play Demo (Full)** (load + run deterministic pipeline, warns it may take time), Reset onboarding/tour state, Open Sample Library. Uses existing `POST /system/samples/{id}/load`; expensive pipeline only on explicit Full.
- [x] **Wiring:** `TourProvider` wraps Routes in `App.tsx`; DemoControlPanel in Layout footer (**Tours & Demo** toggle), Sample Library page, and empty Projects state; `data-tour` anchors added (`nav-projects`, `nav-samples`, `samples-grid`, `data-tools-root`, `studio-root`/`-live`/`-canvas`/`-stream`). localStorage: `guided_tour_seen`, `guided_tour_current_step`, `demo_autoplay_seen`.
- [x] **A11y/UX:** labelled dialog, Esc to skip, arrow-key nav, reduced-motion friendly, backdrop click does not dismiss, fully interactive after skip; disclaimer shown in every step.
- [x] **Tests:** no backend change (uses existing endpoint) → **224 backend still passing**; frontend smoke **74 passing** (+7: overlay renders, Next/Back/Skip, finish persists, panel renders, Play Demo calls load API, studio heuristic disclaimer, reset clears localStorage). `npm run build` green.
- [x] **Docs:** created `docs/GUIDED_TOURS.md`; updated `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `ONBOARDING_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 28 (this phase)
- [x] **Decision Pack aggregator:** `app/services/decision_pack_service.py` — `build_pack` composes a stakeholder document from existing outputs (briefing payload via `briefing_service.build_payload` + scorecard + confidence + assumptions + scenarios + decision history); `render_markdown` for copy/paste. No LLM, no new scoring, no invented findings, no secrets.
- [x] **Endpoints:** `GET /api/v1/projects/{id}/decision-pack` (structured JSON) and `GET …/decision-pack/markdown` (text). Preconditions: 404 `project_not_found`; 409 `events_required`/`report_required`/`scorecard_required` (reuses briefing build); briefing not required (built on the fly).
- [x] **Frontend:** route `/projects/:id/decision-pack` (`DecisionPackPage`, lazy) — clean read-only sections (cover, recommendation, scorecard, top findings, biggest risks, next best actions, scenario/sensitivity snapshot, assumptions & limitations, evidence pack, decision history); buttons Print/Save-as-PDF, Download Markdown, Download JSON, Copy local read-only link, Back to Home. Helpers in `components/decisionpack/DecisionPackParts.tsx` (`ReadOnlyBadge`, `PrintButton`, `DownloadMarkdownButton`, `DownloadJsonButton`, `CopyLinkButton`, `DecisionPackSection`). `api/projects.ts` `getDecisionPack`/`getDecisionPackMarkdown`.
- [x] **Print CSS** (`index.css` `@media print`): hides header/nav/footer + `.print-hide`, white background, page breaks on `.decision-pack-section.page-break`, avoids clipped cards, prints disclaimer.
- [x] **CTAs:** Project Home (**Open Decision Pack**), Briefing (**Create stakeholder decision pack**), Report, Portfolio (per project), Decision History.
- [x] **Tests:** backend `tests/test_decision_pack.py` (6: 404 missing, 409 report-required, success, core sections, markdown non-empty, no-secrets) → **230 backend passing**; frontend smoke **78 passing** (+4: page renders + read-only badge, print/download buttons, key sections, copy-link clipboard). `npm run build` green.
- [x] **Docs:** created `docs/DECISION_PACK_GUIDE.md`; updated `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `BRIEFING_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 29 (this phase)
- [x] **Decision Board aggregator:** `app/services/decision_board_service.py` — `build_board` classifies every project go/validate/revise/hold/incomplete by reusing `scorecard_service.build_for_project` + `briefing_service.decide_recommendation_status` (no new scoring, no LLM); incomplete projects get a stage-specific reason and are excluded from rankings. Adds owner_team + risk_level heuristics, summary counts, top/highest-risk/most-ready/most-needs-validation, 5 rankings, portfolio_recommendation, limitations. `render_markdown` for print/copy.
- [x] **Endpoints:** `GET /api/v1/portfolio/decision-board` (+ `?project_ids=a,b,c` filter) and `GET …/decision-board/markdown`. No secrets; safe on partial/empty portfolios.
- [x] **Frontend:** route `/portfolio/decision-board` (`PortfolioDecisionBoardPage`, lazy; nav item **Board**) — read-only, print/PDF-ready (reuses Phase-28 `DecisionPackParts` + print CSS): summary cards, decision table with label-filter chips, decision buckets, rankings, portfolio recommendation, limitations; per-project Decision Pack links. `api/portfolio.ts` `getDecisionBoard`/`getDecisionBoardMarkdown`.
- [x] **Links:** Portfolio (**Decision Board →**), Compare, Project Home, Layout nav (**Board**).
- [x] **Tests:** backend `tests/test_decision_board.py` (7: empty state, incomplete project, report-ready project, allowed labels, markdown non-empty, no-secrets, project_ids filter) → **237 backend passing**; frontend smoke **82 passing** (+4: board renders + summary cards, decision table, decision-pack link, print/download buttons). `npm run build` green.
- [x] **Docs:** created `docs/PORTFOLIO_DECISION_BOARD.md`; updated `FRONTEND_GUIDE.md`, `DEMO_SCRIPT.md`, `PORTFOLIO_GUIDE.md`, `DECISION_PACK_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 30 (this phase)
- [x] **Project model:** added `pipeline_stage`, `pipeline_stage_source`, `pipeline_stage_note`, `pipeline_stage_updated_at` (nullable). Lightweight SQLite-only additive `ALTER TABLE` migration in `init_db()` so existing local DBs upgrade without losing data.
- [x] **Pipeline service** (`app/services/pipeline_service.py`): 12 stages (new_concept → archived); `infer_stage` from workflow state; `recommended_stage` from Decision Board label + inference; `get_status`/`update_status`/`apply_decision_board`/`build_board`. Decision-board mapping (`go/validate/revise/hold` → same-named stages; `incomplete` left to inference). Manual stages preserved by default via `only_if_not_manual=true`.
- [x] **Decision-log integration:** every manual change writes `entry_type="change"` ("Pipeline stage changed to …", tags `["pipeline","stage-change",<stage>]`); apply-decision-board writes `entry_type="decision"` ("Decision Board applied: …", tags `["pipeline","decision-board",<stage>]`).
- [x] **Endpoints:** `GET/PATCH /api/v1/projects/{id}/pipeline-status` (422 `invalid_stage`/`invalid_source`, 404 missing), `GET /api/v1/portfolio/pipeline` (columns + summary), `POST /api/v1/portfolio/pipeline/apply-decision-board` (`{project_ids?, only_if_not_manual}` → `{changed, skipped_manual, skipped_no_board, unchanged, changes[]}`).
- [x] **Frontend:** `api/pipeline.ts` (+ `STAGE_LABELS`, `PIPELINE_STAGES`); `client.ts` gained `patch`; new route `/portfolio/pipeline` (`PipelineBoardPage`, lazy; nav **Pipeline**) — 12 stage columns with project cards (decision-board chip, score, next action, links to Home/Studio/Decision Pack/Briefing/Update Stage); header **Apply Decision Board** / **Open Decision Board**. `UpdateStageModal` (accessible dialog, Esc/backdrop dismiss). **Project Home** shows pipeline-stage chip + source + inferred hint + next-action + **Update Stage** + **Open Pipeline Board**. Portfolio Decision Board adds *Apply labels to Pipeline →*.
- [x] **Tests:** backend `tests/test_pipeline.py` (9: inferred-empty, ready-for-simulation, PATCH update, decision-log entry, invalid stage 422, missing 404, portfolio columns, apply changes, apply preserves manual) → **246 backend passing**; frontend smoke **87 passing** (+5: page renders, columns + card, Update Stage saves via API, Apply Decision Board, Project Home stage badge). `npm run build` green.
- [x] **Docs:** created `docs/PIPELINE_BOARD_GUIDE.md`; updated `FRONTEND_GUIDE.md`, `PORTFOLIO_DECISION_BOARD.md`, `DECISION_HISTORY_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

### Phase 31 (this phase)
- [x] **Activity feed service** (`app/services/activity_service.py`): `list_activity` aggregates `DecisionLogEntry` rows across all projects into a chronological feed (filters: `event_type`, `project_id`, `stage`, `limit` default 30/max 100). Derives `activity_type` from tags (`stage-change`→`stage_change`, `decision-board`→`decision`), a `stage` hint, and a best `related_url`. Read-only, no secrets, no new persistence.
- [x] **Pipeline filters:** `pipeline_service.build_board` now accepts `stage / decision_label / min_score / max_risk / owner_team / search / include_archived`; cards carry `pipeline_stage_updated_at`, `risk_score`, `owner_team`. Summary reports filtered `total_projects` + `total_projects_unfiltered`.
- [x] **Endpoints:** `GET /api/v1/portfolio/activity` (filtered feed) and filter query-params on `GET /api/v1/portfolio/pipeline`.
- [x] **Frontend:** route `/portfolio/activity` (`PortfolioActivityPage`, lazy; nav **Activity**) with type/stage/limit filters + manual refresh, day-grouped feed. `PipelineFilterBar` (search/stage/decision/min-score/max-risk/owner/include-archived) synced to **URL searchParams** with Clear filters + "Showing X of Y". Pipeline cards show an amber **Recently changed** badge (≤7 days, client-computed). **Project Home** adds a **Recent pipeline activity** panel (last 3 from `getActivity({project_id, limit:3})`) + Decision-history / Pipeline-board links. `api/pipeline.ts` gains `getActivity` + filtered `getPipelineBoard`; `client.ts` already had `patch`.
- [x] **Tests:** backend `tests/test_activity_and_filters.py` (9: stage-change entries, project_id filter, stage filter, limit, no-secrets; pipeline stage/decision_label/search filters + include_archived=false) → **255 backend passing**; frontend smoke **93 passing** (+6: filter bar renders, filter re-fetch, clear filters, recently-changed badge, Project Home recent panel, Activity page). `npm run build` green.
- [x] **Docs:** created `docs/PIPELINE_ACTIVITY_GUIDE.md`; updated `FRONTEND_GUIDE.md`, `PIPELINE_BOARD_GUIDE.md`, `DECISION_HISTORY_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`.

## Files of note (Phase 7)
**Created**
- `backend/app/models/scenario.py`
- `backend/app/schemas/qa.py`, `backend/app/schemas/scenario.py`
- `backend/app/services/qa_service.py`, `backend/app/services/scenario_service.py`
- `backend/app/api/v1/scenarios.py`
- `backend/tests/test_qa.py`, `backend/tests/test_scenario.py`
- `samples/sample_qa_answers.json`, `samples/sample_scenario_price_reduction.json`

**Modified**
- `backend/app/models/event.py` (+`run_type`, +`scenario_id`), `backend/app/models/__init__.py`
- `backend/app/services/simulation_scoring.py` (override adjustment fields)
- `backend/app/services/simulation_service.py` (extracted `run_rounds`; baseline-only queries)
- `backend/app/services/project_service.py`, `backend/app/services/report_service.py` (baseline-only event queries)
- `backend/app/api/v1/qa.py` (rewritten), `backend/app/api/v1/__init__.py` (register scenarios router)
- `docs/API_SPEC.md`, `docs/CURRENT_STATUS.md`, `README.md`

## Endpoints (Phase 7)
- `POST /api/v1/projects/{id}/ask` — 404 project / 409 `events_required`|`report_required` / 200 `QuestionOut`.
- `POST /api/v1/projects/{id}/scenario` — 404 / 409 `ontology_required`|`agents_required`|`baseline_events_required`|`baseline_report_required` / 200 `ScenarioRunOut`.
- `GET /api/v1/projects/{id}/scenarios` — list `ScenarioListItem`.
- `GET /api/v1/projects/{id}/scenarios/{scenario_id}` — `ScenarioRunOut` (404 `scenario_not_found`).
- `GET /api/v1/projects/{id}/scenarios/{scenario_id}/delta` — raw delta payload.
- `DELETE /api/v1/projects/{id}/scenarios/{scenario_id}` — deletes the run + its scenario events.

## Test Coverage
`pytest` (backend): **255 passed** (… + 7 P29 decision-board + 9 P30 pipeline + 9 P31 activity/filters; P27 added no backend tests). `npm test` (frontend): **93 passed** (Vitest smoke). `npm run build`: green (code-split chunks; `e2e/` excluded). Playwright E2E + axe: authored/opt-in + CI-wired, not run here (no browser binaries). Deploy-config check: 10/10 pass. Demo seed verified; Docker compose config valid (image build not run — Docker absent in authoring env).
- **Q&A (12):** 404 project missing; 409 `report_required`; 409 `events_required`; repeat/target-segment/claim-risk/pricing questions route + answer; evidence references well-formed (event_id/round 1–6/action); confidence 0–1; evidence excluded when `include_evidence=false`; interview returns N selected agents + simulated answers + "simulated" caveat; deterministic fallback when `use_llm=true` but no key.
- **Scenario (13):** 404 project missing; 409 `baseline_events_required`; 409 `baseline_report_required`; success with `price_change_pct`; full delta-metrics shape; unique scenario_id per run; baseline events unchanged; baseline report unchanged; list + detail; delta endpoint; 404 `scenario_not_found`; three reruns leave baseline report intact (6 funnel rounds); delete removes run.

## Frontend (Phase 8)
**Created (`/frontend`):** `package.json`, `vite.config.ts`, `tsconfig.json`, `tailwind.config.js`, `postcss.config.js`, `index.html`, `.env.example`, `.gitignore`; `src/main.tsx`, `src/App.tsx`, `src/index.css`, `src/vite-env.d.ts`; `src/types/api.ts`; `src/api/{client,projects,ontology,agents,simulation,reports,qa,scenarios}.ts`; `src/utils/{formatters,sampleBrief}.ts`; `src/components/{Layout,Stepper,StatusBadge,MetricCard,EvidenceChip,LoadingState,ErrorState}.tsx`; `src/pages/{ProjectListPage,ProjectWorkflowPage,ReportPage,QAConsolePage,ScenarioLabPage}.tsx`.

**Backend modified (CORS only):** `app/core/config.py`, `app/main.py`.

**Routes:** `/` (projects), `/projects/:id/workflow`, `/projects/:id/report`, `/projects/:id/qa`, `/projects/:id/scenarios`.

**Build status:** `npm run build` → `tsc --noEmit` clean + `vite build` success (56 modules, 211.8 kB JS / 64.6 kB gzip, 17.5 kB CSS). Live smoke: backend `/healthz` ok, project create over HTTP ok, CORS preflight from `localhost:5173` returns allow-origin. Backend `pytest`: 102 passed.

## Known Limitations
1. **Exploratory decision support, not a forecast** — every Q&A answer and scenario carries this disclaimer; scores come from a deterministic, segment-weighted rule engine, not fitted to historical launch outcomes.
2. **Q&A is grounded only in persisted data** — it answers from the report payload, baseline events, agents, ontology and agent memory; it deliberately refuses to introduce generic marketing knowledge or facts not in the simulation.
3. **Interview answers are simulated personas** — reconstructed from modelled agent memory, not real interview transcripts; always flagged as such and recommended for real qualitative validation.
4. **Scenario deltas are relative, not absolute** — they show direction/magnitude of change between two simulated runs under a rule engine, not predicted real-world sales impact. Levers are additive nudges, not calibrated elasticities.
5. **LLM optional, off by default** — Q&A LLM rewrite only rephrases `direct_answer` and never invents findings; it falls back to deterministic text when unconfigured or on error. All tests run fully offline.

## Next Recommended Prompt

> **Begin Phase 32 — Saved Views, Pipeline Presets & Quick Filters.**
>
> Goal: let users save and recall common pipeline/activity filter combinations as named local views without new analytics, auth, or multi-user. No auth/multi-user/Redis/Celery/WebSocket/real-data connectors/deployment-pipeline; no core-scoring changes; keep SQLite-friendly, deterministic, offline.
>
> Requirements:
> - **Saved views (local):** persist named filter presets in `localStorage` (e.g. "Needs validation", "Ship candidates", "High risk") capturing the Pipeline Board filter set; a small manager to create / apply / rename / delete; one-click apply updates the URL params.
> - **Built-in quick filters:** ship a few read-only presets (Go candidates = stage go + min_score; Needs validation = decision validate; High risk = max_risk low) as chips above the board.
> - **Shareable preset links:** since filters already live in the URL, "Copy view link" copies the current filtered URL; document that saved views are local but links are shareable.
> - **Optional backend convenience:** none required; if added, a tiny stateless `GET /api/v1/portfolio/pipeline/presets` returning the built-in preset definitions (no persistence).
> - **Tests:** frontend (create/apply/delete a saved view persists to localStorage, quick-filter chip applies params, copy-view-link); backend only if a presets endpoint is added.
> - **Docs:** update `FRONTEND_GUIDE.md`, `PIPELINE_ACTIVITY_GUIDE.md`, `README.md`, `CURRENT_STATUS.md`; optionally `docs/SAVED_VIEWS.md`.
> - **Do not** change core scoring formulas, or add auth/multi-user/deployment/real-data connectors.
