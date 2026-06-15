from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.schemas.brief import BriefIn, BriefOut
from app.services import brief_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/brief", tags=["brief"])


@router.post("", response_model=BriefOut)
def submit_brief_json(
    project_id: str, payload: BriefIn, db: Session = Depends(get_db)
) -> BriefOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    brief, field_count = brief_service.submit_brief(db, project_id, payload=payload)
    return BriefOut(brief_id=brief.id, stored=True, field_count=field_count)


@router.post("/upload", response_model=BriefOut)
async def submit_brief_upload(
    project_id: str, file: UploadFile = File(...), db: Session = Depends(get_db)
) -> BriefOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    raw = (await file.read()).decode("utf-8", errors="ignore")
    brief, _ = brief_service.submit_brief(
        db, project_id, raw_text=raw, source_filename=file.filename
    )
    return BriefOut(brief_id=brief.id, stored=True, field_count=0)
