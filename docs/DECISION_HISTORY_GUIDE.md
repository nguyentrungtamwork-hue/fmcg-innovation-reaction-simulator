# DECISION_HISTORY_GUIDE.md

_Phase 13 — Snapshot Diff & Decision History._

Makes the portfolio's snapshots actionable over time: diff two report versions, see how a concept
drifted since a decision was made, and keep a per-project decision log + timeline for stakeholder
traceability. Deterministic and explainable — **no LLM is used for diffing**.

## Snapshot diff
- **API:** `POST /api/v1/projects/{id}/snapshots/diff` with `{ "left": {...}, "right": {...} }`, where
  each side is `{ "type": "active_report" }` or `{ "type": "snapshot", "snapshot_id": "..." }`.
- **Returns:** `scorecard_delta` (per-dimension left/right/delta), `dimension_changes`
  (direction + interpretation; risk dimensions count *down* as improvement), `changed_sections`
  (which report sections changed), `recommendation_changes`, `risk_changes`
  (reduced/removed vs new/increased), `segment_changes`, a `plain_english_summary`, and a
  `decision_implication`.
- **Preconditions:** `404 project_not_found`; `409 report_required` (active side with no report);
  `404 snapshot_not_found`; `400 invalid_diff_request` (e.g. a snapshot side with no id).
- **UI:** `/projects/:id/snapshots/diff` — pick left/right, Compare, see delta cards, a
  `MiniBarChart` of dimension magnitudes, changed sections, risk changes, recommendation changes,
  and segment deltas. "Create decision log from this diff" writes a `change` entry.

## How to read scorecard deltas
- For normal dimensions (trial, repeat, sentiment, advocacy, claim credibility, channel fit,
  confidence, overall): **higher is better** → a positive delta = improved (green).
- For **risk dimensions** (risk, assumption risk, sensitivity risk): **lower is better** → a
  negative delta = improved. The UI labels these with `↓` and inverts the tone accordingly.
- Identical versions produce **all-zero deltas** — a useful sanity check.

## Drift indicator
- On the Report page, a banner shows how the **active report** differs from the **latest snapshot**
  ("Current report is +X overall vs latest snapshot 'v1'. Largest movement: repeat (+8.2)."), with a
  link to the full diff. It is silent when no snapshots exist.

## Decision log
- **API:** `POST/GET/DELETE /api/v1/projects/{id}/decisions[/{entry_id}]`. Each entry has an
  `entry_type` (note / decision / change / meeting / validation_result / auto types), title, body,
  optional related snapshot/scenario/report ids, and tags.
- Creating a snapshot **auto-logs** a `snapshot_created` entry for traceability.
- **UI:** `/projects/:id/decisions` — add notes/decisions with tags and an optional related snapshot.

## Timeline
- **API:** `GET /api/v1/projects/{id}/timeline` merges lifecycle milestones (project, brief,
  ontology, agents, simulation, report), snapshots, scenarios, and decision-log entries into one
  chronological list. Read-only, derived from existing rows.
- **UI:** the Decision history page renders the timeline with icons next to your editable entries.

## Presenting version changes to stakeholders
1. Open the leading concept's **Report** → the **drift banner** shows movement since the decision of record.
2. Open **Snapshot diff** → walk the plain-English summary, the dimension deltas, and risk changes.
3. Log the decision ("Proceed to consumer validation; repeat risk requires sensory test") — it lands on the **timeline**.
4. Use the timeline to show the full decision trail in a review.

## What this does NOT prove
- A positive diff means the **simulated, deterministic** scorecard improved — **not** that real
  market performance improved.
- Diffs and the decision log are traceability and decision-support aids; they are **not** evidence
  of real consumer behavior.
- Always validate the leading concept with real research (concept tests, sensory tests, in-market
  A/B tests) before launch commitments.

## Pipeline stage-change entries (Phase 30)
The Innovation Pipeline Board writes a decision-log entry on every stage change so the timeline is
auditable:
- Manual updates → `entry_type="change"`, title `Pipeline stage changed to <Stage>`, body records the
  previous stage and your optional note; tags `["pipeline", "stage-change", "<stage>"]`.
- Applying the Decision Board → `entry_type="decision"`, title `Decision Board applied: <Stage>`,
  body records the source label; tags `["pipeline", "decision-board", "<stage>"]`.

These appear alongside other timeline events on Decision History. See `docs/PIPELINE_BOARD_GUIDE.md`.

## Cross-project activity feed (Phase 31)
The decision log also powers a cross-project **Portfolio Activity** view
(`GET /api/v1/portfolio/activity` → `/portfolio/activity` page) that aggregates recent entries from
all projects into a single chronological feed (filters: `event_type`, `project_id`, `stage`,
`limit`). Pipeline stage changes appear as `activity_type=stage_change`; apply-decision-board
changes as `decision`. Project Home shows the latest 3 entries inline. See
`docs/PIPELINE_ACTIVITY_GUIDE.md`.
