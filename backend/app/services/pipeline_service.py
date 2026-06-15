"""Innovation Pipeline Board — per-project stage tracking (Phase 30).

Adds a lightweight, deterministic stage state on top of existing data (no new
scoring, no LLM, no invented findings). The stage is either set manually, mapped
from the Decision Board label, or **inferred** from the workflow state. Every
manual or applied change writes a `DecisionLogEntry` for traceability.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Brief, DecisionLogEntry, Event, Ontology, Project, Report
from app.models import BriefingDoc
from app.services import decision_board_service, decision_service, project_service

# Stage definitions -----------------------------------------------------------

STAGES = (
    "new_concept",
    "brief_submitted",
    "ready_for_simulation",
    "simulated",
    "report_ready",
    "briefing_ready",
    "leadership_review",
    "validate",
    "revise",
    "go",
    "hold",
    "archived",
)

STAGE_LABELS = {
    "new_concept": "New Concept",
    "brief_submitted": "Brief Submitted",
    "ready_for_simulation": "Ready for Simulation",
    "simulated": "Simulated",
    "report_ready": "Report Ready",
    "briefing_ready": "Briefing Ready",
    "leadership_review": "Leadership Review",
    "validate": "Validate",
    "revise": "Revise",
    "go": "Go",
    "hold": "Hold",
    "archived": "Archived",
}

SOURCES = ("manual", "inferred", "decision_board", "system")

_BOARD_TO_STAGE = {
    "go": "go",
    "validate": "validate",
    "revise": "revise",
    "hold": "hold",
}


# Inference helpers -----------------------------------------------------------


def _has(db: Session, model, project_id: str, **where) -> bool:
    stmt = select(func.count(model.id)).where(model.project_id == project_id)
    for k, v in where.items():
        stmt = stmt.where(getattr(model, k) == v)
    return (db.execute(stmt).scalar_one() or 0) > 0


def infer_stage(db: Session, project_id: str) -> str:
    """Derive a stage purely from the workflow state (no decision board)."""
    if not _has(db, Brief, project_id):
        return "new_concept"
    if not _has(db, Ontology, project_id):
        return "brief_submitted"
    if not _has(db, Agent, project_id):
        return "brief_submitted"
    if not _has(db, Event, project_id, run_type="baseline"):
        return "ready_for_simulation"
    if not _has(db, Report, project_id):
        return "simulated"
    if not _has(db, BriefingDoc, project_id):
        return "report_ready"
    return "briefing_ready"


def _board_label_for(db: Session, project_id: str) -> str | None:
    """Cheap one-project query of the decision board for its label."""
    project = project_service.get_project(db, project_id)
    if project is None:
        return None
    item, _ = decision_board_service._build_item(db, project)
    return item.get("decision_label")


def recommended_stage(inferred: str, board_label: str | None) -> str:
    if board_label and board_label in _BOARD_TO_STAGE:
        return _BOARD_TO_STAGE[board_label]
    return inferred


def _next_action(stage: str) -> dict:
    table = {
        "new_concept": ("Submit an innovation brief.", "workflow"),
        "brief_submitted": ("Analyze the brief and generate agents.", "workflow"),
        "ready_for_simulation": ("Run the simulation.", "workflow"),
        "simulated": ("Generate the strategic report.", "workflow"),
        "report_ready": ("Generate the executive briefing.", "briefing"),
        "briefing_ready": ("Open the Decision Pack and prepare leadership review.", "decision-pack"),
        "leadership_review": ("Schedule the leadership review meeting.", "decision-pack"),
        "validate": ("De-risk the key assumptions with real validation.", "decision-pack"),
        "revise": ("Revise the concept and re-test.", "scenarios"),
        "go": ("Advance to consumer validation / pilot.", "decision-pack"),
        "hold": ("Hold; revisit only with a materially different concept.", "home"),
        "archived": ("Archived — no further action required.", "home"),
    }
    label, surface = table.get(stage, ("Open the workflow.", "workflow"))
    return {"label": label, "surface": surface}


# Public API ------------------------------------------------------------------


def _to_status_dict(project: Project, *, db: Session) -> dict:
    inferred = infer_stage(db, project.id)
    board_label = _board_label_for(db, project.id)
    stage = project.pipeline_stage or inferred
    source = project.pipeline_stage_source or ("manual" if project.pipeline_stage else "inferred")
    rec = recommended_stage(inferred, board_label)
    return {
        "project_id": project.id,
        "project_name": project.name,
        "pipeline_stage": stage,
        "pipeline_stage_label": STAGE_LABELS.get(stage, stage),
        "pipeline_stage_source": source,
        "pipeline_stage_updated_at": project.pipeline_stage_updated_at.isoformat() if project.pipeline_stage_updated_at else None,
        "pipeline_stage_note": project.pipeline_stage_note,
        "inferred_stage": inferred,
        "decision_board_label": board_label,
        "recommended_stage": rec,
        "next_recommended_action": _next_action(stage),
    }


def get_status(db: Session, project_id: str) -> dict:
    project = project_service.get_project(db, project_id)
    if project is None:
        raise ValueError("project_not_found")
    return _to_status_dict(project, db=db)


def _log_stage_change(
    db: Session,
    project_id: str,
    *,
    entry_type: str,
    from_stage: str | None,
    to_stage: str,
    note: str = "",
    decision_board: bool = False,
) -> None:
    title_prefix = "Decision Board applied" if decision_board else "Pipeline stage changed to"
    title = f"{title_prefix}: {STAGE_LABELS.get(to_stage, to_stage)}"
    body_parts = []
    if from_stage:
        body_parts.append(f"Stage changed from {STAGE_LABELS.get(from_stage, from_stage)} to {STAGE_LABELS.get(to_stage, to_stage)}.")
    else:
        body_parts.append(f"Stage set to {STAGE_LABELS.get(to_stage, to_stage)}.")
    if note:
        body_parts.append(f"Note: {note}")
    tags = ["pipeline", "stage-change" if not decision_board else "decision-board", to_stage]
    decision_service.add_auto_entry(
        db,
        project_id,
        entry_type=entry_type,
        title=title,
        body=" ".join(body_parts),
        tags=tags,
    )


def update_status(
    db: Session,
    project_id: str,
    *,
    pipeline_stage: str,
    note: str | None = None,
    source: str = "manual",
) -> dict:
    if pipeline_stage not in STAGES:
        raise ValueError("invalid_stage")
    if source not in SOURCES:
        raise ValueError("invalid_source")
    project = project_service.get_project(db, project_id)
    if project is None:
        raise ValueError("project_not_found")
    from_stage = project.pipeline_stage
    project.pipeline_stage = pipeline_stage
    project.pipeline_stage_source = source
    project.pipeline_stage_note = note
    project.pipeline_stage_updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(project)
    _log_stage_change(
        db,
        project_id,
        entry_type="change",
        from_stage=from_stage,
        to_stage=pipeline_stage,
        note=note or "",
        decision_board=(source == "decision_board"),
    )
    return _to_status_dict(project, db=db)


def _apply_one(
    db: Session,
    project: Project,
    *,
    only_if_not_manual: bool,
) -> tuple[str, str | None]:
    """Returns (outcome, new_stage_if_changed). Outcome: changed|skipped_manual|skipped_no_board|unchanged."""
    if only_if_not_manual and project.pipeline_stage_source == "manual" and project.pipeline_stage:
        return "skipped_manual", None
    board_label = _board_label_for(db, project.id)
    if not board_label or board_label not in _BOARD_TO_STAGE:
        return "skipped_no_board", None
    new_stage = _BOARD_TO_STAGE[board_label]
    if project.pipeline_stage == new_stage and project.pipeline_stage_source == "decision_board":
        return "unchanged", None
    from_stage = project.pipeline_stage
    project.pipeline_stage = new_stage
    project.pipeline_stage_source = "decision_board"
    project.pipeline_stage_note = f"Applied from Decision Board label '{board_label}'."
    project.pipeline_stage_updated_at = datetime.now(timezone.utc)
    db.flush()
    _log_stage_change(
        db,
        project.id,
        entry_type="decision",
        from_stage=from_stage,
        to_stage=new_stage,
        note=f"Decision Board label: {board_label}.",
        decision_board=True,
    )
    return "changed", new_stage


def apply_decision_board(
    db: Session,
    *,
    project_ids: list[str] | None = None,
    only_if_not_manual: bool = True,
) -> dict:
    projects = project_service.list_projects(db)
    if project_ids:
        wanted = set(project_ids)
        projects = [p for p in projects if p.id in wanted]
    changed = skipped_manual = skipped_no_board = unchanged = 0
    changes: list[dict] = []
    for p in projects:
        outcome, new_stage = _apply_one(db, p, only_if_not_manual=only_if_not_manual)
        if outcome == "changed":
            changed += 1
            changes.append({"project_id": p.id, "project_name": p.name, "new_stage": new_stage})
        elif outcome == "skipped_manual":
            skipped_manual += 1
        elif outcome == "skipped_no_board":
            skipped_no_board += 1
        else:
            unchanged += 1
    db.commit()
    return {
        "changed": changed,
        "skipped_manual": skipped_manual,
        "skipped_no_board": skipped_no_board,
        "unchanged": unchanged,
        "changes": changes,
    }


# Portfolio pipeline view ----------------------------------------------------


def _card_for(db: Session, project: Project, board_items_by_id: dict) -> dict:
    inferred = infer_stage(db, project.id)
    stage = project.pipeline_stage or inferred
    board = board_items_by_id.get(project.id, {})
    return {
        "project_id": project.id,
        "project_name": project.name,
        "pipeline_stage": stage,
        "pipeline_stage_source": project.pipeline_stage_source or ("manual" if project.pipeline_stage else "inferred"),
        "pipeline_stage_updated_at": project.pipeline_stage_updated_at.isoformat() if project.pipeline_stage_updated_at else None,
        "decision_board_label": board.get("decision_label"),
        "overall_score": board.get("overall_score"),
        "risk_score": board.get("risk_score"),
        "owner_team": board.get("owner_team"),
        "top_risk": board.get("top_risk"),
        "next_recommended_action": _next_action(stage),
        "has_decision_pack": bool(board.get("has_decision_pack")),
    }


def _matches(
    card: dict,
    *,
    stage: str | None,
    decision_label: str | None,
    min_score: float | None,
    max_risk: float | None,
    owner_team: str | None,
    search: str | None,
    include_archived: bool,
) -> bool:
    if not include_archived and card["pipeline_stage"] == "archived":
        return False
    if stage and card["pipeline_stage"] != stage:
        return False
    if decision_label and card.get("decision_board_label") != decision_label:
        return False
    if min_score is not None:
        s = card.get("overall_score")
        if s is None or s < min_score:
            return False
    if max_risk is not None:
        r = card.get("risk_score")
        if r is not None and r > max_risk:
            return False
    if owner_team and (card.get("owner_team") or "").lower() != owner_team.lower():
        return False
    if search:
        q = search.lower()
        haystack = " ".join(
            str(v) for v in (
                card.get("project_name"),
                card.get("top_risk"),
                card.get("owner_team"),
                card.get("decision_board_label"),
                card.get("pipeline_stage"),
            ) if v
        ).lower()
        if q not in haystack:
            return False
    return True


def build_board(
    db: Session,
    *,
    stage: str | None = None,
    decision_label: str | None = None,
    min_score: float | None = None,
    max_risk: float | None = None,
    owner_team: str | None = None,
    search: str | None = None,
    include_archived: bool = True,
) -> dict:
    projects = project_service.list_projects(db)
    board = decision_board_service.build_board(db)
    by_id = {it["project_id"]: it for it in board["items"]}

    cards_by_stage: dict[str, list[dict]] = {s: [] for s in STAGES}
    total_matched = 0
    for p in projects:
        card = _card_for(db, p, by_id)
        if not _matches(
            card,
            stage=stage,
            decision_label=decision_label,
            min_score=min_score,
            max_risk=max_risk,
            owner_team=owner_team,
            search=search,
            include_archived=include_archived,
        ):
            continue
        cards_by_stage[card["pipeline_stage"]].append(card)
        total_matched += 1

    columns = [{"stage": s, "label": STAGE_LABELS[s], "items": cards_by_stage[s]} for s in STAGES]

    def _count(stage: str) -> int:
        return len(cards_by_stage.get(stage, []))

    summary = {
        "total_projects": total_matched,
        "total_projects_unfiltered": len(projects),
        "new_count": _count("new_concept"),
        "brief_submitted_count": _count("brief_submitted"),
        "ready_for_simulation_count": _count("ready_for_simulation"),
        "simulated_count": _count("simulated"),
        "report_ready_count": _count("report_ready"),
        "briefing_ready_count": _count("briefing_ready"),
        "leadership_review_count": _count("leadership_review"),
        "validate_count": _count("validate"),
        "revise_count": _count("revise"),
        "go_count": _count("go"),
        "hold_count": _count("hold"),
        "archived_count": _count("archived"),
    }
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "columns": columns,
        "summary": summary,
    }
