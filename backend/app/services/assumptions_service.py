"""Assumptions ledger (Phase 11).

Consolidates everything the simulation is implicitly assuming — ontology gaps,
market assumptions, modelling-method caveats, missing real-world data, simulated
personas, and report limitations — into one auditable, exportable list.
"""
from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.models import Ontology
from app.schemas.insight import AssumptionItem, AssumptionsOut, AssumptionsSummary
from app.schemas.ontology import OntologyPayload
from app.services import ontology_service, report_service

# Static method/data caveats that always apply to this MVP.
_STATIC: list[AssumptionItem] = [
    AssumptionItem(
        category="model",
        assumption="Reactions come from a deterministic, segment-weighted rule engine, not fitted to historical launch outcomes.",
        source="simulation_engine",
        impact="high",
        recommended_validation="Calibrate against past launches or a holdout panel before relying on absolute numbers.",
    ),
    AssumptionItem(
        category="data",
        assumption="No real sales / scan / POS data informs the simulation.",
        source="system",
        impact="high",
        recommended_validation="Backtest against real category sell-through where available.",
    ),
    AssumptionItem(
        category="data",
        assumption="No real social-listening data informs diffusion or WOM signals.",
        source="system",
        impact="medium",
        recommended_validation="Cross-check predicted advocacy/complaints with real social listening.",
    ),
    AssumptionItem(
        category="persona",
        assumption="Consumer agents are modelled archetypes; 'interviews' are simulated personas, not real people.",
        source="agent_generation",
        impact="medium",
        recommended_validation="Run qualitative interviews / concept tests with real consumers in each segment.",
    ),
    AssumptionItem(
        category="scenario",
        assumption="Scenario and sensitivity levers are additive nudges, not calibrated demand elasticities.",
        source="scenario_engine",
        impact="medium",
        recommended_validation="Run in-market A/B tests for price, sampling, and claim levers.",
    ),
]


def build(db: Session, project_id: str) -> AssumptionsOut:
    ont_row: Ontology | None = ontology_service.get_ontology(db, project_id)
    if ont_row is None:
        raise ValueError("ontology_required")
    payload = OntologyPayload.model_validate(json.loads(ont_row.data_json or "{}"))

    items: list[AssumptionItem] = list(_STATIC)

    for gap in payload.missing_information:
        items.append(
            AssumptionItem(
                category="ontology",
                assumption=f"Missing/assumed: {gap}",
                source="ontology.missing_information",
                impact="high",
                recommended_validation="Resolve this gap in the brief and re-run analyze.",
            )
        )
    for ma in payload.market_assumptions:
        items.append(
            AssumptionItem(
                category="ontology",
                assumption=ma,
                source="ontology.market_assumptions",
                impact="medium",
                recommended_validation="Confirm this market assumption with category/retail data.",
            )
        )

    report = report_service.get_report_row(db, project_id)
    if report is not None:
        try:
            limitations = report_service.get_payload(report).limitations
        except Exception:  # noqa: BLE001
            limitations = []
        for lim in limitations:
            items.append(
                AssumptionItem(
                    category="report",
                    assumption=lim,
                    source="report.limitations",
                    impact="low",
                    recommended_validation="Note as a caveat when presenting the report.",
                )
            )

    summary = AssumptionsSummary(
        high_impact_count=sum(1 for i in items if i.impact == "high"),
        medium_impact_count=sum(1 for i in items if i.impact == "medium"),
        low_impact_count=sum(1 for i in items if i.impact == "low"),
    )
    return AssumptionsOut(project_id=project_id, assumptions=items, summary=summary)
