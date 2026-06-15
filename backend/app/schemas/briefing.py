"""Schemas for Phase 14 — executive narrative briefing."""
from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.report import EvidenceRef

RECOMMENDATION_STATUSES = (
    "move_forward",
    "validate_before_move_forward",
    "revise_and_retest",
    "hold",
)

OWNER_TEAMS = (
    "Brand",
    "Innovation",
    "R&D",
    "Trade Marketing",
    "Sales",
    "E-commerce",
    "Media",
    "Creative",
    "Consumer Insight",
    "Leadership",
)


# --- request / response wrappers --------------------------------------------


class BriefingGenerateIn(BaseModel):
    audience: str = "executive"  # executive|brand_team|trade_sales|rd_product|consumer_insight
    tone: str = "concise"  # concise|boardroom|working_session
    include_evidence: bool = True
    include_decision_history: bool = True
    include_next_actions: bool = True
    use_llm_rewrite: bool = False
    force_regenerate: bool = True


# --- payload sections -------------------------------------------------------


class BriefingHeader(BaseModel):
    project_name: str
    product_or_concept_name: str
    generated_at: datetime
    audience: str
    confidence_label: str
    overall_score: float
    recommendation_status: str


class Situation(BaseModel):
    one_paragraph_context: str
    category_or_market_context: str
    concept_summary: str
    current_decision_point: str


class Finding(BaseModel):
    finding_title: str
    explanation: str
    supporting_metric: str
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    affected_segments: list[str] = Field(default_factory=list)
    confidence_level: str
    business_implication: str


class BriefingRisk(BaseModel):
    risk_title: str
    severity: str
    why_it_matters: str
    affected_segments: list[str] = Field(default_factory=list)
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    mitigation: str


class ReadinessAssessment(BaseModel):
    trial_readiness: str
    repeat_readiness: str
    claim_readiness: str
    channel_readiness: str
    confidence_readiness: str
    overall_readiness: str
    readiness_reasoning: str


class WhatChangedRecently(BaseModel):
    has_history: bool
    latest_snapshot_comparison: str
    scorecard_drift: str
    changed_recommendation: str
    major_timeline_events: list[str] = Field(default_factory=list)


class DecisionRecommendation(BaseModel):
    recommended_decision: str
    rationale: str
    conditions_before_launch: list[str] = Field(default_factory=list)
    decision_caveats: list[str] = Field(default_factory=list)


class NextBestAction(BaseModel):
    priority: str
    action: str
    owner_team: str
    effort: str  # low|medium|high
    expected_impact: str
    evidence_basis: str
    suggested_timing: str
    validation_method: str


class ValidationItem(BaseModel):
    question: str
    recommended_method: str
    success_metric: str
    priority: str


class EvidencePack(BaseModel):
    event_evidence: list[EvidenceRef] = Field(default_factory=list)
    segment_evidence: list[str] = Field(default_factory=list)
    scorecard_evidence: list[str] = Field(default_factory=list)
    assumption_evidence: list[str] = Field(default_factory=list)
    scenario_or_sensitivity_evidence: list[str] = Field(default_factory=list)
    decision_history_evidence: list[str] = Field(default_factory=list)


class BriefingPayload(BaseModel):
    briefing_header: BriefingHeader
    situation: Situation
    top_findings: list[Finding] = Field(default_factory=list)
    biggest_risks: list[BriefingRisk] = Field(default_factory=list)
    readiness_assessment: ReadinessAssessment
    what_changed_recently: WhatChangedRecently
    decision_recommendation: DecisionRecommendation
    next_best_actions: list[NextBestAction] = Field(default_factory=list)
    validation_plan: list[ValidationItem] = Field(default_factory=list)
    evidence_pack: EvidencePack
    limitations: list[str] = Field(default_factory=list)


class BriefingSummary(BaseModel):
    recommendation_status: str
    overall_score: float
    confidence_label: str
    headline: str
    top_action: str | None = None


class BriefingOut(BaseModel):
    project_id: str
    briefing_id: str
    status: str
    source_mode: str
    audience: str
    tone: str
    generated_at: datetime
    briefing_payload: BriefingPayload
    markdown: str
    summary: BriefingSummary


# --- Phase 15: briefing Q&A -------------------------------------------------


class BriefingAskIn(BaseModel):
    question: str
    audience: str = "executive"
    tone: str = "concise"
    include_evidence: bool = True
    max_evidence_items: int = 5
    use_llm_rewrite: bool = False


class BriefingAnswer(BaseModel):
    direct_answer: str
    audience_framing: str
    supporting_evidence: list[EvidenceRef] = Field(default_factory=list)
    related_next_actions: list[str] = Field(default_factory=list)
    related_risks: list[str] = Field(default_factory=list)
    confidence_score: float
    limitations: list[str] = Field(default_factory=list)
    recommended_follow_up: list[str] = Field(default_factory=list)


class BriefingAskOut(BaseModel):
    project_id: str
    question: str
    intent: str
    answer: BriefingAnswer
    source_mode: str = "deterministic"


# --- Phase 15: audience tailoring -------------------------------------------


class TailorIn(BaseModel):
    audience: str = "executive"
    tone: str = "concise"
    format: str = "markdown"
    include_evidence: bool = True
    use_llm_rewrite: bool = False


class TailoredPayload(BaseModel):
    headline: str
    audience_priority: str
    what_this_audience_needs_to_know: list[str] = Field(default_factory=list)
    role_specific_risks: list[str] = Field(default_factory=list)
    role_specific_actions: list[str] = Field(default_factory=list)
    evidence_to_show: list[str] = Field(default_factory=list)
    what_not_to_overclaim: list[str] = Field(default_factory=list)
    talk_track: list[str] = Field(default_factory=list)


class TailorOut(BaseModel):
    project_id: str
    audience: str
    tone: str
    tailored_payload: TailoredPayload
    markdown: str
    source_mode: str = "deterministic"


# --- Phase 15: one-page board summary ---------------------------------------


class BoardSummaryIn(BaseModel):
    tone: str = "boardroom"
    include_evidence: bool = True
    use_llm_rewrite: bool = False


class BoardSummaryPayload(BaseModel):
    headline_recommendation: str
    decision_status: str
    one_sentence_concept: str
    three_key_findings: list[str] = Field(default_factory=list)
    top_three_risks: list[str] = Field(default_factory=list)
    decision_gate: str
    next_three_actions: list[str] = Field(default_factory=list)
    validation_needed: list[str] = Field(default_factory=list)
    confidence_and_caveat: str
    evidence_refs: list[str] = Field(default_factory=list)


class BoardSummaryOut(BaseModel):
    project_id: str
    summary_payload: BoardSummaryPayload
    markdown: str
    source_mode: str = "deterministic"
