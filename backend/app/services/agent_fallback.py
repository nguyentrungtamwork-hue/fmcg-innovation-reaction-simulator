"""Deterministic, ontology-grounded fallback agent generator."""
from __future__ import annotations

import random
from typing import Any

from app.schemas.agent import (
    DEFAULT_DISTRIBUTION_50,
    DEFAULT_SEGMENTS,
    MARKET_ACTOR_ROLES,
    ConsumerAgentProfile,
    MarketActorProfile,
)
from app.schemas.ontology import OntologyPayload
from app.services.agent_templates import MARKET_ACTOR_TEMPLATES, SEGMENT_TEMPLATES


# --- ontology helpers ------------------------------------------------------


def _entities_of(ontology: OntologyPayload, etype: str) -> list[str]:
    return [e.name for e in ontology.entities if e.type == etype]


def _ontology_index(ontology: OntologyPayload) -> dict[str, list[str]]:
    return {
        "competitors": _entities_of(ontology, "CompetitorBrand"),
        "channels": _entities_of(ontology, "Channel"),
        "touchpoints": _entities_of(ontology, "Touchpoint")
        + _entities_of(ontology, "InfluencerOrReviewer"),
        "occasions": _entities_of(ontology, "UsageOccasion"),
        "claims": _entities_of(ontology, "FunctionalClaim")
        + _entities_of(ontology, "EmotionalClaim"),
        "needs": _entities_of(ontology, "NeedState") + _entities_of(ontology, "ProductBenefit"),
        "risks": _entities_of(ontology, "RiskSignal"),
        "pack_signals": _entities_of(ontology, "PackagingSignal"),
        "promo": _entities_of(ontology, "PromotionMechanic"),
        "brand": _entities_of(ontology, "Brand"),
        "product": _entities_of(ontology, "ProductInnovation"),
    }


# --- consumer generation ---------------------------------------------------


def _sample_range(rng: random.Random, lo_hi: tuple[float, float]) -> float:
    lo, hi = lo_hi
    return round(rng.uniform(lo, hi), 3)


def _sample_traits(rng: random.Random, template: dict) -> dict[str, float]:
    ranges = template["traits"]
    out: dict[str, float] = {}
    for k, v in ranges.items():
        if isinstance(v, tuple) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v):
            out[k] = _sample_range(rng, v)  # type: ignore[arg-type]
    # Ensure all 11 numeric traits present (defaults from template _t() guarantee this).
    return out


def _pick(rng: random.Random, items: list[str], k: int) -> list[str]:
    if not items:
        return []
    k = min(k, len(items))
    return rng.sample(items, k)


def _consumer_for_segment(
    rng: random.Random,
    segment: str,
    index: int,
    ontology: OntologyPayload,
    onto_idx: dict[str, list[str]],
) -> tuple[str, ConsumerAgentProfile, list[str]]:
    tpl = SEGMENT_TEMPLATES[segment]
    traits = _sample_traits(rng, tpl)

    # Channel preference: drawn from ontology if available, else generic defaults.
    channels = onto_idx["channels"] or [
        "Convenience store",
        "Supermarket",
        "E-commerce",
    ]
    touchpoints = onto_idx["touchpoints"] or ["TikTok", "Facebook"]
    needs = onto_idx["needs"] or [
        "refreshment",
        "manageable sugar intake",
        "everyday energy",
    ]
    occasions = onto_idx["occasions"] or [
        "mid-afternoon at work",
        "after lunch",
        "commute",
    ]
    competitors = onto_idx["competitors"] or ["mainstream incumbent A", "mainstream incumbent B"]
    claims = onto_idx["claims"]
    risks = ontology.risk_signals + onto_idx["risks"]
    triggers = ontology.purchase_triggers
    barriers = ontology.adoption_barriers

    # Segment-specific phrasing on trial barriers / trust drivers, mixed with ontology gaps.
    trial_barriers: list[str] = []
    trust_drivers: list[str] = []

    if segment == "Health/Safety-Conscious Buyer":
        trial_barriers.append("Skeptical about unsubstantiated 'natural' or cooling claims")
        if claims:
            trial_barriers.append(f"Wants ingredient evidence behind: {claims[0]}")
        trust_drivers += ["Clear ingredient list", "Credible RTB", "Third-party verification"]
    elif segment == "Value-Seeking Practical Buyer":
        trial_barriers.append("Premium price not justified vs current SKU")
        trust_drivers += ["Sustained promo", "Clear price-per-100ml", "Sampling"]
    elif segment == "Brand-Loyal Conservative Buyer":
        if competitors:
            trial_barriers.append(f"Already loyal to: {', '.join(competitors[:2])}")
        trust_drivers += ["Trusted-source endorsement", "Long shelf presence"]
    elif segment == "Convenience-Driven Busy Buyer":
        trial_barriers.append("Will skip if not visible in usual CVS")
        trust_drivers += ["Wide availability", "Fast checkout", "Eye-level shelf"]
    elif segment == "Early Adopter / Trend-Seeker":
        trial_barriers.append("Will lose interest if the launch feels derivative")
        trust_drivers += ["Creator hype", "Limited drops", "Distinctive pack"]
    elif segment == "Family Decision Maker":
        trial_barriers.append("Pack size may be wrong for family use")
        if claims:
            trial_barriers.append(f"Will check whether kids accept the taste behind: {claims[0]}")
        trust_drivers += ["Family-friendly pack", "Trusted supermarket placement"]
    elif segment == "Skeptical Reviewer-Dependent Buyer":
        trial_barriers.append("Will not buy until trusted reviewer confirms")
        trust_drivers += ["Long-tail review sentiment", "Comments-section signal"]
    elif segment == "Promotion-Driven Trial Buyer":
        trial_barriers.append("Will wait for a BOGO or sample")
        trust_drivers += ["Stacked promo", "Loyalty stamps", "Sampling booth"]

    if risks:
        trial_barriers.append(f"Concerned about: {risks[0]}")
    if barriers:
        trial_barriers.append(barriers[0])
    if triggers:
        trust_drivers.append(triggers[0])

    # Need states + emotional triggers grounded in ontology
    chosen_needs = _pick(rng, needs, min(3, len(needs))) or tpl.get("category_pain_points", [])
    chosen_occasions = _pick(rng, occasions, min(2, len(occasions)))
    chosen_channels = _pick(rng, channels, min(2, len(channels)))
    chosen_touchpoints = _pick(rng, touchpoints, min(2, len(touchpoints)))

    initial_memory = []
    brand = onto_idx["brand"][0] if onto_idx["brand"] else None
    product = onto_idx["product"][0] if onto_idx["product"] else None
    if brand:
        initial_memory.append(f"Aware of {brand} as a category brand at low salience.")
    if competitors:
        initial_memory.append(f"Currently buys {competitors[0]} as a default in the category.")
    initial_memory.append(f"Belongs to segment: {segment}.")

    grounding_sources: list[str] = []
    if claims:
        grounding_sources.append(f"FunctionalClaim: {claims[0]}")
    if competitors:
        grounding_sources.append(f"CompetitorBrand: {competitors[0]}")
    if chosen_channels:
        grounding_sources.append(f"Channel: {chosen_channels[0]}")
    if risks:
        grounding_sources.append(f"RiskSignal: {risks[0]}")
    if chosen_occasions:
        grounding_sources.append(f"UsageOccasion: {chosen_occasions[0]}")

    profile = ConsumerAgentProfile(
        segment_description=(f"{tpl['archetype']} — evaluating {product}." if product else tpl["archetype"]),
        age_range=tpl["age_range"],
        household_context=tpl["household_context"],
        lifestyle_context=tpl["lifestyle_context"],
        category_usage_frequency=tpl["category_usage_frequency"],
        current_brand_repertoire=competitors[:2] if competitors else [],
        current_purchase_channel=chosen_channels,
        category_pain_points=list(tpl["category_pain_points"]),
        need_states=chosen_needs,
        usage_occasions=chosen_occasions,
        channel_preference=chosen_channels,
        media_touchpoints=chosen_touchpoints,
        trust_drivers=trust_drivers[:5],
        trial_barriers=trial_barriers[:5],
        repeat_purchase_drivers=list(tpl["repeat_purchase_drivers"]),
        likely_objections=list(tpl["likely_objections"]),
        emotional_triggers=list(tpl["emotional_triggers"]),
        initial_memory=initial_memory,
        grounding_sources=grounding_sources,
        **traits,
    )

    # Name: deterministic, non-identifying.
    short = "".join(w[0] for w in segment.replace("/", " ").split() if w)[:4].upper()
    name = f"Consumer-{short}-{index:03d}"
    if product:
        initial_memory.append(f"Heard early buzz about {product}." if rng.random() < 0.4 else "")
        profile.initial_memory = [m for m in profile.initial_memory if m]

    return name, profile, grounding_sources


def generate_consumers(
    rng: random.Random,
    ontology: OntologyPayload,
    distribution: dict[str, int],
) -> list[tuple[str, str, ConsumerAgentProfile]]:
    """Return list of (name, segment_name, profile)."""
    onto_idx = _ontology_index(ontology)
    out: list[tuple[str, str, ConsumerAgentProfile]] = []
    counter = 1
    for segment, n in distribution.items():
        if segment not in SEGMENT_TEMPLATES:
            continue
        for _ in range(n):
            name, profile, _g = _consumer_for_segment(rng, segment, counter, ontology, onto_idx)
            out.append((name, segment, profile))
            counter += 1
    return out


# --- market actor generation -----------------------------------------------


def generate_market_actors(
    rng: random.Random, ontology: OntologyPayload
) -> list[tuple[str, str, MarketActorProfile]]:
    """Return list of (name, role, profile)."""
    onto_idx = _ontology_index(ontology)
    competitor_pressure = ontology.competitor_pressure_points
    diffusion = ontology.social_diffusion_potential
    claim_risks = ontology.claim_credibility_risks
    channel_fit = ontology.channel_fit_observations
    competitor_names = onto_idx["competitors"]

    out: list[tuple[str, str, MarketActorProfile]] = []
    for role in MARKET_ACTOR_ROLES:
        tpl = MARKET_ACTOR_TEMPLATES[role]
        grounding: list[str] = []
        memory: list[str] = []
        likely_actions = list(tpl["likely_actions"])
        risk_to_launch = list(tpl["risk_to_launch"])

        if role == "Retailer":
            if onto_idx["channels"]:
                grounding.append(f"Channel: {onto_idx['channels'][0]}")
                memory.append(
                    f"Will judge launch on first 8 weeks of rotation in {onto_idx['channels'][0]}."
                )
            if channel_fit:
                risk_to_launch.append(channel_fit[0])

        elif role == "Competitor":
            if competitor_names:
                grounding.append(f"CompetitorBrand: {competitor_names[0]}")
                memory.append(f"Defends against new entrant by leaning on {competitor_names[0]}.")
            if competitor_pressure:
                risk_to_launch.append(competitor_pressure[0])

        elif role == "Influencer":
            if onto_idx["touchpoints"]:
                grounding.append(f"Touchpoint: {onto_idx['touchpoints'][0]}")
            if claim_risks:
                risk_to_launch.append(f"Will probe: {claim_risks[0]}")
            if diffusion:
                memory.append(diffusion[0])

        elif role == "SocialCommunity":
            if diffusion:
                grounding.append(f"DiffusionNote: {diffusion[0]}")
            if ontology.adoption_barriers:
                memory.append(f"Likely topic: {ontology.adoption_barriers[0]}")

        elif role == "CategoryExpert":
            for c in ontology.claim_analysis[:2]:
                grounding.append(f"ClaimAnalysis: {c.claim} ({c.credibility})")
                if c.credibility != "believable":
                    risk_to_launch.append(f"Will challenge claim: {c.claim}")

        profile = MarketActorProfile(
            objective=tpl["objective"],
            influence_power=tpl["influence_power"],
            trust_level=tpl["trust_level"],
            likely_actions=likely_actions,
            risk_to_launch=risk_to_launch,
            positive_contribution=list(tpl["positive_contribution"]),
            evaluation_criteria=list(tpl["evaluation_criteria"]),
            initial_memory=memory or [f"{role} baseline posture."],
            grounding_sources=grounding,
        )
        out.append((tpl["name"], role, profile))
    return out


def _ontology_blob(ontology: OntologyPayload) -> str:
    parts = (
        _entities_of(ontology, "FunctionalClaim")
        + _entities_of(ontology, "EmotionalClaim")
        + _entities_of(ontology, "ProductInnovation")
        + _entities_of(ontology, "ProductBenefit")
        + _entities_of(ontology, "NeedState")
        + list(ontology.purchase_triggers)
        + list(ontology.adoption_barriers)
        + list(ontology.price_value_concerns)
        + list(ontology.risk_signals)
    )
    return " ".join(parts).lower()


# Per-category tilt — gives each product CATEGORY a distinct consumer-mix fingerprint,
# so e.g. a snack and a beverage differ even when both are "healthy + promo + premium".
_CATEGORY_TILT: dict[str, dict[str, float]] = {
    "snack": {"Family Decision Maker": 1.35, "Convenience-Driven Busy Buyer": 1.3, "Promotion-Driven Trial Buyer": 1.15},
    "beverage": {"Early Adopter / Trend-Seeker": 1.3, "Convenience-Driven Busy Buyer": 1.3, "Promotion-Driven Trial Buyer": 1.1},
    "dairy": {"Health/Safety-Conscious Buyer": 1.3, "Family Decision Maker": 1.35},
    "skincare": {"Skeptical Reviewer-Dependent Buyer": 1.55, "Early Adopter / Trend-Seeker": 1.35},
    "personal care": {"Health/Safety-Conscious Buyer": 1.3, "Skeptical Reviewer-Dependent Buyer": 1.25},
    "household cleaning": {"Value-Seeking Practical Buyer": 1.3, "Family Decision Maker": 1.3},
}


def _signal_multipliers(ontology: OntologyPayload) -> dict[str, float]:
    """Per-segment tilt derived from the product's ontology (deterministic, text-driven)."""
    from app.services.simulation_scoring import _infer_category

    blob = _ontology_blob(ontology)
    has = lambda words: any(w in blob for w in words)  # noqa: E731

    mult = {s: 1.0 for s in DEFAULT_DISTRIBUTION_50}

    # 1) category fingerprint (breaks ties between similarly-positioned products)
    category, _unit = _infer_category(blob)
    for seg, factor in _CATEGORY_TILT.get(category, {}).items():
        mult[seg] *= factor

    # 2) claim/positioning signals
    if has(("sugar", "health", "natural", "protein", "fiber", "fibre", "less fat", "vitamin", "gut", "wellness", "herbal", "organic")):
        mult["Health/Safety-Conscious Buyer"] *= 1.55
    if has(("promo", "sampl", "bogo", "discount", "loyalty", "trial price", "introductory")):
        mult["Promotion-Driven Trial Buyer"] *= 1.6
        mult["Value-Seeking Practical Buyer"] *= 1.15
    if has(("premium", "pricey", "price barrier", "expensive", "masstige")):
        mult["Value-Seeking Practical Buyer"] *= 1.25
        mult["Brand-Loyal Conservative Buyer"] *= 1.12
    if has(("tiktok", "influencer", "creator", "social", "review", "kol", "viral", "trend", "skinfluencer")) or ontology.social_diffusion_potential:
        mult["Early Adopter / Trend-Seeker"] *= 1.3
        mult["Skeptical Reviewer-Dependent Buyer"] *= 1.2
    if has(("convenience", "cvs", "grab-and-go", "grab and go", "on-the-go", "busy", "commute", "transit")):
        mult["Convenience-Driven Busy Buyer"] *= 1.35
    return mult


def ontology_weighted_distribution(ontology: OntologyPayload, consumer_count: int) -> dict[str, int]:
    """Product-specific consumer mix. Keeps the 8 canonical archetypes (so scoring weights
    are unchanged) but tilts how many agents fall in each, based on ontology signals."""
    mult = _signal_multipliers(ontology)
    base_total = sum(DEFAULT_DISTRIBUTION_50.values())
    weights = {s: (DEFAULT_DISTRIBUTION_50[s] / base_total) * mult[s] for s in DEFAULT_DISTRIBUTION_50}
    wtotal = sum(weights.values()) or 1.0
    # initial allocation, every segment gets at least 1
    alloc = {s: max(1, round(weights[s] / wtotal * consumer_count)) for s in DEFAULT_DISTRIBUTION_50}
    # fix drift to sum exactly == consumer_count, adjusting the largest/smallest deterministically
    drift = consumer_count - sum(alloc.values())
    order = sorted(DEFAULT_DISTRIBUTION_50, key=lambda s: (-weights[s], s))
    i = 0
    guard = 0
    while drift != 0 and guard < 100000:
        s = order[i % len(order)] if drift > 0 else order[-1 - (i % len(order))]
        if drift > 0:
            alloc[s] += 1
            drift -= 1
        elif alloc[s] > 1:
            alloc[s] -= 1
            drift += 1
        i += 1
        guard += 1
    return alloc


def fallback_generate(
    ontology: OntologyPayload,
    consumer_count: int,
    include_market_actors: bool,
    segment_distribution: dict[str, int] | None,
    seed: int,
) -> dict[str, Any]:
    """Top-level fallback entry point."""
    rng = random.Random(seed)
    dist = segment_distribution or ontology_weighted_distribution(ontology, consumer_count)
    consumers = generate_consumers(rng, ontology, dist)
    market_actors = generate_market_actors(rng, ontology) if include_market_actors else []
    return {"consumers": consumers, "market_actors": market_actors, "distribution": dist}


def _scaled_distribution(consumer_count: int) -> dict[str, int]:
    if consumer_count == 50:
        return dict(DEFAULT_DISTRIBUTION_50)
    # Scale proportionally, then fix rounding so it sums to consumer_count.
    total = sum(DEFAULT_DISTRIBUTION_50.values())
    scaled = {k: max(1, round(v * consumer_count / total)) for k, v in DEFAULT_DISTRIBUTION_50.items()}
    drift = consumer_count - sum(scaled.values())
    keys = list(scaled.keys())
    i = 0
    while drift != 0 and keys:
        step = 1 if drift > 0 else -1
        if scaled[keys[i % len(keys)]] + step >= 1:
            scaled[keys[i % len(keys)]] += step
            drift -= step
        i += 1
        if i > 10000:
            break
    return scaled
