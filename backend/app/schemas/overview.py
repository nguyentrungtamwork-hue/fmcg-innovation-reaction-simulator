"""Schemas for Phase 19 — aggregated project overview / workspace home."""
from pydantic import BaseModel, Field


class PipelineStatus(BaseModel):
    has_brief: bool = False
    has_ontology: bool = False
    has_agents: bool = False
    has_simulation: bool = False
    has_report: bool = False
    has_briefing: bool = False


class OverviewCounts(BaseModel):
    agents: int = 0
    events: int = 0
    snapshots: int = 0
    scenarios: int = 0
    decisions: int = 0


class NextAction(BaseModel):
    action: str          # submit_brief | analyze_ontology | generate_agents | run_live_simulation | generate_report | generate_briefing | explore | resolve_stale_run
    label: str
    surface: str         # route key: workflow | studio | report | briefing | scenarios | ...
    reason: str


class ActivityItem(BaseModel):
    timestamp: str | None = None
    type: str
    title: str
    description: str = ""


class OverviewOut(BaseModel):
    project: dict
    pipeline_status: PipelineStatus
    counts: OverviewCounts
    latest_scorecard: dict | None = None
    latest_briefing_summary: dict | None = None
    latest_live_run: dict | None = None
    next_recommended_action: NextAction
    recent_activity: list[ActivityItem] = Field(default_factory=list)
