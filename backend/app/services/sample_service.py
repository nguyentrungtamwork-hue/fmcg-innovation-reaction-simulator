"""Sample-library service (Phase 26).

Reads the fictional FMCG sample concepts in ``samples/library`` and loads a chosen
sample into a brand-new project (brief only, or the full deterministic pipeline).
No LLM required; everything is offline + deterministic. Fictional brands only.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from sqlalchemy.orm import Session

from app.schemas.agent import AgentGenerateIn
from app.schemas.brief import BriefIn
from app.schemas.briefing import BriefingGenerateIn
from app.schemas.project import ProjectCreate
from app.schemas.report import ReportGenerateIn
from app.schemas.simulation import SimulationRunIn
from app.services import (
    agent_generation_service,
    brief_service,
    briefing_service,
    ontology_service,
    project_service,
    report_service,
    simulation_service,
)

_LIBRARY_DIR = Path(__file__).resolve().parents[3] / "samples" / "library"
_INDEX_FILE = _LIBRARY_DIR / "samples_index.json"

_LIST_FIELDS = ("recommended_demo_path",)


@lru_cache(maxsize=1)
def _load_index() -> dict:
    if not _INDEX_FILE.exists():
        return {"version": "0", "samples": []}
    return json.loads(_INDEX_FILE.read_text(encoding="utf-8"))


def _brief_text(sample: dict) -> str:
    fname = sample.get("brief_file")
    if fname:
        path = _LIBRARY_DIR / fname
        if path.exists():
            return path.read_text(encoding="utf-8")
    return sample.get("short_description", "")


def list_samples() -> list[dict]:
    out = []
    for s in _load_index().get("samples", []):
        out.append(
            {
                "sample_id": s["sample_id"],
                "name": s["name"],
                "category": s["category"],
                "short_description": s["short_description"],
                "target_consumer": s.get("target_consumer", ""),
                "key_claim": s.get("key_claim", ""),
                "price_positioning": s.get("price_positioning", ""),
                "channels": s.get("channels", []),
                "known_risks": s.get("known_risks", []),
                "recommended_demo_path": s.get("recommended_demo_path", []),
                "what_to_observe": s.get("what_to_observe", ""),
            }
        )
    return out


def _find(sample_id: str) -> dict | None:
    for s in _load_index().get("samples", []):
        if s["sample_id"] == sample_id:
            return s
    return None


def get_sample(sample_id: str) -> dict:
    s = _find(sample_id)
    if s is None:
        raise ValueError("sample_not_found")
    detail = {
        "sample_id": s["sample_id"],
        "name": s["name"],
        "category": s["category"],
        "short_description": s["short_description"],
        "target_consumer": s.get("target_consumer", ""),
        "key_claim": s.get("key_claim", ""),
        "price_positioning": s.get("price_positioning", ""),
        "channels": s.get("channels", []),
        "known_risks": s.get("known_risks", []),
        "recommended_demo_path": s.get("recommended_demo_path", []),
        "what_to_observe": s.get("what_to_observe", ""),
        "sample_brief_text": _brief_text(s),
        "structured": s.get("structured", {}),
    }
    return detail


def _brief_in(sample: dict) -> BriefIn:
    structured = dict(sample.get("structured", {}))
    structured["raw_text"] = _brief_text(sample)
    return BriefIn(**structured)


def load_sample(db: Session, sample_id: str, *, project_name: str | None = None, run_pipeline: bool = False) -> dict:
    sample = _find(sample_id)
    if sample is None:
        raise ValueError("sample_not_found")

    name = project_name or f"{sample['name']} (sample)"
    structured = sample.get("structured", {})
    project = project_service.create_project(
        db,
        ProjectCreate(name=name, category=structured.get("category"), market=structured.get("launch_market")),
    )
    pid = project.id

    brief_service.submit_brief(db, pid, payload=_brief_in(sample))
    completed = ["project_created", "brief_submitted"]
    warnings: list[str] = []
    next_surface = "workflow"

    if run_pipeline:
        try:
            ontology_service.analyze_brief(db, pid)
            completed.append("ontology")
            agent_generation_service.generate_agents(db, pid, AgentGenerateIn(consumer_count=50, seed=42))
            completed.append("agents")
            simulation_service.run_simulation(db, pid, SimulationRunIn(rounds=6, seed=42, deterministic=True))
            completed.append("simulation")
            report_service.generate_report(db, pid, ReportGenerateIn())
            completed.append("report")
            briefing_service.generate(db, pid, BriefingGenerateIn())
            completed.append("briefing")
            next_surface = "report"
        except Exception as e:  # noqa: BLE001 — partial load still usable
            warnings.append(f"pipeline_incomplete: {e}")

    return {
        "project_id": pid,
        "status": "loaded",
        "completed_steps": completed,
        "next_url": f"/projects/{pid}/{next_surface}",
        "warnings": warnings,
    }
