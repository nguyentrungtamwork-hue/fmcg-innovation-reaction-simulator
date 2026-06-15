"""Per-product customization: dynamic segment mix, category-aware reactions, LLM persona enrichment.

These changes are TEXT/COMPOSITION only — the per-agent scoring formulas are unchanged.
"""
from app.schemas.ontology import OntologyEntity, OntologyPayload
from app.services.agent_fallback import ontology_weighted_distribution
from app.services.simulation_scoring import SimContext, build_context, _react


def _onto(product: str, claims: list[str], triggers: list[str], barriers: list[str]) -> OntologyPayload:
    entities = [OntologyEntity(type="ProductInnovation", name=product)]
    entities += [OntologyEntity(type="FunctionalClaim", name=c) for c in claims]
    return OntologyPayload(
        entities=entities,
        purchase_triggers=triggers,
        adoption_barriers=barriers,
    )


SNACK = _onto(
    "CrispRoot Baked Veggie Crisps",
    ["Baked not fried", "40% less fat", "Real vegetables, high fiber"],
    ["Launch-month promotion and sampling at gyms"],
    ["Premium price vs mainstream crisps"],
)
BEVERAGE = _onto(
    "VerdeCalm Herbal Cool RTD Tea",
    ["50% less sugar", "Natural herbal cooling"],
    ["KOL endorsement on TikTok boosts credibility"],
    ["Premium price; medicinal taste risk"],
)


# --- Level 2: product-aware segment distribution ---------------------------


def test_distribution_keeps_invariants():
    dist = ontology_weighted_distribution(SNACK, 50)
    assert sum(dist.values()) == 50
    assert len(dist) == 8
    assert all(v >= 1 for v in dist.values())


def test_distribution_differs_by_product():
    snack = ontology_weighted_distribution(SNACK, 50)
    bev = ontology_weighted_distribution(BEVERAGE, 50)
    # Different products → different consumer mixes
    assert snack != bev


def test_distribution_tilts_toward_health_for_health_claims():
    # snack has fiber/less-fat health signals → more Health/Safety-Conscious than the flat default (7)
    dist = ontology_weighted_distribution(SNACK, 50)
    assert dist["Health/Safety-Conscious Buyer"] >= 7


def test_distribution_deterministic():
    assert ontology_weighted_distribution(SNACK, 50) == ontology_weighted_distribution(SNACK, 50)


# --- Level 3: category-aware reactions -------------------------------------


def test_build_context_infers_category_and_unit():
    snack_ctx = build_context(SNACK)
    bev_ctx = build_context(BEVERAGE)
    assert snack_ctx.category == "snack" and snack_ctx.unit_noun == "pack"
    assert bev_ctx.category == "beverage" and bev_ctx.unit_noun == "bottle"


def test_snack_reaction_does_not_say_bottle():
    ctx = build_context(SNACK)
    r = _react("purchase_trial", ctx, "Value-Seeking Practical Buyer", "trial")
    assert "bottle" not in r.lower()
    assert "pack" in r.lower()


def test_beverage_reaction_uses_bottle():
    ctx = build_context(BEVERAGE)
    r = _react("purchase_trial", ctx, "Value-Seeking Practical Buyer", "trial")
    assert "bottle" in r.lower()


def test_reactions_never_empty_and_deterministic():
    ctx = build_context(SNACK)
    for action in ("like", "save_for_later", "purchase_trial", "recommend", "repeat_purchase_intent", "ignore"):
        a = _react(action, ctx, "Early Adopter / Trend-Seeker", "concept")
        b = _react(action, ctx, "Early Adopter / Trend-Seeker", "concept")
        assert a and a == b  # non-empty + deterministic


def test_general_category_falls_back_to_pack():
    ctx = SimContext()  # defaults
    assert ctx.unit_noun == "pack"
    r = _react("purchase_trial", ctx, "Family Decision Maker", "trial")
    assert r and "pack" in r.lower()


# --- Level 1: LLM persona enrichment (opt-in, graceful) --------------------


class _FakeLLM:
    configured = True

    def chat_json(self, system, user, **kw):
        return {
            "segments": {
                "Value-Seeking Practical Buyer": {
                    "description": "Budget-minded crisp shopper who reads the price-per-gram.",
                    "trial_barriers": ["Doubts baked crisps taste as good as fried"],
                    "trust_drivers": ["Clear price-per-100g", "Visible 'baked' callout"],
                }
            }
        }


def test_llm_enrichment_rewrites_persona_text():
    from app.services.agent_generation_service import _llm_enrich_consumers
    from app.services.agent_fallback import fallback_generate

    result = fallback_generate(SNACK, consumer_count=50, include_market_actors=False, segment_distribution=None, seed=42)
    applied = _llm_enrich_consumers(_FakeLLM(), SNACK, result["consumers"])
    assert applied is True
    target = next(p for _n, seg, p in result["consumers"] if seg == "Value-Seeking Practical Buyer")
    assert "crisp" in target.segment_description.lower()


def test_llm_enrichment_failure_is_graceful():
    from app.services.agent_generation_service import _llm_enrich_consumers
    from app.services.agent_fallback import fallback_generate

    class _Boom:
        configured = True
        def chat_json(self, *a, **k):
            raise RuntimeError("no network")

    result = fallback_generate(SNACK, consumer_count=50, include_market_actors=False, segment_distribution=None, seed=42)
    before = result["consumers"][0][2].segment_description
    applied = _llm_enrich_consumers(_Boom(), SNACK, result["consumers"])
    assert applied is False
    assert result["consumers"][0][2].segment_description == before  # personas intact
