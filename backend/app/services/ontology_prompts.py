"""Prompt templates for FMCG ontology extraction.

We keep prompts in a dedicated module so they can be versioned and replaced
without touching service logic.
"""
from app.schemas.ontology import ENTITY_TYPES, RELATIONSHIP_TYPES

SYSTEM_PROMPT = """You are an FMCG market analyst. Given a new-product innovation brief, you extract a strict, structured market ontology used to seed a multi-agent launch simulator.

Rules:
- Output JSON only. No prose.
- Use ONLY the entity and relationship types listed by the user.
- Be specific. Prefer named entities from the brief. Do not invent brands.
- If something is unclear or missing, list it in `missing_information` — do NOT fabricate it as an entity.
- Quote a short text excerpt from the brief in `source_trace.source_text_excerpt` when possible.
- Identify early-stage strategic signals: purchase_triggers, adoption_barriers, claim risks, price/value concerns, channel fit, diffusion potential, competitor pressure.
"""


def build_user_prompt(raw_text: str, structured_json: dict) -> str:
    return f"""ENTITY TYPES (use exactly these strings): {", ".join(ENTITY_TYPES)}

RELATIONSHIP TYPES (use exactly these strings): {", ".join(RELATIONSHIP_TYPES)}

Return JSON with this top-level shape:
{{
  "entities": [{{ "type": "...", "name": "...", "attributes": {{}}, "source_trace": {{ "field": "...", "source_text_excerpt": "...", "confidence": 0.0, "reasoning": "..." }} }}],
  "relationships": [{{ "from": "<entity name>", "to": "<entity name>", "type": "...", "attributes": {{}} }}],
  "market_assumptions": [],
  "missing_information": [],
  "risk_signals": [],
  "purchase_triggers": [],
  "adoption_barriers": [],
  "claim_analysis": [{{ "claim": "...", "clarity": "clear|unclear", "credibility": "believable|questionable|unbelievable", "differentiation": "differentiated|generic", "risks": [], "recommended_rewrite": "" }}],
  "channel_analysis": [{{ "channel": "...", "funnel_role": "awareness|comprehension|trial|repeat|diffusion", "fit_score": 0.0, "note": "" }}],
  "claim_clarity_issues": [],
  "claim_credibility_risks": [],
  "price_value_concerns": [],
  "channel_fit_observations": [],
  "social_diffusion_potential": [],
  "competitor_pressure_points": []
}}

STRUCTURED BRIEF FIELDS:
{structured_json}

RAW BRIEF TEXT:
{raw_text}
"""
