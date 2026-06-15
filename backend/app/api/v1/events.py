import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Event
from app.schemas.event import EventOut
from app.schemas.simulation import EventsSummaryOut
from app.services import project_service, simulation_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/events", tags=["events"])


def _to_out(e: Event) -> EventOut:
    return EventOut(
        id=e.id,
        round_number=e.round_number,
        stage_name=e.stage_name,
        agent_id=e.agent_id,
        agent_type=e.agent_type,
        segment_name=e.segment_name,
        touchpoint=e.touchpoint,
        action_type=e.action_type,
        content_seen=e.content_seen,
        reasoning=e.reasoning,
        generated_reaction=e.generated_reaction,
        emotional_tone=e.emotional_tone,
        confidence_score=e.confidence_score,
        sentiment_score=e.sentiment_score,
        trial_probability=e.trial_probability,
        purchase_intent_score=e.purchase_intent_score,
        repeat_probability=e.repeat_probability,
        trust_change=e.trust_change,
        barrier_detected=e.barrier_detected,
        trigger_detected=e.trigger_detected,
        scores=json.loads(e.scores_json or "{}"),
        timestamp=e.timestamp,
    )


@router.get("", response_model=list[EventOut])
def list_events(
    project_id: str,
    limit: int = 100,
    offset: int = 0,
    round_number: int | None = None,
    action_type: str | None = None,
    agent_id: str | None = None,
    agent_type: str | None = None,
    segment_name: str | None = None,
    db: Session = Depends(get_db),
) -> list[EventOut]:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    events = simulation_service.list_events(
        db,
        project_id,
        limit=limit,
        offset=offset,
        round_number=round_number,
        action_type=action_type,
        agent_id=agent_id,
        agent_type=agent_type,
        segment_name=segment_name,
    )
    return [_to_out(e) for e in events]


@router.get("/summary", response_model=EventsSummaryOut)
def events_summary(project_id: str, db: Session = Depends(get_db)) -> EventsSummaryOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return EventsSummaryOut(**simulation_service.events_summary(db, project_id))


@router.get("/{event_id}", response_model=EventOut)
def get_event(project_id: str, event_id: str, db: Session = Depends(get_db)) -> EventOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    event = simulation_service.get_event(db, project_id, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail={"code": "event_not_found"})
    return _to_out(event)
