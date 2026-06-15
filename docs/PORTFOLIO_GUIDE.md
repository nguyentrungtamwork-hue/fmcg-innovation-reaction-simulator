# PORTFOLIO_GUIDE.md

_Phase 12 — Comparative Studies & Portfolio View._

Turns the single-project simulator into a lightweight **innovation portfolio** tool: score each
concept, snapshot decisions over time, compare concepts side by side, and export a shareable
scorecard. Everything is derived from existing report/ontology/confidence/assumptions data — no
new simulation logic, nothing about performance is invented.

## Concept scorecard
- **API:** `GET /api/v1/projects/{id}/scorecard` (and `/snapshots/{sid}/scorecard`).
- A transparent 0–100 heuristic combining trial, repeat, sentiment, advocacy, claim credibility,
  channel fit, and confidence (positives) minus risk, assumption risk, and sensitivity risk
  (negatives). Exact weights + sub-score sources are in `docs/SCORING_LOGIC.md`.
- Every scorecard prints its `ranking_explanation` (the weighted terms) and a disclaimer:
  *"This scorecard is a decision-support heuristic, not a validated market forecast."*
- **Export:** `GET /scorecard/export?format=json|markdown` (UI buttons on the Report page).

## Snapshots (versioning)
- **Why:** a project changes (claim, price, packaging, scenario, regenerated report). Save a named
  snapshot to freeze the current report + scorecard before changing assumptions.
- **API:** `POST/GET/DELETE /api/v1/projects/{id}/snapshots[/{sid}]`. Snapshots are **read-only**
  and **immutable** — regenerating the active report never alters an existing snapshot.
- **UI:** the Report page "Concept scorecard & snapshots" panel: create/list/view/delete, and
  download a snapshot's Markdown/JSON.

## Portfolio dashboard
- **API:** `GET /api/v1/portfolio` → every project with its scorecard columns + a summary
  (top concept, highest risk, best trial/repeat).
- **UI:** `/portfolio` — sortable, filterable table (sort by overall/trial/repeat/risk/confidence;
  filter report-ready / high-risk / low-confidence / needs-validation). Click a row to open it.

## Comparison
- **API:** `POST /api/v1/portfolio/compare` with `project_ids` (and optional `snapshot_ids`).
  Returns per-item scorecards, a `comparison_summary` (best overall/trial/repeat, lowest risk,
  highest confidence, most-needs-validation), `dimension_rankings`, and a `recommendation`.
- **UI:** `/compare` — pick 2–5 report-ready concepts → side-by-side dimension table (best value per
  row highlighted) + scorecard cards + a recommendation.

## What the ranking means — and does NOT mean
- ✅ A **fast, transparent way to triage** which concept to move to consumer testing first.
- ✅ Grounded entirely in the simulator's own (deterministic) outputs and clearly explained.
- ❌ **Not** a validated demand/sales forecast; the `real_world_data` confidence factor is capped
  precisely because no real sales/social data informs it.
- ❌ **Not** a substitute for concept tests, sensory tests, or in-market A/B tests.

## Presenting to stakeholders
1. Open `/portfolio`, sort by overall score — "here's the heuristic ranking of our concepts."
2. Open `/compare` on the top 2–3 — show the dimension table and the recommendation.
3. For the leading concept, open its Report → Confidence + Assumptions → snapshot it as the decision
   of record, and export the scorecard to share.
4. Always close with: *"This prioritizes where to spend real research, it doesn't replace it."*

> Next step over time: use **snapshot diff + decision history** (Phase 13) to track how a concept
> changed since the decision of record. See `docs/DECISION_HISTORY_GUIDE.md`.

## Portfolio Decision Board (Phase 29)
For a leadership roll-up across all concepts, open the **Decision Board** (`/portfolio/decision-board`,
or Portfolio → **Decision Board →**). It classifies every project **go / validate / revise / hold /
incomplete** (deterministically, reusing the scorecard + briefing recommendation logic), with summary
counts, rankings, a portfolio recommendation, per-project Decision Pack links, and print/PDF export.
Incomplete projects appear but are excluded from rankings. See `docs/PORTFOLIO_DECISION_BOARD.md`.
