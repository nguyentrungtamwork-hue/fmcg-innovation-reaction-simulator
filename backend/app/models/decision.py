"""Per-project decision log entry (Phase 13)."""
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.storage.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


class DecisionLogEntry(Base):
    __tablename__ = "decision_log_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id"), index=True)
    entry_type: Mapped[str] = mapped_column(String(40), default="note")
    title: Mapped[str] = mapped_column(String(200), default="")
    body: Mapped[str] = mapped_column(Text, default="")
    related_snapshot_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_scenario_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    related_report_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    tags_json: Mapped[str] = mapped_column(Text, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
