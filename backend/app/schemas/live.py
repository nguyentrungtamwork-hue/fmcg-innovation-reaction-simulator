"""Schemas for Phase 18 — live simulation streaming."""
from datetime import datetime

from pydantic import BaseModel, Field


class LiveSimulationStartIn(BaseModel):
    rounds: int = Field(default=6, ge=1, le=6)
    deterministic: bool = True
    seed: int = 42
    include_market_actors: bool = True
    force_rerun: bool = True
    event_delay_ms: int = Field(default=100, ge=0, le=2000)
    stale_after_seconds: int = Field(default=600, ge=0)


class LiveSimulationStartOut(BaseModel):
    run_id: str
    status: str
    stream_url: str


class LiveRunOut(BaseModel):
    run_id: str
    project_id: str
    status: str
    rounds: int
    seed: int
    deterministic: bool
    include_market_actors: bool
    force_rerun: bool
    event_delay_ms: int
    total_events_expected: int
    total_events_emitted: int
    current_round: int
    stale_after_seconds: int = 600
    error_message: str | None = None
    started_at: datetime | None = None
    last_heartbeat_at: datetime | None = None
    last_event_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    # computed
    is_stale: bool = False
    can_cancel: bool = False
    can_replay_persisted_events: bool = False
    stream_url: str | None = None
