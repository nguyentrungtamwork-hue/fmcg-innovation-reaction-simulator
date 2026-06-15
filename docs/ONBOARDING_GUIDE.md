# ONBOARDING_GUIDE.md

_Phase 26 — first-run guidance, contextual help, and the glossary. Designed to help newcomers reach a
first insight quickly **without blocking power users** (everything is dismissible)._

## First-run onboarding checklist
- Shown on the **Projects** page when there are no projects yet (`OnboardingPanel`).
- An 8-step path: load a sample → analyze ontology → generate agents → run live simulation → open
  Agent Studio → generate report → generate briefing → export project.
- **Dismissible.** Once dismissed it stays hidden via `localStorage` key **`onboarding_seen`**.
- Step 1 links to **Samples**, step 8 links to **Data Tools**; the rest describe the workflow surfaces.

### localStorage keys
| Key | Purpose |
|---|---|
| `onboarding_seen` | `"true"` once the onboarding panel is dismissed. |
| `last_sample_loaded` | The `sample_id` of the most recently loaded sample. |
| `dismissed_help_cards` | Reserved for per-card help dismissal (forward-compatible). |

To re-show onboarding, clear `onboarding_seen` in your browser devtools (Application → Local Storage).

## Guided empty / first-run states
- **Project List (no projects):** onboarding panel + an empty-state card offering **Load a sample
  concept**, **Import a project bundle**, or create a blank project (right-hand form).
- **Project Home (no brief):** an amber hint linking to Workflow, Samples, and Data Tools.
- **Project Home (brief but no simulation):** the existing **What to do next** CTA points to the next
  step.

## Contextual help popovers (`HelpTooltip`)
- A small **?** button that opens a short, business-friendly popover; closes on outside-click or
  **Esc**; accessible (`aria-expanded`, `role="tooltip"`, `aria-describedby`).
- Copy lives in a single registry (`HELP_TEXT` in `src/components/HelpTooltip.tsx`) covering: ontology,
  agent, market actor, simulation event, Live/Replay Mode, trial/repeat probability, confidence,
  assumptions, snapshot, scenario, briefing, export bundle.
- Usage: `<HelpTooltip term="ontology" label="ontology" />` or `<HelpTooltip text="…custom…" />`.

## Glossary (enhanced)
- Footer **Glossary** drawer now has **search** and **category tabs** (Simulation / Research /
  Reporting / Operations), plus inline **Open →** links to relevant pages where useful.
- Source of truth for definitions is mirrored in `docs/GLOSSARY.md`.

## Guided tours & Play Demo (Phase 27)
Beyond the static checklist and help popovers, an active **guided tour** system can walk users through
the app, and **Play Demo** can load a sample and start a tour hands-free. Launch both from the **Demo
Control Panel** (footer **Tours & Demo**, Samples page, or empty Projects state). Tours are optional,
skippable, and remembered in `localStorage` (`guided_tour_seen`, `guided_tour_current_step`,
`demo_autoplay_seen`); **Reset onboarding/tour state** clears them. Full details:
`docs/GUIDED_TOURS.md`.

## Recommended demo flow for newcomers
1. **Samples → Load and run pipeline** on *VerdeCalm Herbal Cool Tea*.
2. Open **Report**; read the recommendation and skim evidence chips.
3. Open **Q&A** and ask "Why is repeat purchase low?".
4. Open **Scenario Lab** and try a price reduction.
5. **Export Project** from Project Home to share or back up.

See `docs/DEMO_SCRIPT.md` for the full walkthrough.
