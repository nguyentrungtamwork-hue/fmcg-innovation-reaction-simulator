# SAMPLE_LIBRARY_GUIDE.md

_Phase 26 — a small library of **fictional** FMCG innovation concepts you can load as a new project
to explore the full workflow in seconds. Samples are illustrative concepts, **not** real products or
market validation, and contain **no real brand names**._

## Where it lives
- **Files:** `samples/library/*.md` (human-readable briefs) + `samples/library/samples_index.json`
  (metadata + structured brief fields + recommended demo path).
- **API:** `GET /api/v1/system/samples`, `GET /api/v1/system/samples/{id}`,
  `POST /api/v1/system/samples/{id}/load`.
- **UI:** **Samples** nav item → `/samples` (cards, search, category filter) and `/samples/{id}`
  (full brief + load buttons).

## The samples
| Sample | Category | Demonstrates | Recommended path |
|---|---|---|---|
| VerdeCalm Herbal Cool Tea | Ready-to-drink beverage | Trial vs repeat gap; price scenario | Workflow → Studio → Report → Scenarios |
| CrispRoot Baked Veggie Crisps | Healthy snack | "Healthy = less tasty" barriers | Workflow → Report → Q&A |
| PureLeaf Gentle Micellar Wash | Personal care | Claim-credibility / trust build | Workflow → Report → Briefing |
| EcoSwirl Plant-Based Surface Spray | Household cleaning | Efficacy-vs-eco trade-off; sampling scenario | Workflow → Report → Scenarios |
| NutriMorning High-Protein Yogurt | Dairy / nutrition | Live Mode reactions; breakfast-habit barrier | Workflow → Studio → Report |
| LumaGlow Vitamin C Day Serum | Beauty / skincare | Claim/sensory barriers; repeat lag | Workflow → Report → Q&A → Briefing |

## How to load a sample
1. Open **Samples** (nav) and pick a concept (search/filter as needed).
2. **Load as new project** — creates a project + submits the brief only (fast). You then run the
   workflow yourself.
3. **Load and run pipeline** — also runs the deterministic pipeline (ontology → agents → simulation →
   report → briefing). No LLM required; results are reproducible (seed 42).
4. After loading, use **Open Project Home / Workflow / Agent Studio**.

API equivalent:
```bash
curl -X POST .../api/v1/system/samples/ready_to_drink_tea/load \
  -H 'Content-Type: application/json' -d '{"run_pipeline": false}'
```

## What each sample includes
`sample_id, name, category, short_description, target_consumer, key_claim, price_positioning,
channels, known_risks, sample_brief_text, recommended_demo_path, what_to_observe`, plus a structured
brief used to create the project.

## Samples vs real market validation
Samples are **modelled, fictional concepts** used to demonstrate the tool. They are not based on real
sales/scan/social data, real brands, or real consumers. Treat every result as **exploratory decision
support** to be validated with real surveys, sensory tests, and in-market A/B tests. See
`docs/ASSUMPTIONS` surfaces and the in-app disclaimer.
