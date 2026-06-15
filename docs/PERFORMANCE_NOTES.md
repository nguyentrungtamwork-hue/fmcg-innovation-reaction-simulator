# PERFORMANCE_NOTES.md

_Phase 20 — performance hardening for larger runs._

## Event Explorer
- Loads up to 1000 baseline events, then **paginates client-side** (page size 50 / 100 / 200,
  default 50) with Prev/Next and a "showing X–Y of N" indicator. Filters apply server-side and reset
  to page 1. Only one page of rows is rendered at a time, so thousands of events stay responsive.

## Live event stream
- The `useLiveSimulation` hook keeps the latest **200** event payloads in memory; the Live panel
  renders a selectable **latest 40 / 100 / 200** (default 40) with a note that the stream is capped
  for performance. **Metrics use the full revealed set**, not just the displayed cards.

## Agent Studio canvas
- Node positions are computed once per node set via `useMemo` (no per-frame layout). The active node
  is highlighted (with a CSS pulse, off under reduced motion). Edges are bounded server-side (≤160).
- **Segment-aggregation fallback:** when an agent network exceeds **150 nodes**, the canvas renders
  one bubble per segment/role (sized by count) instead of every node, keeping it readable and fast.
  Use filters/round selection to drill back into detail at smaller scales.

## Initial bundle / code-splitting
- Heavy routes are `React.lazy` + `Suspense` code-split: ReportPage, EventExplorerPage,
  PortfolioPage, ComparePage, BriefingPage, AgentStudioPage. The main bundle dropped to ~243 kB
  (73 kB gzip); each heavy page loads on demand (3–30 kB). A clean `LoadingState` covers the lazy
  boundary.

## Default-scale targets
- Designed for the sample run: ~55 agents, 330 events, 6 rounds — smooth in Replay and Live mode.

## Remaining limits / future work
- No true windowing/virtualization (e.g. react-window) — pagination + caps are used instead; fine
  for tens of thousands of rows but a virtualized list would scale further.
- Live runs are synchronous in the streaming request (single-user/local); very long runs should move
  to background jobs (see `DEPLOYMENT_OPTIONS.md`).
- SVG canvas is not WebGL — extremely large aggregated graphs would still benefit from a real graph
  engine, intentionally avoided to keep the dependency surface small.
