"""Ontology — entities, relationships, FMCG strategic signals, all stored as JSON."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Ontology(Base):
    __tablename__ = "ontologies"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    brief_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    data_json: Mapped[str] = mapped_column(Text, default="{}")
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_mode: Mapped[str] = mapped_column(String(20), default="fallback")  # 'llm' | 'fallback'
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
