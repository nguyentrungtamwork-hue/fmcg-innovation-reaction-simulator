"""Portfolio Decision Board roll-up (Phase 29).

Classifies every project into a transparent, deterministic decision bucket
(go / validate / revise / hold / incomplete) by reusing the existing scorecard
and the briefing recommendation-status logic — no new scoring, no LLM, no
invented findings. Incomplete projects (no report/scorecard) are included but
excluded from rankings. No secrets are exposed.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Brief, Event, Ontology, Project
from app.services import briefing_service, project_service, report_service, scorecard_service

# Map the existing recommendation status onto the board's decision labels.
_STATUS_TO_LABEL = {
    "move_forward": "go",
    "validate_before_move_forward": "validate",
    "revise_and_retest": "revise",
    "hold": "hold",
}

_LABELS = ("go", "validate", "revise", "hold", "incomplete")

_NEXT_STEP = {
    "go": "Advance to consumer validation / pilot.",
    "validate": "Validate the key risks before moving forward.",
    "revise": "Revise the concept and re-test before progressing.",
    "hold": "Hold; revisit only with a materially different concept.",
    "incomplete": "Complete the simulation workflow to generate a recommendation.",
}


def _owner_team(top_risk: str | None) -> str:
    t = (top_risk or "").lower()
    if any(k in t for k in ("claim", "credib", "believ", "regulat")):
        return "Marketing & Regulatory"
    if any(k in t for k in ("price", "value", "cost")):
        return "Commercial"
    if any(k in t for k in ("repeat", "sensory", "taste", "texture", "formula")):
        return "R&D / Product"
    if any(k in t for k in ("channel", "retail", "distribution")):
        return "Sales & Channel"
    return "Consumer Insights"


def _risk_level(risk_score: float) -> str:
    if risk_score >= 65:
        return "high"
    if risk_score >= 45:
        return "medium"
    return "low"


def _incomplete_reason(db: Session, project_id: str) -> tuple[str, str]:
    """Return (reason, recommended_next_step) describing the missing pipeline stage."""
    has_brief = db.execute(select(func.count(Brief.id)).where(Brief.project_id == project_id)).scalar_one() > 0
    if not has_brief:
        return "No brief submitted yet.", "Submit an innovation brief (Workflow step 2)."
    has_ont = db.execute(select(func.count(Ontology.id)).where(Ontology.project_id == project_id)).scalar_one() > 0
    if not has_ont:
        return "Brief present but ontology not extracted.", "Analyze the brief (Workflow step 3)."
    has_agents = db.execute(select(func.count(Agent.id)).where(Agent.project_id == project_id)).scalar_one() > 0
    if not has_agents:
        return "Ontology present but no agents generated.", "Generate agents (Workflow step 4)."
    has_sim = db.execute(
        select(func.count(Event.id)).where(Event.project_id == project_id, Event.run_type == "baseline")
    ).scalar_one() > 0
    if not has_sim:
        return "Agents present but simulation not run.", "Run the simulation (Workflow step 5)."
    return "Simulation present but no report generated.", "Generate the strategic report (Workflow step 6)."


def _decision_reason(label: str, sc) -> str:
    o = round(sc.overall_score)
    risk = round(sc.risk_score)
    if label == "go":
        return f"Overall {o}/100 with {sc.confidence_label} confidence, manageable risk ({risk}) and acceptable repeat potential."
    if label == "validate":
        return f"Promising (overall {o}/100) but {sc.confidence_label} confidence — validate key risks/assumptions before moving forward."
    if label == "revise":
        return f"Clear opportunity offset by weak repeat/claim/price-value or high risk ({risk}); revise and re-test."
    if label == "hold":
        return f"Low overall ({o}/100) and/or high risk ({risk}) with no strong opportunity; hold for now."
    return "No report/scorecard yet — recommendation cannot be computed."


def _build_item(db: Session, project: Project) -> tuple[dict, object | None]:
    has_report = report_service.get_report_row(db, project.id) is not None
    base = {
        "project_id": project.id,
        "project_name": project.name,
        "decision_label": "incomplete",
        "overall_score": None,
        "confidence_score": None,
        "confidence_label": None,
        "trial_potential_score": None,
        "repeat_potential_score": None,
        "risk_score": None,
        "risk_level": None,
        "top_opportunity": None,
        "top_risk": None,
        "recommended_next_step": _NEXT_STEP["incomplete"],
        "owner_team": "Consumer Insights",
        "decision_reason": "",
        "has_decision_pack": False,
        "decision_pack_url": None,
    }
    if not has_report:
        reason, next_step = _incomplete_reason(db, project.id)
        base["decision_reason"] = reason
        base["recommended_next_step"] = next_step
        return base, None
    try:
        sc = scorecard_service.build_for_project(db, project.id, project.name)
    except ValueError:
        reason, next_step = _incomplete_reason(db, project.id)
        base["decision_reason"] = reason
        base["recommended_next_step"] = next_step
        return base, None

    status = briefing_service.decide_recommendation_status(sc)
    label = _STATUS_TO_LABEL.get(status, "validate")
    base.update(
        {
            "decision_label": label,
            "overall_score": sc.overall_score,
            "confidence_score": sc.confidence_score,
            "confidence_label": sc.confidence_label,
            "trial_potential_score": sc.trial_potential_score,
            "repeat_potential_score": sc.repeat_potential_score,
            "risk_score": sc.risk_score,
            "risk_level": _risk_level(sc.risk_score),
            "top_opportunity": sc.top_opportunity,
            "top_risk": sc.top_risk,
            "recommended_next_step": _NEXT_STEP[label],
            "owner_team": _owner_team(sc.top_risk),
            "decision_reason": _decision_reason(label, sc),
            "has_decision_pack": True,
            "decision_pack_url": f"/projects/{project.id}/decision-pack",
        }
    )
    return base, sc


def build_board(db: Session, *, project_ids: list[str] | None = None) -> dict:
    projects = project_service.list_projects(db)
    if project_ids:
        wanted = set(project_ids)
        projects = [p for p in projects if p.id in wanted]

    items: list[dict] = []
    cards: dict[str, object] = {}
    for p in projects:
        item, sc = _build_item(db, p)
        items.append(item)
        if sc is not None:
            cards[p.id] = sc

    counts = {f"{lbl}_count": sum(1 for it in items if it["decision_label"] == lbl) for lbl in _LABELS}

    def _best_name(attr: str, *, maximize: bool) -> str | None:
        if not cards:
            return None
        chosen = (max if maximize else min)(cards.values(), key=lambda c: getattr(c, attr))
        return chosen.project_name

    def _ranking(attr: str, *, maximize: bool) -> list[dict]:
        ranked = sorted(cards.values(), key=lambda c: getattr(c, attr), reverse=maximize)
        return [{"project_name": c.project_name, "value": round(getattr(c, attr), 2)} for c in ranked[:5]]

    summary = {
        "total_projects": len(items),
        **counts,
        "report_ready_projects": len(cards),
        "top_project": _best_name("overall_score", maximize=True),
        "highest_risk_project": _best_name("risk_score", maximize=True),
        "most_ready_project": _best_name("overall_score", maximize=True),
        "most_needs_validation_project": _best_name("confidence_score", maximize=False),
    }

    rankings = {
        "best_overall": _ranking("overall_score", maximize=True),
        "best_trial": _ranking("trial_potential_score", maximize=True),
        "best_repeat": _ranking("repeat_potential_score", maximize=True),
        "lowest_risk": _ranking("risk_score", maximize=False),
        "highest_confidence": _ranking("confidence_score", maximize=True),
    }

    go = counts["go_count"]
    validate = counts["validate_count"]
    if not cards:
        portfolio_recommendation = "No report-ready concepts yet. Complete the workflow on at least one project to populate the board."
    elif go:
        portfolio_recommendation = (
            f"{go} concept(s) are ready to advance and {validate} need validation first. "
            f"Prioritise leadership review of '{summary['top_project']}'."
        )
    else:
        portfolio_recommendation = (
            f"No concept is clearly ready to advance; {validate} need validation and "
            f"{counts['revise_count']} need revision. Focus on de-risking before committing budget."
        )

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "items": items,
        "rankings": rankings,
        "portfolio_recommendation": portfolio_recommendation,
        "limitations": [
            "Heuristic decision-support — not a validated market forecast.",
            "Decision labels derive from simulated outputs, not real sales/scan/social data.",
            "Incomplete projects appear on the board but are excluded from rankings.",
            "Real consumer validation (surveys, sensory, in-market tests) is still required before launch.",
        ],
    }


# --- markdown ---------------------------------------------------------------


def render_markdown(board: dict) -> str:
    s = board["summary"]
    lines = [
        "# Portfolio Decision Board",
        f"_Generated {board['generated_at'][:10]} · {s['total_projects']} project(s)_",
        "",
        "## Summary",
        f"- Go: {s['go_count']} · Validate: {s['validate_count']} · Revise: {s['revise_count']} · Hold: {s['hold_count']} · Incomplete: {s['incomplete_count']}",
        f"- Top concept: {s['top_project'] or '—'} · Highest risk: {s['highest_risk_project'] or '—'}",
        "",
        f"**Portfolio recommendation:** {board['portfolio_recommendation']}",
        "",
        "## Decision Board",
        "| Project | Decision | Overall | Conf | Trial | Repeat | Risk | Next step | Owner |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for it in board["items"]:
        def _n(v):
            return "—" if v is None else (round(v) if isinstance(v, (int, float)) else v)
        lines.append(
            f"| {it['project_name']} | {it['decision_label']} | {_n(it['overall_score'])} | "
            f"{it['confidence_label'] or '—'} | {_n(it['trial_potential_score'])} | {_n(it['repeat_potential_score'])} | "
            f"{_n(it['risk_score'])} | {it['recommended_next_step']} | {it['owner_team']} |"
        )

    lines += ["", "## Rankings"]
    for key, label in (
        ("best_overall", "Best overall"),
        ("best_trial", "Best trial"),
        ("best_repeat", "Best repeat"),
        ("lowest_risk", "Lowest risk"),
        ("highest_confidence", "Highest confidence"),
    ):
        names = ", ".join(f"{r['project_name']} ({r['value']})" for r in board["rankings"][key]) or "—"
        lines.append(f"- **{label}:** {names}")

    lines += ["", "## Limitations"]
    lines += [f"- {l}" for l in board["limitations"]]
    lines += ["", "> Portfolio decisions are heuristic decision-support outputs, not validated market forecasts."]
    return "\n".join(lines)
