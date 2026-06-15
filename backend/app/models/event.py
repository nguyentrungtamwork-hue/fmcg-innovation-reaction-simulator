"""Simulation event log row."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    round_number: Mapped[int] = mapped_column(Integer, index=True)
    stage_name: Mapped[str] = mapped_column(String(100))
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), index=True)
    agent_type: Mapped[str] = mapped_column(String(50))
    touchpoint: Mapped[str | None] = mapped_column(String(100), nullable=True)
    action_type: Mapped[str] = mapped_column(String(80), index=True)
    content_seen: Mapped[str | None] = mapped_column(Text, nullable=True)
    reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    generated_reaction: Mapped[str | None] = mapped_column(Text, nullable=True)
    emotional_tone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    trial_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    purchase_intent_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    repeat_probability: Mapped[float | None] = mapped_column(Float, nullable=True)
    trust_change: Mapped[float | None] = mapped_column(Float, nullable=True)
    barrier_detected: Mapped[str | None] = mapped_column(String(255), nullable=True)
    trigger_detected: Mapped[str | None] = mapped_column(String(255), nullable=True)
    segment_name: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    run_type: Mapped[str] = mapped_column(String(20), default="baseline", index=True)  # baseline | scenario
    scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    scores_json: Mapped[str] = mapped_column(Text, default="{}")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
