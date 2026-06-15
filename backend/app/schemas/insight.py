"""Schemas for Phase 11 — sensitivity, confidence calibration, assumptions ledger."""
from pydantic import BaseModel, Field


# --- sensitivity ------------------------------------------------------------


class SensitivityIn(BaseModel):
    levers: dict[str, list[float]] | None = None  # None → DEFAULT_LEVERS
    seed: int = 42
    rounds: int = Field(default=6, ge=1, le=6)


class SweepPoint(BaseModel):
    value: float
    trial_probability: float
    repeat_probability: float
    purchase_intent: float
    sentiment: float
    recommend_rate: float
    complaint_rate: float
    top_improved_segments: list[str] = Field(default_factory=list)
    top_declined_segments: list[str] = Field(default_factory=list)
    interpretation: str


class LeverSweep(BaseModel):
    lever: str
    points: list[SweepPoint] = Field(default_factory=list)
    best_point: SweepPoint | None = None
    diminishing_return_point: SweepPoint | None = None
    strategic_read: str


class SensitivityOut(BaseModel):
    project_id: str
    baseline_summary: dict
    sweeps: list[LeverSweep] = Field(default_factory=list)
    overall_recommendation: str
    limitations: list[str] = Field(default_factory=list)


# --- confidence -------------------------------------------------------------


class ConfidenceDriver(BaseModel):
    factor: str
    score: float
    weight: float
    explanation: str


class ConfidenceOut(BaseModel):
    project_id: str
    overall_confidence: float
    confidence_label: str
    drivers: list[ConfidenceDriver] = Field(default_factory=list)
    confidence_risks: list[str] = Field(default_factory=list)
    how_to_improve_confidence: list[str] = Field(default_factory=list)
    disclaimer: str


# --- assumptions ------------------------------------------------------------


class AssumptionItem(BaseModel):
    category: str
    assumption: str
    source: str
    impact: str  # high | medium | low
    recommended_validation: str


class AssumptionsSummary(BaseModel):
    high_impact_count: int = 0
    medium_impact_count: int = 0
    low_impact_count: int = 0


class AssumptionsOut(BaseModel):
    project_id: str
    assumptions: list[AssumptionItem] = Field(default_factory=list)
    summary: AssumptionsSummary
