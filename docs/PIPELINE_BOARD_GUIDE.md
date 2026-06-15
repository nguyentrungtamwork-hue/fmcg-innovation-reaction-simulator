# PIPELINE_BOARD_GUIDE.md

_Phase 30 — the Innovation Pipeline Board turns the system from analysis-only into a lightweight
local operating board. Tracks each project's decision/status stage over time. Deterministic, local,
SQLite-friendly, no auth/multi-user. Heuristic decision-support — not a validated market forecast._

## Stages
Twelve ordered stages cover a concept's lifecycle:

| Stage | Label | Meaning |
|---|---|---|
| `new_concept` | New Concept | No brief yet. |
| `brief_submitted` | Brief Submitted | Brief exists; ontology/agents may still be missing. |
| `ready_for_simulation` | Ready for Simulation | Agents generated; simulation not run. |
| `simulated` | Simulated | Simulation events exist; report not yet generated. |
| `report_ready` | Report Ready | Strategic report generated; briefing pending. |
| `briefing_ready` | Briefing Ready | Executive briefing generated. |
| `leadership_review` | Leadership Review | Manual marker — waiting for leadership. |
| `validate` | Validate | Decision Board: validate first. |
| `revise` | Revise | Decision Board: revise & re-test. |
| `go` | Go | Decision Board: advance. |
| `hold` | Hold | Decision Board: hold. |
| `archived` | Archived | Closed; no further action. |

## Inferred stage
When no manual stage is set, the system infers a stage from the workflow state: no brief →
`new_concept`; brief only → `brief_submitted`; agents present, no events → `ready_for_simulation`;
events present, no report → `simulated`; report present, no briefing → `report_ready`; briefing
present → `briefing_ready`. Stages **after** briefing (leadership review / validate / revise / go /
hold / archived) are **not** auto-inferred — they come from a manual change or the Decision Board.

## Decision-Board mapping
`apply-decision-board` maps Decision Board labels onto the pipeline:

| Decision Board label | Pipeline stage |
|---|---|
| `go` | `go` |
| `validate` | `validate` |
| `revise` | `revise` |
| `hold` | `hold` |
| `incomplete` | _not applied_ (inferred stage stands) |

By default, **manual** stages are not overwritten (`only_if_not_manual=true`).

## Manual override
Use **Update Stage** on Project Home or on any Pipeline card to set a stage explicitly. The change
is stored with `pipeline_stage_source="manual"`. Subsequent `apply-decision-board` calls with the
default `only_if_not_manual=true` will skip the project (counted as `skipped_manual`). Pass
`only_if_not_manual=false` to force overwrite (a fresh decision-history entry is still written).

## Stage-change logging
Every change writes a `DecisionLogEntry` so the timeline is auditable.

- **Manual change:** `entry_type="change"`, title `Pipeline stage changed to <Stage>`, body includes
  the previous stage and the optional note, tags `["pipeline", "stage-change", "<stage>"]`.
- **Apply Decision Board:** `entry_type="decision"`, title `Decision Board applied: <Stage>`, body
  records the previous stage and the source label, tags `["pipeline", "decision-board", "<stage>"]`.

These appear on **Decision History** alongside other timeline events.

## Endpoints
- `GET /api/v1/projects/{id}/pipeline-status` — current stage + inferred + decision-board label + recommended next stage + next action.
- `PATCH /api/v1/projects/{id}/pipeline-status` — `{ pipeline_stage, note?, source? }` (default `source="manual"`). Returns updated status. Invalid stage → `422 invalid_stage`.
- `GET /api/v1/portfolio/pipeline` — Kanban view: `columns[]` (each with stage/label/items) + summary counts.
- `POST /api/v1/portfolio/pipeline/apply-decision-board` — `{ project_ids?, only_if_not_manual }`. Returns `{changed, skipped_manual, skipped_no_board, unchanged, changes[]}`.

## Frontend
Route **`/portfolio/pipeline`** (`PipelineBoardPage`, nav item **Pipeline**) renders 12 horizontally
scrollable columns with project cards; each card shows the decision-board label, overall score, top
risk, next recommended action, and links to Home / Studio / Decision Pack / Briefing / Update Stage.
Header buttons: **Apply Decision Board**, **Open Decision Board**, back to **Portfolio**.

**Project Home** shows a Pipeline-Stage row with the current stage chip, source (manual/inferred/
decision_board/system), inferred stage if different, next action, **Update Stage** and **Open
Pipeline Board** buttons.

## Why drag-and-drop is deferred
Drag-and-drop adds noticeable library weight, accessibility burden, and edge cases (mobile, focus,
keyboard reorder, multi-column DnD libraries). Phase 30 ships an explicit **Update Stage** modal
which is simpler, accessible by default, and good enough for a local single-user board. DnD can be
layered on later without changing the data model or endpoints.

## Filters, activity & notification badges (Phase 31)
The Pipeline Board accepts URL-synced filters — `stage`, `decision_label`, `min_score`, `max_risk`,
`owner_team`, `search`, `include_archived` (default true). Cards with a `pipeline_stage_updated_at`
within the last 7 days show a **Recently changed** chip. A separate **Activity** view
(`/portfolio/activity`) groups recent decision-log entries (stage changes, decision-board applies,
snapshots, scenarios, reports, briefings) by day with manual refresh. Project Home has a **Recent
pipeline activity** panel (last 3 entries). No real-time push. Full details:
`docs/PIPELINE_ACTIVITY_GUIDE.md`.

## What not to overclaim
Stages reflect **modelled, exploratory** outputs and your team's manual judgements — they are not
based on real sales/scan/social data or real consumers. The pipeline is local; there is no auth or
multi-user state. Always validate the leading concepts with real surveys, sensory tests, and
in-market A/B tests before launch decisions.
