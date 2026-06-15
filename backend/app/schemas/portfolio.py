"""Schemas for Phase 12 — scorecards, snapshots, portfolio & comparison."""
from datetime import datetime

from pydantic import BaseModel, Field

_SCORECARD_DISCLAIMER = "This scorecard is a decision-support heuristic, not a validated market forecast."


# --- scorecard --------------------------------------------------------------


class Scorecard(BaseModel):
    project_id: str
    project_name: str
    snapshot_id: str | None = None
    snapshot_name: str | None = None

    overall_score: float                 # 0..100
    confidence_score: float              # 0..1
    trial_potential_score: float         # 0..100
    repeat_potential_score: float        # 0..100
    sentiment_score: float               # 0..100
    advocacy_score: float                # 0..100
    risk_score: float                    # 0..100 (higher = riskier)
    claim_credibility_score: float       # 0..100
    price_value_score: float             # 0..100
    channel_fit_score: float             # 0..100
    assumption_risk_score: float         # 0..100 (higher = riskier)
    sensitivity_risk_score: float        # 0..100 (higher = riskier)

    top_opportunity: str
    top_risk: str
    best_segment: str
    weakest_segment: str
    strongest_trigger: str
    strongest_barrier: str
    recommended_next_step: str
    ranking_explanation: str
    confidence_label: str = "medium"
    disclaimer: str = _SCORECARD_DISCLAIMER


# --- snapshots --------------------------------------------------------------


class SnapshotCreate(BaseModel):
    snapshot_name: str = Field(min_length=1, max_length=160)
    description: str = ""


class SnapshotListItem(BaseModel):
    snapshot_id: str
    snapshot_name: str
    description: str
    source_report_id: str | None = None
    source_project_status: str | None = None
    created_at: datetime


class SnapshotOut(BaseModel):
    snapshot_id: str
    project_id: str
    snapshot_name: str
    description: str
    source_report_id: str | None = None
    source_project_status: str | None = None
    report_payload: dict
    markdown: str
    scorecard: Scorecard
    created_at: datetime


# --- portfolio --------------------------------------------------------------


class PortfolioProjectRow(BaseModel):
    project_id: str
    project_name: str
    status: str
    has_report: bool
    has_simulation: bool
    overall_score: float | None = None
    confidence_score: float | None = None
    trial_potential_score: float | None = None
    repeat_potential_score: float | None = None
    risk_score: float | None = None
    top_opportunity: str | None = None
    top_risk: str | None = None
    recommended_next_step: str | None = None


class PortfolioSummary(BaseModel):
    total_projects: int
    report_ready_projects: int
    highest_score_project: str | None = None
    highest_risk_project: str | None = None
    best_trial_project: str | None = None
    best_repeat_project: str | None = None


class PortfolioOut(BaseModel):
    projects: list[PortfolioProjectRow] = Field(default_factory=list)
    summary: PortfolioSummary


class CompareIn(BaseModel):
    project_ids: list[str] = Field(default_factory=list)
    snapshot_ids: list[str] = Field(default_factory=list)
    include_snapshots: bool = False


class CompareItem(BaseModel):
    type: str  # project | snapshot
    project_id: str
    snapshot_id: str | None = None
    name: str
    scorecard: Scorecard


class ComparisonSummary(BaseModel):
    best_overall: str | None = None
    best_trial: str | None = None
    best_repeat: str | None = None
    lowest_risk: str | None = None
    highest_confidence: str | None = None
    most_needs_validation: str | None = None


class CompareOut(BaseModel):
    items: list[CompareItem] = Field(default_factory=list)
    comparison_summary: ComparisonSummary
    dimension_rankings: dict[str, list[str]] = Field(default_factory=dict)
    recommendation: str
