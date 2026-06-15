"""Deterministic fallback ontology extractor.

Used when no LLM API key is configured (e.g., during testing or offline runs).
The output is intentionally less rich than an LLM extraction but still produces
a valid, useful `OntologyPayload` for the sample brief and any structured
brief that supplies the standard fields.
"""
from __future__ import annotations

import re

from app.schemas.ontology import (
    ChannelObservation,
    ClaimAnalysisItem,
    OntologyEntity,
    OntologyPayload,
    OntologyRelationship,
    SourceTrace,
)

# --- helpers ----------------------------------------------------------------

_CHANNEL_FUNNEL_ROLE = {
    "tiktok": "awareness",
    "tiktok shop": "trial",
    "facebook": "awareness",
    "instagram": "awareness",
    "kol": "comprehension",
    "supermarket": "trial",
    "convenience store": "trial",
    "convenience": "trial",
    "e-commerce": "trial",
    "ecommerce": "trial",
    "sampling": "trial",
    "word-of-mouth": "diffusion",
}


def _trace(field: str, excerpt: str | None, reasoning: str, conf: float = 0.6) -> SourceTrace:
    return SourceTrace(
        field=field,
        source_text_excerpt=(excerpt[:160] if excerpt else None),
        reasoning=reasoning,
        confidence=conf,
    )


def _add(entities: list[OntologyEntity], etype: str, name: str, trace: SourceTrace, **attrs) -> str:
    """Add an entity if not already present (by type+name); return its name."""
    if not name:
        return ""
    for e in entities:
        if e.type == etype and e.name.lower() == name.lower():
            return e.name
    entities.append(OntologyEntity(type=etype, name=name, attributes=attrs, source_trace=trace))
    return name


def _rel(rels: list[OntologyRelationship], a: str, b: str, rtype: str) -> None:
    if not a or not b:
        return
    rels.append(OntologyRelationship.model_validate({"from": a, "to": b, "type": rtype}))


# --- main entrypoint --------------------------------------------------------


def fallback_extract(raw_text: str, structured: dict) -> OntologyPayload:
    entities: list[OntologyEntity] = []
    relationships: list[OntologyRelationship] = []
    missing: list[str] = []
    assumptions: list[str] = []
    triggers: list[str] = []
    barriers: list[str] = []
    risks: list[str] = []
    claim_items: list[ClaimAnalysisItem] = []
    channel_items: list[ChannelObservation] = []
    claim_clarity: list[str] = []
    claim_cred: list[str] = []
    price_concerns: list[str] = []
    channel_fit: list[str] = []
    diffusion: list[str] = []
    competitor_pressure: list[str] = []

    text = raw_text or ""
    s = structured or {}

    # --- Brand & product
    brand = s.get("brand") or _grep_after(text, r"brand\s*[:\-]\s*(.+)")
    product = s.get("product_name") or _grep_after(text, r"product\s*[:\-]\s*(.+)")
    category = s.get("category") or _grep_after(text, r"category\s*[:\-]\s*(.+)")
    market = s.get("launch_market") or _grep_after(text, r"launch\s*market\s*[:\-]\s*(.+)")

    brand_n = _add(entities, "Brand", brand or "", _trace("brand", brand or text[:120], "brand field"))
    prod_n = _add(
        entities, "ProductInnovation", product or "", _trace("product_name", product, "product field")
    )
    cat_n = _add(entities, "Category", category or "", _trace("category", category, "category field"))

    if not brand:
        missing.append("brand_name_unclear")
    if not product:
        missing.append("product_name_unclear")
    if not category:
        missing.append("category_unclear")

    # --- Target segment
    target = s.get("target_consumers") or _grep_after(text, r"target\s*consumers?\s*[:\-]\s*(.+)")
    if target:
        seg = _add(
            entities,
            "ConsumerSegment",
            target.split(",")[0].strip()[:80] or "Primary target",
            _trace("target_consumers", target, "target field"),
            description=target,
        )
        if prod_n:
            _rel(relationships, prod_n, seg, "TARGETS")
    else:
        missing.append("target_audience_unclear")

    # --- Claims
    for fc in s.get("functional_claims", []) or []:
        name = _add(
            entities,
            "FunctionalClaim",
            fc,
            _trace("functional_claims", fc, "from structured claim list", 0.8),
        )
        if prod_n:
            _rel(relationships, prod_n, name, "CLAIMS_TO_SOLVE")
        claim_items.append(_score_claim(fc))
    for ec in s.get("emotional_claims", []) or []:
        _add(entities, "EmotionalClaim", ec, _trace("emotional_claims", ec, "from structured list", 0.7))
        claim_items.append(_score_claim(ec, emotional=True))

    if not s.get("functional_claims"):
        missing.append("functional_claim_unclear")
        claim_clarity.append("No explicit functional claim provided in the brief.")

    # --- Benefit
    benefit = s.get("benefit") or _grep_after(text, r"benefit\s*[:\-]\s*(.+)")
    if benefit:
        _add(entities, "ProductBenefit", benefit[:120], _trace("benefit", benefit, "benefit field", 0.7))
    else:
        missing.append("benefit_unclear")

    # --- Price
    price = s.get("price") or _grep_after(text, r"price\s*[:\-]\s*(.+)")
    if price:
        _add(
            entities,
            "PricePoint",
            str(price)[:80],
            _trace("price", str(price), "price field", 0.7),
        )
        if re.search(r"premium|slightly\s*more|higher", str(price), re.I) or re.search(
            r"premium", text, re.I
        ):
            price_concerns.append(
                "Premium positioning may suppress trial in value-seeking segment without strong RTB."
            )
            barriers.append("Premium price vs mainstream alternatives")
    else:
        missing.append("price_unclear")

    # --- Pack size
    pack_size = s.get("pack_size")
    if pack_size:
        _add(entities, "PackSize", str(pack_size), _trace("pack_size", str(pack_size), "pack_size field"))
    else:
        missing.append("pack_size_unclear")

    # --- Packaging
    packaging = s.get("packaging")
    if packaging:
        _add(
            entities,
            "PackagingSignal",
            (packaging[:80] if isinstance(packaging, str) else "Packaging"),
            _trace("packaging", str(packaging), "packaging field"),
            description=packaging,
        )
    else:
        missing.append("packaging_unclear")

    # --- Channels
    channels = s.get("channels", []) or _split_csv_after(text, r"channels?\s*[:\-]\s*(.+)")
    for ch in channels:
        ch_clean = str(ch).strip()
        ch_name = _add(entities, "Channel", ch_clean, _trace("channels", ch_clean, "channel field"))
        if prod_n:
            _rel(relationships, prod_n, ch_name, "IS_SOLD_THROUGH")
        role = _channel_role(ch_clean)
        channel_items.append(
            ChannelObservation(
                channel=ch_clean,
                funnel_role=role,
                fit_score=0.6,
                note=f"Inferred funnel role: {role}.",
            )
        )
    if not channels:
        missing.append("channel_plan_unclear")
    else:
        roles = {c.funnel_role for c in channel_items}
        if "trial" not in roles:
            channel_fit.append("No trial-conversion channel detected (shelf / e-commerce / sampling).")
        if "diffusion" not in roles:
            channel_fit.append("No diffusion channel (word-of-mouth, community).")

    # --- Usage occasions
    for oc in s.get("usage_occasions", []) or []:
        oc_name = _add(entities, "UsageOccasion", oc, _trace("usage_occasions", oc, "occasion field"))
        if prod_n:
            _rel(relationships, prod_n, oc_name, "USED_IN_OCCASION")
    if not s.get("usage_occasions"):
        missing.append("usage_occasion_unclear")

    # --- Competitors
    for cm in s.get("competitors", []) or []:
        cm_name = _add(entities, "CompetitorBrand", cm, _trace("competitors", cm, "competitors field"))
        if prod_n:
            _rel(relationships, prod_n, cm_name, "COMPETES_WITH")
        competitor_pressure.append(
            f"{cm}: may respond with price/promo or comparative claim content."
        )
    if not s.get("competitors"):
        missing.append("competitor_set_unclear")

    # --- Promotion + sampling
    if s.get("promotion_plan"):
        _add(
            entities,
            "PromotionMechanic",
            "Launch promotion",
            _trace("promotion_plan", str(s.get("promotion_plan")), "promotion_plan field"),
            description=s.get("promotion_plan"),
        )
        triggers.append("Launch-month promotion lowers trial risk.")
    else:
        missing.append("promotion_plan_missing")
    if not s.get("sampling_plan"):
        missing.append("sampling_plan_missing")
    else:
        triggers.append("Sampling plan removes sensory risk for skeptical buyers.")

    # --- Touchpoints inferred from media plan + channels
    media = s.get("media_plan") or ""
    if re.search(r"tiktok", text + media, re.I):
        _add(entities, "Touchpoint", "TikTok short video", _trace("media_plan", "tiktok", "media plan"))
        diffusion.append("TikTok creator content has high social-diffusion potential among 22–35 urban segment.")
    if re.search(r"kol|influencer", text + media, re.I):
        _add(
            entities,
            "InfluencerOrReviewer",
            "KOL partnerships",
            _trace("media_plan", "kol", "media plan"),
        )
        triggers.append("KOL endorsement boosts credibility for skeptical segments.")

    # --- Risks
    for r in s.get("known_risks", []) or []:
        risks.append(r)
        _add(entities, "RiskSignal", r[:120], _trace("known_risks", r, "known_risks field"))
        low = r.lower()
        if "taste" in low or "sensory" in low or "medicinal" in low:
            barriers.append("Sensory acceptability risk (taste/texture).")
            claim_cred.append("Sensory expectation must be managed pre-trial.")
        if "premium" in low or "price" in low:
            barriers.append("Price barrier flagged in brief.")
            price_concerns.append(r)
        if "believe" in low or "credib" in low or "natural" in low:
            claim_cred.append(r)
            claim_clarity.append("Claim credibility flagged by team itself.")

    # --- Triggers/barriers heuristics
    if any(re.search(r"less\s*sugar|low\s*sugar|natural", c.claim, re.I) for c in claim_items):
        triggers.append("Health-leaning claim ('less sugar', 'natural') resonates with health-conscious segment.")
    if any(re.search(r"premium", str(price or ""), re.I) for _ in [0]):
        pass  # already handled

    # --- Strategic notes
    if any(c.credibility != "believable" for c in claim_items):
        risks.append("One or more claims may be challenged on credibility.")
    if not triggers:
        triggers.append("No strong trigger detected — investigate primary purchase motivator.")
    if not barriers:
        barriers.append("No explicit barrier detected — may be hidden; validate via consumer research.")

    # --- Assumptions
    if target:
        assumptions.append(f"Target audience interpreted as: {target[:120]}")
    if market:
        assumptions.append(f"Launch market interpreted as: {market[:120]}")

    return OntologyPayload(
        entities=entities,
        relationships=relationships,
        market_assumptions=assumptions,
        missing_information=sorted(set(missing)),
        risk_signals=risks,
        purchase_triggers=triggers,
        adoption_barriers=barriers,
        claim_analysis=claim_items,
        channel_analysis=channel_items,
        claim_clarity_issues=claim_clarity,
        claim_credibility_risks=claim_cred,
        price_value_concerns=price_concerns,
        channel_fit_observations=channel_fit,
        social_diffusion_potential=diffusion,
        competitor_pressure_points=competitor_pressure,
    )


# --- private helpers --------------------------------------------------------


def _grep_after(text: str, pattern: str) -> str | None:
    m = re.search(pattern, text or "", re.I)
    if not m:
        return None
    return m.group(1).strip().splitlines()[0].strip()


def _split_csv_after(text: str, pattern: str) -> list[str]:
    raw = _grep_after(text, pattern)
    if not raw:
        return []
    return [p.strip() for p in re.split(r"[,;|]", raw) if p.strip()]


def _channel_role(ch: str) -> str:
    low = ch.lower()
    for k, v in _CHANNEL_FUNNEL_ROLE.items():
        if k in low:
            return v
    return "awareness"


def _score_claim(claim: str, emotional: bool = False) -> ClaimAnalysisItem:
    low = claim.lower()
    clarity = "clear" if len(claim.split()) <= 12 else "unclear"
    credibility = "believable"
    if any(w in low for w in ("naturally cooling", "boost", "miracle", "cures", "guaranteed")):
        credibility = "questionable"
    differentiation = "generic"
    if any(w in low for w in ("less sugar", "no artificial", "chrysanthemum", "mulberry", "herbal", "cooling")):
        differentiation = "differentiated"
    risks = []
    if credibility != "believable":
        risks.append("RTB needed to support credibility.")
    if clarity == "unclear":
        risks.append("Phrasing too long; may not parse in 3 seconds at shelf.")
    return ClaimAnalysisItem(
        claim=claim,
        clarity=clarity,
        credibility=credibility,
        differentiation=differentiation,
        risks=risks,
        recommended_rewrite=None,
    )
