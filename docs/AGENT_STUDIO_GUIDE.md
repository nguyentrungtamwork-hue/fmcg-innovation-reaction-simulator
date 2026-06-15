# AGENT_STUDIO_GUIDE.md

_Phase 16 — Visual Agent Interaction Studio._

The Agent Studio (`/projects/:id/studio`) turns the saved simulation into an **animated playback**:
you watch consumer agents and market actors react round by round, inspect any agent, and filter the
view. It is a visualization of **persisted events** — no new simulation, no streaming, no scoring
change.

## How to use it
1. Run the pipeline through **simulation** (Studio shows "Run simulation first" until events exist;
   a one-click **Run simulation** button is provided).
2. Pick a **speed** (0.5x / 1x / 2x / Instant) and press **Play**. Event cards stream in, the active
   agent node highlights, and the metric strip (trials / repeats / recommends / complaints / avg
   sentiment) updates as events are revealed.
3. **Pause / Reset / Replay** at any time. Click a **round** on the timeline or set **filters**
   (segment, agent type, action, trigger, barrier, sentiment) to narrow the playback set.
4. Click any **node** or a card's **Open agent** to open the Agent Inspector (traits, grounding,
   initial/simulation memory, action history). **Open event** jumps to the Event Explorer.
5. **Continue to Report** when done.

## What the nodes mean
- Each node is one **agent**: blue = consumer, violet (larger) = market actor, amber = currently
  active in playback. Nodes are clustered by **segment** (consumers) or **role** (market actors).
- Node size/tooltip shows the agent's event count and group.

## What the edges mean — and what they do NOT
Edges are **visualization aids**, derived deterministically from the event log:
- same round + **same trigger** (star to a group hub),
- same round + **same barrier**,
- **market-actor round impact** (market actor → that round's consumer hub).

> **Interaction links are visualization aids derived from shared triggers/barriers/rounds — not
> real direct conversations.** The agents do not message each other; the edges only express shared
> reactions within a round. This caption is shown in the UI under the canvas.

## What is simulated vs visualized
- **Simulated** (Phases 4–5): the agents, their per-round reactions, scores, triggers/barriers.
- **Visualized** (this phase): the playback ordering, node layout, highlights, counters, and the
  heuristic edges. Nothing here adds findings.

## How to avoid overclaiming
- Don't describe edges as conversations or causation — they are co-occurrence aids.
- Counters reflect the **revealed** subset during playback, not a forecast.
- Everything remains exploratory decision support; validate with real consumer research.

## Control-room header & guided start (Phase 17)
- The header shows the project name, a **simulation-ready** status badge, **agent/event totals**,
  current **mode** (Idle/Playing/Done), and CTAs (Run simulation / Replay / Open Report / Open
  Briefing / Event Explorer).
- If the simulation isn't ready, a **guided next-step** panel runs the remaining pipeline steps in
  place (submit brief → analyze → generate agents → run simulation) using existing APIs — the full
  Workflow page still works.

## Keyboard shortcuts & view toggles (Phase 17)
- **Space** play/pause · **R** reset · **→ / ←** next/previous round (ignored while typing in a field).
- Quick view toggles: **All / Consumers only / Market actors only** (dim non-matching nodes and
  filter the stream). Plus the full filter bar (segment/action/trigger/barrier/sentiment).
- The live stream adds a **Copy evidence** button per card (round · segment · action · sentiment ·
  reaction · event id) for pasting into notes.

## Replay Mode vs Live Mode (Phase 18)
- **Replay Mode** animates the already-persisted events client-side (default when a simulation exists).
- **Live Mode** starts a new simulation and streams each event over **SSE** as the backend generates
  and persists it — live canvas highlight, event stream, metric strip, and round progress. On
  completion you can Generate Report or switch to Replay. Full details + deployment caveats:
  `docs/LIVE_STREAMING_GUIDE.md`.

## Live Run History & stale recovery (Phase 19)
Live Mode shows a **Live Run History** panel (status, stale flag, event count, Cancel, Open-replay).
Stale `running` runs are auto-reaped when you start a new run, and a banner offers "mark stale /
cancel". See `docs/WORKSPACE_HOME_GUIDE.md`.

## Accessibility & performance (Phase 20)
Playback shortcuts are ignored while typing; the active-node pulse respects
`prefers-reduced-motion`; live status/progress is an `aria-live` region. The live stream has a
configurable cap (40/100/200) and the canvas falls back to **segment clusters** when an agent
network exceeds 150 nodes. See `docs/ACCESSIBILITY.md` + `docs/PERFORMANCE_NOTES.md`.

## Performance notes
Designed for the sample run (≈55 nodes, 330 events, 6 rounds). The graph is bounded (≤160 edges
server-side) and the live stream caps to the most recent ~40 cards. For much larger runs, filter by
round/segment first.
