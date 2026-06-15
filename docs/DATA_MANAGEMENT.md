# DATA_MANAGEMENT.md

_Phase 25 — local/demo data export, import, backup, reset, and prune tooling. Everything here is
**local-only**: no cloud storage, no auth, no multi-user. Exports never contain secrets (API keys,
raw env, `DATABASE_URL`)._

## Export a project
A project export is a single self-contained JSON bundle.

- **UI:** Project Home → **Export Project**, or the **Data Tools** page (choose project → *Export
  project (JSON)* / *Download .zip*).
- **API:** `GET /api/v1/projects/{id}/export`
  - `format=json|zip` (default `json`)
  - `include_logs=false` (default), `include_events=true`, `include_artifacts=true`

Bundle shape:
```json
{
  "export_version": "1.0",
  "exported_at": "…",
  "app_version": "…",
  "project_id": "…",
  "data": { "project": {…}, "brief": {…}, "ontology": {…}, "agents": [...], "events": [...],
            "reports": [...], "briefings": [...], "briefing_artifacts": [...], "scenarios": [...],
            "snapshots": [...], "decisions": [...], "live_runs": [...] },
  "checksums": { "<section>": "sha256…", "_all": "sha256…" },
  "limitations": [ … ]
}
```

**Included:** project, brief, ontology, agents, events (baseline + scenario), reports, briefings +
briefing artifacts, scenarios, snapshots (with embedded scorecard payload), decision log, live-run
metadata, and — only with `include_logs=true` — that project's app-log slice.
**Excluded:** secrets, API keys, environment values, `DATABASE_URL`, server stack traces.

## Load a sample concept (Phase 26)
The quickest way to get data in is the **Sample Library** (`/samples`, or
`POST /api/v1/system/samples/{id}/load`), which creates a new project from a fictional concept —
optionally running the full deterministic pipeline. See `docs/SAMPLE_LIBRARY_GUIDE.md`.

## Import / restore a project
- **UI:** Data Tools → *Import / restore a project* (upload a `.json` file or paste the bundle).
- **API:** `POST /api/v1/projects/import` with `{ "bundle": {…}, "mode": "create_new",
  "new_project_name": "…", "preserve_original_ids": false }`.

Rules:
- **`create_new` only** — import always creates a brand-new project with freshly generated IDs;
  internal references (event→agent, event→scenario, snapshot→report, decision→snapshot/scenario/report)
  are remapped automatically.
- `overwrite_existing` is intentionally **deferred** (returns `400 import_mode_not_supported`) to
  avoid destructive in-place edits in the MVP.
- Malformed bundles are rejected with `400 invalid_bundle`.

## Delete a project (cascade)
`DELETE /api/v1/projects/{id}` removes the project and all related rows (events, agents, reports,
briefings + artifacts, scenarios, snapshots, decisions, live runs, brief, ontology, and that
project's app logs) in one transaction, returning per-table counts. No orphan rows remain.

## Backup the SQLite database
```bash
cd backend
python scripts/backup_sqlite.py          # backups/fmcg_sim_<timestamp>.db
python scripts/backup_sqlite.py --zip    # compressed .zip
python scripts/backup_sqlite.py --out /path/to/dir
# or:
make backup
```
Safe by default: copies only the DB file (never `.env`/secrets) and exits cleanly if the DB doesn't
exist. Only applies to SQLite — for Postgres use your platform's backup tooling.

## Reset demo data
```bash
cd backend
python scripts/reset_demo_data.py                 # delete "FreshPlus Demo" projects + their data
python scripts/reset_demo_data.py --prefix "Foo"  # custom name prefix
python scripts/reset_demo_data.py --all --yes     # delete EVERY project (destructive; both flags required)
```
API equivalent (demo only): `POST /api/v1/system/reset-demo` — **guarded by `DEMO_MODE=true`**
(returns `403 demo_mode_required` otherwise); deletes only `FreshPlus Demo*` projects.

## Prune the app-log trail
```bash
cd backend
python scripts/prune_app_logs.py                  # prune to APP_LOG_MAX_ENTRIES
python scripts/prune_app_logs.py --max 100
python scripts/prune_app_logs.py --older-than-days 30
```
API equivalent: `POST /api/v1/system/prune-logs` (prunes to the configured cap, returns the number
removed). The trail is already bounded automatically after each insert — this is for manual cleanup.

## SQLite caveats & when to move to Postgres
SQLite is ideal for a single-user local/VPS demo. Export/import is the portable way to move a project
between instances. For **concurrent users, managed hosting with ephemeral disks, or large datasets**,
move to Postgres (see `DEPLOYMENT_OPTIONS.md` Option D) and use database-native backup/restore — the
JSON export/import here stays useful for sharing individual projects.

## Safety summary
- Exports contain **no secrets**.
- Scripts are **safe by default**; destructive actions (`--all`) require explicit confirmation flags.
- `reset-demo` over the API is gated behind `DEMO_MODE`.
- Import is non-destructive (always creates a new project).
- All tools are local/demo only — no cloud, no auth, no multi-user.
