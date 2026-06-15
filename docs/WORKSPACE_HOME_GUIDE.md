# WORKSPACE_HOME_GUIDE.md

_Phase 19 — Workspace Home, Guided Onboarding & Live-Run Reliability._

## Project Home (`/projects/:id/home`)
One screen that orients you in a project. Powered by `GET /api/v1/projects/{id}/overview` (a
read-only aggregation of existing services).

- **What to do next** — a deterministic widget that reads the project's pipeline state and points to
  the exact next action with a **Go →** button. Rules:
  - no brief → *Submit the innovation brief* (Workflow)
  - brief, no ontology → *Analyze the brief* (Workflow)
  - ontology, no agents → *Generate agents* (Workflow)
  - agents, no simulation → *Run the simulation (try Live Mode)* (Studio)
  - simulation, no report → *Generate the strategic report* (Report)
  - report, no briefing → *Generate the executive briefing* (Briefing)
  - briefing ready → *Explore scenarios / sensitivity / snapshots / compare*
  - a stale live run → *Resolve the stale live run* (Studio) — takes priority.
- **Pipeline status** — badges (Brief → Ontology → Agents → Simulation → Report → Briefing) + counts
  (agents, events, snapshots, scenarios, decisions) + the latest live-run status (with a stale flag).
- **Latest recommendation** — the concept scorecard's overall score, the briefing's recommendation
  status, confidence, top opportunity/risk, and an Open/Generate Briefing CTA.
- **Quick links** — jump to every surface (Workflow, Studio, Events, Report, Briefing, Scenario Lab,
  Sensitivity, Decisions, Portfolio, Compare).
- **Recent activity** — the latest timeline entries (milestones, snapshots, scenarios, decisions).

## Global jump
A small control in the header bar: pick a **project** + **surface** and click **Go** to navigate
anywhere fast (no fuzzy search — just selects).

## Glossary
A **Glossary** link in the footer opens a drawer defining the key terms (also in `docs/GLOSSARY.md`).

## Live-run reliability (recovering stale runs)
Live runs are synchronous inside the streaming request (single-user/local). A run reserved by
`/start` but never streamed — or interrupted — can linger as `running`. Phase 19 adds:
- **Stale detection:** a `running` run with no `last_event_at`/`last_heartbeat_at` activity past its
  TTL (`stale_after_seconds`, default 600) is **stale**. `GET /live-simulation/{run_id}` returns
  `is_stale`, `can_cancel`, `can_replay_persisted_events`, and a `stream_url` (only while genuinely
  running).
- **Auto-reap:** starting a new live run first marks stale running runs as `failed`
  ("Live run marked stale because no stream activity was detected"), so a stuck run never blocks you.
- **Cancel:** `POST /live-simulation/{run_id}/cancel` marks a pending/running run `cancelled` without
  deleting persisted events; calling it on a finished run is safe.
- **Live Run History** (Studio → Live Mode): lists recent runs with status/stale flag/event count,
  plus Cancel and Open-replay actions, and a banner to "Mark stale / cancel" when a stuck run exists.

### Known limitation
Cancel is **status-level only** — it flips the run's status; it does not forcibly interrupt an
in-flight generator mid-stream (the synchronous stream finishes its current request). For true
mid-run cancellation / long runs, move to background jobs (out of scope; see `DEPLOYMENT_OPTIONS.md`).
