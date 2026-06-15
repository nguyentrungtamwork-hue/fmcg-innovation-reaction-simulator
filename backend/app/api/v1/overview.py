"""Project overview / workspace home endpoint (Phase 19, read-only)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.overview import OverviewOut
from app.services import overview_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["overview"])


@router.get("/overview", response_model=OverviewOut)
def get_overview(project_id: str, db: Session = Depends(get_db)) -> OverviewOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return overview_service.build_overview(db, project_id)
