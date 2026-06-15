# DEMO_SCRIPT.md

_A 5–10 minute walkthrough of the FMCG Innovation Reaction Simulator._

## Before you start
- Either run locally (`scripts/dev.ps1` / `scripts/dev.sh`) or via Docker (`docker compose up --build`).
- Optionally pre-seed a complete FreshPlus project so data is ready instantly:
  ```bash
  cd backend && python scripts/seed_demo.py --reset-demo
  ```
  Copy the printed `open:` URL — it jumps straight to the seeded project's workflow.
- The footer shows live status: **Backend connected**, **LLM configured / Deterministic fallback**, **Demo Mode**, and the version.

## The 5-minute flow
1. **Open the dashboard** (http://localhost:5173 local, or http://localhost:3000 in Docker). Point out the Projects list.
2. **Open the FreshPlus project** (seeded) or click **Create project** → **Workflow → Load sample brief → Submit**.
3. **Step 3 — Ontology:** click **Analyze brief**. Show extracted entities, relationships, purchase triggers, adoption barriers, risk signals, and missing information — all derived from the brief.
4. **Step 4 — Agents:** **Generate agents** → 50 consumers across 8 segments + 5 market actors; show the segment distribution.
5. **Step 5 — Simulation:** **Run simulation** (6 rounds, seed 42). Show total events, top triggers/barriers, action distribution.
6. **Step 6 — Report:** **Generate report** → **Open full report**. Walk the executive summary, segment reaction map, triggers/barriers, risk matrix, recommendations, A/B tests. Demonstrate **Download Markdown / Download JSON / Print report**.
7. **Q&A:** ask **"Why is repeat purchase low?"** Read the direct answer, then click an **evidence chip** to show it is grounded in actual simulated events.
8. **Event Explorer:** filter by round/segment/action, expand a row to show the agent's reasoning + generated reaction, then click an agent to open the **Agent Drawer** (traits, memory, action history) — "this is *why* the agent behaved this way."
9. **Scenario Lab:** run a **10% price reduction**. Show the **Baseline | Scenario | Δ** table, segment changes, and the narrative conclusion. If a second scenario exists, use **Compare with** to show A/B vs baseline.
10. **Trust layer (Report page):** open the **Confidence calibration** panel (gauge + driver breakdown), scan the **Assumptions ledger** (what we assumed vs. what needs validation), and click a barrier **evidence chip → Open event / Open agent** to trace a number to its source.
11. **Sensitivity:** open the **Sensitivity** page → run the default sweep → show response curves and "which lever to test first."
12. **Scorecard & snapshot (Report page):** show the **Concept scorecard**, then **Create snapshot** ("Baseline Concept v1") to freeze this decision; export the scorecard Markdown/JSON.
13. **Portfolio & compare:** open **Portfolio** (ranked concepts), then **Compare** two concepts side by side and read the recommendation ("move X forward, validate Y").
14. **Snapshot diff & history:** regenerate or tweak, then open **Snapshot diff** to compare the active report vs the "Baseline Concept v1" snapshot — show the plain-English summary, dimension deltas, and risk changes; log the decision. The **Report page drift banner** summarizes movement vs the latest snapshot, and **History** shows the full timeline.
15. **Executive briefing:** open **Briefing**, pick the audience (e.g. Executive), Generate → present the recommendation banner, top findings, biggest risks, readiness, and the prioritized next-best-actions with owners. Download Markdown/JSON or Print for the deck.
16. **Briefing Q&A / tailoring / board:** on the **Briefing** page, use **Ask Briefing** ("Why this recommendation?"), switch **Tailor by Audience** to the room's role, and generate the **Board Summary** one-pager — all grounded in the same findings (no re-simulation).
17. **Agent Studio:** open **Studio**, press **Play** (try Instant) and watch the market react round by round — the active agent highlights, cards stream, and the metric strip updates. Filter by segment/round, then click an agent to inspect its memory + reasoning. Note the edges are visualization aids, not real conversations.
18. **Studio control room (Phase 17):** in **Studio**, use the header CTAs and keyboard shortcuts (Space/R/←/→), toggle Consumers/Market actors, and "Copy evidence" from a card. From the Projects page, "Open demo in Agent Studio" jumps straight in if a seeded demo exists.
19. **Live simulation (Phase 18):** in **Studio → Live Mode**, set a small event delay and click **Start Live Simulation** — watch rounds begin, agents light up, event cards stream, and metrics climb live. On completion, Generate Report or Replay.
20. **Project Home (Phase 19):** open **Home** to show pipeline status, the "what to do next" widget, the latest recommendation, quick links, and recent activity. Use the header **global jump** to hop between surfaces, and the footer **Glossary** for term definitions.
21. **Close the loop:** reopen the **Report** — the baseline report is unchanged; the snapshot stays immutable. Scenarios and sweeps never overwrite the baseline.

## Deploying a shareable demo
See `docs/DEPLOYMENT_CHECKLIST.md` for step-by-step Railway/Render + Vercel/Cloudflare or VPS Docker, and run `python backend/scripts/check_deploy_config.py` to validate config before deploying.

## Talk track (the story)
- "We turn a one-page innovation brief into a simulated launch: we extract the market ontology, build grounded consumer + market-actor agents, and run a 6-round launch funnel — Concept → Comms → Shelf → Trial → Post-trial → Diffusion."
- "Every number in the report traces back to specific simulated reactions — you can click through to the evidence."
- "Then you can interrogate it in plain language and stress-test what-if levers (price, sampling, claim credibility, channel focus…) before spending real money."

## Key selling points
- **Evidence-grounded:** Q&A and the report cite real simulated events, not generic marketing advice.
- **Deterministic + offline:** reproducible results with seed 42; works with no LLM key (fallback), optional LLM polish.
- **Decision-support speed:** explore segments, barriers, and pricing trade-offs in minutes.
- **Safe experimentation:** scenarios are isolated; the baseline is always preserved.

## What NOT to claim
- ❌ It is **not** a guaranteed sales forecast or a substitute for real research.
- ❌ The numbers are **not** fitted to historical launch outcomes or real POS/scan data.
- ❌ Simulated "interviews" are **modelled personas**, not real consumers.
- ✅ Always frame it as **exploratory decision support** that should be validated with surveys, sensory tests, and in-market A/B tests.

## Leadership roll-up — the Decision Board (Phase 29)
- **Board** nav (or Portfolio → **Decision Board**) opens `/portfolio/decision-board`: every concept
  classified **go / validate / revise / hold / incomplete**, with summary counts, rankings, and a
  plain-language portfolio recommendation. Filter by label, click into any concept's Decision Pack,
  and **Print / Save as PDF**.
- Great for an innovation pipeline meeting: "what advances, what needs validation, what to hold."
  Incomplete projects show with the missing step. See `docs/PORTFOLIO_DECISION_BOARD.md`.

## Closing the review — the Decision Pack (Phase 28)
- From Project Home / Briefing, open **Decision Pack** (`/projects/:id/decision-pack`): a clean,
  read-only, one-document summary (recommendation, scorecard, findings, risks, actions, scenarios,
  assumptions, evidence, decisions).
- Click **Print / Save as PDF** for a leadership deck, or **Download Markdown/JSON**. **Copy local
  read-only link** shares the page URL (local convenience, not secure public sharing).
- Frame it as exploratory decision support — see `docs/DECISION_PACK_GUIDE.md`.

## Hands-free start — Play Demo & guided tours (Phase 27)
- Footer **Tours & Demo** (or the Samples page / empty Projects state) opens the **Demo Control
  Panel**: **Play Demo (Quick)** loads the RTD-tea sample and starts a guided tour; **Play Demo
  (Full)** also runs the deterministic pipeline (may take a little time).
- **Start First-Time Tour** walks Projects → Samples → Studio → Report/Briefing → Scenario Lab → Data
  Tools. **Start Agent Studio Tour** explains Live/Replay, the network canvas, timeline, stream, and
  the heuristic-edge disclaimer.
- Tours are skippable (Esc / Skip), keyboard-navigable (←/→), and remembered in localStorage. **Reset
  onboarding/tour state** restores the first-run experience. Full reference: `docs/GUIDED_TOURS.md`.

## Fastest start — load a sample (Phase 26)
- Open **Samples** (nav) → pick a concept (e.g. *VerdeCalm Herbal Cool Tea*) → **Load and run
  pipeline**. In seconds you have a full project (ontology → agents → simulation → report → briefing).
- New users see a dismissible **onboarding checklist** on the Projects page and **?** help popovers on
  key terms; the **Glossary** (footer) is searchable by category.
- Each sample lists a **recommended demo path** and **what to observe** — follow it for a crisp story.
- Reminder: samples are **fictional, illustrative concepts**, not real products or market validation.

## Sharing, backup & reset (Phase 25)
- **Share a project:** Project Home → **Export Project** (downloads a JSON bundle), then send the
  file. The recipient uses **Data Tools → Import** to restore it as a new project. Nothing secret is
  in the bundle.
- **Back up before a demo:** `python backend/scripts/backup_sqlite.py` (or `make backup`) snapshots
  the SQLite file to `backend/backups/`.
- **Reset between demos:** `python backend/scripts/reset_demo_data.py` removes "FreshPlus Demo"
  projects; re-seed with `python scripts/seed_demo.py`. Full reference: `docs/DATA_MANAGEMENT.md`.

## Troubleshooting
- **Red "Backend is not reachable" banner** → start the backend (`uvicorn app.main:app --port 8000`) or `docker compose up`, then click **Retry**.
- **409 with a code** (e.g. `events_required`) → a prior workflow step hasn't run; follow the step order. The UI explains the next action.
- **Docker frontend can't reach backend** → confirm `VITE_API_BASE_URL` build arg points at `http://localhost:8000/api/v1` and that the backend container is healthy (`docker compose ps`).
- **No data on a fresh clone** → run the seed command above.
