# AUDIENCE_TAILORING_GUIDE.md

_Phase 15 — Briefing Q&A & Audience Tailoring._

Lets stakeholders interrogate the executive briefing, re-frame it for their role, and produce a
one-page board summary — **without re-running the simulation**. Everything is grounded in the
persisted briefing payload (itself derived from report + scorecard + confidence + assumptions +
history). Deterministic by default; an optional LLM pass polishes prose only and never adds claims.

## Briefing Q&A
- **API:** `POST /api/v1/projects/{id}/briefing/ask` with `{ question, audience, tone, include_evidence, max_evidence_items, use_llm_rewrite }`.
- A 12-intent classifier routes the question (explain recommendation status, summarize for exec,
  brand/trade/R&D/insight actions, leadership risks, evidence for recommendation, validate before
  launch, one-page summary, limitations, general). Each intent has a deterministic builder that
  cites/summarizes existing briefing/report evidence — never generic marketing knowledge.
- **Returns** `{ intent, answer:{ direct_answer, audience_framing, supporting_evidence[],
  related_next_actions[], related_risks[], confidence_score, limitations[], recommended_follow_up[] }, source_mode }`.
- **Preconditions:** `404 project_not_found`; `409 report_required`; `409 briefing_required`.

## Audience tailoring
- **API:** `POST /api/v1/projects/{id}/briefing/tailor` with `{ audience, tone, format, include_evidence, use_llm_rewrite }`.
- **Changes framing, not facts.** The same findings/risks/actions are re-emphasized per audience:
  - **Executive** — decision, gate, headline risk, confidence.
  - **Brand** — positioning, claim, message, lead segment.
  - **Trade/Sales** — channel fit, trial drivers, promo/sampling, retailer objections.
  - **R&D/Product** — sensory/taste risk, repeat, claim proof.
  - **Consumer Insight** — open assumptions, validation questions, methods, confidence gaps.
- **Returns** `tailored_payload { headline, audience_priority, what_this_audience_needs_to_know[],
  role_specific_risks[], role_specific_actions[], evidence_to_show[], what_not_to_overclaim[],
  talk_track[] }` + Markdown. Saved as a `BriefingArtifact`.

## One-page board summary
- **API:** `POST /api/v1/projects/{id}/briefing/board-summary` (+ `GET` and `GET .../export?format=json|markdown`).
- A tight one-pager: headline recommendation + status, one-sentence concept, **3 findings / 3 risks
  / 3 actions**, decision gate, validation needed, confidence & caveat, evidence refs. Stored as a
  `BriefingArtifact` (one per project) so it can be re-fetched/exported. `409 board_summary_required`
  before first generation.

## What changes vs what stays the same
- **Stays the same:** the underlying simulation, report, scorecard, confidence, assumptions, and the
  briefing payload's findings/risks/actions. No re-simulation; no new numbers.
- **Changes:** wording, emphasis, ordering, and which subset is surfaced for the chosen audience/tone.

## Using it in stakeholder meetings
1. Present the **Briefing** (Phase 14).
2. In **Tailor by Audience**, switch to the room's audience and read the talk track.
3. Take live questions in **Ask Briefing** — click evidence chips when challenged.
4. Hand out the **Board Summary** (print/Markdown) as the one-pager of record.

## What not to overclaim
- Tailoring/board summary are communication aids over **simulated** decision-support — not a forecast.
- The LLM (if enabled) only rewrites prose; it cannot introduce new findings.
- Always close with: validate the leading concept with real consumer research before committing budget.
