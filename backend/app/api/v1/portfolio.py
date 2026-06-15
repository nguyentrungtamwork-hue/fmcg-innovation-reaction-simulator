"""Portfolio + comparison endpoints (Phase 12; decision board Phase 29)."""
from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.schemas.portfolio import CompareIn, CompareOut, PortfolioOut
from pydantic import BaseModel

from app.services import activity_service, decision_board_service, pipeline_service, portfolio_service
from app.storage.database import get_db

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


@router.get("", response_model=PortfolioOut)
def get_portfolio(db: Session = Depends(get_db)) -> PortfolioOut:
    return portfolio_service.build_portfolio(db)


@router.post("/compare", response_model=CompareOut)
def compare(payload: CompareIn, db: Session = Depends(get_db)) -> CompareOut:
    return portfolio_service.compare(db, payload)


def _parse_ids(project_ids: str | None) -> list[str] | None:
    if not project_ids:
        return None
    ids = [pid.strip() for pid in project_ids.split(",") if pid.strip()]
    return ids or None


@router.get("/decision-board")
def get_decision_board(
    project_ids: str | None = Query(default=None, description="Optional comma-separated project ids to include."),
    db: Session = Depends(get_db),
) -> dict:
    return decision_board_service.build_board(db, project_ids=_parse_ids(project_ids))


@router.get("/decision-board/markdown", response_class=PlainTextResponse)
def get_decision_board_markdown(
    project_ids: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> str:
    board = decision_board_service.build_board(db, project_ids=_parse_ids(project_ids))
    return decision_board_service.render_markdown(board)


class ApplyDecisionBoardIn(BaseModel):
    project_ids: list[str] | None = None
    only_if_not_manual: bool = True


@router.get("/pipeline")
def get_pipeline(
    db: Session = Depends(get_db),
    stage: str | None = Query(default=None),
    decision_label: str | None = Query(default=None),
    min_score: float | None = Query(default=None),
    max_risk: float | None = Query(default=None),
    owner_team: str | None = Query(default=None),
    search: str | None = Query(default=None),
    include_archived: bool = Query(default=True),
) -> dict:
    return pipeline_service.build_board(
        db,
        stage=stage,
        decision_label=decision_label,
        min_score=min_score,
        max_risk=max_risk,
        owner_team=owner_team,
        search=search,
        include_archived=include_archived,
    )


@router.get("/activity")
def get_activity(
    db: Session = Depends(get_db),
    event_type: str | None = Query(default=None),
    project_id: str | None = Query(default=None),
    stage: str | None = Query(default=None),
    limit: int = Query(default=30, ge=1, le=100),
) -> dict:
    return activity_service.list_activity(
        db,
        activity_type=event_type,
        project_id=project_id,
        stage=stage,
        limit=limit,
    )


@router.post("/pipeline/apply-decision-board")
def apply_decision_board(payload: ApplyDecisionBoardIn, db: Session = Depends(get_db)) -> dict:
    return pipeline_service.apply_decision_board(
        db,
        project_ids=payload.project_ids,
        only_if_not_manual=payload.only_if_not_manual,
    )
