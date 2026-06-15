# FRONTEND_GUIDE.md

_Phase 8 — Frontend Dashboard_

A local, internal-tool style dashboard for the FMCG Innovation Reaction Simulator. It is a
Vite + React + TypeScript SPA that talks to the existing FastAPI backend (Phases 1–7) over
its REST API. No backend business logic was changed; the only backend touch was widening the
CORS allowlist to include the Vite dev origin.

## Stack
- **Vite 5** + **React 18** + **TypeScript 5**
- **React Router 6** for navigation
- **Tailwind CSS 3** for styling (PostCSS + autoprefixer)
- A small typed `fetch` client (`src/api/client.ts`) — no data-fetching framework, to keep the
  dependency surface minimal and the workflow imperative/easy to follow.

## Running it

### 1. Start the backend (terminal A)
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### 2. Start the frontend (terminal B)
```bash
cd frontend
npm install            # first time only
cp .env.example .env   # optional; defaults to http://localhost:8000/api/v1
npm run dev            # serves http://localhost:5173
```

Open http://localhost:5173.

### Environment
- `VITE_API_BASE_URL` — backend API base (default `http://localhost:8000/api/v1`, no trailing slash).
- No secrets live in the frontend. The backend keeps its own `OPENAI_API_KEY` in `.env`.

### Build / typecheck
```bash
npm run build       # tsc --noEmit && vite build  → dist/
npm run typecheck   # tsc --noEmit only
npm run preview     # serve the production build
```

## Routes
| Route | Page | Purpose |
| --- | --- | --- |
| `/` | `ProjectListPage` | List + create projects |
| `/projects/:id/workflow` | `ProjectWorkflowPage` | 8-step pipeline runner |
| `/projects/:id/events` | `EventExplorerPage` | Filterable event log + expandable rows + agent drawer |
| `/projects/:id/report` | `ReportPage` | 16-section strategic report viewer + markdown |
| `/projects/:id/qa` | `QAConsolePage` | Evidence-grounded Q&A console |
| `/projects/:id/scenarios` | `ScenarioLabPage` | What-if scenario lab + saved scenarios |
| `/projects/:id/sensitivity` | `SensitivityPage` | Lever response curves + best/risk cards |
| `/portfolio` | `PortfolioPage` | All concepts ranked by scorecard (sort/filter) |
| `/compare` | `ComparePage` | Side-by-side concept comparison |
| `/projects/:id/snapshots/diff` | `SnapshotDiffPage` | Diff active report / snapshots |
| `/projects/:id/decisions` | `DecisionHistoryPage` | Timeline + decision log |
| `/projects/:id/briefing` | `BriefingPage` | Executive narrative briefing |
| `/projects/:id/home` | `ProjectHomePage` | Project overview + what-to-do-next |
| `/projects/:id/studio` | `AgentStudioPage` | Visual agent-interaction playback |

## Workflow steps (ProjectWorkflowPage)
1. **Create Project** — confirmation + project id.
2. **Submit Brief** — textarea + "Load sample brief" (FreshPlus). Sample fill also sends structured fields.
3. **Analyze Ontology** — entities, relationships, triggers, barriers, risk signals, missing info.
4. **Generate Agents** — totals + segment distribution.
5. **Run Simulation** — totals, top triggers/barriers, action distribution (6 rounds, seed 42).
6. **Generate Report** — exec summary cards + link to the full report page.
7. **Ask Questions** — preset Q&A with evidence chips; link to the console.
8. **Scenario Testing** — one-click 10% price-reduction scenario + link to the lab.

Step completion is read back from the backend project envelope (`GET /projects/{id}`:
`has_brief`, `has_ontology`, `agents_count`, `events_count`, `has_report`), so refreshing the
page restores accurate status. The header shows live status badges.

## API client (`src/api/*.ts`)
`createProject`, `getProjects`, `getProject`, `submitBrief`, `analyzeOntology`, `getOntology`,
`generateAgents`, `getAgentsSummary`, `listAgents`, `getAgent`, `runSimulation`,
`getEventsSummary`, `listEvents`, `getEvent`, `generateReport`, `getReport`, `getReportSummary`,
`getReportMarkdown`, `askQuestion`, `runScenario`, `listScenarios`, `getScenario`,
`getScenarioDelta`, `deleteScenario`.

Errors flow through a single `ApiError {status, code}`. `ErrorState` maps backend codes
(`events_required`, `report_required`, `baseline_events_required`, …) to friendly copy.

## Components
`Layout`, `Stepper`, `StatusBadge`, `MetricCard`, `EvidenceChip`, `LoadingState`, `ErrorState`,
`AgentDrawer` (slide-over showing an agent's traits, grounding sources, initial/simulation
memory, action history, trust drivers, trial barriers, repeat drivers, likely objections).

## Event Explorer (Phase 9)
`/projects/:id/events` — filters (round, agent type, segment, action), a wide responsive table
(round, agent/segment, touchpoint, action, sentiment, trial/intent/repeat, barrier/trigger),
expandable rows (stage, emotional tone, confidence, reasoning, generated reaction, event id),
and a clickable agent → `AgentDrawer`. Linked from the Workflow (simulation step) and Report pages.

## Scenario compare (Phase 9)
The Scenario Lab renders a **Baseline | Scenario | Δ** table over trial probability, purchase
intent, repeat probability, sentiment, complaints, recommends, and brand switches (complaint/
switch deltas are tone-inverted so "good" is green). When more than one scenario is saved, a
**Compare with** selector adds a second scenario column for a baseline-anchored A/B comparison.

## Shareable-demo polish (Phase 10)
- **System status footer:** `Layout` calls `GET /api/v1/system/status` on mount and shows pills —
  **Backend connected/offline**, **LLM configured / Deterministic fallback**, **Demo Mode** (when
  `demo_mode`), and the app **version**.
- **Offline retry banner:** if the status call fails, a red top banner appears with a **Retry**
  button and copy: "Backend is not reachable. Start FastAPI on port 8000 or run `docker compose up`."
- **Report downloads + print:** the Report page has **Download Markdown**
  (`fmcg-innovation-report-{id}.md`), **Download JSON** (`…-{id}.json`, the structured payload),
  and **Print report**. A `@media print` stylesheet (in `index.css`) hides nav/footer/controls
  (`print:hidden`), forces a white background, and avoids breaking cards across pages.
- `src/api/system.ts` exposes `getSystemStatus()`, `getReadyz()`, `getDiagnostics()`,
  `getSystemLogs(query)`, and `getRecentErrors()`.
- `src/api/projects.ts` exposes `exportProjectBundle(id)`, `projectExportUrl(id, opts)`,
  `importProject(bundle, opts)`, and `deleteProject(id)` (Phase 25).

## Insight depth & trust (Phase 11)
- **Sensitivity page** (`/projects/:id/sensitivity`): pick levers → `POST /sensitivity` → response
  curves drawn with the dependency-free `MiniLineChart`, plus best-trial / best-repeat /
  highest-risk cards, the recommended lever to test first, and a per-lever table.
- **Confidence panel** (`ConfidencePanel`, on the Report page): `ConfidenceGauge` + weighted driver
  bars + risks + how-to-improve, from `GET /confidence`.
- **Assumptions ledger** (`AssumptionsLedger`, on the Report page): impact-tagged table from
  `GET /assumptions` with a **Download JSON** button.
- **Evidence drill-down:** `EvidenceChip` now takes an optional `projectId`; when set, the expanded
  panel offers **Open event →** / **Open agent →** links into the Event Explorer
  (`?event_id=…&round_number=…` / `?agent_id=…&open_agent=1`), which reads those query params to
  pre-filter and auto-open the Agent Drawer. Used on the Report, Q&A, and Workflow pages.
- **Charts** (`src/components/charts.tsx`): `MiniLineChart`, `MiniBarChart`, `ConfidenceGauge` —
  inline SVG, no charting library. `src/api/insights.ts` exposes `runSensitivity`, `getConfidence`,
  `getAssumptions`. See `docs/EXPLAINABILITY_GUIDE.md`.

## Comparative studies & portfolio (Phase 12)
- **Portfolio** (`/portfolio`): sortable/filterable table of every project with scorecard columns
  (overall, confidence, trial, repeat, risk) + summary metric cards; row click opens the project.
- **Compare** (`/compare`): pick 2–5 report-ready concepts → `POST /portfolio/compare` → dimension
  table (best value per row highlighted), `ScorecardCard`s, and a recommendation.
- **Concept scorecard + snapshots** (`SnapshotPanel` on the Report page): live `ScorecardCard`
  (bar per dimension, risk dimensions inverted, JSON/Markdown export) + create/list/view/delete
  immutable snapshots, with per-snapshot Markdown/JSON download.
- New API module `src/api/portfolio.ts`; component `ScorecardCard` (+ `scorecardMarkdown` helper).
  Top nav gains **Portfolio** and **Compare**. See `docs/PORTFOLIO_GUIDE.md`.

## Snapshot diff & decision history (Phase 13)
- **Snapshot diff** (`/projects/:id/snapshots/diff`, `SnapshotDiffPage`): pick left/right (active
  report or any snapshot) → `POST /snapshots/diff` → delta cards, `MiniBarChart` of dimension
  magnitudes, changed sections, risk changes, recommendation change, segment deltas, plain-English
  summary, and "Create decision log from this diff".
- **Drift indicator** (`DriftIndicator` on the Report page): shows active-report movement vs the
  latest snapshot with a link to the full diff; silent when no snapshots exist.
- **Decision history** (`/projects/:id/decisions`, `DecisionHistoryPage`): merged read-only
  `GET /timeline` + an editable decision log (`GET/POST/DELETE /decisions`) with entry types, tags,
  and optional related snapshot. Snapshot creation auto-logs an entry.
- New API module `src/api/history.ts`. Nav gains **History**; Report page links to Snapshot diff +
  History. Risk dimensions count *down* as improvement everywhere. See `docs/DECISION_HISTORY_GUIDE.md`.

## Executive briefing (Phase 14)
- **Briefing page** (`/projects/:id/briefing`, `BriefingPage`): audience + tone selectors, evidence
  / decision-history toggles → `POST /briefing/generate`. Renders a recommendation banner
  (color-coded by status), situation, top findings (with evidence chips), biggest risks, readiness
  chips, next-best-actions (priority + owner + effort), validation plan, evidence pack, and
  limitations; plus **Download Markdown / Download JSON / Print / Show markdown**.
- New API module `src/api/briefing.ts`. Nav gains **Briefing**; linked from Report, Portfolio
  (per report-ready row), and Decision History. See `docs/BRIEFING_GUIDE.md`.

## Briefing Q&A & audience tailoring (Phase 15)
- The **Briefing page** now has tabs: **Briefing** (Phase 14), **Ask Briefing**, **Tailor by
  Audience**, **Board Summary**.
- **Ask Briefing** (`AskBriefingTab`): preset + free-text questions → `POST /briefing/ask`;
  renders the answer with evidence chips, related actions/risks, limitations, and follow-up buttons.
- **Tailor by Audience** (`TailorTab`): audience + tone → `POST /briefing/tailor`; renders the
  re-framed payload (priority, needs-to-know, role risks/actions, talk track) with MD/JSON/print.
- **Board Summary** (`BoardSummaryTab`): `POST /briefing/board-summary` → one-page cards (3 findings
  / 3 risks / 3 actions + gate + validation + caveat) with MD/JSON/print.
- New API functions in `src/api/briefing.ts` (`askBriefing`, `tailorBriefing`, `generateBoardSummary`).
  `ErrorState` now maps `briefing_required` / `board_summary_required` / `scorecard_required`.
  See `docs/AUDIENCE_TAILORING_GUIDE.md`.

## Agent Studio (Phase 16)
- **Route** `/projects/:id/studio` (`AgentStudioPage`): animated playback of saved events.
- **Zones:** control panel + metric strip (trials/repeats/recommends/complaints/avg sentiment),
  `PlaybackControls` (0.5x/1x/2x/instant, play/pause/reset/replay), `RoundTimeline`, a filter bar
  (segment/agent type/action/trigger/barrier/sentiment), `AgentNetworkCanvas` (dependency-free SVG;
  segment-clustered nodes, consumer/market-actor/active colors, heuristic edges + legend),
  `LiveEventStream` (newest-first cards, capped 40, Open agent / Open event), and the `AgentDrawer`
  inspector on node/card click.
- **Data:** `GET /studio/state` via `src/api/studio.ts`. Empty state shows "Run simulation first"
  with a one-click run. Edges are clearly labelled as visualization aids, not conversations.
- Linked from Workflow (simulation step), Event Explorer, Report; nav gains **Studio**.
  See `docs/AGENT_STUDIO_GUIDE.md`.
- **Phase 17 hardening:** control-room header (status badge + agent/event totals + mode + CTAs),
  guided next-step empty state (analyze/generate/run inline), keyboard shortcuts (Space/R/←/→),
  consumer/market view toggles, copy-evidence on stream cards, and an edge legend that states links
  are heuristic (not conversations). Projects page shows "Open demo in Agent Studio" when a seeded
  `FreshPlus Demo` project exists (`GET /projects?demo=true`).

## Live simulation streaming (Phase 18)
- The Studio has a **Replay / Live** mode switch. **Live Mode** (`LivePanel` + `useLiveSimulation`
  hook) calls `POST /live-simulation/start`, opens an `EventSource` to the SSE stream, and updates
  the canvas (active-agent highlight), live event cards, metric strip, and a progress bar as
  messages arrive; on `run_completed` it offers Generate Report / Replay / Event Explorer; on
  disconnect/failure it shows a hint and lets you fall back to Replay.
- Components: `LiveSimulationControls`, `LiveProgressBar`, `LiveStatusBadge`, `LivePanel`; hook
  `useLiveSimulation`; API `src/api/liveSimulation.ts`. Streamed events persist as normal baseline
  events. See `docs/LIVE_STREAMING_GUIDE.md`.

## Workspace home & onboarding (Phase 19)
- **Project Home** (`/projects/:id/home`, `ProjectHomePage`): from `GET /overview` — pipeline status
  badges + counts, a deterministic "what to do next" card (Go button routes to the right surface),
  latest recommendation (scorecard + briefing), quick links, and recent activity.
- **Global jump** in the Layout header (project + surface select → Go) and a footer **Glossary**
  drawer (`GlossaryModal`). Nav gains **Home**.
- **Live Run History** in Studio Live Mode (`LivePanel`): lists recent runs with status/stale flag,
  Cancel + Open-replay, and a "mark stale / cancel" banner for stuck runs (via `listLiveRuns` /
  `cancelLiveRun`). See `docs/WORKSPACE_HOME_GUIDE.md` + `docs/GLOSSARY.md`.

## Hardening (Phase 20)
- **Accessibility:** Escape closes Agent Drawer + Glossary; `aria-live` on live status/progress;
  `role="dialog"`/`aria-modal` + labels; focus rings; `prefers-reduced-motion` via
  `usePrefersReducedMotion` + CSS (`studio-pulse` disabled). See `docs/ACCESSIBILITY.md`.
- **Performance:** Event Explorer client-side pagination (50/100/200); live-stream cap selector
  (40/100/200, metrics use the full revealed set); canvas **segment-aggregation** above 150 nodes;
  heavy routes `React.lazy`-split (main bundle ~243 kB). See `docs/PERFORMANCE_NOTES.md`.
- **Robustness:** `ErrorState` gains an optional **Retry** button + clearer offline copy; wired on
  Project Home + Event Explorer; live disconnect/failure shows replay/retry guidance.

## Focus management & E2E (Phase 21)
- **Focus traps:** `AgentDrawer` + `GlossaryModal` trap focus while open and restore it to the
  trigger on close via the dependency-free `useFocusTrap` hook (Escape + backdrop close preserved).
- **Skip link:** the Layout has a "Skip to content" link (visible on focus) → `#main-content`
  (`<main role="main" tabIndex={-1}>`).
- **Playwright** opt-in smoke (`frontend/e2e/`, `npm run test:e2e`) — app shell + nav + skip link +
  glossary + seeded page loads, **plus `@axe-core/playwright`** accessibility checks (fail on
  serious/critical). Wired into a non-blocking CI `e2e` job. See `docs/TESTING_GUIDE.md`.

## Observability (Phase 23–24)
- Footer **Diagnostics** drawer (`DiagnosticsPanel`) shows backend connection, `/readyz` readiness,
  version/env/demo/LLM/database/live-streaming, project/event/live-run counts, last `request_id`,
  warnings, and a Retry button (`getSystemStatus` + `getReadyz` + `getDiagnostics`).
- **Phase 24:** the drawer adds a **Recent Errors** section (`getRecentErrors` →
  `/system/logs/recent-errors`) with a **Refresh logs** button, per-entry **Copy ID** (request_id to
  clipboard), and a **"No recent errors"** empty state. `src/api/system.ts` also exposes
  `getSystemLogs(query)` → `/system/logs` (`level/event_type/request_id/project_id/limit`).
- Global **ErrorBoundary** wraps routed content → friendly fallback + Retry/Go-home (stack only in dev).
- The API client captures `request_id` (error body or `X-Request-ID`); `ErrorState` shows
  **"Reference ID: …"** with a **Copy ID** button when present. See `docs/OBSERVABILITY.md`.

## Pipeline filters, activity feed & notifications (Phase 31)
- **Pipeline filters:** `PipelineFilterBar` (`src/components/pipeline/PipelineFilterBar.tsx`) on
  `/portfolio/pipeline` — search / stage / decision label / min score / max risk / owner team /
  include archived — synced to **URL `searchParams`** so views are shareable. Shows `Showing X of Y`
  and a **Clear filters** button.
- **"Recently changed" badge:** Pipeline cards render an amber `Recently changed` chip when
  `pipeline_stage_updated_at` is within the last 7 days (computed client-side, no extra fetch).
- **Activity feed:** route **`/portfolio/activity`** (`PortfolioActivityPage`, lazy; nav **Activity**)
  via `GET /api/v1/portfolio/activity` (filters: type / stage / limit; manual refresh). Items grouped
  by day with project link, activity-type chip, optional stage chip, body excerpt, **Open →** link.
- **Project Home recent panel:** last 3 activity entries from
  `getActivity({ project_id, limit: 3 })`, plus links to Decision history / Pipeline board; empty
  state "No pipeline changes yet." API: `api/pipeline.ts` `getActivity(opts)`,
  `getPipelineBoard(filters)`. See `docs/PIPELINE_ACTIVITY_GUIDE.md`.

## Innovation Pipeline Board (Phase 30)
- Route **`/portfolio/pipeline`** (`PipelineBoardPage`, lazy; nav **Pipeline**) — 12 stage columns
  (new_concept → archived), project cards with decision-board label / score / next action / links to
  Home/Studio/Decision Pack/Briefing/Update Stage. Header **Apply Decision Board** maps board labels
  onto stages (manual stages preserved by default).
- `UpdateStageModal` (`components/pipeline/UpdateStageModal.tsx`): accessible dialog with stage select
  + optional note; saving calls `PATCH /projects/{id}/pipeline-status` and writes a decision-log entry.
- **Project Home** integration: pipeline-stage chip (with source), inferred-stage hint, next action,
  **Update Stage** and **Open Pipeline Board** buttons. **Portfolio Decision Board** adds an *Apply
  labels to Pipeline →* link.
- API: `api/pipeline.ts` → `getPipelineStatus`, `updatePipelineStatus`, `getPipelineBoard`,
  `applyDecisionBoardToPipeline`; `client.ts` gained a `patch` helper. See `docs/PIPELINE_BOARD_GUIDE.md`.

## Portfolio Decision Board (Phase 29)
- Route **`/portfolio/decision-board`** (`PortfolioDecisionBoardPage`, lazy; nav item **Board**;
  linked from Portfolio, Compare, Project Home). Read-only, print/PDF-ready (reuses the Phase-28
  print helpers + CSS). Sections: summary cards, decision table (label filter chips), decision
  buckets, rankings, portfolio recommendation, limitations. Each ready row links to its Decision Pack.
- API: `getDecisionBoard(projectIds?)` / `getDecisionBoardMarkdown()` in `api/portfolio.ts`
  (`GET /portfolio/decision-board[?project_ids=…][/markdown]`). Decision labels: go / validate /
  revise / hold / incomplete. See `docs/PORTFOLIO_DECISION_BOARD.md`.

## Decision Pack & read-only view (Phase 28)
- Route **`/projects/:id/decision-pack`** (`DecisionPackPage`, lazy-loaded): a clean, **read-only**,
  print/PDF-ready document composed from `GET /projects/{id}/decision-pack` (+ `/markdown`). Sections:
  cover/header, recommendation, scorecard, top findings, biggest risks, next best actions, scenario &
  sensitivity snapshot, assumptions & limitations, evidence pack, decision history.
- Reusable helpers in `components/decisionpack/DecisionPackParts.tsx`: `ReadOnlyBadge`, `PrintButton`,
  `DownloadMarkdownButton`, `DownloadJsonButton`, `CopyLinkButton`, `DecisionPackSection`.
- **Print CSS** (`index.css` `@media print`): hides header/nav/footer + `.print-hide` controls, white
  background, page breaks on `.decision-pack-section.page-break`, avoids clipped cards.
- API: `getDecisionPack(id)` / `getDecisionPackMarkdown(id)` in `api/projects.ts`. Linked from Project
  Home, Report, Briefing, Portfolio, Decision History. See `docs/DECISION_PACK_GUIDE.md`.

## Guided Tours & Demo Auto-Play (Phase 27)
- **Tour system** (`src/tours/`): `TourProvider` (wraps the app inside the router; state + route
  navigation + `localStorage` persistence), `TourOverlay` (spotlight ring around `data-tour="…"`
  targets, centered-modal fallback, step card), `useTour()` hook, and `tours.ts` content registry.
- **Tours:** `first_time` (Projects/Samples → Home → Studio → Report/Briefing → Scenario Lab → Data
  Tools) and `studio` (Live/Replay, canvas, timeline, stream, heuristic-edge disclaimer). Studio tour
  launches from the **Tour** button in the Agent Studio header.
- **DemoControlPanel** (`components/DemoControlPanel.tsx`): Start tours, **Play Demo (Quick/Full)**,
  Reset onboarding/tour state, Open Sample Library. Placed in the Layout footer (**Tours & Demo**
  toggle), Sample Library page, and the empty Projects state.
- **Play Demo** loads the RTD-tea sample via `loadSample` (Quick = brief only, Full = run pipeline),
  opens Project Home, and starts the first-time tour. localStorage: `guided_tour_seen`,
  `guided_tour_current_step`, `demo_autoplay_seen`. Keyboard: →/←/Esc. See `docs/GUIDED_TOURS.md`.
- Anchor elements expose `data-tour` keys (`nav-projects`, `nav-samples`, `samples-grid`,
  `data-tools-root`, `studio-root`, `studio-live`, `studio-canvas`, `studio-stream`).

## Onboarding, Samples & Help (Phase 26)
- **Sample Library** route `/samples` (`SampleLibraryPage`, nav item **Samples**) + `/samples/:id`
  (`SampleDetailPage`): cards with search + category filter, **Load as new project** / **Load and run
  pipeline** (`api/samples.ts` → `getSamples`/`getSample`/`loadSample`), then Open Home/Workflow/Studio.
- **OnboardingPanel** on the Projects empty-state: 8-step dismissible checklist persisted via
  `localStorage` (`onboarding_seen`, `last_sample_loaded`). `isOnboardingSeen()` exported.
- **HelpTooltip** (`src/components/HelpTooltip.tsx`): accessible **?** popover (Esc/outside-click to
  close) with a shared `HELP_TEXT` registry; used on Project Home and reusable elsewhere.
- **GlossaryModal** enhanced with search + category tabs (Simulation/Research/Reporting/Operations)
  and inline page links.
- Guided states: Project List empty-state (load sample / import / blank) and Project Home no-brief hint.

## Data Tools (Phase 25)
- Route **`/data-tools`** (`DataToolsPage`, nav item **Data Tools**): export a selected project to
  JSON (or `.zip`), import a bundle (file upload or paste → `importProject`, create-new), and inline
  instructions for backup / reset-demo / prune-logs scripts.
- **Project Home** adds an **Export Project** button (downloads the JSON bundle) and a **Data Tools**
  link. The **Diagnostics** drawer adds an app-log-entry count, a **Download diagnostics snapshot**
  button, and a **Data Tools** link.

## Testing
- **Stack:** Vitest + React Testing Library + jsdom. Run with `npm test` (`vitest run`);
  `npm run test:watch` for watch mode.
- **Setup:** `src/test/setup.ts` wires `@testing-library/jest-dom` matchers and DOM cleanup.
- **Smoke suite** (`src/test/smoke.test.tsx`, 10 tests, no backend required — API modules are
  mocked with `vi.mock`): App renders; Layout nav; ProjectList create UI; Workflow 8 steps;
  Report error state; QA preset questions; Scenario form controls; ErrorState code mapping;
  MetricCard; EvidenceChip.
- TypeScript globals for tests come from `tsconfig.json` `types: ["vitest/globals",
  "@testing-library/jest-dom"]`, so `npm run build` (`tsc --noEmit && vite build`) stays clean.

## Design notes
- Internal-tool aesthetic: cards for metrics, tables for segment maps, chips for evidence and
  scenario deltas. Charts were intentionally skipped in favour of clean tables/cards.
- Raw JSON is not surfaced except the optional markdown panel on the report page and the
  JSON export link.
- The exploratory-decision-support disclaimer appears on the report page, scenario lab, and
  in the global footer. Scenario output explicitly states the baseline is preserved, and
  simulated interview answers are badged "Simulated personas — not real interviews."

## Manual QA checklist
1. Create a project.
2. Submit the sample brief ("Load sample brief" → Submit).
3. Analyze ontology.
4. Generate agents.
5. Run simulation.
6. Generate report → open the report page.
7. Open the Event Explorer → filter by round/segment/action; expand a row; click an agent → drawer.
8. Ask a Q&A question (e.g. "Why is repeat purchase low?") → evidence chips render.
9. Run the 10% price-reduction scenario in the Scenario Lab.
10. View the scenario delta (Baseline | Scenario | Δ table, segment changes, conclusion); compare two scenarios.
11. Reload the report page → baseline report still loads unchanged.

## Known limitations
- No authentication / multi-user workspace (local MVP, by design).
- Smoke tests only (10) — render + mapping coverage, not full interaction flows; no e2e/browser tests.
- Long-running steps (simulation/report) are synchronous calls with a spinner; no progress streaming.
- Charts are not implemented — data is shown as tables/cards.
- The report page renders the structured payload + a raw markdown panel (no markdown→HTML
  renderer, to avoid an extra dependency).
- Event Explorer loads up to 200 events at a time (no pagination UI yet).
