"""Scenario testing schemas (Phase 7)."""
from datetime import datetime

from pydantic import BaseModel, Field


class ScenarioOverrides(BaseModel):
    """What-if levers. All neutral by default → identical to baseline."""

    price_change_pct: float = 0.0  # e.g. -10 = 10% cheaper
    claim_credibility_boost: float = 0.0  # 0..1 added to claim credibility
    sampling_boost: float = 0.0  # 0..1
    promotion_boost: float = 0.0  # 0..1
    channel_focus: str | None = None  # e.g. "tiktok" → concentrate on one channel
    competitor_pressure_boost: float = 0.0  # 0..1 (raises perceived risk)
    packaging_appeal_boost: float = 0.0  # 0..1
    social_proof_boost: float = 0.0  # 0..1
    sensory_risk_reduction: float = 0.0  # 0..1 (de-risks taste)
    retailer_support_boost: float = 0.0  # 0..1 (improves findability)


class ScenarioRunIn(BaseModel):
    scenario_name: str = "Scenario"
    description: str = ""
    overrides: ScenarioOverrides = Field(default_factory=ScenarioOverrides)
    rounds: int = Field(default=6, ge=1, le=6)
    seed: int = 42
    generate_delta_report: bool = True


class MetricChanges(BaseModel):
    trial_probability_delta: float
    purchase_intent_delta: float
    repeat_probability_delta: float
    sentiment_delta: float
    complaint_delta: int
    recommend_delta: int
    switch_delta: int
    trial_count_delta: int
    top_segments_improved: list[str] = Field(default_factory=list)
    top_segments_declined: list[str] = Field(default_factory=list)


class ScenarioRunOut(BaseModel):
    scenario_id: str
    project_id: str
    scenario_name: str
    description: str
    overrides: ScenarioOverrides
    baseline_summary: dict
    scenario_summary: dict
    delta_summary: str
    key_metric_changes: MetricChanges
    segment_changes: list[dict] = Field(default_factory=list)
    action_distribution_changes: dict[str, int] = Field(default_factory=dict)
    trigger_changes: dict[str, int] = Field(default_factory=dict)
    barrier_changes: dict[str, int] = Field(default_factory=dict)
    recommendation_changes: list[str] = Field(default_factory=list)
    conclusion: str
    created_at: datetime | None = None


class ScenarioListItem(BaseModel):
    scenario_id: str
    scenario_name: str
    description: str
    baseline_event_count: int
    scenario_event_count: int
    created_at: datetime
