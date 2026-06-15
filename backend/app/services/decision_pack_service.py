"""Stakeholder Decision Pack aggregator (Phase 28).

Composes a concise, print/PDF-ready decision document from data the app already
produces (report, scorecard, briefing payload, confidence, assumptions,
scenarios, decision history). No LLM, no new scoring, no invented findings —
everything is grounded in existing persisted outputs. No secrets are included.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schemas.briefing import BriefingGenerateIn
from app.services import (
    assumptions_service,
    briefing_service,
    confidence_service,
    decision_service,
    scenario_service,
    scorecard_service,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scenario_summary(db: Session, project_id: str) -> dict:
    runs = scenario_service.list_scenarios(db, project_id)
    items = []
    for r in runs[:6]:
        delta = {}
        try:
            delta = json.loads(r.delta_payload_json or "{}")
        except json.JSONDecodeError:
            delta = {}
        items.append(
            {
                "scenario_name": r.scenario_name,
                "delta_summary": delta.get("delta_summary", ""),
                "conclusion": delta.get("conclusion", ""),
            }
        )
    return {"count": len(runs), "scenarios": items}


def _assumptions_summary(assumptions) -> dict:
    s = assumptions.summary
    high = [a for a in assumptions.assumptions if a.impact == "high"]
    return {
        "high_impact_count": s.high_impact_count,
        "medium_impact_count": s.medium_impact_count,
        "low_impact_count": s.low_impact_count,
        "top_assumptions": [
            {"assumption": a.assumption, "impact": a.impact, "recommended_validation": a.recommended_validation}
            for a in high[:5]
        ],
    }


def _evidence_pack(ep) -> list[dict]:
    out = []
    for label, key in (
        ("Event evidence", "event_evidence"),
        ("Segment evidence", "segment_evidence"),
        ("Scorecard evidence", "scorecard_evidence"),
        ("Assumption evidence", "assumption_evidence"),
        ("Scenario / sensitivity evidence", "scenario_or_sensitivity_evidence"),
        ("Decision-history evidence", "decision_history_evidence"),
    ):
        items = getattr(ep, key, None) or []
        # event_evidence may be structured refs; stringify safely.
        norm = [it if isinstance(it, str) else getattr(it, "excerpt", None) or str(it) for it in items]
        if norm:
            out.append({"category": label, "items": norm})
    return out


def build_pack(db: Session, project_id: str) -> dict:
    # build_payload raises events_required / report_required / scorecard_required.
    bp = briefing_service.build_payload(db, project_id, BriefingGenerateIn())
    h = bp.briefing_header

    sc = scorecard_service.build_for_project(db, project_id, h.project_name)
    confidence = confidence_service.compute(db, project_id)
    assumptions = assumptions_service.build(db, project_id)
    decisions = decision_service.list_entries(db, project_id)

    pack = {
        "project_id": project_id,
        "generated_at": _now_iso(),
        "header": {
            "project_name": h.project_name,
            "concept_name": h.product_or_concept_name,
            "category": bp.situation.category_or_market_context,
            "recommendation_status": h.recommendation_status,
            "overall_score": h.overall_score,
            "confidence_label": h.confidence_label,
        },
        "executive_summary": {
            "recommended_decision": bp.decision_recommendation.recommended_decision,
            "rationale": bp.decision_recommendation.rationale,
            "conditions_before_launch": bp.decision_recommendation.conditions_before_launch,
            "decision_caveats": bp.decision_recommendation.decision_caveats,
            "context": bp.situation.one_paragraph_context,
            "concept_summary": bp.situation.concept_summary,
            "decision_point": bp.situation.current_decision_point,
        },
        "scorecard": sc.model_dump(),
        "confidence": {
            "overall_confidence": confidence.overall_confidence,
            "confidence_label": confidence.confidence_label,
            "confidence_risks": confidence.confidence_risks,
            "how_to_improve_confidence": confidence.how_to_improve_confidence,
        },
        "top_findings": [f.model_dump() for f in bp.top_findings],
        "biggest_risks": [r.model_dump() for r in bp.biggest_risks],
        "next_best_actions": [a.model_dump() for a in bp.next_best_actions],
        "scenario_summary": _scenario_summary(db, project_id),
        "sensitivity_summary": {
            "available": False,
            "note": "Sensitivity sweeps are computed on demand and not persisted in this MVP. Run them on the Sensitivity page.",
        },
        "assumptions_summary": _assumptions_summary(assumptions),
        "evidence_pack": _evidence_pack(bp.evidence_pack),
        "decision_history": [
            {
                "entry_type": d.entry_type,
                "title": d.title,
                "body": d.body,
                "created_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions[:20]
        ],
        "limitations": list(bp.limitations) + [sc.disclaimer],
    }
    return pack


# --- markdown ---------------------------------------------------------------


def render_markdown(pack: dict) -> str:
    h = pack["header"]
    es = pack["executive_summary"]
    sc = pack["scorecard"]
    lines = [
        f"# Decision Pack — {h['project_name']}",
        f"_{h['concept_name']} · {h['category']} · generated {pack['generated_at'][:10]}_",
        "",
        "## Recommendation",
        f"**{str(h['recommendation_status']).replace('_', ' ').title()}** — {es['recommended_decision']}",
        f"Overall score {h['overall_score']}/100 · confidence {h['confidence_label']}.",
        es["rationale"],
        "",
        "## Executive Summary",
        es["context"],
        f"Concept: {es['concept_summary']}",
        f"Decision point: {es['decision_point']}",
        "",
        "## Scorecard",
        f"- Overall: {sc.get('overall_score')}/100 (confidence {sc.get('confidence_label')})",
        f"- Trial potential: {sc.get('trial_potential_score')} · Repeat potential: {sc.get('repeat_potential_score')}",
        f"- Sentiment: {sc.get('sentiment_score')} · Risk: {sc.get('risk_score')}",
        "",
        "## Top Findings",
    ]
    for f in pack["top_findings"]:
        lines.append(f"- **{f.get('finding_title')}** — {f.get('explanation')} ({f.get('supporting_metric')}).")
    lines += ["", "## Biggest Risks"]
    for r in pack["biggest_risks"]:
        lines.append(f"- **{r.get('risk_title')}** ({r.get('severity')}) — {r.get('why_it_matters')} _Mitigation:_ {r.get('mitigation')}")
    lines += ["", "## Next Best Actions"]
    for a in pack["next_best_actions"]:
        lines.append(f"- [{a.get('priority')}] {a.get('action')} — {a.get('owner_team')} ({a.get('expected_impact')})")

    sceno = pack["scenario_summary"]
    lines += ["", "## Scenario Snapshot", f"{sceno['count']} scenario(s) saved."]
    for s in sceno["scenarios"]:
        lines.append(f"- **{s['scenario_name']}** — {s['delta_summary']} {s['conclusion']}")

    asum = pack["assumptions_summary"]
    lines += [
        "",
        "## Assumptions & Limitations",
        f"Assumptions — high: {asum['high_impact_count']}, medium: {asum['medium_impact_count']}, low: {asum['low_impact_count']}.",
    ]
    for a in asum["top_assumptions"]:
        lines.append(f"- ({a['impact']}) {a['assumption']} → validate: {a['recommended_validation']}")
    lines += [f"- {l}" for l in pack["limitations"]]

    if pack["decision_history"]:
        lines += ["", "## Decision History"]
        for d in pack["decision_history"]:
            lines.append(f"- {d['title']} ({d['entry_type']})")

    lines += [
        "",
        "## Evidence Pack",
    ]
    for block in pack["evidence_pack"]:
        lines.append(f"**{block['category']}**")
        lines += [f"- {it}" for it in block["items"][:6]]

    lines += ["", "> Simulation output is exploratory decision support, not a validated market forecast."]
    return "\n".join(lines)
