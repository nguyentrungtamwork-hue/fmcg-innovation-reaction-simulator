# PORTFOLIO_DECISION_BOARD.md

_Phase 29 — a cross-project roll-up that classifies every concept into a transparent decision bucket
and summarizes the portfolio for leadership review. Reuses existing scorecard + briefing
recommendation logic — no new scoring, no LLM, no invented findings, no secrets. Print/PDF-ready._

## What the board does
Answers, across all projects at once: which concepts should **go**, which need **validation**, which
need **revision**, which to **hold**, and which are **incomplete**; plus the top concept, highest-risk
concept, rankings, and a plain-language portfolio recommendation. Suitable for innovation pipeline
meetings, brand/marketing planning, and consumer-insight prioritization.

## Decision labels & how they're assigned
Labels are derived **deterministically** from the existing scorecard via the same
`decide_recommendation_status` logic used by the Briefing, then mapped:

| Recommendation status | Board label | Meaning |
|---|---|---|
| `move_forward` | **go** | Strong overall, medium/high confidence, manageable risk, acceptable repeat. |
| `validate_before_move_forward` | **validate** | Promising but confidence/assumption risk warrants validation first. |
| `revise_and_retest` | **revise** | Clear opportunity offset by weak repeat/claim/price-value or high risk. |
| `hold` | **hold** | Low overall and/or high risk with no strong opportunity. |
| _(no report/scorecard)_ | **incomplete** | Workflow not far enough to compute a recommendation. |

Each item also carries `decision_reason`, `recommended_next_step`, `owner_team` (heuristic from the
top risk: Marketing & Regulatory / Commercial / R&D / Sales & Channel / Consumer Insights),
`confidence_label`, and `risk_level` (high ≥65, medium ≥45, else low).

### Interpreting go / validate / revise / hold
- **Go** → advance to consumer validation / pilot.
- **Validate** → de-risk the key assumptions/claims before committing budget.
- **Revise** → change the concept (formula, price, claim) and re-test.
- **Hold** → park unless materially rethought.
- **Incomplete** → finish the workflow to get a recommendation (the reason names the missing stage).

## Endpoints
- `GET /api/v1/portfolio/decision-board` → `{ generated_at, summary, items[], rankings, portfolio_recommendation, limitations }`.
- `GET /api/v1/portfolio/decision-board/markdown` → copy/paste / print Markdown.
- Optional filter: `?project_ids=a,b,c` includes only those projects.

`summary` has counts per label, `report_ready_projects`, and `top_project` / `highest_risk_project` /
`most_ready_project` / `most_needs_validation_project`. `rankings` (report-ready only): best_overall,
best_trial, best_repeat, lowest_risk, highest_confidence.

## Frontend
Route **`/portfolio/decision-board`** (`PortfolioDecisionBoardPage`, nav item **Board**; linked from
Portfolio, Compare, and Project Home). Sections: header + summary cards, decision table (with label
filter chips), decision buckets, rankings, portfolio recommendation, limitations. Read-only, with
**Print / Save as PDF**, **Download Markdown**, **Download JSON** (reuses the Phase-28 print helpers).
Each ready row links to that project's **Decision Pack**.

## Incomplete / completeness handling
Projects at any stage appear safely: missing brief/ontology/agents/simulation/report all yield an
**incomplete** label with a reason and the exact next step. Incomplete projects are shown on the
board but **excluded from rankings** and the "best/top" picks. The endpoint never crashes on partial
data.

## How to print / save as PDF
Open the board → **Print / Save as PDF**. Print CSS hides nav/footer/buttons, uses a white
background, prints the summary + table cleanly, page-breaks before the rankings, and prints the
disclaimer footer.

## Using it in leadership reviews
1. Ensure the concepts you want compared are report-ready (run their workflows / Play Demo).
2. Open **Board**, scan the summary counts and portfolio recommendation.
3. Walk the table top-down; filter to **go**/**validate** to focus discussion.
4. Click into a concept's **Decision Pack** for the full one-pager.
5. **Print / Save as PDF** for the meeting record.

## Pipeline integration (Phase 30)
The Decision Board feeds the **Innovation Pipeline Board** (`/portfolio/pipeline`). Open the
Pipeline Board from the Decision Board header (**Apply labels to Pipeline →**) and click **Apply
Decision Board** to map labels onto stages (go/validate/revise/hold). Manual stages are preserved
by default. Every change writes a decision-history entry. Full details: `docs/PIPELINE_BOARD_GUIDE.md`.

## What not to overclaim
The board is **heuristic decision-support over simulated outputs** — not a validated market forecast.
Labels reflect modelled reactions, not real sales/scan/social data or real consumers. Incomplete
projects are excluded from rankings. Always validate the leading concepts with real surveys, sensory
tests, and in-market A/B tests before launch decisions.
