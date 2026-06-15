"""Project CRUD service."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Agent, Brief, Event, Ontology, Project, Report
from app.schemas.project import ProjectCreate


def create_project(db: Session, payload: ProjectCreate) -> Project:
    project = Project(name=payload.name, category=payload.category, market=payload.market)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(db: Session, project_id: str) -> Project | None:
    return db.get(Project, project_id)


DEMO_NAME_PREFIX = "FreshPlus Demo"


def list_projects(db: Session, *, demo_only: bool = False) -> list[Project]:
    stmt = select(Project).order_by(Project.created_at.desc())
    if demo_only:
        stmt = stmt.where(Project.name.like(f"{DEMO_NAME_PREFIX}%"))
    return list(db.execute(stmt).scalars())


def envelope_counts(db: Session, project_id: str) -> dict:
    return {
        "has_brief": db.execute(
            select(func.count(Brief.id)).where(Brief.project_id == project_id)
        ).scalar_one() > 0,
        "has_ontology": db.execute(
            select(func.count(Ontology.id)).where(Ontology.project_id == project_id)
        ).scalar_one() > 0,
        "agents_count": db.execute(
            select(func.count(Agent.id)).where(Agent.project_id == project_id)
        ).scalar_one(),
        "events_count": db.execute(
            select(func.count(Event.id)).where(
                Event.project_id == project_id, Event.run_type == "baseline"
            )
        ).scalar_one(),
        "has_report": db.execute(
            select(func.count(Report.id)).where(Report.project_id == project_id)
        ).scalar_one() > 0,
    }


def set_status(db: Session, project: Project, status: str) -> Project:
    project.status = status
    db.commit()
    db.refresh(project)
    return project
