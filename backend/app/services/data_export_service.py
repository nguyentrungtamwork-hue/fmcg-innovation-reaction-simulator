"""Local-demo data export / import / delete tooling (Phase 25).

Deterministic, no-secret JSON bundles for backing up, sharing and restoring a
single project on a local SQLite instance. No cloud storage, no auth — this is
local/demo tooling only. Secrets (API keys, env, DATABASE_URL) are never part of
a bundle: only persisted project data is serialised.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import DateTime
from sqlalchemy import inspect as sa_inspect
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import __version__
from app.models import (
    Agent,
    AppLogEntry,
    Brief,
    BriefingArtifact,
    BriefingDoc,
    DecisionLogEntry,
    Event,
    LiveSimulationRun,
    Ontology,
    Project,
    Report,
    ReportSnapshot,
    ScenarioRun,
)

EXPORT_VERSION = "1.0"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_dict(obj: Any) -> dict:
    """Serialise an ORM row to a plain JSON-safe dict (columns only)."""
    out: dict = {}
    for col in sa_inspect(obj).mapper.column_attrs:
        key = col.key
        val = getattr(obj, key)
        if isinstance(val, datetime):
            val = val.isoformat()
        out[key] = val
    return out


def _rows(db: Session, model, project_id: str, order=None) -> list[dict]:
    stmt = select(model).where(model.project_id == project_id)
    if order is not None:
        stmt = stmt.order_by(order)
    return [_row_to_dict(r) for r in db.execute(stmt).scalars().all()]


def _checksum(payload: Any) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    ).hexdigest()


# --- export -----------------------------------------------------------------


def export_project(
    db: Session,
    project_id: str,
    *,
    include_logs: bool = False,
    include_events: bool = True,
    include_artifacts: bool = True,
) -> dict:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("project_not_found")

    data: dict[str, Any] = {
        "project": _row_to_dict(project),
        "brief": (_rows(db, Brief, project_id, Brief.created_at) or [None])[0],
        "ontology": (_rows(db, Ontology, project_id, Ontology.created_at) or [None])[0],
        "agents": _rows(db, Agent, project_id, Agent.id),
        "events": _rows(db, Event, project_id, Event.id) if include_events else [],
        "reports": _rows(db, Report, project_id, Report.created_at),
        "briefings": _rows(db, BriefingDoc, project_id, BriefingDoc.created_at),
        "briefing_artifacts": _rows(db, BriefingArtifact, project_id, BriefingArtifact.created_at)
        if include_artifacts
        else [],
        "scenarios": _rows(db, ScenarioRun, project_id, ScenarioRun.created_at),
        "snapshots": _rows(db, ReportSnapshot, project_id, ReportSnapshot.created_at),
        "decisions": _rows(db, DecisionLogEntry, project_id, DecisionLogEntry.created_at),
        "live_runs": _rows(db, LiveSimulationRun, project_id, LiveSimulationRun.created_at),
    }
    if include_logs:
        data["app_logs"] = [
            _row_to_dict(r)
            for r in db.execute(
                select(AppLogEntry).where(AppLogEntry.project_id == project_id).order_by(AppLogEntry.timestamp)
            ).scalars().all()
        ]

    checksums = {section: _checksum(rows) for section, rows in data.items()}
    checksums["_all"] = _checksum(data)

    limitations = [
        "Exploratory decision-support data only — not a forecast.",
        "Local/demo export: no secrets, API keys, or environment values are included.",
        "Import in create_new mode regenerates all IDs; cross-project references are remapped.",
        "Live-run rows carry timing metadata only; they are informational after import.",
    ]
    if not include_events:
        limitations.append("Events were excluded from this export (include_events=false).")
    if not include_logs:
        limitations.append("App logs were excluded from this export (include_logs=false).")

    return {
        "export_version": EXPORT_VERSION,
        "exported_at": _now_iso(),
        "app_version": __version__,
        "project_id": project_id,
        "data": data,
        "checksums": checksums,
        "limitations": limitations,
    }


# --- import -----------------------------------------------------------------


def _new_id() -> str:
    import uuid

    return str(uuid.uuid4())


def _parse_dt(val):
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except ValueError:
            return None
    return val


def _coerce(model, row: dict) -> dict:
    """Strip pk/project_id and coerce ISO-string datetimes back to datetime objects."""
    body = dict(row)
    body.pop("id", None)
    body.pop("project_id", None)
    dt_cols = {c.key for c in sa_inspect(model).columns if isinstance(c.type, DateTime)}
    for k in list(body.keys()):
        if k in dt_cols:
            body[k] = _parse_dt(body[k])
    return body


def import_project(
    db: Session,
    bundle: dict,
    *,
    mode: str = "create_new",
    new_project_name: str | None = None,
    preserve_original_ids: bool = False,
) -> dict:
    if not isinstance(bundle, dict) or "data" not in bundle or "export_version" not in bundle:
        raise ValueError("invalid_bundle")
    if mode != "create_new":
        # overwrite_existing is intentionally deferred (see DATA_MANAGEMENT.md).
        raise ValueError("import_mode_not_supported")

    data = bundle.get("data") or {}
    proj_src = data.get("project")
    if not isinstance(proj_src, dict):
        raise ValueError("invalid_bundle")

    warnings: list[str] = []
    if preserve_original_ids:
        warnings.append("preserve_original_ids is not supported in create_new mode; new IDs generated.")

    # --- project
    new_pid = _new_id()
    project = Project(
        id=new_pid,
        name=new_project_name or f"{proj_src.get('name', 'Imported Project')} (imported)",
        category=proj_src.get("category"),
        market=proj_src.get("market"),
        status=proj_src.get("status", "created"),
    )
    db.add(project)

    counts: dict[str, int] = {}

    # --- brief (single)
    brief_map: dict[str, str] = {}
    brief = data.get("brief")
    if isinstance(brief, dict):
        bid = _new_id()
        if brief.get("id"):
            brief_map[brief["id"]] = bid
        db.add(Brief(id=bid, project_id=new_pid, raw_text=brief.get("raw_text", ""),
                     structured_json=brief.get("structured_json", "{}"),
                     source_filename=brief.get("source_filename")))
        counts["briefs"] = 1

    # --- ontology (single)
    ont = data.get("ontology")
    if isinstance(ont, dict):
        db.add(Ontology(id=_new_id(), project_id=new_pid,
                        brief_id=brief_map.get(ont.get("brief_id")),
                        data_json=ont.get("data_json", "{}"),
                        confidence_score=ont.get("confidence_score", 0.0),
                        source_mode=ont.get("source_mode", "fallback")))
        counts["ontology"] = 1

    # --- agents (build id map; events reference these)
    agent_map: dict[str, str] = {}
    for a in data.get("agents", []) or []:
        nid = _new_id()
        if a.get("id"):
            agent_map[a["id"]] = nid
        db.add(Agent(id=nid, project_id=new_pid, **_coerce(Agent, a)))
    counts["agents"] = len(agent_map)

    # --- reports (id map for snapshots/decisions)
    report_map: dict[str, str] = {}
    for r in data.get("reports", []) or []:
        nid = _new_id()
        if r.get("id"):
            report_map[r["id"]] = nid
        db.add(Report(id=nid, project_id=new_pid, **_coerce(Report, r)))
    counts["reports"] = len(report_map)

    # --- scenarios (id map for scenario events/decisions)
    scenario_map: dict[str, str] = {}
    for s in data.get("scenarios", []) or []:
        nid = _new_id()
        if s.get("id"):
            scenario_map[s["id"]] = nid
        db.add(ScenarioRun(id=nid, project_id=new_pid, **_coerce(ScenarioRun, s)))
    counts["scenarios"] = len(scenario_map)

    # --- snapshots (id map for decisions; remap source_report_id)
    snapshot_map: dict[str, str] = {}
    for sn in data.get("snapshots", []) or []:
        nid = _new_id()
        if sn.get("id"):
            snapshot_map[sn["id"]] = nid
        body = _coerce(ReportSnapshot, sn)
        if body.get("source_report_id"):
            body["source_report_id"] = report_map.get(body["source_report_id"])
        db.add(ReportSnapshot(id=nid, project_id=new_pid, **body))
    counts["snapshots"] = len(snapshot_map)

    # --- events (remap agent_id + scenario_id)
    ev_count = 0
    for e in data.get("events", []) or []:
        body = _coerce(Event, e)
        old_agent = body.get("agent_id")
        body["agent_id"] = agent_map.get(old_agent, old_agent)
        if old_agent and old_agent not in agent_map:
            warnings.append(f"event referenced unknown agent {old_agent}")
        if body.get("scenario_id"):
            body["scenario_id"] = scenario_map.get(body["scenario_id"])
        db.add(Event(id=_new_id(), project_id=new_pid, **body))
        ev_count += 1
    counts["events"] = ev_count

    # --- briefings + artifacts
    bc = 0
    for b in data.get("briefings", []) or []:
        db.add(BriefingDoc(id=_new_id(), project_id=new_pid, **_coerce(BriefingDoc, b)))
        bc += 1
    counts["briefings"] = bc
    ac = 0
    for art in data.get("briefing_artifacts", []) or []:
        db.add(BriefingArtifact(id=_new_id(), project_id=new_pid, **_coerce(BriefingArtifact, art)))
        ac += 1
    counts["briefing_artifacts"] = ac

    # --- decisions (remap related ids)
    dc = 0
    for d in data.get("decisions", []) or []:
        body = _coerce(DecisionLogEntry, d)
        if body.get("related_snapshot_id"):
            body["related_snapshot_id"] = snapshot_map.get(body["related_snapshot_id"])
        if body.get("related_scenario_id"):
            body["related_scenario_id"] = scenario_map.get(body["related_scenario_id"])
        if body.get("related_report_id"):
            body["related_report_id"] = report_map.get(body["related_report_id"])
        db.add(DecisionLogEntry(id=_new_id(), project_id=new_pid, **body))
        dc += 1
    counts["decisions"] = dc

    # --- live runs (informational metadata)
    lc = 0
    for lr in data.get("live_runs", []) or []:
        db.add(LiveSimulationRun(id=_new_id(), project_id=new_pid, **_coerce(LiveSimulationRun, lr)))
        lc += 1
    counts["live_runs"] = lc

    try:
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise ValueError("import_failed") from exc

    return {"status": "imported", "new_project_id": new_pid, "counts": counts, "warnings": warnings}


# --- delete (cascade) -------------------------------------------------------


def delete_project(db: Session, project_id: str) -> dict:
    project = db.get(Project, project_id)
    if project is None:
        raise ValueError("project_not_found")

    counts: dict[str, int] = {}
    for label, model in (
        ("events", Event),
        ("agents", Agent),
        ("reports", Report),
        ("briefings", BriefingDoc),
        ("briefing_artifacts", BriefingArtifact),
        ("scenarios", ScenarioRun),
        ("snapshots", ReportSnapshot),
        ("decisions", DecisionLogEntry),
        ("live_runs", LiveSimulationRun),
        ("briefs", Brief),
        ("ontology", Ontology),
        ("app_logs", AppLogEntry),
    ):
        rows = db.execute(select(model).where(model.project_id == project_id)).scalars().all()
        for r in rows:
            db.delete(r)
        counts[label] = len(rows)

    db.delete(project)
    db.commit()
    counts["project"] = 1
    return {"status": "deleted", "project_id": project_id, "counts": counts}


# --- reset demo -------------------------------------------------------------


def reset_demo_data(db: Session, *, name_prefix: str = "FreshPlus Demo", all_data: bool = False) -> dict:
    """Delete demo projects (name starts with `name_prefix`), or all projects if all_data."""
    stmt = select(Project)
    if not all_data:
        stmt = stmt.where(Project.name.like(f"{name_prefix}%"))
    projects = db.execute(stmt).scalars().all()
    deleted_ids: list[str] = []
    totals: dict[str, int] = {}
    for p in projects:
        result = delete_project(db, p.id)
        deleted_ids.append(p.id)
        for k, v in result["counts"].items():
            totals[k] = totals.get(k, 0) + v
    return {"status": "reset", "projects_deleted": len(deleted_ids), "counts": totals}
