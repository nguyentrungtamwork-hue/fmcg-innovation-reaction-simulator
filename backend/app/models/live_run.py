"""Live simulation run tracking (Phase 18)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class LiveSimulationRun(Base):
    __tablename__ = "live_simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="pending", index=True)  # pending|running|completed|failed|cancelled
    rounds: Mapped[int] = mapped_column(Integer, default=6)
    seed: Mapped[int] = mapped_column(Integer, default=42)
    deterministic: Mapped[bool] = mapped_column(Boolean, default=True)
    include_market_actors: Mapped[bool] = mapped_column(Boolean, default=True)
    force_rerun: Mapped[bool] = mapped_column(Boolean, default=True)
    event_delay_ms: Mapped[int] = mapped_column(Integer, default=100)
    total_events_expected: Mapped[int] = mapped_column(Integer, default=0)
    total_events_emitted: Mapped[int] = mapped_column(Integer, default=0)
    current_round: Mapped[int] = mapped_column(Integer, default=0)
    stale_after_seconds: Mapped[int] = mapped_column(Integer, default=600)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
