"""Schemas for Phase 13 — snapshot diff, decision log, timeline."""
from datetime import datetime

from pydantic import BaseModel, Field


# --- snapshot diff ----------------------------------------------------------


class DiffSide(BaseModel):
    type: str  # "active_report" | "snapshot"
    snapshot_id: str | None = None


class DiffRequest(BaseModel):
    left: DiffSide
    right: DiffSide


class DiffSideInfo(BaseModel):
    type: str
    name: str
    created_at: datetime | None = None


class NumericDelta(BaseModel):
    left: float
    right: float
    delta: float


class DimensionChange(BaseModel):
    dimension: str
    delta: float
    direction: str  # improved | declined | unchanged
    interpretation: str


class SectionChange(BaseModel):
    section: str
    change_type: str  # changed | unchanged
    summary: str


class RecommendationChange(BaseModel):
    left_recommendation: str
    right_recommendation: str
    changed: bool
    interpretation: str


class RiskChanges(BaseModel):
    reduced_risks: list[str] = Field(default_factory=list)
    new_or_increased_risks: list[str] = Field(default_factory=list)
    unchanged_risks: list[str] = Field(default_factory=list)


class SegmentChange(BaseModel):
    segment_name: str
    trial_delta: float
    repeat_delta: float
    sentiment_delta: float
    interpretation: str


class SnapshotDiffOut(BaseModel):
    project_id: str
    left: DiffSideInfo
    right: DiffSideInfo
    scorecard_delta: dict[str, NumericDelta] = Field(default_factory=dict)
    dimension_changes: list[DimensionChange] = Field(default_factory=list)
    changed_sections: list[SectionChange] = Field(default_factory=list)
    recommendation_changes: RecommendationChange
    risk_changes: RiskChanges
    segment_changes: list[SegmentChange] = Field(default_factory=list)
    plain_english_summary: str
    decision_implication: str
    limitations: list[str] = Field(default_factory=list)


# --- decision log -----------------------------------------------------------

ENTRY_TYPES = (
    "note",
    "decision",
    "change",
    "meeting",
    "validation_result",
    "snapshot_created",
    "report_regenerated",
    "scenario_reviewed",
)


class DecisionCreate(BaseModel):
    entry_type: str = "note"
    title: str = Field(min_length=1, max_length=200)
    body: str = ""
    related_snapshot_id: str | None = None
    related_scenario_id: str | None = None
    related_report_id: str | None = None
    tags: list[str] = Field(default_factory=list)


class DecisionOut(BaseModel):
    id: str
    project_id: str
    entry_type: str
    title: str
    body: str
    related_snapshot_id: str | None = None
    related_scenario_id: str | None = None
    related_report_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# --- timeline ---------------------------------------------------------------


class TimelineItem(BaseModel):
    timestamp: datetime
    type: str
    title: str
    description: str = ""
    related_id: str | None = None
    metadata: dict = Field(default_factory=dict)


class TimelineOut(BaseModel):
    project_id: str
    timeline: list[TimelineItem] = Field(default_factory=list)
