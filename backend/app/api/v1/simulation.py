from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.simulation import SimulationRunIn, SimulationRunOut
from app.services import project_service, simulation_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["simulation"])


@router.post("/simulate", response_model=SimulationRunOut)
def simulate(
    project_id: str, payload: SimulationRunIn | None = None, db: Session = Depends(get_db)
) -> SimulationRunOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    try:
        result = simulation_service.run_simulation(db, project_id, payload or SimulationRunIn())
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)}) from e
    return SimulationRunOut(**result)


@router.get("/simulate/status")
def simulate_status(project_id: str, db: Session = Depends(get_db)) -> dict:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    summary = simulation_service.events_summary(db, project_id)
    summary["simulation_status"] = "completed" if summary["total_events"] else "not_run"
    return summary
