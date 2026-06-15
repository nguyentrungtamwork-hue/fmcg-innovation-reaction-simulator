"""Snapshot + scorecard endpoints (Phase 12)."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.schemas.portfolio import Scorecard, SnapshotCreate, SnapshotListItem, SnapshotOut
from app.services import project_service, scorecard_service, snapshot_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["snapshots"])


def _require_project(db: Session, project_id: str):
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return project


# --- scorecard --------------------------------------------------------------


@router.get("/scorecard", response_model=Scorecard)
def get_scorecard(project_id: str, db: Session = Depends(get_db)) -> Scorecard:
    project = _require_project(db, project_id)
    try:
        return scorecard_service.build_for_project(db, project_id, project.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})


@router.get("/scorecard/export")
def export_scorecard(project_id: str, format: str = "json", db: Session = Depends(get_db)) -> Response:
    project = _require_project(db, project_id)
    try:
        sc = scorecard_service.build_for_project(db, project_id, project.name)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return _scorecard_response(sc, format, f"scorecard-{project_id}")


# --- snapshots --------------------------------------------------------------


@router.post("/snapshots", response_model=SnapshotOut)
def create_snapshot(project_id: str, payload: SnapshotCreate, db: Session = Depends(get_db)) -> SnapshotOut:
    _require_project(db, project_id)
    try:
        snap = snapshot_service.create_snapshot(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return snapshot_service.to_out(snap)


@router.get("/snapshots", response_model=list[SnapshotListItem])
def list_snapshots(project_id: str, db: Session = Depends(get_db)) -> list[SnapshotListItem]:
    _require_project(db, project_id)
    return [
        SnapshotListItem(
            snapshot_id=s.id,
            snapshot_name=s.snapshot_name,
            description=s.description,
            source_report_id=s.source_report_id,
            source_project_status=s.source_project_status,
            created_at=s.created_at,
        )
        for s in snapshot_service.list_snapshots(db, project_id)
    ]


@router.get("/snapshots/{snapshot_id}", response_model=SnapshotOut)
def get_snapshot(project_id: str, snapshot_id: str, db: Session = Depends(get_db)) -> SnapshotOut:
    _require_project(db, project_id)
    snap = snapshot_service.get_snapshot(db, project_id, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found"})
    return snapshot_service.to_out(snap)


@router.get("/snapshots/{snapshot_id}/scorecard", response_model=Scorecard)
def snapshot_scorecard(project_id: str, snapshot_id: str, db: Session = Depends(get_db)) -> Scorecard:
    _require_project(db, project_id)
    snap = snapshot_service.get_snapshot(db, project_id, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found"})
    return snapshot_service.scorecard_of(snap)


@router.get("/snapshots/{snapshot_id}/scorecard/export")
def export_snapshot_scorecard(project_id: str, snapshot_id: str, format: str = "json", db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    snap = snapshot_service.get_snapshot(db, project_id, snapshot_id)
    if snap is None:
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found"})
    return _scorecard_response(snapshot_service.scorecard_of(snap), format, f"scorecard-{snapshot_id}")


@router.delete("/snapshots/{snapshot_id}")
def delete_snapshot(project_id: str, snapshot_id: str, db: Session = Depends(get_db)) -> dict:
    _require_project(db, project_id)
    if not snapshot_service.delete_snapshot(db, project_id, snapshot_id):
        raise HTTPException(status_code=404, detail={"code": "snapshot_not_found"})
    return {"deleted": snapshot_id}


def _scorecard_response(sc: Scorecard, format: str, filename: str) -> Response:
    if format == "markdown":
        return Response(
            content=scorecard_service.to_markdown(sc),
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="{filename}.md"'},
        )
    return Response(
        content=sc.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
    )
