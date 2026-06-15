# GLOSSARY.md

Plain-language definitions of the key terms in the FMCG Innovation Reaction Simulator. The same
list powers the in-app **Glossary** drawer (footer link). Everything here is **exploratory decision
support** — simulated reactions, not a guaranteed market forecast.

- **Ontology** — the structured FMCG map extracted from the brief: entities (brand, claims, segments,
  channels, price, packaging…) plus relationships, purchase triggers, adoption barriers, and risks.
- **Agent** — a simulated consumer persona with traits, memory, and round-by-round reactions.
- **Market actor** — a non-consumer actor (Retailer, Competitor, Influencer, Social Community,
  Category Expert) that reacts to the launch each round.
- **Simulation event** — one agent's action + reasoning in a round (e.g. `purchase_trial`,
  `complain`) with scores like sentiment, trial probability, repeat probability.
- **Trial probability** — modelled likelihood an agent tries the product (higher is better).
- **Repeat probability** — modelled likelihood of buying again after trial — usually the tightest
  part of the funnel.
- **Evidence chip** — a clickable reference to a specific simulated event backing a finding; opens
  the Event Explorer / Agent Drawer.
- **Scenario** — a what-if re-run under lever overrides (price, sampling, claim credibility, channel
  focus…). The baseline simulation/report are always preserved.
- **Sensitivity sweep** — running one lever across several values to see the trial/repeat response
  curve — how responsive the launch is.
- **Confidence** — a heuristic 0–1 score of internal data coverage / grounding. It is **not**
  validation against the real market (the no-real-data factor caps it).
- **Assumptions ledger** — everything the simulation assumes (data gaps, modelling caveats,
  simulated personas), each with impact + a recommended validation step.
- **Scorecard** — a transparent 0–100 concept heuristic combining trial, repeat, sentiment,
  advocacy, claim credibility, channel fit, and confidence minus risk/assumption/sensitivity risk
  (see `SCORING_LOGIC.md`).
- **Snapshot** — an immutable, named freeze of a report + scorecard so a decision is preserved when
  the project changes.
- **Diff** — a comparison of two report versions (or active vs snapshot) showing per-dimension
  deltas and which sections/risks changed.
- **Briefing** — an evidence-grounded executive narrative: recommendation status, findings, risks,
  next best actions, validation plan, evidence pack.
- **Live Simulation** — watching the simulation generate events in real time over SSE (Live Mode).
- **Replay Mode vs Live Mode** — Replay animates already-saved events client-side; Live Mode streams
  a new run as the backend generates **and persists** it. Both visualize the same deterministic
  engine.
- **Stale live run** — a run stuck in `running` with no recent stream activity (past its TTL,
  default 10 min). Starting a new run auto-reaps stale ones; you can also cancel them.
- **Sample library** — a set of ready-made **fictional** FMCG concepts you can load as a new project
  (brief only, or full pipeline) to explore the tool. Not real products or market validation.
- **Export bundle** — a single no-secret JSON file containing a whole project, for backup or sharing;
  importing recreates it as a new project with fresh IDs.
- **Diagnostics** — a read-only drawer with backend status, DB counts, app-log count, recent errors,
  and request IDs for troubleshooting.

### In-app Glossary (Phase 26)
The footer **Glossary** drawer is **searchable** and grouped into **categories** — Simulation,
Research, Reporting, Operations — with inline links to relevant pages. The same definitions are
mirrored here and surfaced contextually via **?** help popovers (`HelpTooltip`).
