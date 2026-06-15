# OBSERVABILITY.md

_Phase 23 — operational visibility for local/demo runs. Everything here is read-only and
**never exposes secrets** (no API keys, no raw env, no `DATABASE_URL`)._

## Health vs readiness
- **`GET /healthz`** — liveness: the process is up. `{status, app, version, llm_configured}`.
- **`GET /readyz`** — readiness: the app is up **and** the DB is reachable + core tables accessible.
  `{ status: "ready"|"degraded", database:{connected,type,checks[]}, app:{version,environment,demo_mode} }`.
  Use `/healthz` for "is it alive?", `/readyz` for "can it serve requests?" (load balancers / demos).

## System status vs diagnostics (both under `/api/v1/system`)
- **`GET /system/status`** — safe config for the UI badge: `app_name, version, environment,
  demo_mode, llm_configured, database` + `database_type, frontend_origin_configured,
  live_streaming_supported, e2e_configured`. No counts, no secrets.
- **`GET /system/diagnostics`** — safe operational snapshot: `{ status, request_id, app{…},
  database{connected, project_count, event_count, live_run_count}, features{…}, warnings[] }`.
  `warnings` flags non-fatal conditions (e.g. `llm_not_configured_using_deterministic_fallback`).

## Request IDs & logging
- Every response carries an **`X-Request-ID`** header (echoed if the client sends one).
- Error envelopes include it: `{"detail": {"code", "message?", "request_id"}}`.
- Structured access logs (one line per request) include `method`, `path`, `status_code`,
  `duration_ms`, `request_id`; unhandled exceptions log the same `request_id` + traceback
  (server-side only — never returned to the client).

## JSON structured logging (Phase 24)
Set **`LOG_JSON=true`** to emit logs as single-line JSON (default `false` keeps the readable
`key=value` format). When enabled:
- **Access** lines: `{timestamp, level, event_type:"http_request", request_id, method, path,
  status_code, duration_ms, client_ip, user_agent, error_code}`.
- **Exception** lines: `{timestamp, level, event_type:"exception", request_id, path, method,
  error_code, error_message, exception_type}`.
Each line is valid one-line JSON suitable for a log shipper. Secrets, API keys, env values and
request bodies are never logged.

## Persistent app-log trail (Phase 24)
Notable events are persisted to a **bounded** `app_log_entries` SQLite table (default 500 rows,
configurable via `APP_LOG_MAX_ENTRIES`; oldest pruned after each insert). Only meaningful events are
stored — **not** every successful request. Event types: `http_error`, `exception`,
`live_run_started/completed/failed`, `report_generated`, `briefing_generated`, `scenario_created`,
`system_warning`. Each row keeps `id, timestamp, level, event_type, request_id, project_id?, run_id?,
scenario_id?, path?, method?, status_code?, code?, message, metadata`.

Read it back (read-only, no secrets):
- **`GET /system/logs`** — query `level, event_type, request_id, project_id, limit` (default 50,
  max 200) → `{ items[], total_returned, limit }`.
- **`GET /system/logs/recent-errors`** — last 10 entries at `error`/`warning` level.

`GET /system/diagnostics` also surfaces `recent_error_count`, `recent_warning_count`, `last_error`,
`log_retention_limit`, and `database.app_log_count`. Manual cleanup: `POST /system/prune-logs` (or
`python scripts/prune_app_logs.py`). See `docs/DATA_MANAGEMENT.md` for export/backup/reset tooling.

## Frontend Diagnostics panel
A footer **Diagnostics** link opens a read-only drawer that calls `/system/status`, `/readyz`,
`/system/diagnostics`, and `/system/logs/recent-errors` and shows: backend connected, readiness,
version, environment, demo mode, LLM mode, database type, live-streaming support,
project/event/live-run counts, the last `request_id`, any warnings, and a **Retry status check**
button. A **Recent Errors** section lists the latest error/warning entries (with a **Refresh logs**
button, a per-entry **Copy ID** button for the `request_id`, and a **"No recent errors"** empty
state). It's a developer/demo helper, kept low-profile.

## Frontend error recovery
- A global **ErrorBoundary** wraps the routed content: a page-level render crash shows a friendly
  "Something went wrong while rendering this page" fallback with **Retry** + **Go home** (stack trace
  only in dev). It does not catch async/API errors — those flow through `ErrorState`.
- `ErrorState` shows **"Reference ID: …"** when the API error carried a `request_id` (captured
  from the error body or the `X-Request-ID` header), with a **Copy ID** button, plus an optional
  **Retry** button.

## Debugging a demo error
1. Reproduce; note the **Reference ID** shown in the error (or the `X-Request-ID` response header).
2. Grep the backend logs for that `request_id` to find the matching access line + traceback.
3. Open the **Diagnostics** drawer to confirm backend readiness, DB connectivity, counts, warnings.
4. If the backend is unreachable, the offline banner / Diagnostics will say so — start it or check
   `VITE_API_BASE_URL`.

## Intentionally NOT exposed
API keys / `OPENAI_API_KEY`, raw environment variables, `DATABASE_URL`, secrets of any kind, and
server stack traces (logged server-side only). Tests assert the status/diagnostics payloads contain
none of these.

## Operational limitations
- Logging is stdlib `logging` to stdout (readable or `LOG_JSON=true`) — no external APM / log shipper
  integration (Sentry/Datadog/OpenTelemetry are out of scope).
- The persistent app-log trail is a small bounded SQLite table for local triage, not a log store;
  old rows are pruned past `APP_LOG_MAX_ENTRIES`.
- Single-process, single-user, SQLite; live runs are synchronous (see `DEPLOYMENT_OPTIONS.md`).
- No metrics endpoint (Prometheus) or tracing — out of scope for the MVP.
