"""Phase 11 endpoints — sensitivity, confidence calibration, assumptions ledger."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.insight import AssumptionsOut, ConfidenceOut, SensitivityIn, SensitivityOut
from app.services import assumptions_service, confidence_service, project_service, sensitivity_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["insights"])


def _require_project(db: Session, project_id: str) -> None:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})


@router.post("/sensitivity", response_model=SensitivityOut)
def sensitivity(
    project_id: str, payload: SensitivityIn | None = None, db: Session = Depends(get_db)
) -> SensitivityOut:
    _require_project(db, project_id)
    try:
        return sensitivity_service.run_sensitivity(db, project_id, payload or SensitivityIn())
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})


@router.get("/confidence", response_model=ConfidenceOut)
def confidence(project_id: str, db: Session = Depends(get_db)) -> ConfidenceOut:
    _require_project(db, project_id)
    try:
        return confidence_service.compute(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})


@router.get("/assumptions", response_model=AssumptionsOut)
def assumptions(project_id: str, db: Session = Depends(get_db)) -> AssumptionsOut:
    _require_project(db, project_id)
    try:
        return assumptions_service.build(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
