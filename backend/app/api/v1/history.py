"""Phase 13 endpoints — snapshot diff, decision log, timeline."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.history import (
    DecisionCreate,
    DecisionOut,
    DiffRequest,
    SnapshotDiffOut,
    TimelineOut,
)
from app.services import decision_service, diff_service, project_service, timeline_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["history"])


def _require_project(db: Session, project_id: str):
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return project


# --- snapshot diff ----------------------------------------------------------


@router.post("/snapshots/diff", response_model=SnapshotDiffOut)
def snapshot_diff(project_id: str, payload: DiffRequest, db: Session = Depends(get_db)) -> SnapshotDiffOut:
    project = _require_project(db, project_id)
    try:
        return diff_service.diff(db, project_id, project.name, payload)
    except ValueError as e:
        code = str(e)
        status = 404 if code == "snapshot_not_found" else 400 if code == "invalid_diff_request" else 409
        raise HTTPException(status_code=status, detail={"code": code})


# --- decision log -----------------------------------------------------------


@router.post("/decisions", response_model=DecisionOut)
def create_decision(project_id: str, payload: DecisionCreate, db: Session = Depends(get_db)) -> DecisionOut:
    _require_project(db, project_id)
    return decision_service.to_out(decision_service.create_entry(db, project_id, payload))


@router.get("/decisions", response_model=list[DecisionOut])
def list_decisions(project_id: str, db: Session = Depends(get_db)) -> list[DecisionOut]:
    _require_project(db, project_id)
    return [decision_service.to_out(e) for e in decision_service.list_entries(db, project_id)]


@router.get("/decisions/{entry_id}", response_model=DecisionOut)
def get_decision(project_id: str, entry_id: str, db: Session = Depends(get_db)) -> DecisionOut:
    _require_project(db, project_id)
    entry = decision_service.get_entry(db, project_id, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail={"code": "decision_not_found"})
    return decision_service.to_out(entry)


@router.delete("/decisions/{entry_id}")
def delete_decision(project_id: str, entry_id: str, db: Session = Depends(get_db)) -> dict:
    _require_project(db, project_id)
    if not decision_service.delete_entry(db, project_id, entry_id):
        raise HTTPException(status_code=404, detail={"code": "decision_not_found"})
    return {"deleted": entry_id}


# --- timeline ---------------------------------------------------------------


@router.get("/timeline", response_model=TimelineOut)
def timeline(project_id: str, db: Session = Depends(get_db)) -> TimelineOut:
    project = _require_project(db, project_id)
    return timeline_service.build_timeline(db, project)
