import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Ontology
from app.schemas.ontology import OntologyOut, OntologyPayload
from app.services import ontology_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}", tags=["ontology"])


def _to_out(o: Ontology) -> OntologyOut:
    payload = OntologyPayload.model_validate(json.loads(o.data_json or "{}"))
    return OntologyOut(
        ontology_id=o.id,
        project_id=o.project_id,
        brief_id=o.brief_id,
        source_mode=o.source_mode,
        confidence_score=o.confidence_score,
        created_at=o.created_at,
        updated_at=o.updated_at,
        **payload.model_dump(by_alias=True),
    )


@router.post("/analyze", response_model=OntologyOut)
def analyze(project_id: str, db: Session = Depends(get_db)) -> OntologyOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    try:
        ontology = ontology_service.analyze_brief(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)}) from e
    except ontology_service.OntologyExtractionError as e:
        raise HTTPException(
            status_code=502, detail={"code": "extraction_failed", "message": str(e)}
        ) from e
    return _to_out(ontology)


@router.get("/ontology", response_model=OntologyOut)
def get_ontology(project_id: str, db: Session = Depends(get_db)) -> OntologyOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    ontology = ontology_service.get_ontology(db, project_id)
    if ontology is None:
        raise HTTPException(status_code=404, detail={"code": "ontology_not_found"})
    return _to_out(ontology)
