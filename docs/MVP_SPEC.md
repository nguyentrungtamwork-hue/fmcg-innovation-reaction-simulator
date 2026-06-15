# MVP_SPEC.md

## Goal
A locally-runnable MVP that takes an FMCG innovation brief and returns a strategic launch-reaction report grounded in a multi-agent simulation. End-to-end flow must work before any feature is polished.

## In Scope (MVP / Phase 1 implementation)
- One project per brief.
- Text input and Markdown/PDF file upload.
- FMCG ontology extraction (entities + relationships + assumptions + missing info).
- Generate **50 consumer agents** across **5 default segments** (subset of the 8 in the long spec).
- Generate **5 market-actor agents**: 1 retailer, 1 competitor, 1 influencer, 1 community, 1 category expert.
- **6 simulation rounds** mapped to the funnel stages.
- Event logging with reasoning per action.
- Per-agent private memory (JSON), shared market event log (SQLite).
- Strategic report (14 sections from the long spec, condensed where needed).
- Markdown + HTML export.
- Deep Q&A endpoint over project context.
- Simple React/Next.js dashboard: setup → ontology → agents → timeline → report → Q&A.

## Out of Scope (deferred)
- Real-time streaming of round events to the UI (poll instead).
- Celery/Redis async workers (synchronous execution with a progress indicator).
- Neo4j / Zep (NetworkX + JSON files instead).
- Postgres (SQLite, schema designed to migrate).
- Auth / multi-user (single local user assumed).
- Advanced scenario rounds beyond the 6 base rounds (price-change scenario only for Q&A endpoint).
- A/B testing automation (we *suggest* tests in the report; we don't run them).

## Defaults
| Parameter | MVP default | Configurable later |
|---|---|---|
| Consumer agents | 50 | Yes (50–200) |
| Segments | 5 | Yes (up to 8 built-in + custom) |
| Market actors | 5 | Yes |
| Rounds | 6 | Yes (add advanced rounds) |
| LLM | OpenAI-compatible via env var | Yes |
| Storage | SQLite + JSON | Postgres / Neo4j upgrade path |

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic v2, SQLAlchemy (SQLite), NetworkX.
- **Frontend**: Next.js (React, TypeScript), Tailwind, shadcn/ui.
- **LLM client**: `openai` SDK pointed at any OpenAI-compatible endpoint via `OPENAI_BASE_URL` / `OPENAI_API_KEY`.
- **Packaging**: `uv` or `pip` for backend; `pnpm` for frontend.
- **Container**: optional `docker-compose.yml` for local one-command run.

## End-to-End Flow (Definition of Done for MVP)
1. User pastes/uploads the sample FreshPlus brief.
2. `POST /projects` → `POST /projects/{id}/brief` → `POST /projects/{id}/analyze` returns ontology JSON within ~60s.
3. `POST /projects/{id}/agents/generate` returns 50 consumer + 5 market-actor agents within ~90s.
4. `POST /projects/{id}/simulate` runs 6 rounds, persists ~50×6 + market-actor events ≈ 330+ events.
5. `GET /projects/{id}/report` returns the full Markdown report with segment-level numbers and recommendations.
6. `POST /projects/{id}/ask` answers "Why did Segment A reject?" with citations to specific events.
7. Dashboard renders all of the above; report can be exported as `.md` and `.html`.

## Non-Functional Targets
- Cold-run end-to-end on the sample brief: < 5 minutes wall clock.
- Token budget per full run: target < 300k input + 100k output tokens (50 agents × 6 rounds + report + ontology).
- All LLM calls use a single retry with exponential backoff.
- No secrets in code; `.env.example` documents required variables.

## Risks
- **Token blowup**: 50 agents × 6 rounds = 300 reasoning calls. Mitigation: batch per round (group agents in the same segment with similar context), cache product/ontology context.
- **Generic LLM reactions**: mitigated by SCORING_LOGIC.md prompts that force grounding in agent profile + brief + round context.
- **Ontology drift**: mitigated by strict Pydantic schemas and a validation pass before agent generation.

## Acceptance Criteria
- README enables a new user to run the full flow on the sample brief in one session.
- `samples/sample_report.md` shows non-generic, segment-specific recommendations tied to events.
- Every report claim links to ≥1 event id.
