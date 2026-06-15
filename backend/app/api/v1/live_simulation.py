"""Live simulation streaming endpoints (Phase 18, SSE)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.schemas.live import LiveRunOut, LiveSimulationStartIn, LiveSimulationStartOut
from app.services import live_simulation_service, project_service, simulation_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/live-simulation", tags=["live-simulation"])


def _require_project(db: Session, project_id: str) -> None:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})


@router.post("/start", response_model=LiveSimulationStartOut)
def start(project_id: str, payload: LiveSimulationStartIn | None = None, db: Session = Depends(get_db)) -> LiveSimulationStartOut:
    _require_project(db, project_id)
    try:
        run = live_simulation_service.start_run(db, project_id, payload or LiveSimulationStartIn())
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return LiveSimulationStartOut(
        run_id=run.id,
        status=run.status,
        stream_url=f"/api/v1/projects/{project_id}/live-simulation/{run.id}/stream",
    )


@router.get("/runs", response_model=list[LiveRunOut])
def list_runs(project_id: str, db: Session = Depends(get_db)) -> list[LiveRunOut]:
    _require_project(db, project_id)
    return [live_simulation_service.to_out(r) for r in live_simulation_service.list_runs(db, project_id)]


@router.get("/{run_id}", response_model=LiveRunOut)
def get_run(project_id: str, run_id: str, db: Session = Depends(get_db)) -> LiveRunOut:
    _require_project(db, project_id)
    run = live_simulation_service.get_run(db, project_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "live_run_not_found"})
    has_events = simulation_service.events_summary(db, project_id)["total_events"] > 0
    return live_simulation_service.to_out(run, has_events=has_events)


@router.post("/{run_id}/cancel", response_model=LiveRunOut)
def cancel(project_id: str, run_id: str, db: Session = Depends(get_db)) -> LiveRunOut:
    _require_project(db, project_id)
    run = live_simulation_service.get_run(db, project_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "live_run_not_found"})
    if run.status in ("pending", "running"):
        run.status = "cancelled"
        db.commit()
        db.refresh(run)
    return live_simulation_service.to_out(run)


@router.get("/{run_id}/stream")
def stream(project_id: str, run_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    _require_project(db, project_id)
    run = live_simulation_service.get_run(db, project_id, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "live_run_not_found"})

    def gen():
        # initial heartbeat so the client knows the stream is open
        yield ": heartbeat\n\n"
        for message in live_simulation_service.iter_stream(db, project_id, run_id):
            yield f"event: {message['type']}\ndata: {json.dumps(message, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no", "Connection": "keep-alive"},
    )
