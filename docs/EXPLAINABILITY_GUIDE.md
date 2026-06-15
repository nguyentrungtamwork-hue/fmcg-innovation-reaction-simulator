# EXPLAINABILITY_GUIDE.md

_Phase 11 — Insight Depth & Trust: how to read and demo the explainability features._

These features deepen **trust** in the simulator's output without changing the core scoring
engine. Everything here is still **exploratory decision support**, not a validated forecast.

## 1. Sensitivity sweeps — "how responsive is the launch?"
- **What it is:** for each lever (price, sampling, social proof, claim credibility, promotion,
  packaging, sensory risk, retailer support, competitor pressure) the system re-runs the
  deterministic 6-round simulation at several lever values and reports the **response curve** of
  trial / repeat / sentiment / recommend / complaint.
- **API:** `POST /api/v1/projects/{id}/sensitivity` (default levers if none supplied). Sweep runs
  use the scenario engine, then their events are deleted — the **baseline is never touched**.
- **How to read it:**
  - The **response curve** (line chart) shows trial probability vs lever value.
  - **best_point** = highest trial in the swept range; **diminishing_return_point** = where extra
    investment stops paying off (marginal gain drops below ⅓ of the first step's gain).
  - **strategic_read** / **overall_recommendation** name the most responsive lever to test first.
- **What it is NOT:** the levers are additive nudges on a rule engine, *not* calibrated demand
  elasticities. Treat magnitudes as relative, directional signals.

## 2. Confidence calibration — "how much should I trust this?"
- **API:** `GET /api/v1/projects/{id}/confidence` → an `overall_confidence` (0–1) + label, plus a
  breakdown of weighted **drivers** (data coverage + grounding quality), **risks**, and **how to
  improve**. See `docs/SCORING_LOGIC.md` for the exact formula.
- **How to read it:** the gauge is an *internal data-coverage* score. The `real_world_data` driver
  is fixed at 0.3 because no real sales/social data informs the model — so confidence is
  structurally capped. High confidence means "well-covered and internally consistent," **not**
  "validated against the market."

## 3. Assumptions ledger — "what are we taking for granted?"
- **API:** `GET /api/v1/projects/{id}/assumptions` consolidates: modelling-method caveats, missing
  real data, simulated personas, scenario/sensitivity caveats, ontology `missing_information` +
  `market_assumptions`, and report limitations. Each item has an **impact** (high/medium/low) and a
  **recommended validation** step. Exportable as JSON from the Report page.
- **Use it** to frame the demo honestly: "here's exactly what we assumed and what still needs real
  research before a launch decision."

## 4. Evidence drill-down — "show me the proof"
- Report trigger/barrier evidence chips and Q&A evidence chips are **clickable**:
  - **Open event →** jumps to the Event Explorer pre-filtered (`?event_id=…&round_number=…` or
    `?agent_id=…`).
  - **Open agent →** opens the Agent Drawer (`?agent_id=…&open_agent=1`) with the agent's traits,
    memory, and action history.
- This lets you trace any headline number back to the specific simulated reactions behind it.

## Demo tips
- Start from the **Report** → open the **Confidence** panel (set expectations on trust), scan the
  **Assumptions ledger** (honesty), click a barrier **evidence chip → Open event/agent** (proof),
  then open **Sensitivity** to show which lever to pull first. Close by reminding the audience this
  is decision-support to *prioritize real research*, not replace it.
