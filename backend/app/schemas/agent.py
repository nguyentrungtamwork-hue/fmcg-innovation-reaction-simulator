"""Pydantic schemas for consumer and market-actor agents."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# --- Defaults --------------------------------------------------------------

DEFAULT_SEGMENTS: tuple[str, ...] = (
    "Early Adopter / Trend-Seeker",
    "Value-Seeking Practical Buyer",
    "Brand-Loyal Conservative Buyer",
    "Health/Safety-Conscious Buyer",
    "Convenience-Driven Busy Buyer",
    "Family Decision Maker",
    "Skeptical Reviewer-Dependent Buyer",
    "Promotion-Driven Trial Buyer",
)

DEFAULT_DISTRIBUTION_50: dict[str, int] = {
    "Early Adopter / Trend-Seeker": 7,
    "Value-Seeking Practical Buyer": 10,
    "Brand-Loyal Conservative Buyer": 7,
    "Health/Safety-Conscious Buyer": 7,
    "Convenience-Driven Busy Buyer": 7,
    "Family Decision Maker": 4,
    "Skeptical Reviewer-Dependent Buyer": 4,
    "Promotion-Driven Trial Buyer": 4,
}

MARKET_ACTOR_ROLES: tuple[str, ...] = (
    "Retailer",
    "Competitor",
    "Influencer",
    "SocialCommunity",
    "CategoryExpert",
)

# Names of trait keys that must be in [0,1].
NUMERIC_TRAITS: tuple[str, ...] = (
    "price_sensitivity",
    "novelty_seeking_level",
    "brand_loyalty_level",
    "claim_skepticism_level",
    "health_safety_concern_level",
    "convenience_need_level",
    "taste_or_sensory_importance",
    "packaging_sensitivity",
    "promotion_sensitivity",
    "social_influence_sensitivity",
    "review_dependency_level",
)


# --- Profile payloads ------------------------------------------------------


class ConsumerAgentProfile(BaseModel):
    """The full consumer-agent payload (stored in agents.profile_json)."""

    segment_description: str
    age_range: str
    household_context: str
    lifestyle_context: str
    category_usage_frequency: str
    current_brand_repertoire: list[str] = Field(default_factory=list)
    current_purchase_channel: list[str] = Field(default_factory=list)
    category_pain_points: list[str] = Field(default_factory=list)
    need_states: list[str] = Field(default_factory=list)
    usage_occasions: list[str] = Field(default_factory=list)

    price_sensitivity: float = Field(ge=0.0, le=1.0)
    novelty_seeking_level: float = Field(ge=0.0, le=1.0)
    brand_loyalty_level: float = Field(ge=0.0, le=1.0)
    claim_skepticism_level: float = Field(ge=0.0, le=1.0)
    health_safety_concern_level: float = Field(ge=0.0, le=1.0)
    convenience_need_level: float = Field(ge=0.0, le=1.0)
    taste_or_sensory_importance: float = Field(ge=0.0, le=1.0)
    packaging_sensitivity: float = Field(ge=0.0, le=1.0)
    promotion_sensitivity: float = Field(ge=0.0, le=1.0)
    social_influence_sensitivity: float = Field(ge=0.0, le=1.0)
    review_dependency_level: float = Field(ge=0.0, le=1.0)

    channel_preference: list[str] = Field(default_factory=list)
    media_touchpoints: list[str] = Field(default_factory=list)
    trust_drivers: list[str] = Field(default_factory=list)
    trial_barriers: list[str] = Field(default_factory=list)
    repeat_purchase_drivers: list[str] = Field(default_factory=list)
    likely_objections: list[str] = Field(default_factory=list)
    emotional_triggers: list[str] = Field(default_factory=list)

    initial_memory: list[str] = Field(default_factory=list)
    grounding_sources: list[str] = Field(default_factory=list)


class MarketActorProfile(BaseModel):
    objective: str
    influence_power: float = Field(ge=0.0, le=1.0)
    trust_level: float = Field(ge=0.0, le=1.0)
    likely_actions: list[str] = Field(default_factory=list)
    risk_to_launch: list[str] = Field(default_factory=list)
    positive_contribution: list[str] = Field(default_factory=list)
    evaluation_criteria: list[str] = Field(default_factory=list)
    initial_memory: list[str] = Field(default_factory=list)
    grounding_sources: list[str] = Field(default_factory=list)


# --- API request/response --------------------------------------------------


class AgentGenerateIn(BaseModel):
    consumer_count: int = Field(default=50, ge=5, le=200)
    include_market_actors: bool = True
    segment_distribution: dict[str, int] | None = None
    force_regenerate: bool = True
    seed: int = 42


class AgentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    agent_type: Literal["consumer", "market_actor"]
    name: str
    segment_name: str | None = None
    role: str | None = None
    source_mode: str
    confidence_score: float
    profile: dict
    memory: list = Field(default_factory=list)
    simulation_memory: list = Field(default_factory=list)
    action_history: list = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class AgentGenerateOut(BaseModel):
    total_agents: int
    consumer_agents: int
    market_actor_agents: int
    segment_distribution: dict[str, int]
    source_mode: str


class AgentSummaryOut(BaseModel):
    total_agents: int
    consumer_agents: int
    market_actor_agents: int
    segment_distribution: dict[str, int]
    average_trait_scores: dict[str, float]
    top_trial_barriers: list[tuple[str, int]] = Field(default_factory=list)
    top_trust_drivers: list[tuple[str, int]] = Field(default_factory=list)
    top_channel_preferences: list[tuple[str, int]] = Field(default_factory=list)
