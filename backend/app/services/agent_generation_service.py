"""Agent generation orchestrator. LLM-first with deterministic fallback."""
from __future__ import annotations

import json
import logging
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Agent
from app.schemas.agent import (
    NUMERIC_TRAITS,
    AgentGenerateIn,
    AgentSummaryOut,
    ConsumerAgentProfile,
    MarketActorProfile,
)
from app.schemas.ontology import OntologyPayload
from app.services import ontology_service
from app.services.agent_fallback import fallback_generate
from app.services.llm_client import LLMClient

logger = logging.getLogger(__name__)


class AgentGenerationError(RuntimeError):
    pass


# Protected attributes that must never appear in stored agent payloads.
PROTECTED_ATTRIBUTES: tuple[str, ...] = (
    "race",
    "ethnicity",
    "religion",
    "political_affiliation",
    "sexual_orientation",
    "disability",
    "precise_address",
    "home_address",
    "health_diagnosis",
    "criminal_history",
)


def _scrub_protected(profile: dict) -> dict:
    return {k: v for k, v in profile.items() if k.lower() not in PROTECTED_ATTRIBUTES}


def _confidence(profile: ConsumerAgentProfile | MarketActorProfile, mode: str) -> float:
    base = 0.8 if mode == "llm" else 0.55
    grounding = len(getattr(profile, "grounding_sources", []) or [])
    return round(min(1.0, base + 0.02 * grounding), 3)


def _load_ontology(db: Session, project_id: str) -> OntologyPayload:
    ontology = ontology_service.get_ontology(db, project_id)
    if ontology is None:
        raise ValueError("ontology_required")
    return OntologyPayload.model_validate(json.loads(ontology.data_json or "{}"))


def generate_agents(
    db: Session,
    project_id: str,
    params: AgentGenerateIn,
    llm_client: LLMClient | None = None,
) -> dict:
    """Generate consumer + market-actor agents grounded in the project's ontology."""
    ontology = _load_ontology(db, project_id)

    client = llm_client or LLMClient()
    use_llm = client.configured
    mode = "fallback"

    # Deterministic, ontology-grounded, product-aware generation is always the base.
    result = fallback_generate(
        ontology,
        consumer_count=params.consumer_count,
        include_market_actors=params.include_market_actors,
        segment_distribution=params.segment_distribution,
        seed=params.seed,
    )

    # Optional LLM enrichment (Level 1): rewrites persona TEXT only (description, barriers,
    # trust drivers) to sound product-specific. Numeric traits / scoring are never touched.
    # Falls back silently to the deterministic personas if unconfigured or on any error.
    if use_llm:
        if _llm_enrich_consumers(client, ontology, result["consumers"]):
            mode = "llm"

    # Replace existing agents if force_regenerate (default).
    if params.force_regenerate:
        existing = db.execute(select(Agent).where(Agent.project_id == project_id)).scalars().all()
        for a in existing:
            db.delete(a)
        db.flush()

    persisted: list[Agent] = []
    for name, segment, profile in result["consumers"]:
        payload = _scrub_protected(profile.model_dump())
        agent = Agent(
            project_id=project_id,
            agent_type="consumer",
            segment_name=segment,
            role=None,
            name=name,
            profile_json=json.dumps(payload, ensure_ascii=False),
            memory_json=json.dumps(payload.get("initial_memory", []), ensure_ascii=False),
            source_mode=mode,
            confidence_score=_confidence(profile, mode),
        )
        db.add(agent)
        persisted.append(agent)

    for name, role, ma_profile in result["market_actors"]:
        payload = _scrub_protected(ma_profile.model_dump())
        agent = Agent(
            project_id=project_id,
            agent_type="market_actor",
            segment_name=None,
            role=role,
            name=name,
            profile_json=json.dumps(payload, ensure_ascii=False),
            memory_json=json.dumps(payload.get("initial_memory", []), ensure_ascii=False),
            source_mode=mode,
            confidence_score=_confidence(ma_profile, mode),
        )
        db.add(agent)
        persisted.append(agent)

    db.commit()

    distribution = dict(
        Counter(a.segment_name for a in persisted if a.agent_type == "consumer")
    )
    return {
        "total_agents": len(persisted),
        "consumer_agents": sum(1 for a in persisted if a.agent_type == "consumer"),
        "market_actor_agents": sum(1 for a in persisted if a.agent_type == "market_actor"),
        "segment_distribution": distribution,
        "source_mode": mode,
    }


_LLM_PERSONA_SYSTEM = (
    "You are an FMCG consumer-insight assistant. Given a product concept and consumer "
    "segments, rewrite ONLY the persona TEXT so it sounds specific to THIS product. "
    "Do NOT invent numbers, prices, or quantitative traits. Keep each field short. "
    'Return strict JSON: {"segments": {"<segment name>": '
    '{"description": "...", "trial_barriers": ["...","...","..."], '
    '"trust_drivers": ["...","...","..."]}}}.'
)


def _llm_enrich_consumers(client: LLMClient, ontology: OntologyPayload, consumers: list) -> bool:
    """Mutate consumer profiles' TEXT fields using the LLM. Returns True if applied.

    Never raises and never touches numeric traits — on any error the deterministic
    personas are left intact.
    """
    try:
        names = lambda t: [e.name for e in ontology.entities if e.type == t]  # noqa: E731
        product = (names("ProductInnovation") or ["the new product"])[0]
        claims = names("FunctionalClaim") + names("EmotionalClaim")
        segments = sorted({seg for _n, seg, _p in consumers})
        user = json.dumps(
            {
                "product": product,
                "claims": claims[:6],
                "segments": segments,
                "instruction": "For each segment give a one-line description and 3 product-specific trial_barriers and trust_drivers.",
            },
            ensure_ascii=False,
        )
        data = client.chat_json(_LLM_PERSONA_SYSTEM, user, temperature=0.3, max_tokens=2048)
        seg_map = data.get("segments")
        if not isinstance(seg_map, dict):
            return False

        applied = 0
        for _name, segment, profile in consumers:
            info = seg_map.get(segment)
            if not isinstance(info, dict):
                continue
            desc = info.get("description")
            if isinstance(desc, str) and desc.strip():
                profile.segment_description = desc.strip()[:240]
            tb = info.get("trial_barriers")
            if isinstance(tb, list) and tb:
                profile.trial_barriers = [str(x)[:160] for x in tb][:5]
            td = info.get("trust_drivers")
            if isinstance(td, list) and td:
                profile.trust_drivers = [str(x)[:160] for x in td][:5]
            applied += 1
        return applied > 0
    except Exception as e:  # noqa: BLE001 — enrichment must never break generation
        logger.warning("LLM persona enrichment failed; using deterministic personas. error=%s", e)
        return False


# --- queries ----------------------------------------------------------------


def list_agents(
    db: Session,
    project_id: str,
    agent_type: str | None = None,
    segment_name: str | None = None,
    role: str | None = None,
) -> list[Agent]:
    q = db.query(Agent).filter(Agent.project_id == project_id)
    if agent_type:
        q = q.filter(Agent.agent_type == agent_type)
    if segment_name:
        q = q.filter(Agent.segment_name == segment_name)
    if role:
        q = q.filter(Agent.role == role)
    return q.order_by(Agent.agent_type, Agent.segment_name, Agent.name).all()


def get_agent(db: Session, project_id: str, agent_id: str) -> Agent | None:
    return (
        db.query(Agent)
        .filter(Agent.project_id == project_id, Agent.id == agent_id)
        .first()
    )


def summary(db: Session, project_id: str) -> AgentSummaryOut:
    agents = list_agents(db, project_id)
    consumers = [a for a in agents if a.agent_type == "consumer"]
    market = [a for a in agents if a.agent_type == "market_actor"]

    segment_distribution = dict(Counter(a.segment_name for a in consumers))

    # average traits across consumers
    trait_sums = {t: 0.0 for t in NUMERIC_TRAITS}
    trait_counts = {t: 0 for t in NUMERIC_TRAITS}
    barrier_counter: Counter[str] = Counter()
    trust_counter: Counter[str] = Counter()
    channel_counter: Counter[str] = Counter()

    for a in consumers:
        prof = json.loads(a.profile_json or "{}")
        for t in NUMERIC_TRAITS:
            v = prof.get(t)
            if isinstance(v, (int, float)):
                trait_sums[t] += float(v)
                trait_counts[t] += 1
        for b in prof.get("trial_barriers", []) or []:
            barrier_counter[b] += 1
        for d in prof.get("trust_drivers", []) or []:
            trust_counter[d] += 1
        for c in prof.get("channel_preference", []) or []:
            channel_counter[c] += 1

    averages = {
        t: round(trait_sums[t] / trait_counts[t], 3) if trait_counts[t] else 0.0
        for t in NUMERIC_TRAITS
    }

    return AgentSummaryOut(
        total_agents=len(agents),
        consumer_agents=len(consumers),
        market_actor_agents=len(market),
        segment_distribution=segment_distribution,
        average_trait_scores=averages,
        top_trial_barriers=barrier_counter.most_common(5),
        top_trust_drivers=trust_counter.most_common(5),
        top_channel_preferences=channel_counter.most_common(5),
    )
