"""Ontology extraction orchestrator. LLM path with deterministic fallback."""
from __future__ import annotations

import json
import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Brief, Ontology
from app.schemas.ontology import OntologyPayload
from app.services.llm_client import LLMClient, LLMNotConfigured
from app.services.ontology_fallback import fallback_extract
from app.services.ontology_prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


class OntologyExtractionError(RuntimeError):
    pass


def _latest_brief(db: Session, project_id: str) -> Brief | None:
    return db.execute(
        select(Brief).where(Brief.project_id == project_id).order_by(Brief.created_at.desc())
    ).scalars().first()


def _confidence_from_payload(p: OntologyPayload, mode: str) -> float:
    base = 0.85 if mode == "llm" else 0.55
    penalty = min(0.3, 0.03 * len(p.missing_information))
    bonus = min(0.1, 0.005 * (len(p.entities) + len(p.relationships)))
    return round(max(0.0, min(1.0, base - penalty + bonus)), 3)


def _extract_with_llm(raw_text: str, structured: dict, client: LLMClient) -> OntologyPayload:
    user = build_user_prompt(raw_text, structured)
    try:
        data = client.chat_json(SYSTEM_PROMPT, user)
    except json.JSONDecodeError as e:
        raise OntologyExtractionError(f"LLM returned invalid JSON: {e}") from e
    try:
        return OntologyPayload.model_validate(data)
    except Exception as e:  # noqa: BLE001
        raise OntologyExtractionError(f"LLM JSON failed schema validation: {e}") from e


def analyze_brief(
    db: Session,
    project_id: str,
    llm_client: LLMClient | None = None,
    force_fallback: bool = False,
) -> Ontology:
    """Extract an ontology from the project's latest brief, persist, return it.

    Behavior:
    - If no brief exists, raises ValueError('brief_required').
    - If an ontology already exists for the project, it is replaced (delete + insert).
    - Uses the LLM client if configured; otherwise falls back to the deterministic extractor.
    """
    brief = _latest_brief(db, project_id)
    if brief is None:
        raise ValueError("brief_required")

    structured: dict = {}
    if brief.structured_json:
        try:
            structured = json.loads(brief.structured_json) or {}
        except json.JSONDecodeError:
            structured = {}

    client = llm_client or LLMClient()
    use_llm = client.configured and not force_fallback

    payload: OntologyPayload
    mode = "fallback"
    if use_llm:
        try:
            payload = _extract_with_llm(brief.raw_text or "", structured, client)
            mode = "llm"
        except (OntologyExtractionError, LLMNotConfigured, Exception) as e:  # noqa: BLE001
            logger.warning("LLM ontology extraction failed; falling back. error=%s", e)
            payload = fallback_extract(brief.raw_text or "", structured)
            mode = "fallback"
    else:
        payload = fallback_extract(brief.raw_text or "", structured)

    # Replace any existing ontology for the project.
    existing = db.execute(
        select(Ontology).where(Ontology.project_id == project_id)
    ).scalars().all()
    for o in existing:
        db.delete(o)
    db.flush()

    ontology = Ontology(
        project_id=project_id,
        brief_id=brief.id,
        data_json=payload.model_dump_json(by_alias=True),
        confidence_score=_confidence_from_payload(payload, mode),
        source_mode=mode,
    )
    db.add(ontology)
    db.commit()
    db.refresh(ontology)
    return ontology


def get_ontology(db: Session, project_id: str) -> Ontology | None:
    return db.execute(
        select(Ontology).where(Ontology.project_id == project_id).order_by(Ontology.created_at.desc())
    ).scalars().first()
