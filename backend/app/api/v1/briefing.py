"""Executive briefing endpoints (Phase 14)."""
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.schemas.briefing import (
    BriefingAskIn,
    BriefingAskOut,
    BriefingGenerateIn,
    BriefingOut,
    BriefingSummary,
    BoardSummaryIn,
    BoardSummaryOut,
    TailorIn,
    TailorOut,
)
from app.services import briefing_qa_service, briefing_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/briefing", tags=["briefing"])


def _require_project(db: Session, project_id: str) -> None:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})


def _to_out(doc) -> BriefingOut:
    return BriefingOut(
        project_id=doc.project_id,
        briefing_id=doc.id,
        status="generated",
        source_mode=doc.source_mode,
        audience=doc.audience,
        tone=doc.tone,
        generated_at=doc.updated_at or doc.created_at,
        briefing_payload=briefing_service.get_payload(doc),
        markdown=doc.markdown,
        summary=briefing_service.get_summary(doc),
    )


@router.post("/generate", response_model=BriefingOut)
def generate(project_id: str, body: BriefingGenerateIn | None = None, db: Session = Depends(get_db)) -> BriefingOut:
    _require_project(db, project_id)
    try:
        doc = briefing_service.generate(db, project_id, body or BriefingGenerateIn())
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)})
    return _to_out(doc)


@router.get("", response_model=BriefingOut)
def get_briefing(project_id: str, db: Session = Depends(get_db)) -> BriefingOut:
    _require_project(db, project_id)
    doc = briefing_service.get_briefing_row(db, project_id)
    if doc is None:
        raise HTTPException(status_code=409, detail={"code": "briefing_required"})
    return _to_out(doc)


@router.get("/markdown")
def get_markdown(project_id: str, db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    doc = briefing_service.get_briefing_row(db, project_id)
    if doc is None:
        raise HTTPException(status_code=409, detail={"code": "briefing_required"})
    return Response(content=doc.markdown, media_type="text/markdown")


@router.get("/summary", response_model=BriefingSummary)
def get_summary(project_id: str, db: Session = Depends(get_db)) -> BriefingSummary:
    _require_project(db, project_id)
    doc = briefing_service.get_briefing_row(db, project_id)
    if doc is None:
        raise HTTPException(status_code=409, detail={"code": "briefing_required"})
    return briefing_service.get_summary(doc)


@router.get("/export")
def export_briefing(project_id: str, format: str = "json", db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    doc = briefing_service.get_briefing_row(db, project_id)
    if doc is None:
        raise HTTPException(status_code=409, detail={"code": "briefing_required"})
    if format == "markdown":
        return Response(
            content=doc.markdown,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="briefing-{project_id}.md"'},
        )
    return Response(
        content=doc.payload_json,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="briefing-{project_id}.json"'},
    )


# --- Phase 15: Q&A, tailoring, board summary --------------------------------


def _409(e: ValueError) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": str(e)})


@router.post("/ask", response_model=BriefingAskOut)
def ask(project_id: str, payload: BriefingAskIn, db: Session = Depends(get_db)) -> BriefingAskOut:
    _require_project(db, project_id)
    try:
        return briefing_qa_service.ask(db, project_id, payload)
    except ValueError as e:
        raise _409(e)


@router.post("/tailor", response_model=TailorOut)
def tailor(project_id: str, payload: TailorIn | None = None, db: Session = Depends(get_db)) -> TailorOut:
    _require_project(db, project_id)
    try:
        return briefing_qa_service.tailor(db, project_id, payload or TailorIn())
    except ValueError as e:
        raise _409(e)


@router.post("/board-summary", response_model=BoardSummaryOut)
def board_summary(project_id: str, payload: BoardSummaryIn | None = None, db: Session = Depends(get_db)) -> BoardSummaryOut:
    _require_project(db, project_id)
    try:
        return briefing_qa_service.generate_board_summary(db, project_id, payload or BoardSummaryIn())
    except ValueError as e:
        raise _409(e)


@router.get("/board-summary", response_model=BoardSummaryOut)
def get_board_summary(project_id: str, db: Session = Depends(get_db)) -> BoardSummaryOut:
    _require_project(db, project_id)
    try:
        return briefing_qa_service.get_board_summary(db, project_id)
    except ValueError as e:
        raise _409(e)


@router.get("/board-summary/export")
def export_board_summary(project_id: str, format: str = "json", db: Session = Depends(get_db)) -> Response:
    _require_project(db, project_id)
    try:
        bs = briefing_qa_service.get_board_summary(db, project_id)
    except ValueError as e:
        raise _409(e)
    if format == "markdown":
        return Response(
            content=bs.markdown,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="board-summary-{project_id}.md"'},
        )
    return Response(
        content=bs.summary_payload.model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="board-summary-{project_id}.json"'},
    )
