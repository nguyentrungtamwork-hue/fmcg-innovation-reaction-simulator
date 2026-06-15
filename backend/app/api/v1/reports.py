"""Strategic launch report endpoints (Phase 6)."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.schemas.report import ReportGenerateIn, ReportGenerateOut
from app.services import project_service, report_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/report", tags=["report"])


def _require_project(db: Session, project_id: str) -> None:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})


def _to_out(report) -> ReportGenerateOut:
    return ReportGenerateOut(
        project_id=report.project_id,
        report_id=report.id,
        status="completed",
        source_mode=report.source_mode,
        confidence_score=report.confidence_score,
        generated_at=report.updated_at or report.created_at,
        report_payload=report_service.get_payload(report),
        markdown_report=report.markdown,
        summary=report_service.get_summary(report),
    )


@router.post("/generate", response_model=ReportGenerateOut)
def generate_report(
    project_id: str,
    body: ReportGenerateIn | None = None,
    db: Session = Depends(get_db),
) -> ReportGenerateOut:
    _require_project(db, project_id)
    try:
        report = report_service.generate_report(db, project_id, body or ReportGenerateIn())
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return _to_out(report)


@router.get("/markdown")
def get_report_markdown(project_id: str, db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise HTTPException(status_code=409, detail={"code": "report_required"})
    return Response(content=report.markdown, media_type="text/markdown")


@router.get("/summary")
def get_report_summary(project_id: str, db: Session = Depends(get_db)):
    _require_project(db, project_id)
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise HTTPException(status_code=409, detail={"code": "report_required"})
    return report_service.get_summary(report)


@router.get("/export")
def export_report(project_id: str, db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise HTTPException(status_code=409, detail={"code": "report_required"})
    return Response(
        content=report.payload_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="report_{project_id}.json"'},
    )


@router.get("", response_model=ReportGenerateOut)
def get_report(project_id: str, db: Session = Depends(get_db)) -> ReportGenerateOut:
    _require_project(db, project_id)
    report = report_service.get_report_row(db, project_id)
    if report is None:
        raise HTTPException(status_code=409, detail={"code": "report_required"})
    return _to_out(report)
