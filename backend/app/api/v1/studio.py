"""Agent Studio aggregated state endpoint (Phase 16, read-only)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.studio import StudioStateOut
from app.services import project_service, studio_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/studio", tags=["studio"])


@router.get("/state", response_model=StudioStateOut)
def studio_state(project_id: str, db: Session = Depends(get_db)) -> StudioStateOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return studio_service.build_state(db, project_id)
