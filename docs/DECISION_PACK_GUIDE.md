# DECISION_PACK_GUIDE.md

_Phase 28 — a concise, print/PDF-ready **Decision Pack** and a shareable **read-only** project view
for stakeholder reviews. No new analysis: everything is composed from data the app already produced
(report, scorecard, briefing payload, confidence, assumptions, scenarios, decision history). No LLM,
no invented findings, no secrets, no server-side PDF._

## What the Decision Pack includes
1. **Cover / header** — project, concept, category, generated date, overall score, recommendation, confidence.
2. **Recommendation** — recommended decision, rationale, conditions before launch.
3. **Scorecard** — overall, trial/repeat potential, risk (+ disclaimer).
4. **Top findings** — evidence-grounded, from the report/briefing payload.
5. **Biggest risks** — severity, why it matters, mitigation.
6. **Next best actions** — prioritized (P0/P1…), owner, expected impact.
7. **Scenario & sensitivity snapshot** — saved scenario deltas; sensitivity is on-demand (note shown).
8. **Assumptions & limitations** — impact counts, top high-impact assumptions, limitations.
9. **Evidence pack** — referenced reactions/segments/scorecard/assumption/scenario/decision evidence.
10. **Decision history** — logged decisions and milestones.

## Endpoints
- `GET /api/v1/projects/{id}/decision-pack` — structured JSON (above shape).
- `GET /api/v1/projects/{id}/decision-pack/markdown` — copy/paste Markdown.

**Preconditions:** project missing → `404 project_not_found`; no simulation/report →
`409 events_required` / `409 report_required`; no scorecard → `409 scorecard_required`. The pack
builds the briefing payload on the fly, so a persisted briefing is **not** required.

## Frontend route & view
`/projects/:id/decision-pack` (`DecisionPackPage`) renders a clean, presentation-friendly, **read-only**
document — editing and heavy interactive controls are hidden. Buttons (hidden in print):
**Print / Save as PDF**, **Download Markdown**, **Download JSON**, **Copy local read-only link**,
**Back to Project Home**. Reusable parts: `ReadOnlyBadge`, `PrintButton`, `DownloadMarkdownButton`,
`DownloadJsonButton`, `CopyLinkButton`, `DecisionPackSection`.

Linked from **Project Home** ("Open Decision Pack"), **Report**, **Briefing** ("Create stakeholder
decision pack"), **Portfolio** (per project), and **Decision History**.

## How to print / save as PDF
Open the Decision Pack and click **Print / Save as PDF** (or use the browser print dialog). Print CSS
hides the header/nav/footer and all buttons, uses a clean white background, avoids clipped cards, and
adds page breaks before major sections. Choose "Save as PDF" as the destination. The disclaimer
prints in the footer.

## Sharing a read-only local link
**Copy local read-only link** copies the current `/projects/:id/decision-pack` URL. This is a
**local** convenience only — it is **not** secure public sharing: there are no tokens, no auth, and
the link only works against your local/instance backend. To hand off externally, prefer **Download
PDF/Markdown/JSON** or export the project bundle (Data Tools).

## What read-only does and does NOT mean
- **Does:** hides editing/interactive controls for a clean presentation; safe to show in a review.
- **Does not:** enforce access control or permissions. Anyone who can reach the instance can open the
  page. It is a presentation mode, not a security boundary.

## Using it in stakeholder meetings
1. Generate the report (and optionally briefing) for the project.
2. Open **Decision Pack** from Project Home/Briefing.
3. **Print / Save as PDF** for the deck, or present the page directly.
4. Walk Recommendation → Scorecard → Findings → Risks → Actions → Scenarios → Assumptions → Evidence.

## Portfolio roll-up (Phase 29)
For a cross-project view, the **Portfolio Decision Board** (`/portfolio/decision-board`) classifies
every concept go / validate / revise / hold / incomplete and links to each project's Decision Pack.
Use the Board to triage the pipeline, then open a specific Decision Pack for the full one-pager. See
`docs/PORTFOLIO_DECISION_BOARD.md`.

## What not to overclaim
The pack summarizes **simulated, exploratory** decision support — not a validated market forecast. It
is not based on real sales/scan/social data or real consumers. Always recommend validation with real
surveys, sensory tests, and in-market A/B tests before launch decisions.
