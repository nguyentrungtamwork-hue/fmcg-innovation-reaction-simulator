"""Static segment templates used by the fallback generator.

Each segment defines:
- trait_ranges: dict[trait_name -> (low, high)] in [0,1].
- archetype: short prose for `segment_description`.
- age_range, household_context, lifestyle_context defaults.
- characteristic pain points, need states, objections, repeat drivers, emotional triggers.

Trait ranges encode the segment's behavioral fingerprint. The fallback samples
inside the range with a seeded RNG so different agents in the same segment
still feel distinct, but the segment remains recognizable.
"""

# Trait range envelope helper
_LOW = (0.0, 0.35)
_MID = (0.35, 0.65)
_HIGH = (0.65, 1.0)
_VHIGH = (0.75, 1.0)
_VLOW = (0.0, 0.25)


def _t(**kw) -> dict:
    """Convenience: trait ranges, missing ones default to mid."""
    base = {
        "price_sensitivity": _MID,
        "novelty_seeking_level": _MID,
        "brand_loyalty_level": _MID,
        "claim_skepticism_level": _MID,
        "health_safety_concern_level": _MID,
        "convenience_need_level": _MID,
        "taste_or_sensory_importance": _MID,
        "packaging_sensitivity": _MID,
        "promotion_sensitivity": _MID,
        "social_influence_sensitivity": _MID,
        "review_dependency_level": _MID,
    }
    base.update(kw)
    return base


SEGMENT_TEMPLATES: dict[str, dict] = {
    "Early Adopter / Trend-Seeker": {
        "archetype": "Curious, social-first buyer who actively seeks out new launches and shares discoveries.",
        "age_range": "22-32",
        "household_context": "single or sharing with roommates; urban",
        "lifestyle_context": "active on social media; follows lifestyle and food creators",
        "category_usage_frequency": "buys category 3-5x/week, often experimenting",
        "category_pain_points": ["category feels stale", "wants conversation-worthy products"],
        "likely_objections": ["if it feels like an old idea repackaged"],
        "repeat_purchase_drivers": ["new flavor drops", "limited editions", "creator buzz"],
        "emotional_triggers": ["being first to discover", "shareable aesthetic"],
        "traits": _t(
            novelty_seeking_level=_VHIGH,
            social_influence_sensitivity=_HIGH,
            review_dependency_level=_LOW,
            brand_loyalty_level=_LOW,
            packaging_sensitivity=_HIGH,
            price_sensitivity=_MID,
            claim_skepticism_level=(0.25, 0.55),
        ),
    },
    "Value-Seeking Practical Buyer": {
        "archetype": "Calculates price-per-volume; rarely tries new items at full price.",
        "age_range": "28-45",
        "household_context": "couple or small family; budget-conscious",
        "lifestyle_context": "promo-aware; compares unit prices in-store",
        "category_usage_frequency": "buys category weekly, same SKUs",
        "category_pain_points": ["premium creep", "shrinking pack sizes"],
        "likely_objections": ["price too high vs current SKU", "doesn't justify premium"],
        "repeat_purchase_drivers": ["sustained promo", "clear price-per-100ml"],
        "emotional_triggers": ["sense of smart purchase"],
        "traits": _t(
            price_sensitivity=_VHIGH,
            promotion_sensitivity=_HIGH,
            novelty_seeking_level=_LOW,
            brand_loyalty_level=_MID,
            claim_skepticism_level=_HIGH,
            social_influence_sensitivity=_LOW,
        ),
    },
    "Brand-Loyal Conservative Buyer": {
        "archetype": "Sticks with proven brand; suspicious of unfamiliar entrants.",
        "age_range": "35-55",
        "household_context": "established household",
        "lifestyle_context": "low novelty appetite; values reliability",
        "category_usage_frequency": "buys same brand weekly for years",
        "category_pain_points": ["disliked when favorite brand changes recipe"],
        "likely_objections": ["why switch from a brand that works?"],
        "repeat_purchase_drivers": ["consistency", "trust signals"],
        "emotional_triggers": ["familiarity", "trusted endorsement"],
        "traits": _t(
            brand_loyalty_level=_VHIGH,
            novelty_seeking_level=_VLOW,
            claim_skepticism_level=_HIGH,
            promotion_sensitivity=_LOW,
            social_influence_sensitivity=_LOW,
            health_safety_concern_level=_MID,
        ),
    },
    "Health/Safety-Conscious Buyer": {
        "archetype": "Reads labels; cares about ingredients, sugar, additives, sourcing.",
        "age_range": "26-45",
        "household_context": "varies; often health-leaning lifestyle",
        "lifestyle_context": "follows wellness content; reads ingredient lists",
        "category_usage_frequency": "selective buyer, 2-3x/week",
        "category_pain_points": ["too much sugar in mainstream options", "vague natural claims"],
        "likely_objections": ["is the cooling claim actually substantiated?"],
        "repeat_purchase_drivers": ["clean label", "credible RTB", "noticeable benefit"],
        "emotional_triggers": ["feeling cared for", "alignment with health goals"],
        "traits": _t(
            health_safety_concern_level=_VHIGH,
            claim_skepticism_level=_HIGH,
            review_dependency_level=_HIGH,
            taste_or_sensory_importance=_HIGH,
            price_sensitivity=_MID,
        ),
    },
    "Convenience-Driven Busy Buyer": {
        "archetype": "Time-poor; chooses what's closest, fastest, easiest.",
        "age_range": "25-40",
        "household_context": "urban working professional",
        "lifestyle_context": "buys at CVS on commute; doesn't browse",
        "category_usage_frequency": "buys category 4-6x/week, grab-and-go",
        "category_pain_points": ["confusing shelves", "out-of-stock favorites"],
        "likely_objections": ["if I can't see it on the shelf I skip it"],
        "repeat_purchase_drivers": ["availability everywhere", "fast checkout"],
        "emotional_triggers": ["relief of one less decision"],
        "traits": _t(
            convenience_need_level=_VHIGH,
            packaging_sensitivity=_MID,
            price_sensitivity=_MID,
            novelty_seeking_level=_LOW,
            claim_skepticism_level=_MID,
            review_dependency_level=_LOW,
        ),
    },
    "Family Decision Maker": {
        "archetype": "Buys for household; balances kids' taste, health concerns, and pack size.",
        "age_range": "32-48",
        "household_context": "family with children",
        "lifestyle_context": "supermarket weekly run; pack-size aware",
        "category_usage_frequency": "weekly bulk purchase",
        "category_pain_points": ["singles waste money", "kids reject taste"],
        "likely_objections": ["pack too small for family", "kids might not like herbal taste"],
        "repeat_purchase_drivers": ["family-friendly pack", "approved by kids"],
        "emotional_triggers": ["doing right by the family"],
        "traits": _t(
            health_safety_concern_level=_HIGH,
            price_sensitivity=_HIGH,
            promotion_sensitivity=_HIGH,
            convenience_need_level=_MID,
            brand_loyalty_level=_MID,
            taste_or_sensory_importance=_HIGH,
        ),
    },
    "Skeptical Reviewer-Dependent Buyer": {
        "archetype": "Will not try until trusted reviewer confirms it works.",
        "age_range": "24-40",
        "household_context": "varies",
        "lifestyle_context": "follows reviewer accounts; reads comment sections",
        "category_usage_frequency": "category buyer but late adopter",
        "category_pain_points": ["wasted money on overhyped launches"],
        "likely_objections": ["not enough reviews yet", "claims sound too good"],
        "repeat_purchase_drivers": ["positive reviewer follow-up", "long-tail comments"],
        "emotional_triggers": ["validation by trusted creator"],
        "traits": _t(
            review_dependency_level=_VHIGH,
            claim_skepticism_level=_VHIGH,
            novelty_seeking_level=_LOW,
            social_influence_sensitivity=_HIGH,
        ),
    },
    "Promotion-Driven Trial Buyer": {
        "archetype": "Tries new items when there's a discount, sample, or BOGO.",
        "age_range": "22-40",
        "household_context": "varies",
        "lifestyle_context": "tracks deals; opportunistic",
        "category_usage_frequency": "variable; spikes around promos",
        "category_pain_points": ["full-price feels overpriced"],
        "likely_objections": ["I'll wait for the promo"],
        "repeat_purchase_drivers": ["recurring promos", "loyalty rewards"],
        "emotional_triggers": ["thrill of a deal"],
        "traits": _t(
            promotion_sensitivity=_VHIGH,
            price_sensitivity=_HIGH,
            brand_loyalty_level=_LOW,
            novelty_seeking_level=_MID,
        ),
    },
}


# --- Market actor templates ------------------------------------------------

MARKET_ACTOR_TEMPLATES: dict[str, dict] = {
    "Retailer": {
        "name": "Modern-Trade Retailer",
        "objective": "Maximize per-SKU velocity and category margin.",
        "influence_power": 0.75,
        "trust_level": 0.6,
        "likely_actions": [
            "Negotiate shelf position based on early sell-through",
            "Trim facings if velocity is below category median",
            "Pair with on-shelf promo if launch promo expires",
        ],
        "risk_to_launch": [
            "De-list within 8 weeks if rotation is weak",
            "Demand higher slotting / promo support",
        ],
        "positive_contribution": [
            "Premium shelf visibility if initial sell-through is strong",
            "Co-branded sampling at high-traffic stores",
        ],
        "evaluation_criteria": [
            "shelf visibility",
            "price competitiveness vs category",
            "promo attractiveness",
            "channel fit",
            "repeat sales potential",
        ],
    },
    "Competitor": {
        "name": "Incumbent Category Leader",
        "objective": "Defend share and minimize switching to the new entrant.",
        "influence_power": 0.8,
        "trust_level": 0.55,
        "likely_actions": [
            "Run defensive price promo at same channels",
            "Push comparative claim content if our claim is challenged",
            "Seed neutral-looking content questioning new RTB",
            "Buy KOL slots to dilute novelty",
        ],
        "risk_to_launch": [
            "Aggressive bundle discounting that resets price reference",
            "Doubt-seeding around credibility of cooling/health claim",
            "Lock retail visibility through trade spend",
        ],
        "positive_contribution": [],
        "evaluation_criteria": [
            "discounting risk",
            "claim comparison risk",
            "content attack / seeding doubt",
            "retail visibility defense",
        ],
    },
    "Influencer": {
        "name": "Mid-Tier Lifestyle KOL",
        "objective": "Earn engagement by reviewing review-worthy products honestly.",
        "influence_power": 0.65,
        "trust_level": 0.65,
        "likely_actions": [
            "Test product on camera and react to taste",
            "Compare with current go-to brand",
            "Highlight pack design + ingredient story",
        ],
        "risk_to_launch": [
            "Negative taste reaction goes viral",
            "Pointed challenge to the health/cooling claim",
        ],
        "positive_contribution": [
            "Endorses RTB if pack story is clean and taste is acceptable",
            "Drives initial trial spike among social-leaning segments",
        ],
        "evaluation_criteria": [
            "review-worthiness",
            "believability",
            "sensory appeal",
            "packaging appeal",
            "controversy potential",
        ],
    },
    "SocialCommunity": {
        "name": "Category Community / Comment Section",
        "objective": "Surface honest aggregate sentiment among engaged consumers.",
        "influence_power": 0.55,
        "trust_level": 0.6,
        "likely_actions": [
            "Debate taste vs claim authenticity",
            "Share comparison photos vs competitor",
            "Amplify complaints if they recur",
        ],
        "risk_to_launch": [
            "Complaint amplification (taste/price)",
            "Spread of doubt about claim credibility",
        ],
        "positive_contribution": [
            "Organic recommendations that drive long-tail trial",
            "Use-case discovery (new occasions)",
        ],
        "evaluation_criteria": [
            "likely discussion topics",
            "concerns that may spread",
            "positive word-of-mouth potential",
            "complaint amplification risk",
        ],
    },
    "CategoryExpert": {
        "name": "Category / Nutrition Expert",
        "objective": "Evaluate product on category logic and credibility of claims.",
        "influence_power": 0.5,
        "trust_level": 0.8,
        "likely_actions": [
            "Critique claim phrasing for clarity and substantiation",
            "Compare RTB to category benchmarks",
            "Flag regulatory phrasing risk",
        ],
        "risk_to_launch": [
            "Publicly question the strength of the 'natural cooling' RTB",
            "Recommend clearer ingredient disclosure",
        ],
        "positive_contribution": [
            "Validates differentiation if RTB is solid",
            "Suggests sharper claim rewrites",
        ],
        "evaluation_criteria": [
            "claim clarity",
            "differentiation",
            "category fit",
            "product-market fit",
            "reason-to-believe strength",
        ],
    },
}
