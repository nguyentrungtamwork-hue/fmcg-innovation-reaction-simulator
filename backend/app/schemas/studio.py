"""Schemas for Phase 16 — Agent Studio aggregated read-only state."""
from pydantic import BaseModel, Field


class StudioNode(BaseModel):
    id: str
    label: str
    type: str           # consumer | market_actor
    group: str          # segment name (consumers) or role (market actors)
    event_count: int = 0
    avg_sentiment: float = 0.0
    dominant_action: str | None = None


class StudioEdge(BaseModel):
    source: str
    target: str
    reason: str
    round_number: int


class StudioGraph(BaseModel):
    nodes: list[StudioNode] = Field(default_factory=list)
    edges: list[StudioEdge] = Field(default_factory=list)
    note: str = (
        "Interaction links are visualization aids derived from shared triggers/barriers/rounds "
        "and market-actor round impact — not real direct conversations."
    )


class StudioStateOut(BaseModel):
    project: dict
    agents: list[dict] = Field(default_factory=list)
    events: list[dict] = Field(default_factory=list)
    events_summary: dict = Field(default_factory=dict)
    rounds: list[dict] = Field(default_factory=list)
    graph: StudioGraph
