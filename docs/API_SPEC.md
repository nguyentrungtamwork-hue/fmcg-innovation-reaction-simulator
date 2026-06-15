# API_SPEC.md

Base URL: `http://localhost:8000/api/v1`
Auth: none (local MVP). All endpoints return JSON unless noted.

## Conventions
- IDs are UUIDv4 strings.
- Timestamps are ISO-8601 UTC.
- Errors: `{ "error": { "code": "...", "message": "..." } }` with appropriate HTTP status.
- Long-running endpoints return `202 Accepted` with a `job_id`; clients poll the resource GET to check completion. MVP may run synchronously and return `200` directly; the schema is forward-compatible.

---

## Projects

### `POST /projects`
Create a project.
**Body:**
```json
{ "name": "FreshPlus Low-Sugar Tea Launch", "category": "Ready-to-drink tea", "market": "VN" }
```
**Response 201:**
```json
{ "id": "uuid", "name": "...", "category": "...", "market": "...", "status": "created", "created_at": "..." }
```

### `GET /projects/{id}`
Returns the full project state envelope: status, brief presence, ontology presence, agents count, events count, report presence.

### `GET /projects`
List projects (id, name, status, created_at).

---

## Brief

### `POST /projects/{id}/brief`
Upload or submit the innovation brief. Accepts either:
- JSON body with structured fields (brand, product_name, claims[], price, channels[], ...).
- `multipart/form-data` with a `.md`, `.txt`, or `.pdf` file under `file`.

**Response 200:** `{ "brief_id": "uuid", "stored": true, "field_count": N }`

---

## Ontology

### `POST /projects/{id}/analyze`
Run ontology extraction over the stored brief.
**Response 200:**
```json
{
  "ontology_id": "uuid",
  "entities": [{ "type": "Brand", "name": "FreshPlus", "attributes": {...} }, ...],
  "relationships": [{ "from": "...", "to": "...", "type": "CLAIMS_TO_SOLVE" }, ...],
  "assumptions": ["Target audience inferred as urban 22–35"],
  "missing_information": ["No sampling plan provided"]
}
```

### `GET /projects/{id}/ontology`
Return the stored ontology JSON. Returns 404 if `analyze` has not been run yet.

The returned payload includes, in addition to `entities` and `relationships`:
`market_assumptions`, `missing_information`, `risk_signals`, `purchase_triggers`,
`adoption_barriers`, `claim_analysis`, `channel_analysis`, `claim_clarity_issues`,
`claim_credibility_risks`, `price_value_concerns`, `channel_fit_observations`,
`social_diffusion_potential`, `competitor_pressure_points`, plus
`source_mode` (`llm` | `fallback`) and `confidence_score`.

Re-running `POST /projects/{id}/analyze` **replaces** any existing ontology for
the project (delete-and-insert). Only one ontology is stored per project.

---

## Agents

### `POST /projects/{id}/agents/generate`
**Body (optional overrides):**
```json
{ "num_consumers": 50, "segments": ["early_adopter", "value_seeker", "health_conscious", "convenience", "brand_loyal"], "include_market_actors": true }
```
**Response 200:** `{ "agents_generated": 55, "consumers": 50, "market_actors": 5 }`

### `GET /projects/{id}/agents`
**Query:** `?agent_type=consumer|market_actor&segment_name=...&role=...`
Returns array of agent profiles (full profile JSON + memory). 404 if project missing.

### `GET /projects/{id}/agents/summary`
Returns aggregate stats:
```
{
  "total_agents", "consumer_agents", "market_actor_agents",
  "segment_distribution": { "<segment>": N, ... },
  "average_trait_scores": { "<trait>": float, ... },
  "top_trial_barriers": [["barrier", count], ...],
  "top_trust_drivers":  [["driver",  count], ...],
  "top_channel_preferences": [["channel", count], ...]
}
```

### `GET /projects/{id}/agents/{agent_id}`
Single agent including profile + initial memory. 404 if not found.

**`POST /projects/{id}/agents/generate` semantics (Phase 4 live):**
- 404 if project missing.
- 409 (`ontology_required`) if `analyze` hasn't been run.
- Body (optional): `{ "consumer_count": 50, "include_market_actors": true, "segment_distribution": null, "force_regenerate": true, "seed": 42 }`.
- Default: 50 consumers across 8 segments + 5 market actors (Retailer, Competitor, Influencer, SocialCommunity, CategoryExpert).
- `force_regenerate=true` (default) deletes existing agents before insert — no duplication on rerun.
- Returns `AgentGenerateOut`: total / consumer / market-actor counts, segment distribution, source_mode (`llm` | `fallback`).

---

## Simulation _(live — Phase 5)_

The engine runs a 6-round FMCG launch funnel — Round 1 Pre-launch concept → 2 Launch
communication → 3 Shelf / e-commerce → 4 Trial decision → 5 Post-trial → 6 Social diffusion.
Every consumer agent is scored and acts each round (one `Event` per agent per round); each
market actor takes one structured action per round grounded in that round's aggregated consumer
signal. Scoring is **deterministic given the seed** (LLM-first with deterministic fallback;
fallback is always used in Phase 5). 50 consumers + 5 market actors × 6 rounds = **330 events**.

### `POST /projects/{id}/simulate`
**Body (optional):**
```json
{ "rounds": 6, "deterministic": true, "seed": 42, "include_market_actors": true, "force_rerun": true }
```
- `force_rerun=true` (default) deletes prior events and resets each agent's
  `action_history` / `simulation_memory` before the run — no accumulation across reruns.
- `include_market_actors=false` runs consumers only (0 market-actor events).

**Response 200 (`SimulationRunOut`):**
```json
{
  "simulation_status": "completed",
  "source_mode": "fallback",
  "rounds_run": 6,
  "total_events": 330,
  "consumer_events": 300,
  "market_actor_events": 30,
  "action_distribution": { "save_for_later": 60, "purchase_trial": 23, "...": 0 },
  "segment_summary": { "Early Adopter / Trend-Seeker": { "n": 42, "avg_trial_probability": 0.51, "avg_sentiment": 0.49, "trial_purchases": 6, "top_action": "save_for_later" } },
  "top_barriers": [["Premium price vs mainstream alternatives", 73]],
  "top_triggers": [["Launch-month promotion lowers trial risk.", 111]],
  "per_round": [ { "round_number": 1, "stage_name": "Pre-launch concept exposure", "consumer_events": 50, "market_actor_events": 5, "action_distribution": {"like": 17, "save_for_later": 32, "view": 1}, "avg_sentiment": 0.484, "avg_trial_probability": 0.403 } ],
  "token_usage": null
}
```
**Errors:** `404 project_not_found`, `409 brief_required`, `409 ontology_required`, `409 agents_required`.

### `GET /projects/{id}/simulate/status`
Last-run summary: same shape as `GET /events/summary` plus `simulation_status`
(`completed` | `not_run`).

### `GET /projects/{id}/events`
**Query:** `?round_number=1..6&agent_id=...&agent_type=consumer|market_actor&action_type=...&segment_name=...&limit=...&offset=...`
Returns paginated `EventOut` rows (round, stage, agent, segment, touchpoint, action_type,
reasoning, generated_reaction, emotional_tone, confidence_score, sentiment/trial/purchase/repeat
scores, trust_change, barrier/trigger detected, raw `scores` dict, timestamp).

### `GET /projects/{id}/events/summary`
Aggregate (`EventsSummaryOut`): totals, action_distribution, `per_round` summaries,
`segment_summary`, top barriers/triggers.

### `GET /projects/{id}/events/{event_id}`
Single event with full reasoning and scores.

---

## Report _(live — Phase 6)_

The strategic launch report synthesizes the persisted brief + ontology + agents +
simulation events into a **16-section** Strategic FMCG Innovation Launch Simulation
Report. The deterministic builder (`services/report_builder.py`) grounds every
quantitative claim in event aggregates and attaches compact evidence references
(`event_id`, `round_number`, `agent_id`, `segment_name`, `action_type`,
`short_reaction_excerpt`). LLM narrative enhancement is optional and falls back
gracefully — tests never require an external LLM. Output is **exploratory decision
support, not a guaranteed forecast**.

Sections: `executive_summary`, `launch_funnel_summary`, `segment_reaction_map`,
`purchase_trigger_analysis`, `adoption_barrier_analysis`,
`claim_clarity_and_credibility`, `packaging_price_perception`,
`channel_touchpoint_analysis`, `trial_repeat_forecast`, `social_diffusion_and_wom`,
`competitor_and_retail_response`, `innovation_risk_matrix`,
`strategic_recommendations`, `recommended_ab_tests`, `human_validation_questions`,
`limitations`.

### `POST /projects/{id}/report/generate`
**Body (optional):** `{ "format": "json_markdown", "use_llm_narrative": false, "force_regenerate": true }`
Builds the report deterministically, optionally enhances the executive-summary
narrative via LLM (graceful fallback), and **replaces** any prior report (no stale
duplicates).
- **404** `project_not_found`.
- **409** `brief_required` | `ontology_required` | `agents_required` | `events_required`.
- **200** `{ project_id, report_id, status, source_mode ("deterministic"|"llm_enhanced"), confidence_score, generated_at, report_payload, markdown_report, summary }`.

### `GET /projects/{id}/report`
Returns the saved report (same shape as `generate`). **409 `report_required`** if none generated yet.

### `GET /projects/{id}/report/markdown`
Returns `text/markdown` rendering. **409 `report_required`** if none yet.

### `GET /projects/{id}/report/summary`
Compact summary: `overall_market_reaction`, `top_opportunity`, `top_risk`,
`top_segments`, `top_triggers`, `top_barriers`, `key_recommendations`.

### `GET /projects/{id}/report/export`
Downloads the structured `report_payload` as a JSON attachment.

---

## Deep Q&A (Phase 7)

Answers are grounded strictly in persisted data — the strategic report payload, baseline
events, consumer agents + their simulation memory, and the ontology. No generic marketing
knowledge is introduced. An optional LLM pass may rephrase the prose but never invents facts.

### `POST /projects/{id}/ask`
**Body:**
```json
{
  "question": "Why is repeat purchase probability so low?",
  "use_llm": false,
  "include_evidence": true,
  "max_evidence_events": 5
}
```
**Preconditions:** `404 project_not_found`; `409 events_required` (simulate first);
`409 report_required` (generate the report first).

**Response 200:**
```json
{
  "project_id": "uuid",
  "question": "...",
  "intent": "repeat_purchase",
  "source_mode": "deterministic",
  "answer": {
    "direct_answer": "...",
    "evidence_summary": "...",
    "supporting_events": [
      { "event_id": "uuid", "round_number": 6, "agent_id": "uuid",
        "segment_name": "...", "action_type": "complain", "short_reaction_excerpt": "..." }
    ],
    "supporting_segments": ["..."],
    "confidence_score": 0.66,
    "limitations": ["..."],
    "recommended_next_action": ["..."],
    "selected_agents": [],
    "simulated_interview_answers": []
  }
}
```
- **Intents (12):** `interview_agents`, `repeat_purchase`, `target_segment`, `claim_risk`,
  `pricing`, `channel_touchpoint`, `trial`, `barriers`, `triggers`, `recommendations`,
  `competitor_response`, `general_summary` (default).
- **Interview questions** (e.g. "interview 3 skeptical consumers") additionally populate
  `selected_agents` and `simulated_interview_answers` (each with `agent_id`, `segment_name`,
  `persona_label`, `answer`, `evidence_from_agent_memory`), with a caveat that these are
  SIMULATED personas, not real interviews.
- `source_mode` is `deterministic` unless `use_llm=true` AND an LLM is configured AND the
  rewrite succeeds (`llm`); otherwise it falls back to `deterministic`.

---

## Scenarios (Phase 7)

Re-simulates the launch under modified assumptions WITHOUT touching the baseline simulation,
report, or agent memory. Scenario events are tagged `run_type="scenario"` + `scenario_id`.

### `POST /projects/{id}/scenario`
**Body:**
```json
{
  "scenario_name": "10% price reduction",
  "description": "...",
  "overrides": {
    "price_change_pct": -10,
    "claim_credibility_boost": 0.0,
    "sampling_boost": 0.0,
    "promotion_boost": 0.0,
    "channel_focus": null,
    "competitor_pressure_boost": 0.0,
    "packaging_appeal_boost": 0.0,
    "social_proof_boost": 0.0,
    "sensory_risk_reduction": 0.0,
    "retailer_support_boost": 0.0
  },
  "rounds": 6,
  "seed": 42,
  "generate_delta_report": true
}
```
All overrides default to neutral (0.0 / null) → a neutral scenario reproduces the baseline.

**Preconditions:** `404 project_not_found`; `409 ontology_required`; `409 agents_required`;
`409 baseline_events_required`; `409 baseline_report_required`.

**Response 200 (`ScenarioRunOut`):**
```json
{
  "scenario_id": "uuid",
  "project_id": "uuid",
  "scenario_name": "...",
  "description": "...",
  "overrides": { ... },
  "baseline_summary": { "trial_probability": 0.462, "repeat_probability": 0.086, "...": "..." },
  "scenario_summary": { "...": "..." },
  "delta_summary": "Trial probability +0.031, repeat +0.004, ...",
  "key_metric_changes": {
    "trial_probability_delta": 0.031, "purchase_intent_delta": 0.0, "repeat_probability_delta": 0.004,
    "sentiment_delta": 0.01, "complaint_delta": -1, "recommend_delta": 2, "switch_delta": 0,
    "trial_count_delta": 3, "top_segments_improved": ["..."], "top_segments_declined": ["..."]
  },
  "segment_changes": [ { "segment_name": "...", "trial_probability_delta": 0.0, "sentiment_delta": 0.0 } ],
  "action_distribution_changes": { "purchase_trial": 3 },
  "trigger_changes": { "...": 1 },
  "barrier_changes": { "...": -1 },
  "recommendation_changes": ["..."],
  "conclusion": "...",
  "created_at": "..."
}
```

### `GET /projects/{id}/scenarios`
List of `ScenarioListItem` (`scenario_id`, `scenario_name`, `description`,
`baseline_event_count`, `scenario_event_count`, `created_at`), newest first.

### `GET /projects/{id}/scenarios/{scenario_id}`
Full `ScenarioRunOut` (`404 scenario_not_found`).

### `GET /projects/{id}/scenarios/{scenario_id}/delta`
The raw persisted delta payload (`404 scenario_not_found`).

### `DELETE /projects/{id}/scenarios/{scenario_id}`
Deletes the scenario run and its scenario-tagged events (`404 scenario_not_found`).

---

## Agent Studio (Phase 16)

### `GET /projects/{id}/studio/state`
Read-only aggregation for the visual studio (no scoring change, baseline untouched). Returns
`{ project, agents[], events[] (baseline, sorted by round+id), events_summary, rounds[],
graph{ nodes[], edges[], note } }`. Graph nodes are one per agent (type/group/event_count/avg_sentiment);
edges are bounded (≤160) transparent visualization links from shared trigger/barrier within a round
and market-actor round impact — **not real conversations** (stated in `graph.note`). `404 project_not_found`.

---

## Workspace Overview (Phase 19)

### `GET /projects/{id}/overview`
Read-only aggregation for the project home. Returns `{ project, pipeline_status{has_brief…has_briefing},
counts{agents,events,snapshots,scenarios,decisions}, latest_scorecard?, latest_briefing_summary?,
latest_live_run?, next_recommended_action{action,label,surface,reason}, recent_activity[] }`.
`next_recommended_action.action ∈ {submit_brief, analyze_ontology, generate_agents,
run_live_simulation, generate_report, generate_briefing, explore, resolve_stale_run}`. `404 project_not_found`.

---

## Live Simulation Streaming (Phase 18, SSE)

_Phase 19 reliability:_ `start` body also accepts `stale_after_seconds` (default 600); starting a run
auto-reaps stale `running` runs. `GET /{run_id}` and `/runs` now include `is_stale`, `can_cancel`,
`can_replay_persisted_events`, `last_event_at`, `last_heartbeat_at`, and a `stream_url` (only while
genuinely running). `POST /{run_id}/cancel` marks pending/running runs `cancelled` (status-level;
keeps persisted events).

### `POST /projects/{id}/live-simulation/start`
Body `{ rounds, deterministic, seed, include_market_actors, force_rerun, event_delay_ms }`.
Returns `{ run_id, status, stream_url }`. **Errors:** `404 project_not_found`; `409 brief_required`/
`ontology_required`/`agents_required`/`simulation_exists`/`live_run_already_running`. With
`force_rerun=true` clears baseline events + agent memory first.

### `GET /projects/{id}/live-simulation/{run_id}/stream`
`text/event-stream` (SSE). Frames `event: <type>\ndata: <json>\n\n`. Message types:
`run_started, round_started, agent_started, event_generated, agent_memory_updated,
market_actor_event_generated, round_completed, run_completed, run_failed, heartbeat`. Each carries
`{run_id, project_id, type, timestamp, sequence, round_number, stage_name, progress{...}, payload}`.
Streamed events persist as `run_type="baseline"` (identical to `POST /simulate`).

### `GET /projects/{id}/live-simulation/{run_id}` · `GET /projects/{id}/live-simulation/runs` · `POST .../{run_id}/cancel`
Run status / list runs / cancel a pending/running run (`404 live_run_not_found`).

---

## Executive Briefing (Phase 14)

### `POST /projects/{id}/briefing/generate`
Body `{ audience, tone, include_evidence, include_decision_history, include_next_actions, use_llm_rewrite, force_regenerate }`.
Deterministic assembly from report + scorecard + confidence + assumptions (+ optional snapshot diff /
timeline). Returns `{ project_id, briefing_id, status, source_mode, audience, tone, generated_at,
briefing_payload, markdown, summary }`. The payload has 11 sections: `briefing_header`, `situation`,
`top_findings`, `biggest_risks`, `readiness_assessment`, `what_changed_recently`,
`decision_recommendation`, `next_best_actions`, `validation_plan`, `evidence_pack`, `limitations`.
`recommendation_status ∈ {move_forward, validate_before_move_forward, revise_and_retest, hold}`
(logic in `SCORING_LOGIC.md`). **Errors:** `404 project_not_found`; `409 events_required`;
`409 report_required`; `409 scorecard_required`.

### `GET /projects/{id}/briefing` · `/briefing/markdown` · `/briefing/summary` · `/briefing/export?format=json|markdown`
Saved briefing / markdown / compact summary / download. `409 briefing_required` before first generation.

### `POST /projects/{id}/briefing/ask` (Phase 15)
Briefing-grounded Q&A. Body `{ question, audience, tone, include_evidence, max_evidence_items, use_llm_rewrite }`.
12-intent classifier; deterministic evidence-cited answers. Returns `{ intent, answer{ direct_answer,
audience_framing, supporting_evidence[], related_next_actions[], related_risks[], confidence_score,
limitations[], recommended_follow_up[] }, source_mode }`. **Errors:** `404 project_not_found`;
`409 report_required`; `409 briefing_required`.

### `POST /projects/{id}/briefing/tailor` (Phase 15)
Re-frames the same findings for an audience (executive/brand_team/trade_sales/rd_product/consumer_insight).
Returns `{ audience, tone, tailored_payload{ headline, audience_priority, what_this_audience_needs_to_know[],
role_specific_risks[], role_specific_actions[], evidence_to_show[], what_not_to_overclaim[], talk_track[] }, markdown, source_mode }`.

### `POST /projects/{id}/briefing/board-summary` · `GET` · `GET .../board-summary/export?format=json|markdown` (Phase 15)
One-page board summary (3 findings / 3 risks / 3 actions + decision gate + validation + caveat).
`409 board_summary_required` on GET/export before first generation.

---

## Snapshot Diff & Decision History (Phase 13)

### `POST /projects/{id}/snapshots/diff`
Body `{ "left": {"type":"active_report|snapshot","snapshot_id":null}, "right": {...} }`.
Deterministic diff (no LLM). Returns `scorecard_delta` (per-dimension `{left,right,delta}`),
`dimension_changes` (direction + interpretation; risk dims improve when they decrease),
`changed_sections`, `recommendation_changes`, `risk_changes` (reduced/new/unchanged),
`segment_changes`, `plain_english_summary`, `decision_implication`, `limitations`.
**Errors:** `404 project_not_found`; `409 report_required`; `404 snapshot_not_found`;
`400 invalid_diff_request`.

### `POST/GET/DELETE /projects/{id}/decisions[/{entry_id}]`
Per-project decision log. Create body: `{ entry_type, title, body, related_snapshot_id?,
related_scenario_id?, related_report_id?, tags[] }`. Creating a snapshot auto-logs a
`snapshot_created` entry. `404 decision_not_found` on missing entry.

### `GET /projects/{id}/timeline`
Merged chronological timeline: `{ project_id, timeline:[{timestamp,type,title,description,related_id,metadata}] }`
spanning project/brief/ontology/agents/simulation/report milestones + scenarios + snapshots + decisions.

---

## Portfolio, Scorecards & Snapshots (Phase 12)

### `GET /projects/{id}/scorecard`
Transparent 0–100 concept heuristic (see `SCORING_LOGIC.md`). `409 report_required` if no report.
Returns `Scorecard` (overall + sub-scores + top_opportunity/risk + best/weakest segment +
strongest trigger/barrier + recommended_next_step + ranking_explanation + disclaimer).

### `GET /projects/{id}/scorecard/export?format=json|markdown`
Downloadable scorecard (default `json`).

### `POST /projects/{id}/snapshots`
Body `{ "snapshot_name": "...", "description": "..." }`. Freezes the current report + scorecard
(read-only). `404 project_not_found`; `409 report_required`.

### `GET /projects/{id}/snapshots` · `GET /projects/{id}/snapshots/{sid}` · `DELETE /projects/{id}/snapshots/{sid}`
List / detail (`SnapshotOut` with report_payload, markdown, scorecard) / delete. `404 snapshot_not_found`.

### `GET /projects/{id}/snapshots/{sid}/scorecard` · `/scorecard/export`
The snapshot's frozen scorecard (and its export).

### `GET /portfolio`
All projects with scorecard columns + `summary` (total, report-ready, highest-score/risk, best
trial/repeat). Projects without a report appear with null scores.

### `POST /portfolio/compare`
Body `{ "project_ids": [...], "snapshot_ids": [...], "include_snapshots": false }`. Returns
`{ items:[{type,project_id,snapshot_id,name,scorecard}], comparison_summary, dimension_rankings, recommendation }`.

---

## Insight, Trust & Explainability (Phase 11)

### `POST /projects/{id}/sensitivity`
Deterministic lever sweeps. Reuses the scenario engine; sweep events are deleted after
aggregation, so the **baseline simulation/report are never modified**.
**Body** (omit `levers` to use defaults):
```json
{ "levers": { "price_change_pct": [0,-5,-10,-15], "sampling_boost": [0,0.05,0.1,0.15] }, "seed": 42, "rounds": 6 }
```
**Preconditions:** `404 project_not_found`; `409 ontology_required`/`agents_required`/`baseline_events_required`/`baseline_report_required`.
**Response:** `{ project_id, baseline_summary, sweeps:[{lever, points:[{value,trial_probability,repeat_probability,purchase_intent,sentiment,recommend_rate,complaint_rate,top_improved_segments,top_declined_segments,interpretation}], best_point, diminishing_return_point, strategic_read}], overall_recommendation, limitations }`.
Valid levers: `price_change_pct, claim_credibility_boost, sampling_boost, promotion_boost, social_proof_boost, packaging_appeal_boost, sensory_risk_reduction, retailer_support_boost, competitor_pressure_boost`.

### `GET /projects/{id}/confidence`
Explains the confidence score (see `SCORING_LOGIC.md`). `409 report_required` if no report.
**Response:** `{ project_id, overall_confidence, confidence_label, drivers:[{factor,score,weight,explanation}], confidence_risks, how_to_improve_confidence, disclaimer }`.

### `GET /projects/{id}/assumptions`
Consolidated assumptions ledger. `409 ontology_required` if not analyzed.
**Response:** `{ project_id, assumptions:[{category,assumption,source,impact,recommended_validation}], summary:{high_impact_count,medium_impact_count,low_impact_count} }`.

---

## System & Meta

### `GET /api/v1/system/status` (Phase 10)
Safe, non-secret configuration for the dashboard status badges. No secrets are exposed.
```json
{
  "app_name": "FMCG Innovation Reaction Simulator",
  "version": "0.1.0",
  "environment": "local",
  "llm_configured": false,
  "database": "sqlite",
  "demo_mode": false,
  "database_type": "sqlite",
  "frontend_origin_configured": false,
  "live_streaming_supported": true,
  "e2e_configured": true
}
```

### `GET /healthz`
`{ "status": "ok", "app": "...", "version": "...", "llm_configured": false }`

### `GET /readyz` (Phase 23)
Readiness: app up + DB reachable + tables accessible.
`{ "status": "ready"|"degraded", "database": {"connected", "type", "checks": [...]}, "app": {"version","environment","demo_mode"} }`.

### `GET /api/v1/system/diagnostics` (Phase 23)
Read-only ops snapshot (no secrets): `{ "status", "request_id", "app": {...}, "database": {"connected","project_count","event_count","live_run_count"}, "features": {...}, "warnings": [...] }`.

Every response includes an `X-Request-ID` header. Error responses use a consistent envelope:
`{ "detail": { "code": "...", "message": "...?", "request_id": "..." } }`.

### `GET /meta/segments`
Built-in segment templates.

### `GET /meta/ontology-schema`
Returns the entity-type and relationship-type vocabulary.

---

## Error Codes
- `400 invalid_brief` — brief missing or unparseable.
- `404 project_not_found`
- `409 ontology_required` — agent generation called before analyze.
- `409 agents_required` — simulate called before agents/generate.
- `409 events_required` — report generation / Q&A called before simulate.
- `409 report_required` — report GET/markdown/summary/export or Q&A requested before generate.
- `409 baseline_events_required` — scenario requested before a baseline simulation exists.
- `409 baseline_report_required` — scenario requested before the baseline report is generated.
- `404 scenario_not_found` — scenario detail/delta/delete for an unknown scenario_id.
- `502 llm_unavailable`
- `500 internal_error`
