"""Derived briefing artifacts (Phase 15) — board summary / tailored briefing."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class BriefingArtifact(Base):
    __tablename__ = "briefing_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), default="board_summary", index=True)  # board_summary | tailored_briefing
    audience: Mapped[str] = mapped_column(String(40), default="")
    tone: Mapped[str] = mapped_column(String(40), default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    markdown: Mapped[str] = mapped_column(Text, default="")
    source_mode: Mapped[str] = mapped_column(String(20), default="deterministic")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
