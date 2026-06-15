"""Pydantic schemas for the Phase 6 strategic launch report."""
from datetime import datetime

from pydantic import BaseModel, Field


# --- evidence ---------------------------------------------------------------


class EvidenceRef(BaseModel):
    event_id: str
    round_number: int
    agent_id: str
    segment_name: str | None = None
    action_type: str
    short_reaction_excerpt: str


# --- 1. executive summary ---------------------------------------------------


class ExecutiveSummary(BaseModel):
    overall_market_reaction: str
    top_opportunity: str
    top_risk: str
    estimated_trial_potential: str
    estimated_repeat_potential: str
    key_recommendation: str
    confidence_score: float
    important_assumptions: list[str] = Field(default_factory=list)


# --- 2. launch funnel summary ----------------------------------------------


class RoundSummaryItem(BaseModel):
    round_number: int
    stage_name: str
    dominant_action: str | None = None
    avg_sentiment: float
    avg_trial_probability: float


class LaunchFunnelSummary(BaseModel):
    awareness_signal: str
    trial_signal: str
    repeat_signal: str
    advocacy_signal: str
    rejection_signal: str
    complaint_signal: str
    switching_signal: str
    action_distribution: dict[str, int] = Field(default_factory=dict)
    round_summary: list[RoundSummaryItem] = Field(default_factory=list)


# --- 3. segment reaction map ------------------------------------------------


class SegmentReaction(BaseModel):
    segment_name: str
    number_of_agents: int
    average_trial_probability: float
    average_purchase_intent_score: float
    average_repeat_probability: float
    average_sentiment_score: float
    strongest_trigger: str | None = None
    strongest_barrier: str | None = None
    dominant_actions: list[str] = Field(default_factory=list)
    representative_reaction: str
    recommended_message_angle: str
    confidence_score: float


# --- 4. purchase trigger analysis -------------------------------------------


class TriggerAnalysis(BaseModel):
    trigger: str
    frequency: int
    affected_segments: list[str] = Field(default_factory=list)
    related_touchpoints: list[str] = Field(default_factory=list)
    evidence_events: list[EvidenceRef] = Field(default_factory=list)
    strategic_implication: str


# --- 5. adoption barrier analysis -------------------------------------------


class BarrierAnalysis(BaseModel):
    barrier: str
    frequency: int
    affected_segments: list[str] = Field(default_factory=list)
    related_touchpoints: list[str] = Field(default_factory=list)
    evidence_events: list[EvidenceRef] = Field(default_factory=list)
    severity_level: str
    recommended_fix: str


# --- 6. claim clarity & credibility -----------------------------------------


class ClaimAssessment(BaseModel):
    claim: str
    clarity_assessment: str
    credibility_assessment: str
    supporting_signals: list[str] = Field(default_factory=list)
    risk_signals: list[str] = Field(default_factory=list)
    representative_reactions: list[str] = Field(default_factory=list)
    recommended_rewrite: str | None = None


# --- 7. packaging & price perception ----------------------------------------


class PackagingPricePerception(BaseModel):
    packaging_appeal_summary: str
    price_value_summary: str
    premium_price_risk: str
    pack_size_concern: str
    promotion_dependency: str
    recommended_price_or_promo_action: str


# --- 8. channel / touchpoint analysis ---------------------------------------


class ChannelTouchpoint(BaseModel):
    channel_or_touchpoint: str
    positive_signal: str
    negative_signal: str
    trial_contribution: str
    risk_signal: str
    recommended_role_in_launch: str


# --- 9. trial & repeat forecast ---------------------------------------------


class TrialRepeatForecast(BaseModel):
    likely_triers: str
    likely_repeaters: str
    one_time_trial_risk: str
    switch_potential: str
    dependency_on_promotion: str
    confidence_score: float


# --- 10. social diffusion & WOM ---------------------------------------------


class SocialDiffusion(BaseModel):
    likely_advocates: str
    likely_complainers: str
    share_drivers: list[str] = Field(default_factory=list)
    complaint_drivers: list[str] = Field(default_factory=list)
    social_questions_likely_to_spread: list[str] = Field(default_factory=list)
    recommended_social_content_response: str


# --- 11. competitor & retail response ---------------------------------------


class CompetitorRetailResponse(BaseModel):
    competitor_risks: list[str] = Field(default_factory=list)
    retailer_opportunities: list[str] = Field(default_factory=list)
    retailer_objections: list[str] = Field(default_factory=list)
    influencer_review_risks: list[str] = Field(default_factory=list)
    community_discussion_risks: list[str] = Field(default_factory=list)
    category_expert_concerns: list[str] = Field(default_factory=list)


# --- 12. innovation risk matrix ---------------------------------------------


class RiskItem(BaseModel):
    risk_type: str
    severity: str
    evidence: str
    affected_segments: list[str] = Field(default_factory=list)
    mitigation: str


# --- 13. strategic recommendations ------------------------------------------


class Recommendation(BaseModel):
    priority: str
    recommendation: str
    rationale: str
    supporting_evidence: str
    expected_impact: str
    owner_team: str


# --- 14. recommended A/B tests ----------------------------------------------


class ABTest(BaseModel):
    test_name: str
    hypothesis: str
    variant_a: str
    variant_b: str
    target_segment: str
    success_metric: str
    why_this_test_matters: str


# --- full payload -----------------------------------------------------------


class ReportPayload(BaseModel):
    executive_summary: ExecutiveSummary
    launch_funnel_summary: LaunchFunnelSummary
    segment_reaction_map: list[SegmentReaction] = Field(default_factory=list)
    purchase_trigger_analysis: list[TriggerAnalysis] = Field(default_factory=list)
    adoption_barrier_analysis: list[BarrierAnalysis] = Field(default_factory=list)
    claim_clarity_and_credibility: list[ClaimAssessment] = Field(default_factory=list)
    packaging_price_perception: PackagingPricePerception
    channel_touchpoint_analysis: list[ChannelTouchpoint] = Field(default_factory=list)
    trial_repeat_forecast: TrialRepeatForecast
    social_diffusion_and_wom: SocialDiffusion
    competitor_and_retail_response: CompetitorRetailResponse
    innovation_risk_matrix: list[RiskItem] = Field(default_factory=list)
    strategic_recommendations: list[Recommendation] = Field(default_factory=list)
    recommended_ab_tests: list[ABTest] = Field(default_factory=list)
    human_validation_questions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


# --- request / response -----------------------------------------------------


class ReportGenerateIn(BaseModel):
    format: str = "json_markdown"
    use_llm_narrative: bool = False
    force_regenerate: bool = True


class ReportSummaryOut(BaseModel):
    overall_market_reaction: str
    top_opportunity: str
    top_risk: str
    top_segments: list[dict] = Field(default_factory=list)
    top_triggers: list[dict] = Field(default_factory=list)
    top_barriers: list[dict] = Field(default_factory=list)
    key_recommendations: list[str] = Field(default_factory=list)


class ReportGenerateOut(BaseModel):
    project_id: str
    report_id: str
    status: str
    source_mode: str
    confidence_score: float
    generated_at: datetime
    report_payload: ReportPayload
    markdown_report: str
    summary: ReportSummaryOut
