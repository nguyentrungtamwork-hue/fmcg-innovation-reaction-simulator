# TESTING_GUIDE.md

_Current automated testing strategy and what's still missing._

## Backend — pytest (205 tests)
```bash
cd backend && python -m pytest -q
```
Covers every phase end-to-end against an in-process FastAPI `TestClient` with a per-test SQLite
tempfile (schema recreated each test). Deterministic + offline (no LLM, `event_delay_ms=0` for live
streaming). Areas: project/brief/ontology/agents/simulation, report (16 sections + evidence),
Q&A, scenarios + sensitivity, confidence, assumptions, scorecard/portfolio/compare,
snapshots/diff/decision-history/timeline, briefing + briefing-Q&A/tailor/board, studio state,
**live SSE streaming** (lifecycle + persistence parity), **overview + live-run reliability**
(stale/reap/cancel), request-id/error-envelope hardening, deploy-config check, Phase 20
edge cases (brief-only overview, no-event studio, empty compare, idempotent cancel, custom TTL),
and Phase 23 observability (`/readyz`, `/system/status` no-secrets, `/system/diagnostics` counts +
request_id, error-envelope request_id), and **Phase 24 logging** (`test_app_logs.py`: JSON log line
is valid one-line JSON when `LOG_JSON=true`, `AppLogEntry` create + bounded pruning, error responses
persist an `http_error` entry, live-run lifecycle entries, `/system/logs` + `/system/logs/recent-errors`
shape/filtering, diagnostics recent-error summary, and no-secrets in log payloads).

## Frontend — Vitest + React Testing Library + jsdom (57 tests)
```bash
cd frontend && npm test         # vitest run
npm run build                   # tsc --noEmit && vite build (must stay green)
```
`src/test/smoke.test.tsx` mocks all API modules (no backend needed) and a controllable
`EventSource`. Covers: every page renders, the 8-step workflow, report sections, Q&A + evidence
chips, scenario lab + delta, sensitivity, portfolio/compare, snapshots/diff/decisions, briefing
tabs + ask/tailor/board, Agent Studio (replay playback, filters, legend, reduced-motion path),
**live mode** (mocked SSE stream → event cards → completion/disconnect guidance), live run history,
project home + next-step, global jump, glossary open/close (incl. Escape), AgentDrawer Escape, and
**Phase 24 log UI** (Diagnostics "Recent Errors" list + Refresh logs, the "No recent errors" empty
state, and ErrorState's copyable request-id button writing to the clipboard).

## Deterministic principles
- No real network in unit tests; API modules mocked with `vi.mock`.
- No timing-flaky tests — live streaming is driven by a mock `EventSource` the test emits into via
  `act()`, never real timers; backend live tests use `event_delay_ms=0`.

## Frontend E2E — Playwright (opt-in, Phase 21)
An optional browser smoke lives in `frontend/e2e/smoke.spec.ts` (`frontend/playwright.config.ts`).
It is **not** part of `npm test` or default CI — run it deliberately:
```bash
cd frontend
npm install                       # pulls @playwright/test
npx playwright install chromium   # one-time browser download
# in separate terminals: start backend (:8000) and frontend (npm run dev, :5173)
cd backend && python scripts/seed_demo.py --reset-demo   # optional, enables the seeded flow
cd frontend && npm run test:e2e   # or test:e2e:headed / test:e2e:ui
```
Override the target with `E2E_BASE_URL` (e.g. `http://localhost:4173` for `vite preview`).
**Covers:** app shell + Projects/Portfolio/Compare nav links, the skip-to-content link, Glossary
open/Escape-close, Portfolio/Compare routes, and a best-effort seeded flow (Home → Studio → Events →
Report) that **skips gracefully** when no project is seeded.
**Accessibility (axe):** `@axe-core/playwright` runs `wcag2a`/`wcag2aa` checks on the app shell,
Portfolio, the open Glossary dialog, and (seeded) Home + Studio; the assertions **fail only on
`serious`/`critical`** violations (minor/moderate are not gated).
**Does NOT cover:** full live simulation timing, visual regression, or deep multi-page flows.
**Status:** authored + config validated; not executed in the authoring environment (no browser
binaries there). Run locally with the steps above, or via the CI `e2e` job.

## CI
`.github/workflows/ci.yml` has three jobs: **backend** (`pytest`), **frontend** (`npm ci` + `npm test`
+ `npm run build`), and **e2e** (`continue-on-error: true`, non-blocking): it starts uvicorn, seeds a
demo, `vite preview`s the built frontend, installs Playwright chromium, runs `npm run test:e2e`
(Playwright + axe), and uploads the `playwright-report` artifact. E2E is intentionally non-blocking
so a flaky browser run can't fail required CI; promote it to required once proven stable.

## What's still missing (future E2E / a11y)
- Automated axe now runs in the E2E suite (serious/critical gating); still **no visual-regression**
  and no screen-reader audit.
- The E2E job is **non-blocking** in CI until proven stable across several runs.
- No load/perf test harness for very large runs (manual reasoning in `PERFORMANCE_NOTES.md`).
