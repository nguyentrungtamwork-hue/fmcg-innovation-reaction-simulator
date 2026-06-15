# ACCESSIBILITY.md

_Phase 20 — accessibility pass. The dashboard is an internal decision-support tool; these are the
a11y affordances implemented and the gaps that remain._

## Keyboard
- All primary controls are native `<button>`/`<a>`/`<select>`/`<input>` elements → keyboard
  reachable and operable by default.
- Visible focus rings on buttons, nav links, and inputs (`focus-visible:ring` in `index.css`).
- **Escape closes** the Agent Drawer and the Glossary modal.
- Agent Studio playback shortcuts (Space play/pause, R reset, ←/→ round) are ignored while typing in
  an `INPUT`/`SELECT`/`TEXTAREA`.

## Focus & dialogs (Phase 21)
- `AgentDrawer` and `GlossaryModal` render with `role="dialog"` + `aria-modal="true"` and an
  aria-labelled title; a full-size backdrop button closes them; Escape closes them.
- **Focus is trapped** inside each dialog while open and **restored to the triggering element** on
  close, via a dependency-free `useFocusTrap` hook (saves `document.activeElement`, moves focus into
  the dialog, cycles Tab/Shift+Tab within it, restores on unmount). The dialog container has
  `tabIndex={-1}` as a focus fallback.
- Live Mode controls follow a clear DOM/tab order (controls → status → canvas → stream).

## Skip to content (Phase 21)
- The Layout renders a **"Skip to content"** link that is visually hidden until focused
  (`sr-only focus:not-sr-only`) and jumps to `#main-content`. The main container is a
  `<main id="main-content" role="main" tabIndex={-1}>` landmark.

## ARIA
- Icon-only / symbol buttons have `aria-label` (drawer close, etc.).
- Live simulation status + progress are inside an `aria-live="polite"` region so screen readers
  announce updates.
- Filters, range inputs, and the global jump selects have associated labels / `aria-label`.
- Studio canvases expose `role="img"` with descriptive `aria-label`; the network legend is labelled.
- Tabbed surfaces (Briefing, Studio mode) use `role="tab"`/`tablist` with `aria-selected`.

## Reduced motion
- `@media (prefers-reduced-motion: reduce)` disables the active-node pulse and smooth scrolling.
- A `usePrefersReducedMotion()` hook also turns off the JS-driven pulse class in Agent Studio. The
  live event stream and all data remain fully functional with motion disabled.

## Contrast
- Status badges use the emerald/amber/red/slate palette at weights chosen for adequate contrast on
  light backgrounds; the exploratory-decision-support disclaimer is always visible.

## Browser smoke + automated axe (Phase 21–22)
An opt-in **Playwright** suite (`frontend/e2e/smoke.spec.ts`) verifies the app shell, primary
navigation, the skip link, the Glossary dialog open/Escape-close, and seeded page loads. It also runs
**`@axe-core/playwright`** (`wcag2a`/`wcag2aa`) on the app shell, Portfolio, the open Glossary dialog,
and seeded Home + Studio — asserting **zero `serious`/`critical`** violations (minor/moderate are not
gated). Runs via `npm run test:e2e` and a **non-blocking** CI `e2e` job (`TESTING_GUIDE.md`).

### Phase 22 fixes
- Added `aria-label`s to previously unlabeled `<select>`s (Agent Studio filters; Decision-history
  related-snapshot picker) so every form control has an accessible name.

## Known gaps (future work)
- Focus trap is a lightweight custom hook (no inert/`aria-hidden` on background siblings) — adequate
  for these dialogs but not a full WAI-ARIA APG implementation.
- Not yet audited with a screen reader, and **no automated axe run** (jest-axe was evaluated but
  deferred to avoid heavier/flakier tests — a future improvement).
- Charts are SVG with labels; detailed data also exists as adjacent tables for AT.
