"""Scenario run — a what-if re-simulation under modified assumptions.

Stored separately from the baseline so the baseline simulation + report are
never overwritten. The full baseline-vs-scenario delta is persisted as JSON.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    scenario_name: Mapped[str] = mapped_column(String(160), default="Scenario")
    description: Mapped[str] = mapped_column(Text, default="")
    overrides_json: Mapped[str] = mapped_column(Text, default="{}")
    baseline_event_count: Mapped[int] = mapped_column(Integer, default=0)
    scenario_event_count: Mapped[int] = mapped_column(Integer, default=0)
    delta_payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
