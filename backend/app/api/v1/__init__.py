from fastapi import APIRouter

from app.api.v1 import (
    agents,
    briefing,
    briefs,
    events,
    history,
    insights,
    live_simulation,
    ontology,
    overview,
    portfolio,
    projects,
    qa,
    reports,
    scenarios,
    simulation,
    snapshots,
    studio,
    system,
)

api_router = APIRouter()
api_router.include_router(projects.router)
api_router.include_router(briefs.router)
api_router.include_router(ontology.router)
api_router.include_router(agents.router)
api_router.include_router(simulation.router)
api_router.include_router(events.router)
api_router.include_router(reports.router)
api_router.include_router(qa.router)
api_router.include_router(scenarios.router)
api_router.include_router(system.router)
api_router.include_router(insights.router)
api_router.include_router(snapshots.router)
api_router.include_router(portfolio.router)
api_router.include_router(history.router)
api_router.include_router(briefing.router)
api_router.include_router(studio.router)
api_router.include_router(live_simulation.router)
api_router.include_router(overview.router)
