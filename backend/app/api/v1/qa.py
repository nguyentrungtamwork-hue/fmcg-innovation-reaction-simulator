from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.schemas.qa import QuestionIn, QuestionOut
from app.services import project_service, qa_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["qa"])


@router.post("/ask", response_model=QuestionOut)
def ask(project_id: str, payload: QuestionIn, db: Session = Depends(get_db)) -> QuestionOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    try:
        return qa_service.ask(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
