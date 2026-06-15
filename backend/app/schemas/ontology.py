"""Pydantic schemas for the FMCG ontology layer."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ENTITY_TYPES: tuple[str, ...] = (
    "Brand",
    "ProductInnovation",
    "Category",
    "SubCategory",
    "ConsumerSegment",
    "NeedState",
    "UsageOccasion",
    "ProductBenefit",
    "FunctionalClaim",
    "EmotionalClaim",
    "IngredientOrTechnology",
    "PackagingSignal",
    "PricePoint",
    "PackSize",
    "Channel",
    "RetailEnvironment",
    "PromotionMechanic",
    "CompetitorBrand",
    "CompetingProduct",
    "InfluencerOrReviewer",
    "SocialCommunity",
    "AdoptionBarrier",
    "PurchaseTrigger",
    "RiskSignal",
    "MessageAngle",
    "CreativeAsset",
    "Touchpoint",
)

RELATIONSHIP_TYPES: tuple[str, ...] = (
    "TARGETS",
    "COMPETES_WITH",
    "CLAIMS_TO_SOLVE",
    "USED_IN_OCCASION",
    "ATTRACTS",
    "CONFUSES",
    "TRIGGERS_TRIAL",
    "BLOCKS_TRIAL",
    "BUILDS_TRUST",
    "REDUCES_TRUST",
    "DRIVES_REPEAT",
    "CAUSES_REJECTION",
    "IS_SHARED_BY",
    "IS_REVIEWED_BY",
    "IS_SOLD_THROUGH",
    "IS_PROMOTED_BY",
    "IS_SUBSTITUTED_BY",
    "IS_COMPARED_WITH",
)


class SourceTrace(BaseModel):
    field: str | None = None
    source_text_excerpt: str | None = None
    confidence: float = 0.5
    reasoning: str | None = None


class OntologyEntity(BaseModel):
    type: str
    name: str
    attributes: dict = Field(default_factory=dict)
    source_trace: SourceTrace | None = None


class OntologyRelationship(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    from_: str = Field(alias="from")
    to: str
    type: str
    attributes: dict = Field(default_factory=dict)


class ClaimAnalysisItem(BaseModel):
    claim: str
    clarity: Literal["clear", "unclear"] = "clear"
    credibility: Literal["believable", "questionable", "unbelievable"] = "believable"
    differentiation: Literal["differentiated", "generic"] = "generic"
    risks: list[str] = Field(default_factory=list)
    recommended_rewrite: str | None = None


class ChannelObservation(BaseModel):
    channel: str
    funnel_role: str
    fit_score: float = 0.5
    note: str | None = None


class OntologyPayload(BaseModel):
    """The shape persisted in `ontologies.data_json`."""

    entities: list[OntologyEntity] = Field(default_factory=list)
    relationships: list[OntologyRelationship] = Field(default_factory=list)
    market_assumptions: list[str] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    purchase_triggers: list[str] = Field(default_factory=list)
    adoption_barriers: list[str] = Field(default_factory=list)
    claim_analysis: list[ClaimAnalysisItem] = Field(default_factory=list)
    channel_analysis: list[ChannelObservation] = Field(default_factory=list)
    claim_clarity_issues: list[str] = Field(default_factory=list)
    claim_credibility_risks: list[str] = Field(default_factory=list)
    price_value_concerns: list[str] = Field(default_factory=list)
    channel_fit_observations: list[str] = Field(default_factory=list)
    social_diffusion_potential: list[str] = Field(default_factory=list)
    competitor_pressure_points: list[str] = Field(default_factory=list)


class OntologyOut(BaseModel):
    ontology_id: str
    project_id: str
    brief_id: str | None
    source_mode: str
    confidence_score: float
    created_at: datetime
    updated_at: datetime

    # flattened payload (echoed at the top level for client convenience)
    entities: list[OntologyEntity]
    relationships: list[OntologyRelationship]
    market_assumptions: list[str]
    missing_information: list[str]
    risk_signals: list[str]
    purchase_triggers: list[str]
    adoption_barriers: list[str]
    claim_analysis: list[ClaimAnalysisItem]
    channel_analysis: list[ChannelObservation]
    claim_clarity_issues: list[str]
    claim_credibility_risks: list[str]
    price_value_concerns: list[str]
    channel_fit_observations: list[str]
    social_diffusion_potential: list[str]
    competitor_pressure_points: list[str]
