"""Agent — consumer or market actor, grounded in the project's ontology."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    agent_type: Mapped[str] = mapped_column(String(50), index=True)  # consumer | market_actor
    segment_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    role: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)  # for market actors
    name: Mapped[str] = mapped_column(String(120))
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    memory_json: Mapped[str] = mapped_column(Text, default="[]")  # initial memory
    simulation_memory_json: Mapped[str] = mapped_column(Text, default="[]")
    action_history_json: Mapped[str] = mapped_column(Text, default="[]")
    source_mode: Mapped[str] = mapped_column(String(20), default="fallback")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
