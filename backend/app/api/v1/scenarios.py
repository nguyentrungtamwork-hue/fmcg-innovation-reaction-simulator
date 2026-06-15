"""Scenario testing endpoints (Phase 7)."""
import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.scenario import ScenarioListItem, ScenarioRunIn, ScenarioRunOut
from app.services import project_service, scenario_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["scenarios"])


def _require_project(db: Session, project_id: str) -> None:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})


@router.post("/scenario", response_model=ScenarioRunOut)
def run_scenario(
    project_id: str, payload: ScenarioRunIn, db: Session = Depends(get_db)
) -> ScenarioRunOut:
    _require_project(db, project_id)
    try:
        run = scenario_service.run_scenario(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return scenario_service.to_out(run)


@router.get("/scenarios", response_model=list[ScenarioListItem])
def list_scenarios(project_id: str, db: Session = Depends(get_db)) -> list[ScenarioListItem]:
    _require_project(db, project_id)
    return [
        ScenarioListItem(
            scenario_id=r.id,
            scenario_name=r.scenario_name,
            description=r.description,
            baseline_event_count=r.baseline_event_count,
            scenario_event_count=r.scenario_event_count,
            created_at=r.created_at,
        )
        for r in scenario_service.list_scenarios(db, project_id)
    ]


@router.get("/scenarios/{scenario_id}", response_model=ScenarioRunOut)
def get_scenario(
    project_id: str, scenario_id: str, db: Session = Depends(get_db)
) -> ScenarioRunOut:
    _require_project(db, project_id)
    run = scenario_service.get_scenario(db, project_id, scenario_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "scenario_not_found"})
    return scenario_service.to_out(run)


@router.get("/scenarios/{scenario_id}/delta")
def get_scenario_delta(
    project_id: str, scenario_id: str, db: Session = Depends(get_db)
) -> dict:
    _require_project(db, project_id)
    run = scenario_service.get_scenario(db, project_id, scenario_id)
    if run is None:
        raise HTTPException(status_code=404, detail={"code": "scenario_not_found"})
    return json.loads(run.delta_payload_json or "{}")


@router.delete("/scenarios/{scenario_id}")
def delete_scenario(
    project_id: str, scenario_id: str, db: Session = Depends(get_db)
) -> dict:
    _require_project(db, project_id)
    if not scenario_service.delete_scenario(db, project_id, scenario_id):
        raise HTTPException(status_code=404, detail={"code": "scenario_not_found"})
    return {"deleted": scenario_id}
