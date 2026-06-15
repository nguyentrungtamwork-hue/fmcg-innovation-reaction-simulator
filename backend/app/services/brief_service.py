"""Brief submission service. Accepts structured JSON or raw uploaded file."""
import json

from sqlalchemy.orm import Session

from app.models import Brief
from app.schemas.brief import BriefIn


def submit_brief(
    db: Session,
    project_id: str,
    payload: BriefIn | None = None,
    raw_text: str | None = None,
    source_filename: str | None = None,
) -> tuple[Brief, int]:
    """Create or replace the brief for a project. Returns (brief, structured field count)."""
    structured: dict = {}
    text = raw_text or ""
    if payload is not None:
        data = payload.model_dump(exclude_none=False)
        text = data.pop("raw_text", "") or text
        structured = {k: v for k, v in data.items() if v not in (None, "", [], {})}

    brief = Brief(
        project_id=project_id,
        raw_text=text,
        structured_json=json.dumps(structured, ensure_ascii=False),
        source_filename=source_filename,
    )
    db.add(brief)
    db.commit()
    db.refresh(brief)
    return brief, len(structured)
