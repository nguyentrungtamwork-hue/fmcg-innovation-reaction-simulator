"""Deterministic FreshPlus demo seeder (Phase 10).

Creates a complete demo project against the real backend database so a fresh
clone shows data immediately:

    project -> brief -> ontology -> agents -> simulation -> report
              (+ a sample Q&A and a 10% price-reduction scenario)

Offline + deterministic (no external LLM required). Run from the backend dir so
the SQLite file matches the one uvicorn uses:

    cd backend
    python scripts/seed_demo.py            # create a new demo project
    python scripts/seed_demo.py --reset-demo   # delete prior demo projects first

Usage notes are printed at the end (project_id + URLs).
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime

# Allow running as `python scripts/seed_demo.py` from the backend dir.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import delete, select  # noqa: E402

from app.models import Agent, Brief, Event, Ontology, Project, Report, ScenarioRun  # noqa: E402
from app.schemas.agent import AgentGenerateIn  # noqa: E402
from app.schemas.brief import BriefIn  # noqa: E402
from app.schemas.project import ProjectCreate  # noqa: E402
from app.schemas.qa import QuestionIn  # noqa: E402
from app.schemas.report import ReportGenerateIn  # noqa: E402
from app.schemas.scenario import ScenarioOverrides, ScenarioRunIn  # noqa: E402
from app.schemas.simulation import SimulationRunIn  # noqa: E402
from app.services import (  # noqa: E402
    agent_generation_service,
    brief_service,
    ontology_service,
    project_service,
    qa_service,
    report_service,
    scenario_service,
)
from app.services import simulation_service  # noqa: E402
from app.storage.database import SessionLocal, init_db  # noqa: E402

DEMO_PREFIX = "FreshPlus Demo"

DEMO_BRIEF = BriefIn(
    raw_text=(
        "FreshPlus Herbal Cool — a ready-to-drink herbal tea with 50% less sugar. "
        "Refreshes naturally; a calm reset in the afternoon. Premium 450ml frosted PET. "
        "Target: urban office workers 22-35 in Vietnam. Channels: convenience stores, "
        "supermarkets, TikTok Shop. Risks: claim believability, premium price, medicinal taste."
    ),
    brand="FreshPlus",
    product_name="FreshPlus Herbal Cool",
    category="Ready-to-drink tea",
    benefit="Refreshes naturally with less sugar",
    functional_claims=["50% less sugar than leading RTD teas", "Contains chrysanthemum"],
    emotional_claims=["A calm reset"],
    packaging="450ml PET, frosted look",
    price="Slightly premium",
    pack_size="450ml",
    target_consumers="Urban office workers 22-35",
    usage_occasions=["mid-afternoon at work", "after lunch", "commute"],
    channels=["Convenience stores", "Supermarkets", "TikTok Shop"],
    launch_market="Vietnam",
    competitors=["Mainstream bottled teas", "Zero-sugar teas"],
    media_plan="TikTok creators, 2 KOLs",
    sampling_plan="4-week sampling at office CVS",
    promotion_plan="BOGO at convenience chains",
    known_risks=[
        "Consumers may not believe the natural cooling claim",
        "Premium price may suppress trial",
        "Herbal taste may feel medicinal",
    ],
)


def reset_demo(db) -> int:
    """Delete prior demo projects and all their child rows."""
    ids = db.execute(
        select(Project.id).where(Project.name.like(f"{DEMO_PREFIX}%"))
    ).scalars().all()
    if not ids:
        return 0
    for model in (Event, Agent, Report, ScenarioRun, Ontology, Brief):
        db.execute(delete(model).where(model.project_id.in_(ids)))
    db.execute(delete(Project).where(Project.id.in_(ids)))
    db.commit()
    return len(ids)


def seed(db, reset: bool) -> str:
    if reset:
        removed = reset_demo(db)
        print(f"  reset-demo: removed {removed} prior demo project(s)")

    name = f"{DEMO_PREFIX} — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    project = project_service.create_project(db, ProjectCreate(name=name, category="Ready-to-drink tea", market="Vietnam"))
    pid = project.id
    print(f"  project created: {pid}")

    brief_service.submit_brief(db, pid, payload=DEMO_BRIEF)
    print("  brief stored")

    ontology_service.analyze_brief(db, pid)
    print("  ontology extracted")

    agent_generation_service.generate_agents(db, pid, AgentGenerateIn(consumer_count=50, seed=42))
    print("  agents generated")

    sim = simulation_service.run_simulation(db, pid, SimulationRunIn(rounds=6, seed=42, deterministic=True))
    print(f"  simulation complete: {sim['total_events']} events")

    report = report_service.generate_report(db, pid, ReportGenerateIn())
    print(f"  report generated: {report.id} (confidence {report.confidence_score})")

    qa = qa_service.ask(db, pid, QuestionIn(question="Why is repeat purchase low?", include_evidence=True, max_evidence_events=3))
    print(f"  sample Q&A: intent={qa.intent}, {len(qa.answer.supporting_events)} evidence events")

    scenario = scenario_service.run_scenario(
        db,
        pid,
        ScenarioRunIn(
            scenario_name="10% price reduction",
            description="Seeded demo scenario: cut shelf price by 10%.",
            overrides=ScenarioOverrides(price_change_pct=-10),
        ),
    )
    print(f"  scenario created: {scenario.id}")
    return pid


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed a deterministic FreshPlus demo project.")
    parser.add_argument("--reset-demo", action="store_true", help="Delete prior demo projects first.")
    parser.add_argument("--frontend-url", default="http://localhost:5173", help="Frontend URL to print.")
    parser.add_argument("--backend-url", default="http://localhost:8000", help="Backend URL to print.")
    args = parser.parse_args()

    init_db()
    db = SessionLocal()
    try:
        print("Seeding FreshPlus demo...")
        pid = seed(db, reset=args.reset_demo)
    finally:
        db.close()

    print("\n[OK] Demo ready.")
    print(f"   project_id:  {pid}")
    print(f"   open:        {args.frontend_url}/projects/{pid}/workflow")
    print(f"   backend API: {args.backend_url}/api/v1/projects/{pid}")
    print(f"   report:      {args.backend_url}/api/v1/projects/{pid}/report")


if __name__ == "__main__":
    main()
