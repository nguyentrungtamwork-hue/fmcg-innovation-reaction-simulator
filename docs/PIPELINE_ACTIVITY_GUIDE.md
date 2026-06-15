# PIPELINE_ACTIVITY_GUIDE.md

_Phase 31 — cross-project activity feed, stage-change notifications, and URL-based filters on the
Innovation Pipeline Board. Read-only, deterministic, local-only. No real-time notifications, no auth,
no multi-user. Notification badges are computed from existing data, not pushed._

## What the activity feed shows
The portfolio activity feed is a single chronological view of recent **DecisionLogEntry** rows
across all projects, projected into an activity-shaped item:

| Field | Meaning |
|---|---|
| `id` | The underlying decision-log entry id. |
| `timestamp` | When it was written (ISO 8601). |
| `project_id`, `project_name` | Which project it belongs to. |
| `activity_type` | `stage_change`, `decision`, `snapshot`, `scenario`, `report`, `briefing`. |
| `title`, `description` | Human-friendly summary (decision-log title + body excerpt). |
| `stage` | The pipeline stage tagged on the entry, if any (e.g. `validate`). |
| `tags` | The raw tag list from the entry. |
| `related_url` | Best in-app destination (Decision History, Snapshot Diff, Report, Scenario Lab, or Home). |

`activity_type` is derived from tags first (`stage-change` → `stage_change`,
`decision-board` → `decision`), falling back to the entry's `entry_type`.

## Where activity entries come from
- **Manual stage updates** (`PATCH /projects/{id}/pipeline-status`) write
  `entry_type="change"`, tags `["pipeline","stage-change","<stage>"]`, body recording previous → new
  stage + optional note.
- **Apply Decision Board** (`POST /portfolio/pipeline/apply-decision-board`) writes
  `entry_type="decision"`, tags `["pipeline","decision-board","<stage>"]`, body noting the source label.
- **Pre-existing decision-log entries** (snapshots, scenarios, manual notes) are also surfaced.

The feed does not write any new data — it reads from the existing decision log.

## Endpoints
- `GET /api/v1/portfolio/activity` — recent cross-project entries.
  Query params: `event_type` (e.g. `stage_change`), `project_id`, `stage`, `limit` (default 30, max 100).
  Response: `{ items[], total_returned }`.

- `GET /api/v1/portfolio/pipeline` — now accepts filters:
  `stage`, `decision_label`, `min_score`, `max_risk`, `owner_team`, `search`, `include_archived`.
  Filters are evaluated against each pipeline card; `summary.total_projects` is the **filtered**
  count and `summary.total_projects_unfiltered` is the total across the portfolio.

## Pipeline filters (URL-shareable)
The Pipeline Board page renders a `PipelineFilterBar` synced to URL `searchParams`:

| Filter | URL key | Notes |
|---|---|---|
| Search | `search` | Substring match (case-insensitive) over project_name, top_risk, owner_team, decision_label, stage. |
| Stage | `stage` | One of the 12 pipeline stages. |
| Decision label | `decision_label` | `go`, `validate`, `revise`, `hold`, `incomplete`. |
| Min score | `min_score` | Filters out cards whose `overall_score` is below this. |
| Max risk | `max_risk` | Filters out cards whose `risk_score` exceeds this. |
| Owner team | `owner_team` | Exact match (case-insensitive). |
| Include archived | `include_archived=false` | Default is `true`. |

The current URL is the share URL — copy and send. **Clear filters** resets to `/portfolio/pipeline`
with no params.

## "Recently changed" badge
A `Recently changed` chip appears on Pipeline Board cards when
`pipeline_stage_updated_at` is within the last **7 days** (computed in the browser from the
timestamp the backend returns; no extra request). This is a **soft notification badge**, not a push
notification — it's a hint, not an alert.

## Project Home — recent pipeline activity
Project Home shows a **Recent pipeline activity** panel with the last **3** entries from
`GET /portfolio/activity?project_id={id}&limit=3` (title, timestamp, body excerpt, stage chip), plus
links to **Decision history** and **Pipeline board**. Empty state: *"No pipeline changes yet."*

## Portfolio Activity page
Route **`/portfolio/activity`** (`PortfolioActivityPage`, nav **Activity**). Header has type/stage/limit
filters and a **Refresh** button (manual; no polling). Entries are grouped by day. Each item shows
the activity-type chip, optional stage chip, project link, timestamp, title, description, and an
**Open →** link to the related surface.

## Why notifications are not real-time
This is a local single-user MVP. Real-time push needs server-side fan-out (WebSocket/SSE), per-user
state, and read/unread tracking — all of which need auth and persistence beyond the MVP's scope. The
"Recently changed" badge + manual **Refresh** cover the demo / local-team use case without that
complexity.

## Using filters in review meetings
- "What needs validation?" → set Stage = **Validate** (or Decision label = `validate`).
- "What might we ship?" → set Stage = **Go** and Min score = 60.
- "What's high-risk?" → set Max risk = 70.
- "Anything moved in the last week?" → look for **Recently changed** badges, or open **Activity**
  and filter Type = `stage_change`.

Share the URL with teammates so everyone sees the same view.

## What not to overclaim
Activity reflects modelled simulation outputs and your team's manual judgments — not real consumer
behavior. Filtered views are presentation aids, not validated market segments. Always validate the
leading concept with real research before launch commitments.
