# GUIDED_TOURS.md

_Phase 27 — lightweight guided tours and an opt-in demo auto-play. Custom implementation (no tour
library). Everything is optional, skippable, and local-demo friendly. Tours explain **simulated**
outputs — not real-world validated market forecasts._

## What's included
- A reusable **tour system** (`src/tours/`): `TourProvider` (state + navigation + persistence),
  `TourOverlay` (spotlight + step card), `useTour()` hook, and a content registry (`tours.ts`).
- Two tours: **First-Time Product Tour** and **Agent Studio Tour**.
- A **Demo Control Panel** (`DemoControlPanel`) and a **Play Demo** auto-play flow.

## How tours work
- `TourProvider` wraps the app (inside the router) and renders `TourOverlay`.
- Each `TourStep` has: `id`, optional `route` (navigated to before the step; supports `:projectId`),
  optional `target_selector` (a `data-tour="…"` element to spotlight), `title`, `body`, `placement`,
  and an optional `action_hint`.
- If the target element is found, the overlay draws a **spotlight ring** and positions the step card
  near it. If not found, it shows a **centered modal** step (graceful fallback).
- Controls: **Next**, **Back**, **Skip**, **Finish**. Keyboard: **→** next, **←** back, **Esc** skip.
- Tours are **never mandatory** — skipping/finishing closes the overlay and returns full control.

### Persistence & resume (localStorage)
| Key | Purpose |
|---|---|
| `guided_tour_seen` | `"true"` once any tour is finished or skipped. |
| `guided_tour_current_step` | `{tourId, index, projectId}` of an in-progress tour; restored on reload. |
| `demo_autoplay_seen` | `"true"` once Play Demo has been used. |

Reloading mid-tour restores the saved step (resume). Finishing/skipping clears the current-step key.

## The two tours
**First-Time Product Tour** (`first_time`): Welcome → Sample Library → Projects nav → Agent Studio →
Report & Briefing → Scenario Lab → Data Tools. Explains what each surface is for.

**Agent Studio Tour** (`studio`): Studio intro → Live vs Replay Mode → Agent network & round timeline
→ Live event stream & filters → **heuristic-edge disclaimer** (network edges are heuristic visual
groupings, not a measured social graph). Launch it from the **Tour** button in the Studio header.

## Demo Auto-Play
Open the **Demo Control Panel** (footer **Tours & Demo**, the Samples page, or the empty Projects
state) and choose:
- **Play Demo (Quick):** loads the *Ready-to-drink tea* sample (`run_pipeline=false`) — creates a new
  project + brief so you can run steps yourself — then opens Project Home and starts the First-Time
  Tour.
- **Play Demo (Full):** same, but `run_pipeline=true` runs the deterministic pipeline
  (ontology → agents → simulation → report → briefing). **May take a little time.**

Both use the existing `POST /api/v1/system/samples/{sample_id}/load`. The expensive pipeline only runs
when you explicitly choose **Full** — never automatically.

## Demo Control Panel features
Start First-Time Tour · Start Agent Studio Tour · Play Demo (Quick/Full) · Reset onboarding/tour state
· Open Sample Library. Locations: Layout footer (**Tours & Demo** toggle), Sample Library page, and
the empty Projects state.

## Reset tour / onboarding state
Click **Reset onboarding/tour state** in the Demo Control Panel. It clears `guided_tour_seen`,
`guided_tour_current_step`, `onboarding_seen`, and `demo_autoplay_seen`, so the onboarding checklist
and tours behave as on a first visit.

## Accessibility & UX
- Overlay is a labelled `role="dialog"`; **Esc** skips; arrow keys navigate; buttons are focusable.
- Respects reduced-motion (no essential animation).
- Backdrop click does **not** advance/skip (avoids accidental dismissal); use the explicit buttons.
- After skipping/finishing, no overlay remains and the app is fully interactive.

## What the demo does NOT prove
Tours and Play Demo showcase **simulated, fictional** concepts. They are not based on real sales,
scan, or social data, real brands, or real consumers. Treat every output as **exploratory decision
support** to validate with real surveys, sensory tests, and in-market A/B tests.
