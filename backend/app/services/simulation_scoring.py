"""Deterministic FMCG launch scoring engine.

Given an agent profile, the ontology-derived market context, the round stage,
and a small seeded jitter, this module produces:
  - a dict of perception/decision scores (all bounded as documented in SCORING_LOGIC.md)
  - a chosen action_type (rule-based on the scores)
  - grounded reasoning text + a first-person reaction
  - emotional_tone, barrier_detected, trigger_detected

The engine is intentionally NOT random-only: scores are a transparent function
of agent traits and ontology signals. A tiny seeded jitter (±0.04) breaks ties
between otherwise-identical agents without destabilizing tests (counts, ranges,
and action diversity remain stable).
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field

from app.schemas.ontology import OntologyPayload

ROUND_STAGES: dict[int, str] = {
    1: "Pre-launch concept exposure",
    2: "Launch communication exposure",
    3: "Shelf / e-commerce exposure",
    4: "Trial decision",
    5: "Post-trial reaction",
    6: "Social diffusion and market feedback",
}

ROUND_TOUCHPOINTS: dict[int, list[str]] = {
    1: ["TikTok short video", "Facebook post"],
    2: ["Facebook ad", "KOL review", "TikTok short video"],
    3: ["Supermarket shelf", "Convenience store display", "TikTok Shop / e-commerce product page"],
    4: ["Sampling booth", "TikTok Shop / e-commerce product page", "Convenience store display"],
    5: ["Word-of-mouth conversation", "Consumer review section"],
    6: [
        "Word-of-mouth conversation",
        "TikTok short video",
        "Consumer review section",
        "Competitor comparison content",
    ],
}

# Social-proof baseline per round (before scaling by the agent's sensitivity).
_SOCIAL_PROOF_BY_ROUND: dict[int, float] = {1: 0.10, 2: 0.22, 3: 0.32, 4: 0.45, 5: 0.55, 6: 0.70}

# Per-segment blend weights (see SCORING_LOGIC.md).
SEGMENT_WEIGHTS: dict[str, dict[str, float]] = {
    "Early Adopter / Trend-Seeker": {"intent": 0.30, "find": 0.15, "social": 0.25, "risk": 0.10, "price": 0.10},
    "Value-Seeking Practical Buyer": {"intent": 0.20, "find": 0.20, "social": 0.10, "risk": 0.15, "price": 0.35},
    "Brand-Loyal Conservative Buyer": {"intent": 0.20, "find": 0.15, "social": 0.10, "risk": 0.30, "price": 0.15},
    "Health/Safety-Conscious Buyer": {"intent": 0.30, "find": 0.10, "social": 0.15, "risk": 0.25, "price": 0.10},
    "Convenience-Driven Busy Buyer": {"intent": 0.20, "find": 0.30, "social": 0.15, "risk": 0.10, "price": 0.15},
    "Family Decision Maker": {"intent": 0.22, "find": 0.18, "social": 0.12, "risk": 0.20, "price": 0.28},
    "Skeptical Reviewer-Dependent Buyer": {"intent": 0.18, "find": 0.12, "social": 0.30, "risk": 0.25, "price": 0.15},
    "Promotion-Driven Trial Buyer": {"intent": 0.18, "find": 0.18, "social": 0.14, "risk": 0.10, "price": 0.40},
}
_DEFAULT_WEIGHTS = {"intent": 0.22, "find": 0.18, "social": 0.16, "risk": 0.20, "price": 0.24}


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return round(max(lo, min(hi, x)), 3)


@dataclass
class SimContext:
    brand: str = "the brand"
    product: str = "the new product"
    main_claim: str = ""
    premium: bool = False
    has_promo: bool = False
    has_sampling: bool = False
    health_flag: bool = False
    taste_risk: bool = False
    channels: list[str] = field(default_factory=list)
    claim_clarity: float = 0.7
    claim_credibility: float = 0.7
    differentiation: float = 0.5
    triggers: list[str] = field(default_factory=list)
    barriers: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    risk_intensity: float = 0.3
    # --- product/category voice (TEXT-ONLY; never used in numeric scoring) ---
    category: str = "general"
    unit_noun: str = "pack"
    benefit: str = ""
    # --- scenario-override adjustments (additive nudges; 0.0 = baseline) ---
    price_value_adj: float = 0.0
    social_proof_adj: float = 0.0
    pack_adj: float = 0.0
    channel_adj: float = 0.0
    risk_adj: float = 0.0

    @property
    def top_trigger(self) -> str | None:
        return self.triggers[0] if self.triggers else None

    @property
    def top_barrier(self) -> str | None:
        return self.barriers[0] if self.barriers else None


def _infer_category(blob: str) -> tuple[str, str]:
    """Deterministically map an ontology text blob → (category, unit_noun). Text-only."""
    rules: list[tuple[tuple[str, ...], str, str]] = [
        # NOTE: keep keywords specific — short substrings like "bar"/"nut" are avoided because
        # they greedily match unrelated words ("barrier", "nutrition").
        (("crisp", "chip", "snack", "biscuit", "cracker", "popcorn", "pretzel", "granola bar", "protein bar", "veggie crisp"), "snack", "pack"),
        (("yogurt", "yoghurt", "dairy", "cheese", "kefir"), "dairy", "bottle"),
        (("tea", "juice", "drink", "beverage", "rtd", "water", "coffee", "soda", "kombucha", "smoothie"), "beverage", "bottle"),
        (("serum", "cream", "lotion", "moistur", "spf", "vitamin c", "skin", "cleanser", "toner"), "skincare", "tube"),
        (("shampoo", "soap", "micellar", "wash", "deodor", "toothpaste", "hair"), "personal care", "bottle"),
        (("spray", "cleaner", "detergent", "wipe", "disinfect", "laundry", "surface"), "household cleaning", "spray bottle"),
    ]
    for keys, cat, unit in rules:
        if any(k in blob for k in keys):
            return cat, unit
    return "general", "pack"


def build_context(ontology: OntologyPayload) -> SimContext:
    def names(t: str) -> list[str]:
        return [e.name for e in ontology.entities if e.type == t]

    brand = (names("Brand") or ["the brand"])[0]
    product = (names("ProductInnovation") or ["the new product"])[0]
    claims = names("FunctionalClaim") + names("EmotionalClaim")
    channels = [c.lower() for c in names("Channel")]
    price_entities = " ".join(names("PricePoint")).lower()
    benefits = names("ProductBenefit") + names("NeedState")
    cat_blob = " ".join(
        [product] + claims + benefits + names("Category") + ontology.purchase_triggers
    ).lower()
    category, unit_noun = _infer_category(cat_blob)
    benefit = (benefits[0] if benefits else (claims[0] if claims else "")).strip()

    premium = "premium" in price_entities or any(
        "premium" in c.lower() for c in ontology.price_value_concerns
    )
    has_promo = bool(names("PromotionMechanic")) or any(
        "promo" in t.lower() for t in ontology.purchase_triggers
    )
    has_sampling = any("sampl" in t.lower() for t in ontology.purchase_triggers)
    blob = " ".join(claims + ontology.risk_signals + ontology.adoption_barriers).lower()
    health_flag = any(w in blob for w in ("sugar", "natural", "health", "herbal", "cooling"))
    taste_risk = any(w in blob for w in ("taste", "medicinal", "sensory", "herbal"))

    # claim clarity / credibility / differentiation from the claim_analysis block
    if ontology.claim_analysis:
        clarity_vals = [1.0 if c.clarity == "clear" else 0.45 for c in ontology.claim_analysis]
        cred_map = {"believable": 0.8, "questionable": 0.5, "unbelievable": 0.3}
        cred_vals = [cred_map.get(c.credibility, 0.6) for c in ontology.claim_analysis]
        diff_vals = [0.75 if c.differentiation == "differentiated" else 0.4 for c in ontology.claim_analysis]
        claim_clarity = sum(clarity_vals) / len(clarity_vals)
        claim_credibility = sum(cred_vals) / len(cred_vals)
        differentiation = sum(diff_vals) / len(diff_vals)
    else:
        claim_clarity, claim_credibility, differentiation = 0.6, 0.6, 0.45

    risk_intensity = clamp(0.2 + 0.08 * len(ontology.risk_signals) + 0.05 * len(ontology.adoption_barriers))

    return SimContext(
        brand=brand,
        product=product,
        main_claim=claims[0] if claims else "",
        premium=premium,
        has_promo=has_promo,
        has_sampling=has_sampling,
        health_flag=health_flag,
        taste_risk=taste_risk,
        channels=channels,
        claim_clarity=claim_clarity,
        claim_credibility=claim_credibility,
        differentiation=differentiation,
        triggers=list(ontology.purchase_triggers),
        barriers=list(ontology.adoption_barriers),
        risks=list(ontology.risk_signals),
        risk_intensity=risk_intensity,
        category=category,
        unit_noun=unit_noun,
        benefit=benefit,
    )


def _t(profile: dict, key: str, default: float = 0.5) -> float:
    v = profile.get(key, default)
    return float(v) if isinstance(v, (int, float)) else default


def _channel_match(profile: dict, ctx: SimContext) -> float:
    prefs = [c.lower() for c in profile.get("channel_preference", [])]
    if not prefs or not ctx.channels:
        return 0.5
    hit = any(any(tok in ch or ch in tok for tok in ctx.channels) for ch in prefs)
    return 1.0 if hit else 0.35


def _emotional_tone(sentiment: float) -> str:
    if sentiment >= 0.72:
        return "enthusiastic"
    if sentiment >= 0.58:
        return "positive"
    if sentiment >= 0.45:
        return "curious"
    if sentiment >= 0.32:
        return "hesitant"
    return "skeptical"


def choose_touchpoint(profile: dict, pool: list[str], idx: int) -> str:
    prefs = [c.lower() for c in profile.get("channel_preference", []) + profile.get("media_touchpoints", [])]
    for tp in pool:
        low = tp.lower()
        if any(tok.split()[0] in low or low.split()[0] in tok for tok in prefs if tok):
            return tp
    return pool[idx % len(pool)]


# --- main scoring per round -------------------------------------------------


def score_round(
    profile: dict,
    segment: str,
    ctx: SimContext,
    round_no: int,
    state: dict,
    idx: int,
    seed: int,
) -> dict:
    """Return a full event dict for one consumer agent in one round.

    `state` carries cross-round memory (interest, credibility, trial_prob,
    purchased, satisfaction). It is mutated in place.
    """
    rng = random.Random(seed * 1009 + idx * 31 + round_no)
    jitter = rng.uniform(-0.04, 0.04)

    novelty = _t(profile, "novelty_seeking_level")
    loyalty = _t(profile, "brand_loyalty_level")
    skeptic = _t(profile, "claim_skepticism_level")
    health = _t(profile, "health_safety_concern_level")
    price_sens = _t(profile, "price_sensitivity")
    promo_sens = _t(profile, "promotion_sensitivity")
    social_sens = _t(profile, "social_influence_sensitivity")
    review_dep = _t(profile, "review_dependency_level")
    convenience = _t(profile, "convenience_need_level")
    pack_sens = _t(profile, "packaging_sensitivity")
    taste_imp = _t(profile, "taste_or_sensory_importance")

    ch_match = _channel_match(profile, ctx)
    social_proof = clamp(_SOCIAL_PROOF_BY_ROUND[round_no] * (0.5 + 0.5 * social_sens) + ctx.social_proof_adj)

    # --- perception scores (round-agnostic base) ---
    relevance = clamp(
        0.35
        + 0.25 * novelty
        + (0.20 * health if ctx.health_flag else 0.0)
        - 0.12 * loyalty
        + (0.10 if ctx.triggers else 0.0)
        + jitter
    )
    clarity = clamp(ctx.claim_clarity - 0.12 * skeptic + jitter)
    credibility = clamp(ctx.claim_credibility * (1.0 - 0.5 * skeptic) + jitter)
    if ctx.premium:
        price_value = clamp(0.75 - 0.55 * price_sens + (0.15 if ctx.has_promo else 0.0) + ctx.price_value_adj + jitter)
    else:
        price_value = clamp(0.85 - 0.25 * price_sens + (0.10 if ctx.has_promo else 0.0) + ctx.price_value_adj + jitter)
    channel_fit = clamp(0.35 + 0.45 * ch_match + 0.15 * convenience + ctx.channel_adj + jitter)
    pack_appeal = clamp(0.5 + 0.3 * pack_sens + ctx.pack_adj + jitter)
    awareness = clamp(0.3 + 0.35 * social_sens + 0.2 * novelty + 0.15 * ch_match + jitter)
    risk = clamp(ctx.risk_intensity * (0.6 + 0.4 * skeptic) + (0.1 * price_sens if ctx.premium else 0.0) + ctx.risk_adj)

    # composites (additive blends — keep signal spread instead of collapsing to ~0)
    interest = clamp(0.2 + 0.5 * relevance + 0.3 * clarity)
    intent_signal = clamp(0.5 * interest + 0.3 * credibility + 0.2 * ctx.differentiation)
    findability = clamp(channel_fit * (0.6 + 0.4 * pack_appeal))

    state.setdefault("interest", interest)
    state["interest"] = interest
    state["credibility"] = credibility
    state["findability"] = findability

    w = SEGMENT_WEIGHTS.get(segment, _DEFAULT_WEIGHTS)
    pos = w["intent"] * intent_signal + w["find"] * findability + w["social"] * social_proof
    pos_norm = pos / (w["intent"] + w["find"] + w["social"])
    price_gap = 1.0 - price_value
    penalty = (w["risk"] * risk + w["price"] * price_gap) / (w["risk"] + w["price"])
    trial_prob = clamp(pos_norm - 0.35 * penalty + (0.10 if (ctx.has_promo and promo_sens > 0.6) else 0.0))

    # defaults carried out
    purchase_intent = trial_prob
    repeat_prob = state.get("repeat_prob", 0.0)
    trust_change = clamp(
        0.12 * (credibility - 0.5) - 0.18 * risk + (0.06 if ctx.top_trigger else 0.0), -0.3, 0.3
    )
    barrier = None
    trigger = None
    action = "view"
    reaction = ""
    round_metric = interest

    # --- round-specific decision ---
    if round_no == 1:
        round_metric = interest
        if interest >= 0.55 and awareness >= 0.45:
            action = "like" if social_sens > 0.5 else "save_for_later"
        elif interest >= 0.4:
            action = "view"
        elif interest >= 0.3:
            action = "comment_positive" if relevance > 0.5 else "ignore"
        else:
            action = "ignore" if novelty < 0.5 else "comment_negative"
        if action in ("ignore", "comment_negative"):
            barrier = ctx.top_barrier or "concept not relevant to need state"
        else:
            trigger = ctx.top_trigger or "novelty / category curiosity"
        reaction = _react(action, ctx, segment, "concept")

    elif round_no == 2:
        round_metric = intent_signal
        if review_dep > 0.65 and credibility < 0.7:
            action = "request_review"
            barrier = "wants trusted reviews before trusting the claim"
        elif intent_signal >= 0.5 and clarity >= 0.55:
            action = "like" if social_sens > 0.5 else "save_for_later"
            trigger = ctx.top_trigger or f"clear benefit: {ctx.main_claim or 'core claim'}"
        elif price_sens > 0.6:
            action = "ask_price"
            barrier = "needs to know the price before considering"
        elif skeptic > 0.6 or credibility < 0.5:
            action = "comment_negative"
            barrier = ctx.top_barrier or "claim credibility doubt"
        else:
            action = "compare_with_current_brand"
            barrier = "comparing against current repertoire"
        reaction = _react(action, ctx, segment, "comms")

    elif round_no == 3:
        round_metric = findability
        has_commerce = any("commerce" in c or "shop" in c or "tiktok" in c for c in ctx.channels)
        if promo_sens > 0.6 and ctx.has_promo and trial_prob < 0.55:
            action = "wait_for_promotion"
            trigger = "promotion-driven trial intent"
        elif findability >= 0.55 and trial_prob >= 0.5 and has_commerce:
            action = "add_to_cart"
            trigger = "good visibility + intent to buy online"
        elif findability >= 0.5:
            action = "ask_where_to_buy"
            trigger = "wants to find it in a preferred channel"
        elif findability >= 0.35:
            action = "compare_with_current_brand"
            barrier = "weighing against shelf alternatives"
        else:
            action = "ignore"
            barrier = ctx.top_barrier or "not visible in preferred channel"
        reaction = _react(action, ctx, segment, "shelf")

    elif round_no == 4:
        round_metric = trial_prob
        if trial_prob >= 0.48:
            action = "purchase_trial"
            trigger = ctx.top_trigger or "benefit + acceptable risk"
            state["purchased"] = True
        elif trial_prob >= 0.3:
            if promo_sens > 0.55:
                action = "wait_for_promotion"
                trigger = "would try under promotion"
            elif review_dep > 0.55:
                action = "request_review"
                barrier = "needs review validation before trial"
            else:
                action = "compare_with_current_brand"
                barrier = ctx.top_barrier or "not yet convinced vs current brand"
        else:
            action = "reject_before_trial"
            barrier = ctx.top_barrier or ("premium price" if ctx.premium and price_sens > 0.5 else "low relevance / trust")
        purchase_intent = trial_prob
        reaction = _react(action, ctx, segment, "trial")

    elif round_no == 5:
        round_metric = state.get("trial_prob", trial_prob)
        if state.get("purchased"):
            sensory_gap = (0.2 * taste_imp) if ctx.taste_risk else 0.05
            satisfaction = clamp(0.45 + 0.3 * credibility + 0.15 * (1 - skeptic) - sensory_gap + jitter)
            state["satisfaction"] = satisfaction
            occasion_rep = 0.6 + 0.4 * (1 - price_sens if ctx.premium else 0.5)
            repeat_prob = clamp(satisfaction * occasion_rep)
            if satisfaction >= 0.55 and repeat_prob >= 0.45:
                action = "repeat_purchase_intent" if loyalty > 0.4 else "recommend"
                trigger = "trial met expectations"
            elif satisfaction >= 0.42:
                action = "no_repeat_intent"
                barrier = "satisfaction not high enough to commit to repeat"
            else:
                action = "complain"
                barrier = "taste / value disappointment after trial" if ctx.taste_risk else "did not meet expectations"
            reaction = _react(action, ctx, segment, "post_trial")
        else:
            satisfaction = 0.0
            repeat_prob = clamp(0.1 + 0.1 * novelty)
            action = "stay_with_current_brand"
            barrier = ctx.top_barrier or "never tried — stayed with current brand"
            reaction = _react(action, ctx, segment, "no_trial")
        state["repeat_prob"] = repeat_prob

    elif round_no == 6:
        round_metric = state.get("satisfaction", 0.3)
        sat = state.get("satisfaction", 0.0)
        share_prob = clamp(sat * (0.5 + 0.5 * social_sens))
        if state.get("purchased") and sat >= 0.55:
            action = "share_with_friend" if social_sens > 0.5 else "recommend"
            trigger = "positive trial → advocacy"
            repeat_prob = state.get("repeat_prob", repeat_prob)
        elif state.get("purchased") and sat < 0.42:
            action = "complain"
            barrier = "negative post-trial experience spreads"
        elif not state.get("purchased") and novelty > 0.6 and loyalty < 0.4:
            action = "switch_brand"
            trigger = "curiosity may still convert later"
        else:
            action = "stay_with_current_brand"
            barrier = ctx.top_barrier or "no behavior change"
        purchase_intent = state.get("trial_prob", trial_prob)
        reaction = _react(action, ctx, segment, "diffusion", share_prob=share_prob)

    state["trial_prob"] = trial_prob

    sentiment = clamp(0.45 + 0.5 * (round_metric - 0.5) + 0.2 * (credibility - 0.5) - 0.2 * risk + jitter)
    tone = _emotional_tone(sentiment)
    confidence = clamp(0.5 + 0.3 * abs(round_metric - 0.5) * 2 + 0.1 * (1 - skeptic))

    reasoning = _reasoning(segment, action, ctx, {
        "relevance": relevance,
        "credibility": credibility,
        "trial_prob": trial_prob,
        "channel_fit": channel_fit,
        "risk": risk,
        "price_value": price_value,
        "round_no": round_no,
    }, barrier, trigger)

    return {
        "action_type": action,
        "reasoning": reasoning,
        "generated_reaction": reaction,
        "emotional_tone": tone,
        "sentiment_score": sentiment,
        "trial_probability": clamp(trial_prob),
        "purchase_intent_score": clamp(purchase_intent),
        "repeat_probability": clamp(repeat_prob),
        "trust_change": round(trust_change, 3),
        "confidence_score": confidence,
        "barrier_detected": barrier,
        "trigger_detected": trigger,
        "scores": {
            "awareness_score": awareness,
            "relevance_score": relevance,
            "claim_clarity_score": clarity,
            "claim_credibility_score": credibility,
            "price_value_score": price_value,
            "channel_fit_score": channel_fit,
            "pack_appeal_score": pack_appeal,
            "social_proof_score": social_proof,
            "interest": interest,
            "intent_signal": intent_signal,
            "findability": findability,
            "risk_score": risk,
        },
    }


# --- text generation --------------------------------------------------------

# Category-neutral base phrases. `{unit}` is filled from ctx.unit_noun (pack/bottle/tube…).
_REACTIONS: dict[str, str] = {
    "ignore": "Not for me right now — scrolled past it.",
    "view": "Interesting, I'll keep an eye on this.",
    "like": "This looks good, I tapped like.",
    "save_for_later": "Saving this to check out later.",
    "comment_positive": "Looks promising, especially the benefit angle.",
    "comment_negative": "Sounds too good to be true, honestly.",
    "ask_price": "How much is it though? Price matters to me.",
    "ask_where_to_buy": "Where can I actually buy this?",
    "compare_with_current_brand": "Is this really better than what I already buy?",
    "request_review": "I'll wait until I see real reviews first.",
    "wait_for_promotion": "I'd try it if there were a promo or sample.",
    "add_to_cart": "Adding one {unit} to my cart to try.",
    "purchase_trial": "I'll grab one {unit} to try it out.",
    "reject_before_trial": "I'll pass — not convinced enough to buy.",
    "repeat_purchase_intent": "I'd buy this again — it worked for me.",
    "no_repeat_intent": "It was okay, but I won't repurchase.",
    "complain": "Disappointed — the taste/value didn't match the claim.",
    "recommend": "I'd recommend this to a friend.",
    "share_with_friend": "Sharing this with friends who'd like it.",
    "switch_brand": "I might switch from my usual brand to this.",
    "stay_with_current_brand": "Sticking with my current brand for now.",
}

# Product/category-aware phrasing variants. `{unit}`/`{benefit}`/`{product}`/`{category}`
# are filled at render time. Variants that need `{benefit}` are skipped when benefit is empty.
_VARIANTS: dict[str, list[str]] = {
    "like": [
        "This looks good, I tapped like.",
        "The {benefit} angle caught my eye — liked it.",
        "Nice — this {category} concept stands out, liked.",
    ],
    "save_for_later": [
        "Saving this to check out later.",
        "Bookmarking this {category} idea for later.",
        "Saving — want to see if the {benefit} holds up.",
    ],
    "comment_positive": [
        "Looks promising, especially the benefit angle.",
        "If the {benefit} is real, this could win me over.",
        "Promising for a {category} — the positioning works.",
    ],
    "purchase_trial": [
        "I'll grab one {unit} to try it out.",
        "Picking up a {unit} to see if the {benefit} delivers.",
        "Worth a {unit} — I'll try this {category}.",
    ],
    "repeat_purchase_intent": [
        "I'd buy this again — it worked for me.",
        "The {benefit} delivered — I'll repurchase.",
        "Good enough to add to my regular {category} rotation.",
    ],
    "recommend": [
        "I'd recommend this to a friend.",
        "Telling friends who care about {benefit}.",
        "I'd point fellow {category} shoppers to this.",
    ],
}


def _stable_pick(key: str, n: int) -> int:
    if n <= 1:
        return 0
    return sum(ord(c) for c in key) % n


def _fmt(template: str, ctx: SimContext) -> str:
    return template.format(
        unit=ctx.unit_noun,
        benefit=(ctx.benefit or "the main benefit"),
        product=(ctx.product or "this product"),
        category=ctx.category,
    )


def _react(action: str, ctx: SimContext, segment: str, phase: str, share_prob: float | None = None) -> str:
    # context-specific overrides first (kept product/category-aware, not beverage-specific)
    if action == "purchase_trial" and ctx.taste_risk:
        return _fmt("I'll try one {unit} first, but I need the taste/sensory to live up to the claim.", ctx)
    if action == "reject_before_trial" and ctx.premium:
        return _fmt("It's pricier than my usual {category} — not worth the risk without trying it.", ctx)
    if action == "request_review" and ctx.main_claim:
        return f"The '{ctx.main_claim}' claim is interesting, but I want reviews before I trust it."

    variants = _VARIANTS.get(action)
    if variants:
        idx = _stable_pick(f"{segment}|{action}|{phase}", len(variants))
        chosen = variants[idx]
        if "{benefit}" in chosen and not ctx.benefit:
            chosen = variants[0]  # base variant never needs benefit
        return _fmt(chosen, ctx)

    return _fmt(_REACTIONS.get(action, ""), ctx)


def _reasoning(segment: str, action: str, ctx: SimContext, s: dict, barrier: str | None, trigger: str | None) -> str:
    parts = [f"Segment '{segment}' at stage '{ROUND_STAGES[s['round_no']]}'."]
    if trigger:
        parts.append(f"Trigger: {trigger}.")
    if barrier:
        parts.append(f"Barrier: {barrier}.")
    drivers = []
    if s["relevance"] >= 0.55:
        drivers.append("relevance to need-state is high")
    if s["credibility"] < 0.5:
        drivers.append("claim credibility is weak for this skeptical profile")
    if ctx.premium and s["price_value"] < 0.5:
        drivers.append("premium price hurts perceived value")
    if s["channel_fit"] >= 0.6:
        drivers.append("strong channel fit aids findability")
    if s["risk"] >= 0.45:
        drivers.append("perceived risk is elevated")
    if drivers:
        parts.append("Drivers: " + ", ".join(drivers) + ".")
    parts.append(f"→ chose '{action}' (trial_prob={s['trial_prob']}).")
    return " ".join(parts)
