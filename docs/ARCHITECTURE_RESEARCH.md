# ARCHITECTURE_RESEARCH.md

## Purpose
This document captures what we learn from the MiroFish repository (https://github.com/666ghj/MiroFish) as an *architectural reference only*. We do not copy code. MiroFish is AGPL-3.0; our implementation is a clean-room rewrite tailored to FMCG innovation launch simulation.

## MiroFish — Observed Architecture (high level)

MiroFish positions itself as a multi-agent prediction engine. Reading the repo at a structural level, its workflow can be decomposed into five stages:

1. **Seed Extraction & Graph Building**
   - User uploads seed material (a brief, a narrative, a report).
   - The system extracts entities and relationships from the seed.
   - A knowledge graph (GraphRAG-style) is constructed to give agents shared world knowledge.
   - Individual and collective memory is injected into the graph.

2. **Environment Setup**
   - Personas are generated from the graph and seed.
   - Each agent is configured (role, traits, memory pointer).
   - The simulation environment (touchpoints, channels, interactions) is instantiated.

3. **Simulation Engine**
   - Multi-agent simulation is executed on top of an OASIS-style engine (CAMEL-AI's Open Agent Social Interaction Simulations).
   - Agents interact across rounds; their memory updates dynamically.
   - Events are logged.

4. **Report Generation**
   - A dedicated ReportAgent reads logs, memory, and graph state.
   - It composes a structured report.

5. **Deep Interaction**
   - The user can chat with the post-simulation environment: ask the ReportAgent follow-ups or interview individual agents.

### Tech Stack (observed)
- Backend: Python 3.11–3.12.
- Frontend: Vue.js.
- Memory: Zep Cloud for long-term agent memory.
- LLM: OpenAI-compatible SDK (provider-pluggable, e.g. Qwen).
- Simulation: OASIS by CAMEL-AI.
- Packaging: `uv` for Python, npm for frontend; Docker support.

## What We Learn (and adapt) for FMCG Innovation Reaction Simulator

| MiroFish concept | What we take | What we change |
|---|---|---|
| Seed extraction | Treat the FMCG innovation **brief** as the seed. | Replace generic NER with an FMCG-specific ontology (Brand, Claim, Pack, Channel, …). |
| GraphRAG / shared memory | Build a category-market graph linking product, claims, segments, occasions, channels, competitors. | Use NetworkX + JSON locally (MVP); plan Neo4j/Zep upgrade. |
| Persona generation | Generate consumer + market-actor agents from the graph + brief. | Constrain personas to FMCG segments (8 defaults). Avoid protected attributes. |
| OASIS-style simulation | Round-based multi-agent loop with action logs and memory updates. | Replace generic social-interaction engine with a **launch-stage** environment (concept exposure → comms → shelf → trial → post-trial → diffusion). |
| ReportAgent | Specialized agent that synthesizes logs into a structured report. | Force-fit report to FMCG launch decisions: trial/repeat forecast, claim credibility, barriers, channel mix, A/B tests. |
| Deep interaction | Chat with the simulated world. | Constrain to FMCG decision questions ("Why did Segment A reject?", "What if price drops 10%?"). |

## What We Explicitly Reject from a Direct Port
- Generic social-network simulation primitives (likes/follows in a Twitter-style graph).
- Heavy infra (Zep Cloud, Docker stack) in MVP — defer to upgrade path.
- Frontend in Vue — we use React/Next.js to align with our team.
- Anything tied to MiroFish's specific prompt templates or report formatters (license boundary).

## License Boundary
MiroFish is AGPL-3.0. To stay clean:
- No copy-paste of source files, prompt templates, schemas, or report templates from MiroFish.
- All code authored fresh against the *concepts* described in this doc.
- Where a MiroFish concept is referenced (e.g., GraphRAG), we re-implement with our own data structures and prompts.
- AGPL is not "inherited" by inspiration — only by derivative code. We keep our repo MIT/Apache-2.0 compatible.

## Key Architectural Decisions Inspired by MiroFish

1. **Graph-first, not prompt-first.** Build the ontology graph before generating agents, so agent reasoning has a grounded world model.
2. **Memory per agent + shared market memory.** Each consumer agent has a private memory trace; the market has a shared event log.
3. **Round = launch stage.** Each round is a semantically distinct phase of an FMCG launch, not an arbitrary time tick.
4. **Specialist report agent.** Separate the simulator from the analyst — the report is a synthesis pass over logs, not emitted mid-simulation.
5. **Deep interaction is a retrieval task, not a re-simulation.** Q&A queries the logs + ontology + report; it does not re-run rounds unless the user requests a scenario.

## Open Questions (to be resolved in MVP_SPEC)
- Do we run agents in parallel or sequentially in MVP? (Likely sequential for token-cost control.)
- Do we batch LLM calls per round to cut cost?
- Do we let the user edit the ontology before agent generation?
