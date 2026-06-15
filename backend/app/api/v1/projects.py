import io
import json
import zipfile

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.schemas.project import ProjectCreate, ProjectEnvelope, ProjectOut
from app.services import data_export_service, decision_pack_service, pipeline_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects", tags=["projects"])


class ProjectImportIn(BaseModel):
    bundle: dict
    mode: str = "create_new"
    new_project_name: str | None = None
    preserve_original_ids: bool = False


class ProjectImportOut(BaseModel):
    status: str
    new_project_id: str
    counts: dict
    warnings: list[str] = []


class ProjectDeleteOut(BaseModel):
    status: str
    project_id: str
    counts: dict


_IMPORT_ERROR_STATUS = {
    "invalid_bundle": 400,
    "import_mode_not_supported": 400,
    "import_failed": 400,
}


@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)) -> ProjectOut:
    project = project_service.create_project(db, payload)
    return ProjectOut.model_validate(project)


@router.get("", response_model=list[ProjectOut])
def list_projects(demo: bool = False, db: Session = Depends(get_db)) -> list[ProjectOut]:
    return [ProjectOut.model_validate(p) for p in project_service.list_projects(db, demo_only=demo)]


@router.post("/import", response_model=ProjectImportOut)
def import_project(payload: ProjectImportIn, db: Session = Depends(get_db)) -> ProjectImportOut:
    try:
        result = data_export_service.import_project(
            db,
            payload.bundle,
            mode=payload.mode,
            new_project_name=payload.new_project_name,
            preserve_original_ids=payload.preserve_original_ids,
        )
    except ValueError as e:
        code = str(e)
        raise HTTPException(status_code=_IMPORT_ERROR_STATUS.get(code, 400), detail={"code": code})
    return ProjectImportOut(**result)


@router.get("/{project_id}", response_model=ProjectEnvelope)
def get_project(project_id: str, db: Session = Depends(get_db)) -> ProjectEnvelope:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    counts = project_service.envelope_counts(db, project_id)
    return ProjectEnvelope(project=ProjectOut.model_validate(project), **counts)


@router.get("/{project_id}/export")
def export_project(
    project_id: str,
    format: str = Query(default="json", pattern="^(json|zip)$"),
    include_logs: bool = False,
    include_events: bool = True,
    include_artifacts: bool = True,
    db: Session = Depends(get_db),
):
    try:
        bundle = data_export_service.export_project(
            db,
            project_id,
            include_logs=include_logs,
            include_events=include_events,
            include_artifacts=include_artifacts,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": str(e)})

    name = (bundle["data"]["project"].get("name") or "project").replace(" ", "_")[:40]
    text = json.dumps(bundle, ensure_ascii=False, indent=2, default=str)
    if format == "zip":
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(f"{name}_export.json", text)
        buf.seek(0)
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{name}_export.zip"'},
        )
    return StreamingResponse(
        io.BytesIO(text.encode("utf-8")),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="{name}_export.json"'},
    )


@router.delete("/{project_id}", response_model=ProjectDeleteOut)
def delete_project(project_id: str, db: Session = Depends(get_db)) -> ProjectDeleteOut:
    try:
        result = data_export_service.delete_project(db, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail={"code": str(e)})
    return ProjectDeleteOut(**result)


_PACK_ERRORS = {"events_required", "report_required", "scorecard_required", "briefing_required"}


def _build_pack_or_raise(db: Session, project_id: str) -> dict:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    try:
        return decision_pack_service.build_pack(db, project_id)
    except ValueError as e:
        code = str(e)
        status_code = 409 if code in _PACK_ERRORS else 400
        raise HTTPException(status_code=status_code, detail={"code": code})


@router.get("/{project_id}/decision-pack")
def get_decision_pack(project_id: str, db: Session = Depends(get_db)) -> dict:
    return _build_pack_or_raise(db, project_id)


@router.get("/{project_id}/decision-pack/markdown", response_class=PlainTextResponse)
def get_decision_pack_markdown(project_id: str, db: Session = Depends(get_db)) -> str:
    pack = _build_pack_or_raise(db, project_id)
    return decision_pack_service.render_markdown(pack)


class PipelineStatusUpdateIn(BaseModel):
    pipeline_stage: str
    note: str | None = None
    source: str = "manual"


_PIPELINE_ERROR_STATUS = {"project_not_found": 404, "invalid_stage": 422, "invalid_source": 422}


@router.get("/{project_id}/pipeline-status")
def get_pipeline_status(project_id: str, db: Session = Depends(get_db)) -> dict:
    try:
        return pipeline_service.get_status(db, project_id)
    except ValueError as e:
        code = str(e)
        raise HTTPException(status_code=_PIPELINE_ERROR_STATUS.get(code, 400), detail={"code": code})


@router.patch("/{project_id}/pipeline-status")
def update_pipeline_status(
    project_id: str, payload: PipelineStatusUpdateIn, db: Session = Depends(get_db)
) -> dict:
    try:
        return pipeline_service.update_status(
            db,
            project_id,
            pipeline_stage=payload.pipeline_stage,
            note=payload.note,
            source=payload.source,
        )
    except ValueError as e:
        code = str(e)
        raise HTTPException(status_code=_PIPELINE_ERROR_STATUS.get(code, 400), detail={"code": code})
