# LIVE_STREAMING_GUIDE.md

_Phase 18 — Live Simulation Streaming (SSE)._

The Agent Studio now has two modes:
- **Replay Mode** — animates the **already-persisted** simulation events client-side (Phases 16–17).
- **Live Mode** — starts a new simulation and **streams each event over SSE** as the backend
  generates and persists it.

Both visualize the **same deterministic engine**; Live mode just shows generation as it happens.

## How SSE works here
1. `POST /api/v1/projects/{id}/live-simulation/start` validates preconditions, (optionally) resets
   the baseline, creates a `LiveSimulationRun` (status `running`), and returns `{run_id, stream_url}`.
2. The browser opens an `EventSource` to
   `GET /api/v1/projects/{id}/live-simulation/{run_id}/stream`.
3. The backend streams `text/event-stream` frames (`event: <type>\ndata: <json>\n\n`) as it runs the
   6-round loop, persisting each `Event` (`run_type="baseline"`) before emitting `event_generated`.
4. On completion it persists agent memory/action history, marks the run `completed`, and emits
   `run_completed`.

`event_delay_ms` (0–2000, default 120) paces the stream for a watchable demo; tests use `0`.

## Stream event types
`run_started`, `round_started`, `agent_started`, `event_generated`, `agent_memory_updated`,
`market_actor_event_generated`, `round_completed`, `run_completed`, `run_failed`, `heartbeat`.
Every message carries `{run_id, project_id, type, timestamp, sequence, round_number, stage_name,
progress{round, rounds_total, events_emitted, events_expected, percent}, payload}`.

## What is persisted
Streamed events are **identical** to a normal run: same scoring (`score_round` /
`market_actor_action`), same agent ordering and seed, `run_type="baseline"`. After `run_completed`:
`GET /events`, `/studio/state`, report generation, Q&A, briefing, scenarios, and portfolio all work
exactly as with the sync `POST /simulate`. (Determinism guarantees the persisted set matches the
sync path for the same seed.)

## What happens on failure / disconnect
- On a backend error mid-run: the run row becomes `failed` with an `error_message`, the stream emits
  `run_failed`, and any **already-committed round events remain** (no partial rollback).
- If the browser loses the connection: the UI shows a disconnect hint and you can switch to
  **Replay Mode** to view whatever persisted, or start again.
- Concurrency: a second `start` while one is `running` returns `409 live_run_already_running`.

## Preconditions (errors)
`404 project_not_found`; `409 brief_required` / `ontology_required` / `agents_required`;
`409 simulation_exists` (baseline exists and `force_rerun=false`); `409 live_run_already_running`.
With `force_rerun=true` the baseline events + agent memory are cleared before streaming.

## Deployment caveats
- **No proxy buffering.** Reverse proxies must not buffer SSE. The backend already sends
  `Cache-Control: no-cache` and `X-Accel-Buffering: no`. For nginx in front of the API add
  `proxy_buffering off;` on the API location. (The bundled frontend nginx serves static files only
  and does not proxy the API.)
- **Split hosting:** the browser's `EventSource` connects to the backend stream URL
  (`VITE_API_BASE_URL`), so the backend CORS allowlist must include the frontend origin
  (`FRONTEND_ORIGIN`).
- **Request timeouts:** managed platforms (Render/Railway/Vercel) may cap long requests. Keep
  `event_delay_ms` modest and rounds ≤6 for demos; a long stream may hit platform limits.
- **Production:** move live runs to background jobs + Redis/pub-sub or a WebSocket gateway. Out of
  scope here.

## Why WebSocket is deferred
The stream is **one-way backend → frontend**, which SSE handles simply and reliably with the native
`EventSource` (auto-reconnect, no extra deps). WebSocket adds bidirectional complexity we don't need
for baseline streaming, so it's documented as an optional future upgrade.

## Reliability: stale runs (Phase 19)
A `running` run with no `last_event_at`/`last_heartbeat_at` activity past its TTL
(`stale_after_seconds`, default 600s) is **stale**. Starting a new run **auto-reaps** stale runs
(marks them `failed`), so a stuck run never blocks you; you can also **cancel** any pending/running
run (status-level — persisted events are kept). `GET /{run_id}` exposes `is_stale`, `can_cancel`,
`can_replay_persisted_events`, and a `stream_url` (only while genuinely running). The Studio's **Live
Run History** panel surfaces all of this. See `docs/WORKSPACE_HOME_GUIDE.md`.

## Accessibility & performance (Phase 20)
Live status + progress are in an `aria-live="polite"` region; the active-agent pulse respects
`prefers-reduced-motion`. The event stream is capped (selectable 40/100/200) for performance while
**metrics use the full revealed set**. Disconnect/failure shows clear retry / replay-persisted-events
guidance.

## How to demo Live Mode
1. Open **Studio** for a project that has agents (or use the guided steps to get there).
2. Switch to **Live Mode** → set rounds/seed/delay → **Start Live Simulation**.
3. Watch rounds begin, the active agent pulse on the canvas, event cards stream in, and the metric
   strip + progress bar update live.
4. On completion, click **Generate Report** or **Replay saved events**.

> The visualization shows simulated reactions; interaction edges remain heuristic aids, not real
> conversations. Output is exploratory decision support, not a forecast.
