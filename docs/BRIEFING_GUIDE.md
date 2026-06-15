# BRIEFING_GUIDE.md

_Phase 14 — Guided Insights & Narrative Briefing._

Turns everything the system already computed into a concise, audience-ready **executive launch
briefing** in plain business language — with traceable evidence, risks, a recommendation, and a
prioritized action list. Deterministic and offline by default; an optional LLM pass only polishes
prose and never invents findings.

## How the briefing is generated
- **API:** `POST /api/v1/projects/{id}/briefing/generate` with
  `{ audience, tone, include_evidence, include_decision_history, include_next_actions, use_llm_rewrite }`.
  Also `GET /briefing`, `/briefing/markdown`, `/briefing/summary`, `/briefing/export?format=json|markdown`.
- It is assembled **only** from existing data: the strategic report payload, the concept scorecard,
  the confidence calibration, the assumptions ledger, and (optionally) the latest snapshot diff +
  decision timeline. No new simulation is run; nothing about performance is invented.
- **Preconditions:** `404 project_not_found`; `409 events_required`; `409 report_required`;
  `409 scorecard_required`. `GET /briefing` returns `409 briefing_required` before first generation.
- **Sections:** header, situation, top findings, biggest risks, readiness assessment, what changed
  recently, decision recommendation, next best actions, validation plan, evidence pack, limitations.

## Recommendation status
`move_forward` / `validate_before_move_forward` / `revise_and_retest` / `hold` — derived
deterministically from the scorecard (overall, trial, repeat, claim credibility, risk, assumption
risk, confidence). The exact precedence is documented in `docs/SCORING_LOGIC.md`. Readiness chips
(trial / repeat / claim / channel / confidence / overall) map to ready / caution / not_ready.

## How next-best-actions are prioritized
Candidates are gathered from high/medium **barriers**, report **recommendations**, the **weakest
scorecard dimension** (test first), **confidence** improvement steps, and the top high-impact
**assumption**. They are deduplicated, prioritized (severity → trial/repeat impact → confidence →
effort → owner clarity), tagged with an **owner team** (Brand, Innovation, R&D, Trade Marketing,
Sales, E-commerce, Media, Creative, Consumer Insight, Leadership) and **effort** (low/medium/high),
and capped at 5–10. Actions are **specific** (e.g. "Run a 2-cell sensory test to validate herbal
taste acceptance among Health/Safety-Conscious Buyers"), never generic ("improve marketing").

## What evidence is included
The **evidence pack** compiles: referenced event reactions (clickable chips → Event Explorer /
Agent Drawer), per-segment metrics, scorecard scores, top high-impact assumptions, any
scenario/sensitivity runs, and recent snapshots/decisions. Findings and risks carry their own
evidence chips so every headline traces back to a simulated reaction.

## Optional LLM polish
With `use_llm_rewrite: true` and a configured key, an LLM rewrites the **Markdown prose only**
(no new facts/numbers/segments) and falls back to the deterministic text on any failure. Tests
never depend on the LLM.

## Using it in stakeholder meetings
1. Generate the briefing for the chosen **audience** (executive / brand / trade-sales / R&D / insight).
2. Lead with the **Recommendation** banner and one-line rationale.
3. Walk **Top findings → Biggest risks → Readiness**, clicking evidence chips when challenged.
4. Land the **Next best actions** (with owners) and the **Validation plan**.
5. **Download Markdown/JSON** or **Print** for the deck/minutes.

## Follow-ups, tailoring & board summary (Phase 15)
After generating the briefing you can: **ask** follow-up questions grounded in the briefing
(`POST /briefing/ask`), **tailor** it per audience (`POST /briefing/tailor` — reframes, never
re-simulates), and produce a **one-page board summary** (`POST /briefing/board-summary`). See
`docs/AUDIENCE_TAILORING_GUIDE.md`.

## Decision Pack (Phase 28)
For a stakeholder hand-off, the briefing's findings/risks/actions are also composed into a concise,
print/PDF-ready **Decision Pack** at `/projects/:id/decision-pack` (CTA: **Create stakeholder
decision pack**). It adds the scorecard, scenario snapshot, assumptions/limitations, evidence pack,
and decision history in one read-only document you can Print/Save-as-PDF or download as Markdown/JSON.
A persisted briefing is not required (the pack builds the payload on the fly). See
`docs/DECISION_PACK_GUIDE.md`.

## What the briefing does NOT prove
- A recommendation is a **heuristic triage** of simulated outputs — **not** a validated launch decision.
- No real sales/scan or social data informs it; confidence is structurally capped.
- Always close with: validate the leading concept with real research before committing budget.
