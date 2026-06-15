import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models import Agent
from app.schemas.agent import AgentGenerateIn, AgentGenerateOut, AgentOut, AgentSummaryOut
from app.services import agent_generation_service, project_service
from app.storage.database import get_db

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["agents"])


def _to_out(a: Agent) -> AgentOut:
    return AgentOut(
        id=a.id,
        project_id=a.project_id,
        agent_type=a.agent_type,  # type: ignore[arg-type]
        name=a.name,
        segment_name=a.segment_name,
        role=a.role,
        source_mode=a.source_mode,
        confidence_score=a.confidence_score,
        profile=json.loads(a.profile_json or "{}"),
        memory=json.loads(a.memory_json or "[]"),
        simulation_memory=json.loads(a.simulation_memory_json or "[]"),
        action_history=json.loads(a.action_history_json or "[]"),
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.post("/generate", response_model=AgentGenerateOut)
def generate(
    project_id: str,
    payload: AgentGenerateIn | None = None,
    db: Session = Depends(get_db),
) -> AgentGenerateOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    params = payload or AgentGenerateIn()
    try:
        result = agent_generation_service.generate_agents(db, project_id, params)
    except ValueError as e:
        raise HTTPException(status_code=409, detail={"code": str(e)}) from e
    return AgentGenerateOut(**result)


@router.get("/summary", response_model=AgentSummaryOut)
def get_summary(project_id: str, db: Session = Depends(get_db)) -> AgentSummaryOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    return agent_generation_service.summary(db, project_id)


@router.get("", response_model=list[AgentOut])
def list_agents(
    project_id: str,
    agent_type: str | None = None,
    segment_name: str | None = None,
    role: str | None = None,
    db: Session = Depends(get_db),
) -> list[AgentOut]:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    agents = agent_generation_service.list_agents(
        db, project_id, agent_type=agent_type, segment_name=segment_name, role=role
    )
    return [_to_out(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(project_id: str, agent_id: str, db: Session = Depends(get_db)) -> AgentOut:
    if project_service.get_project(db, project_id) is None:
        raise HTTPException(status_code=404, detail={"code": "project_not_found"})
    agent = agent_generation_service.get_agent(db, project_id, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail={"code": "agent_not_found"})
    return _to_out(agent)
