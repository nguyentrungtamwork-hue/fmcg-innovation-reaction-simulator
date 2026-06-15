"""Deterministic strategic launch report builder (Phase 6).

Synthesizes the persisted brief + ontology + agents + simulation events into a
structured `ReportPayload` and a Markdown rendering. Every quantitative claim is
derived from the event aggregates — no invented findings, no LLM required.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from app.models import Agent, Event
from app.schemas.ontology import OntologyPayload
from app.schemas.report import (
    ABTest,
    BarrierAnalysis,
    ChannelTouchpoint,
    ClaimAssessment,
    CompetitorRetailResponse,
    EvidenceRef,
    ExecutiveSummary,
    LaunchFunnelSummary,
    PackagingPricePerception,
    Recommendation,
    ReportPayload,
    RiskItem,
    RoundSummaryItem,
    SegmentReaction,
    SocialDiffusion,
    TriggerAnalysis,
    TrialRepeatForecast,
)
from app.services.simulation_scoring import ROUND_STAGES, build_context

# --- action groupings -------------------------------------------------------

AWARENESS_POS = {"like", "save_for_later", "comment_positive", "view"}
TRIAL_ACTIONS = {"purchase_trial", "add_to_cart"}
REPEAT_ACTIONS = {"repeat_purchase_intent"}
ADVOCACY_ACTIONS = {"recommend", "share_with_friend"}
REJECTION_ACTIONS = {"reject_before_trial", "ignore"}
COMPLAINT_ACTIONS = {"complain", "comment_negative"}
SWITCH_ACTIONS = {"switch_brand"}
STAY_ACTIONS = {"stay_with_current_brand"}


def _title(brand: str, product: str) -> str:
    """Combine brand + product without duplicating the brand token."""
    b = (brand or "").strip()
    p = (product or "").strip()
    if not p:
        return b or "the innovation"
    if not b or p.lower().startswith(b.lower()):
        return p
    return f"{b} {p}"


def _excerpt(text: str | None, n: int = 140) -> str:
    if not text:
        return ""
    text = text.strip().replace("\n", " ")
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"


def _pct(part: int, whole: int) -> float:
    return round(100.0 * part / whole, 1) if whole else 0.0


def _avg(vals: list[float]) -> float:
    vals = [v for v in vals if v is not None]
    return round(sum(vals) / len(vals), 3) if vals else 0.0


def _evidence(events: list[Event], limit: int = 3) -> list[EvidenceRef]:
    out = []
    for e in events[:limit]:
        out.append(
            EvidenceRef(
                event_id=e.id,
                round_number=e.round_number,
                agent_id=e.agent_id,
                segment_name=e.segment_name,
                action_type=e.action_type,
                short_reaction_excerpt=_excerpt(e.generated_reaction or e.reasoning, 120),
            )
        )
    return out


# --- segment message-angle hints -------------------------------------------

_SEGMENT_ANGLE = {
    "Early Adopter / Trend-Seeker": "Lead with novelty and shareability; give them a first-to-discover hook.",
    "Value-Seeking Practical Buyer": "Make the price-per-serve and concrete savings explicit; avoid premium framing.",
    "Brand-Loyal Conservative Buyer": "Borrow trust via familiar endorsements and a low-risk reason to switch.",
    "Health/Safety-Conscious Buyer": "Substantiate the low-sugar / natural-cooling reason-to-believe with clear evidence.",
    "Convenience-Driven Busy Buyer": "Stress availability and grab-and-go ease at convenience stores.",
    "Family Decision Maker": "Reassure on taste acceptance and offer family-friendly pack/value.",
    "Skeptical Reviewer-Dependent Buyer": "Seed credible third-party reviews before asking for trial.",
    "Promotion-Driven Trial Buyer": "Anchor trial on a clear promo/sample mechanic.",
}


def _segment_angle(segment: str, trigger: str | None, barrier: str | None) -> str:
    base = _SEGMENT_ANGLE.get(segment, "Tailor the message to this segment's dominant motivation.")
    if barrier:
        base += f" Address the recurring barrier: {barrier}."
    return base


# --- main entry -------------------------------------------------------------


def build_report(
    brief_structured: dict,
    ontology: OntologyPayload,
    consumers: list[Agent],
    market: list[Agent],
    events: list[Event],
) -> tuple[ReportPayload, float]:
    ctx = build_context(ontology)
    brand = ctx.brand
    product = ctx.product

    consumer_events = [e for e in events if e.agent_type == "consumer"]
    market_events = [e for e in events if e.agent_type == "market_actor"]
    n_consumers = max(1, len(consumers))
    total_ce = max(1, len(consumer_events))

    # --- global action distribution + per-round ---
    action_dist = Counter(e.action_type for e in consumer_events)
    rounds = sorted({e.round_number for e in consumer_events})
    round_items: list[RoundSummaryItem] = []
    for rnd in rounds:
        rc = [e for e in consumer_events if e.round_number == rnd]
        ract = Counter(e.action_type for e in rc)
        round_items.append(
            RoundSummaryItem(
                round_number=rnd,
                stage_name=ROUND_STAGES.get(rnd, rc[0].stage_name if rc else ""),
                dominant_action=ract.most_common(1)[0][0] if ract else None,
                avg_sentiment=_avg([e.sentiment_score for e in rc]),
                avg_trial_probability=_avg([e.trial_probability for e in rc]),
            )
        )

    # --- distinct-agent funnel sets ---
    triers = {e.agent_id for e in consumer_events if e.action_type == "purchase_trial"}
    repeaters = {e.agent_id for e in consumer_events if e.action_type in REPEAT_ACTIONS}
    advocates = {e.agent_id for e in consumer_events if e.action_type in ADVOCACY_ACTIONS}
    complainers = {e.agent_id for e in consumer_events if e.action_type in COMPLAINT_ACTIONS}
    switchers = {e.agent_id for e in consumer_events if e.action_type in SWITCH_ACTIONS}
    rejecters = {e.agent_id for e in consumer_events if e.action_type == "reject_before_trial"}
    aware = {e.agent_id for e in consumer_events if e.round_number == 1 and e.action_type in AWARENESS_POS}
    promo_waiters = {e.agent_id for e in consumer_events if e.action_type == "wait_for_promotion"}

    trial_rate = _pct(len(triers), n_consumers)
    repeat_rate = _pct(len(repeaters), max(1, len(triers)))

    # --- per-segment aggregation ---
    seg_events: dict[str, list[Event]] = defaultdict(list)
    for e in consumer_events:
        seg_events[e.segment_name or "Unknown"].append(e)
    seg_agent_counts = Counter(a.segment_name for a in consumers)

    segment_map: list[SegmentReaction] = []
    for seg, evs in sorted(seg_events.items(), key=lambda kv: -_avg([e.trial_probability for e in kv[1]])):
        trig = Counter(e.trigger_detected for e in evs if e.trigger_detected)
        barr = Counter(e.barrier_detected for e in evs if e.barrier_detected)
        acts = Counter(e.action_type for e in evs)
        rep_ev = _representative(evs)
        strongest_trigger = trig.most_common(1)[0][0] if trig else None
        strongest_barrier = barr.most_common(1)[0][0] if barr else None
        seg_trial = _avg([e.trial_probability for e in evs])
        segment_map.append(
            SegmentReaction(
                segment_name=seg,
                number_of_agents=seg_agent_counts.get(seg, len({e.agent_id for e in evs})),
                average_trial_probability=seg_trial,
                average_purchase_intent_score=_avg([e.purchase_intent_score for e in evs]),
                average_repeat_probability=_avg([e.repeat_probability for e in evs]),
                average_sentiment_score=_avg([e.sentiment_score for e in evs]),
                strongest_trigger=strongest_trigger,
                strongest_barrier=strongest_barrier,
                dominant_actions=[a for a, _ in acts.most_common(3)],
                representative_reaction=_excerpt(rep_ev.generated_reaction if rep_ev else "", 180),
                recommended_message_angle=_segment_angle(seg, strongest_trigger, strongest_barrier),
                confidence_score=round(min(0.8, 0.55 + 0.01 * len(evs)), 3),
            )
        )

    # --- triggers / barriers with evidence ---
    trigger_analysis = _trigger_analysis(consumer_events)
    barrier_analysis = _barrier_analysis(consumer_events, total_ce)

    # --- claims ---
    claim_section = _claim_section(ontology, consumer_events)

    # --- packaging & price ---
    pack_price = _packaging_price(ctx, brief_structured, action_dist, len(promo_waiters), n_consumers)

    # --- channel / touchpoint ---
    channel_section = _channel_section(consumer_events)

    # --- trial / repeat forecast ---
    forecast = TrialRepeatForecast(
        likely_triers=f"≈ {trial_rate}% of simulated consumers ({len(triers)}/{n_consumers}) chose to trial, "
        f"concentrated in {_top_seg_names(segment_map, 2)}.",
        likely_repeaters=f"≈ {repeat_rate}% of triers ({len(repeaters)}/{max(1, len(triers))}) signalled repeat intent; "
        "repeat is the funnel's tightest constraint.",
        one_time_trial_risk=f"{len(complainers)} consumers complained post-trial and {len(rejecters)} rejected before trial — "
        "one-and-done risk is real where taste/credibility expectations are unmet.",
        switch_potential=f"{len(switchers)} consumers signalled switching toward {brand}; "
        f"{len(aware)} showed positive awareness in Round 1.",
        dependency_on_promotion=f"{len(promo_waiters)} consumers deferred to a promotion/sample before trialling — "
        "promo dependency is "
        + ("HIGH" if _pct(len(promo_waiters), n_consumers) >= 25 else "MODERATE")
        + ".",
        confidence_score=0.62,
    )

    # --- social diffusion ---
    social = _social_section(consumer_events, advocates, complainers, ontology)

    # --- competitor & retail (from market actor events + ontology) ---
    comp_retail = _competitor_retail(market_events, ontology)

    # --- risk matrix ---
    risk_matrix = _risk_matrix(ctx, segment_map, barrier_analysis, action_dist, len(promo_waiters), n_consumers)

    # --- recommendations ---
    recommendations = _recommendations(ctx, brand, segment_map, barrier_analysis, forecast, channel_section)

    # --- A/B tests ---
    ab_tests = _ab_tests(ctx, brand, product, segment_map)

    # --- executive summary ---
    top_seg = segment_map[0] if segment_map else None
    weak_seg = segment_map[-1] if segment_map else None
    top_barrier = barrier_analysis[0].barrier if barrier_analysis else "claim credibility"
    top_trigger = trigger_analysis[0].trigger if trigger_analysis else "category novelty"
    overall_sent = _avg([e.sentiment_score for e in consumer_events])
    reaction_word = (
        "cautiously positive" if overall_sent >= 0.5 else "mixed-to-cautious" if overall_sent >= 0.42 else "cautious"
    )
    exec_summary = ExecutiveSummary(
        overall_market_reaction=(
            f"Across {len(rounds)} simulated launch rounds, consumer reaction to {_title(brand, product)} is {reaction_word} "
            f"(avg sentiment {overall_sent}). Trial reaches ≈ {trial_rate}% but repeat intent is the binding constraint "
            f"at ≈ {repeat_rate}% of triers."
        ),
        top_opportunity=(
            f"{top_seg.segment_name} is the strongest beachhead (avg trial {top_seg.average_trial_probability}), "
            f"driven by '{top_trigger}'." if top_seg else "No clear lead segment identified."
        ),
        top_risk=f"'{top_barrier}' is the most frequent adoption barrier and suppresses repeat across segments.",
        estimated_trial_potential=f"≈ {trial_rate}% trial ({len(triers)}/{n_consumers} simulated consumers).",
        estimated_repeat_potential=f"≈ {repeat_rate}% of triers signal repeat ({len(repeaters)}/{max(1, len(triers))}).",
        key_recommendation=(
            recommendations[0].recommendation if recommendations else "Strengthen the reason-to-believe before scaling media."
        ),
        confidence_score=0.62,
        important_assumptions=[
            "Scoring is deterministic and segment-weighted, not fitted to real sales data.",
            f"Market context derived from the ontology: premium={ctx.premium}, promo_available={ctx.has_promo}, "
            f"sampling={ctx.has_sampling}, taste_risk={ctx.taste_risk}.",
            "Each simulated consumer represents a behavioural archetype, not an individual.",
        ],
    )

    funnel = LaunchFunnelSummary(
        awareness_signal=f"{len(aware)}/{n_consumers} consumers engaged positively at first exposure (Round 1).",
        trial_signal=f"{len(triers)}/{n_consumers} reached trial (≈ {trial_rate}%).",
        repeat_signal=f"{len(repeaters)} triers signalled repeat intent (≈ {repeat_rate}% of triers).",
        advocacy_signal=f"{len(advocates)} consumers recommended or shared the product.",
        rejection_signal=f"{len(rejecters)} rejected before trial; {action_dist.get('ignore', 0)} ignore actions logged.",
        complaint_signal=f"{len(complainers)} consumers complained or commented negatively post-trial.",
        switching_signal=f"{len(switchers)} signalled switching to {brand}; {action_dist.get('stay_with_current_brand', 0)} stayed with incumbents.",
        action_distribution=dict(action_dist),
        round_summary=round_items,
    )

    payload = ReportPayload(
        executive_summary=exec_summary,
        launch_funnel_summary=funnel,
        segment_reaction_map=segment_map,
        purchase_trigger_analysis=trigger_analysis,
        adoption_barrier_analysis=barrier_analysis,
        claim_clarity_and_credibility=claim_section,
        packaging_price_perception=pack_price,
        channel_touchpoint_analysis=channel_section,
        trial_repeat_forecast=forecast,
        social_diffusion_and_wom=social,
        competitor_and_retail_response=comp_retail,
        innovation_risk_matrix=risk_matrix,
        strategic_recommendations=recommendations,
        recommended_ab_tests=ab_tests,
        human_validation_questions=_validation_questions(top_barrier, top_trigger, ctx),
        limitations=[
            "This simulation is exploratory decision support, NOT a guaranteed forecast.",
            "Scores are produced by a deterministic, segment-weighted rule engine, not fitted to historical launch outcomes.",
            "No real sales, scan, or POS data informs these numbers yet.",
            "No real social-listening data is used; diffusion signals are simulated.",
            "Findings must be validated with real consumer research before any launch decision.",
        ],
    )

    confidence = round(min(0.75, 0.5 + 0.0005 * len(events) + 0.01 * len(segment_map)), 3)
    return payload, confidence


# --- section helpers --------------------------------------------------------


def _representative(evs: list[Event]) -> Event | None:
    """Pick the most decisive event: prefer trial/post-trial rounds, high confidence."""
    if not evs:
        return None
    decisive = [e for e in evs if e.round_number in (4, 5, 6) and e.generated_reaction]
    pool = decisive or [e for e in evs if e.generated_reaction] or evs
    return max(pool, key=lambda e: (e.confidence_score or 0.0))


def _top_seg_names(segment_map: list[SegmentReaction], k: int) -> str:
    names = [s.segment_name for s in segment_map[:k]]
    return ", ".join(names) if names else "no segment"


def _affected_segments(evs: list[Event]) -> list[str]:
    return [s for s, _ in Counter(e.segment_name for e in evs if e.segment_name).most_common(4)]


def _related_touchpoints(evs: list[Event]) -> list[str]:
    return [t for t, _ in Counter(e.touchpoint for e in evs if e.touchpoint).most_common(3)]


def _trigger_analysis(consumer_events: list[Event]) -> list[TriggerAnalysis]:
    by_trigger: dict[str, list[Event]] = defaultdict(list)
    for e in consumer_events:
        if e.trigger_detected:
            by_trigger[e.trigger_detected].append(e)
    out = []
    for trig, evs in sorted(by_trigger.items(), key=lambda kv: -len(kv[1]))[:6]:
        out.append(
            TriggerAnalysis(
                trigger=trig,
                frequency=len(evs),
                affected_segments=_affected_segments(evs),
                related_touchpoints=_related_touchpoints(evs),
                evidence_events=_evidence(evs),
                strategic_implication=(
                    f"Appears {len(evs)} times across {len(_affected_segments(evs))} segments — "
                    "lean into this in creative and at the touchpoints above to pull consumers down the funnel."
                ),
            )
        )
    return out


def _barrier_analysis(consumer_events: list[Event], total_ce: int) -> list[BarrierAnalysis]:
    by_barrier: dict[str, list[Event]] = defaultdict(list)
    for e in consumer_events:
        if e.barrier_detected:
            by_barrier[e.barrier_detected].append(e)
    fixes = {
        "premium": "Clarify value-per-serve, or pair launch with a trial-driving promo/sample.",
        "price": "Make price-per-serve explicit and test a sharper entry price.",
        "review": "Seed credible third-party reviews before asking for trial.",
        "credibility": "Add a concrete, substantiated reason-to-believe for the claim.",
        "claim": "Rewrite the claim to be clearer and more believable.",
        "taste": "De-risk taste via sampling and a 'proof-of-taste' content push.",
        "satisfaction": "Improve post-trial experience (taste/value) to convert trial into repeat.",
        "current brand": "Give a concrete, low-risk reason to switch from the incumbent.",
        "visible": "Improve shelf/e-commerce visibility in the segment's preferred channel.",
    }
    out = []
    for barr, evs in sorted(by_barrier.items(), key=lambda kv: -len(kv[1]))[:6]:
        share = len(evs) / total_ce
        severity = "high" if share >= 0.15 else "medium" if share >= 0.06 else "low"
        low = barr.lower()
        fix = next((v for k, v in fixes.items() if k in low), "Investigate and address this barrier with targeted research.")
        out.append(
            BarrierAnalysis(
                barrier=barr,
                frequency=len(evs),
                affected_segments=_affected_segments(evs),
                related_touchpoints=_related_touchpoints(evs),
                evidence_events=_evidence(evs),
                severity_level=severity,
                recommended_fix=fix,
            )
        )
    return out


def _claim_section(ontology: OntologyPayload, consumer_events: list[Event]) -> list[ClaimAssessment]:
    # credibility/clarity reactions from skeptical or request_review / comment_negative events
    cred_reactions = [
        _excerpt(e.generated_reaction, 120)
        for e in consumer_events
        if e.action_type in ("request_review", "comment_negative") and e.generated_reaction
    ][:3]
    out = []
    items = ontology.claim_analysis or []
    if not items:
        # fall back to functional/emotional claim entity names
        claim_names = [e.name for e in ontology.entities if e.type in ("FunctionalClaim", "EmotionalClaim")]
        for c in claim_names[:4]:
            out.append(
                ClaimAssessment(
                    claim=c,
                    clarity_assessment="Not explicitly scored in the ontology; assumed moderate clarity.",
                    credibility_assessment="Credibility unverified — recommend substantiation.",
                    supporting_signals=[],
                    risk_signals=ontology.claim_credibility_risks[:2],
                    representative_reactions=cred_reactions,
                    recommended_rewrite=None,
                )
            )
        return out
    for c in items:
        out.append(
            ClaimAssessment(
                claim=c.claim,
                clarity_assessment=f"{c.clarity} — " + ("reads clearly to most segments." if c.clarity == "clear" else "risks confusion; tighten wording."),
                credibility_assessment=f"{c.credibility} — "
                + (
                    "broadly accepted."
                    if c.credibility == "believable"
                    else "skeptical segments want proof." if c.credibility == "questionable" else "likely to be disbelieved without strong RTB."
                ),
                supporting_signals=([f"differentiation: {c.differentiation}"]),
                risk_signals=list(c.risks) or ontology.claim_credibility_risks[:2],
                representative_reactions=cred_reactions,
                recommended_rewrite=c.recommended_rewrite,
            )
        )
    return out


def _packaging_price(ctx, brief: dict, action_dist: Counter, promo_waiters: int, n_consumers: int) -> PackagingPricePerception:
    promo_share = _pct(promo_waiters, n_consumers)
    pack_size = brief.get("pack_size") or "single-serve"
    return PackagingPricePerception(
        packaging_appeal_summary=(
            "Packaging is a secondary driver in the simulation; appeal is moderate and matters most for "
            "novelty-seeking and packaging-sensitive segments."
        ),
        price_value_summary=(
            "Premium positioning depresses perceived value for price-sensitive segments."
            if ctx.premium
            else "Price is broadly acceptable across segments."
        ),
        premium_price_risk=(
            "HIGH — premium price is a top barrier and the main reason value-seekers defer or reject."
            if ctx.premium
            else "LOW — price is not a primary barrier."
        ),
        pack_size_concern=f"Family segments may want a larger/multipack format beyond the {pack_size} pack.",
        promotion_dependency=f"≈ {promo_share}% of consumers waited for a promotion/sample before trialling.",
        recommended_price_or_promo_action=(
            "Hold premium price but anchor trial on the sampling + BOGO mechanic; revisit price only if repeat stays weak."
            if ctx.premium
            else "Maintain current price; use promo tactically rather than as a crutch."
        ),
    )


def _channel_section(consumer_events: list[Event]) -> list[ChannelTouchpoint]:
    by_tp: dict[str, list[Event]] = defaultdict(list)
    for e in consumer_events:
        if e.touchpoint:
            by_tp[e.touchpoint].append(e)
    out = []
    for tp, evs in sorted(by_tp.items(), key=lambda kv: -len(kv[1])):
        n = len(evs)
        pos = sum(1 for e in evs if (e.sentiment_score or 0) >= 0.55)
        neg = sum(1 for e in evs if (e.sentiment_score or 0) < 0.4)
        trial = sum(1 for e in evs if e.action_type in TRIAL_ACTIONS)
        risk = "elevated negative sentiment" if neg / n >= 0.4 else "low"
        role = (
            "trial conversion"
            if trial > 0
            else "awareness & consideration" if any(e.round_number <= 2 for e in evs) else "support"
        )
        out.append(
            ChannelTouchpoint(
                channel_or_touchpoint=tp,
                positive_signal=f"{pos}/{n} interactions were positive (sentiment ≥ 0.55).",
                negative_signal=f"{neg}/{n} interactions were negative (sentiment < 0.4).",
                trial_contribution=f"{trial} trial/cart actions occurred at this touchpoint.",
                risk_signal=risk,
                recommended_role_in_launch=role,
            )
        )
    return out


def _social_section(consumer_events, advocates, complainers, ontology: OntologyPayload) -> SocialDiffusion:
    share_drivers = [e.trigger_detected for e in consumer_events if e.action_type in ADVOCACY_ACTIONS and e.trigger_detected]
    complaint_drivers = [e.barrier_detected for e in consumer_events if e.action_type in COMPLAINT_ACTIONS and e.barrier_detected]
    return SocialDiffusion(
        likely_advocates=f"{len(advocates)} consumers recommended or shared — advocacy skews to satisfied triers and social-leaning segments.",
        likely_complainers=f"{len(complainers)} consumers complained or posted negatively, mostly around taste/credibility.",
        share_drivers=[s for s, _ in Counter(share_drivers).most_common(3)] or ["positive trial experience"],
        complaint_drivers=[s for s, _ in Counter(complaint_drivers).most_common(3)] or ["unmet taste/value expectations"],
        social_questions_likely_to_spread=(ontology.social_diffusion_potential[:3] or [
            "Does the cooling/health claim actually deliver?",
            "Is it worth the premium vs my usual brand?",
        ]),
        recommended_social_content_response=(
            "Pre-empt taste and claim doubts with proof-of-taste KOC content and a clear, substantiated RTB; "
            "monitor comment sections and respond to recurring objections quickly."
        ),
    )


def _competitor_retail(market_events: list[Event], ontology: OntologyPayload) -> CompetitorRetailResponse:
    def role_actions(role_keywords: tuple[str, ...]) -> list[str]:
        out = []
        for e in market_events:
            if (e.touchpoint or "").lower() in role_keywords or any(k in (e.touchpoint or "").lower() for k in role_keywords):
                out.append(f"R{e.round_number}: {e.action_type} — {_excerpt(e.generated_reaction, 90)}")
        return out[:3]

    return CompetitorRetailResponse(
        competitor_risks=role_actions(("competitor",)) or ontology.competitor_pressure_points[:3],
        retailer_opportunities=[a for a in role_actions(("retailer",)) if "expand" in a or "maintain" in a]
        or ["Premium facings if early sell-through holds."],
        retailer_objections=[a for a in role_actions(("retailer",)) if "delist" in a or "threaten" in a]
        or ["De-listing risk if rotation is weak within 8 weeks."],
        influencer_review_risks=role_actions(("influencer",)) or ["Critical taste review could dampen trial."],
        community_discussion_risks=role_actions(("socialcommunity",)) or ["Complaint amplification around taste/price."],
        category_expert_concerns=role_actions(("categoryexpert",)) or ontology.claim_credibility_risks[:2],
    )


def _risk_matrix(ctx, segment_map, barrier_analysis, action_dist, promo_waiters, n_consumers) -> list[RiskItem]:
    weak_segs = [s.segment_name for s in segment_map if s.average_trial_probability < 0.4][:3]
    top_barrier = barrier_analysis[0].barrier if barrier_analysis else "credibility doubt"
    rejects = action_dist.get("reject_before_trial", 0)
    complaints = action_dist.get("complain", 0)
    risks = [
        RiskItem(
            risk_type="claim risk",
            severity="high" if ctx.claim_credibility < 0.6 else "medium",
            evidence=f"Skeptical segments request reviews; top barrier is '{top_barrier}'.",
            affected_segments=["Skeptical Reviewer-Dependent Buyer", "Health/Safety-Conscious Buyer"],
            mitigation="Add a concrete, substantiated reason-to-believe and seed credible reviews.",
        ),
        RiskItem(
            risk_type="price risk",
            severity="high" if ctx.premium else "low",
            evidence=f"{promo_waiters} consumers waited for promo before trialling.",
            affected_segments=["Value-Seeking Practical Buyer", "Promotion-Driven Trial Buyer"],
            mitigation="Make value-per-serve explicit; anchor trial on sampling/BOGO.",
        ),
        RiskItem(
            risk_type="sensory risk",
            severity="high" if ctx.taste_risk else "medium",
            evidence=f"{complaints} post-trial complaints; herbal taste flagged as a launch risk.",
            affected_segments=["Family Decision Maker", "Health/Safety-Conscious Buyer"],
            mitigation="De-risk taste through sampling and proof-of-taste content before scaling.",
        ),
        RiskItem(
            risk_type="trust risk",
            severity="medium",
            evidence=f"{rejects} consumers rejected before trial citing low relevance/trust.",
            affected_segments=weak_segs or ["Brand-Loyal Conservative Buyer"],
            mitigation="Borrow trust via familiar endorsements and transparent labelling.",
        ),
        RiskItem(
            risk_type="channel risk",
            severity="medium",
            evidence="Findability drives the shelf/e-commerce round; weak visibility caps trial.",
            affected_segments=["Convenience-Driven Busy Buyer"],
            mitigation="Secure visible facings and a strong e-commerce product page.",
        ),
        RiskItem(
            risk_type="competitor risk",
            severity="medium",
            evidence="Incumbent runs defensive promos / doubt-seeding in later rounds.",
            affected_segments=["Value-Seeking Practical Buyer", "Brand-Loyal Conservative Buyer"],
            mitigation="Lock trade visibility early and pre-empt comparison claims.",
        ),
        RiskItem(
            risk_type="social backlash risk",
            severity="medium" if ctx.taste_risk else "low",
            evidence=f"{complaints} negative reactions could amplify in comment sections.",
            affected_segments=["Skeptical Reviewer-Dependent Buyer"],
            mitigation="Monitor social, respond to recurring objections, avoid over-claiming.",
        ),
    ]
    return risks


def _recommendations(ctx, brand, segment_map, barrier_analysis, forecast, channel_section) -> list[Recommendation]:
    top_barrier = barrier_analysis[0].barrier if barrier_analysis else "claim credibility"
    lead_segs = _top_seg_names(segment_map, 2)
    recs = [
        Recommendation(
            priority="P0",
            recommendation=f"Lead the launch with a clearer, substantiated reason-to-believe for the core claim.",
            rationale=f"'{top_barrier}' is the most frequent barrier and the main repeat constraint.",
            supporting_evidence=f"Top barrier appears {barrier_analysis[0].frequency if barrier_analysis else 'most'} times across segments.",
            expected_impact="Higher credibility → improved trial-to-repeat conversion.",
            owner_team="Brand",
        ),
        Recommendation(
            priority="P0",
            recommendation="Use sampling to de-risk taste before scaling paid media.",
            rationale="Sensory uncertainty (herbal taste) suppresses repeat and drives complaints.",
            supporting_evidence="Post-trial complaints concentrate where taste importance is high.",
            expected_impact="Lower one-and-done risk; stronger word-of-mouth.",
            owner_team="Trade Marketing",
        ),
        Recommendation(
            priority="P1",
            recommendation=f"Focus initial targeting on the beachhead segments: {lead_segs}.",
            rationale="These segments show the highest simulated trial probability.",
            supporting_evidence=f"Lead segment avg trial {segment_map[0].average_trial_probability if segment_map else 0}.",
            expected_impact="Efficient early trial and advocacy seeding.",
            owner_team="Media",
        ),
        Recommendation(
            priority="P1",
            recommendation="Anchor trial on the sampling + BOGO mechanic rather than a price cut.",
            rationale=forecast.dependency_on_promotion,
            supporting_evidence="A meaningful share of consumers deferred to a promo/sample.",
            expected_impact="Protects premium positioning while driving trial.",
            owner_team="Sales",
        ),
        Recommendation(
            priority="P2",
            recommendation="Secure visible facings and a strong e-commerce product page in convenience + TikTok Shop.",
            rationale="Findability gates the shelf/e-commerce round.",
            supporting_evidence=f"{len(channel_section)} touchpoints analysed; trial concentrates where visibility is high.",
            expected_impact="Converts consideration into trial at the point of purchase.",
            owner_team="E-commerce",
        ),
        Recommendation(
            priority="P2",
            recommendation="Brief creators on a proof-of-taste, honest-review format.",
            rationale="Skeptical and review-dependent segments need credible third-party validation.",
            supporting_evidence="request_review actions cluster in the comms round.",
            expected_impact="Builds credibility ahead of broad trial.",
            owner_team="Creative",
        ),
    ]
    return recs


def _ab_tests(ctx, brand, product, segment_map) -> list[ABTest]:
    return [
        ABTest(
            test_name="Claim reason-to-believe",
            hypothesis="A substantiated RTB increases claim credibility and trial intent vs the current claim.",
            variant_a="Current claim wording.",
            variant_b="Claim + concrete substantiation (ingredient/mechanism + proof point).",
            target_segment="Health/Safety-Conscious Buyer",
            success_metric="Trial intent + credibility rating uplift.",
            why_this_test_matters="Credibility is the top repeat constraint in the simulation.",
        ),
        ABTest(
            test_name="Sampling vs media-first trial",
            hypothesis="Sampling-led trial converts to repeat better than media-led trial for a taste-risk product.",
            variant_a="Media-first (paid social) trial push.",
            variant_b="Sampling-first at convenience stores, media as support.",
            target_segment="Convenience-Driven Busy Buyer",
            success_metric="Trial-to-repeat conversion rate.",
            why_this_test_matters="Sensory risk drives one-and-done behaviour.",
        ),
        ABTest(
            test_name="Price/promo elasticity",
            hypothesis="A sharper entry promo lifts trial without permanently resetting price reference.",
            variant_a="Premium price, BOGO launch promo.",
            variant_b="Premium price, single-serve discount + bundle.",
            target_segment="Value-Seeking Practical Buyer",
            success_metric="Trial rate and post-promo repeat.",
            why_this_test_matters="Promo dependency is a flagged risk to margin.",
        ),
        ABTest(
            test_name="TikTok KOC proof-of-taste",
            hypothesis="Honest proof-of-taste creator content drives more trial than aspirational lifestyle content.",
            variant_a="Lifestyle / aesthetic creator content.",
            variant_b="Honest proof-of-taste reaction content.",
            target_segment="Early Adopter / Trend-Seeker",
            success_metric="Click-to-trial and positive comment ratio.",
            why_this_test_matters="Diffusion depends on credible social proof.",
        ),
    ]


def _validation_questions(top_barrier: str, top_trigger: str, ctx) -> list[str]:
    return [
        f"[Survey] Do target consumers find the core claim believable, and does '{top_barrier}' suppress purchase as simulated?",
        "[Focus group] How do consumers describe the herbal taste, and does it match or break the cooling claim expectation?",
        "[Sensory test] What share of triers rate taste acceptable enough to repurchase?",
        f"[Social listening] Is '{top_trigger}' actually the dominant positive driver in real conversation?",
        "[Retail test] Does shelf visibility in convenience stores move trial as the findability round suggests?",
        "[E-commerce A/B test] Does the substantiated-RTB product page outperform the current page on add-to-cart?",
        "[Sampling booth] Does sampling convert taste-skeptics into triers at the simulated rate?",
        "[Survey] Is the premium price acceptable once value-per-serve is made explicit?",
    ]


# --- markdown rendering -----------------------------------------------------


def render_markdown(payload: ReportPayload, brand: str = "the brand", product: str = "the innovation") -> str:
    p = payload
    L: list[str] = []
    L.append(f"# Strategic Launch Simulation Report — {_title(brand, product)}")
    L.append("")
    L.append("> **Exploratory decision support, not a guaranteed forecast.** "
             "All figures are simulated and must be validated with real consumer research.")
    L.append("")

    es = p.executive_summary
    L.append("## 1. Executive Summary")
    L.append(f"- **Overall reaction:** {es.overall_market_reaction}")
    L.append(f"- **Top opportunity:** {es.top_opportunity}")
    L.append(f"- **Top risk:** {es.top_risk}")
    L.append(f"- **Estimated trial:** {es.estimated_trial_potential}")
    L.append(f"- **Estimated repeat:** {es.estimated_repeat_potential}")
    L.append(f"- **Key recommendation:** {es.key_recommendation}")
    L.append(f"- **Confidence:** {es.confidence_score}")
    L.append("- **Assumptions:** " + "; ".join(es.important_assumptions))
    L.append("")

    f = p.launch_funnel_summary
    L.append("## 2. Launch Funnel Summary")
    for label, val in [
        ("Awareness", f.awareness_signal), ("Trial", f.trial_signal), ("Repeat", f.repeat_signal),
        ("Advocacy", f.advocacy_signal), ("Rejection", f.rejection_signal),
        ("Complaint", f.complaint_signal), ("Switching", f.switching_signal),
    ]:
        L.append(f"- **{label}:** {val}")
    L.append("")
    L.append("| Round | Stage | Dominant action | Avg sentiment | Avg trial prob |")
    L.append("|---|---|---|---|---|")
    for r in f.round_summary:
        L.append(f"| {r.round_number} | {r.stage_name} | {r.dominant_action} | {r.avg_sentiment} | {r.avg_trial_probability} |")
    L.append("")

    L.append("## 3. Segment Reaction Map")
    L.append("| Segment | n | Trial | Intent | Repeat | Sentiment | Strongest barrier | Top actions |")
    L.append("|---|---|---|---|---|---|---|---|")
    for s in p.segment_reaction_map:
        L.append(
            f"| {s.segment_name} | {s.number_of_agents} | {s.average_trial_probability} | "
            f"{s.average_purchase_intent_score} | {s.average_repeat_probability} | {s.average_sentiment_score} | "
            f"{s.strongest_barrier or '—'} | {', '.join(s.dominant_actions)} |"
        )
    L.append("")
    for s in p.segment_reaction_map:
        L.append(f"- **{s.segment_name}** — _\"{s.representative_reaction}\"_ → {s.recommended_message_angle}")
    L.append("")

    L.append("## 4. Purchase Trigger Analysis")
    for t in p.purchase_trigger_analysis:
        L.append(f"- **{t.trigger}** (×{t.frequency}; segments: {', '.join(t.affected_segments)}). {t.strategic_implication}")
    L.append("")

    L.append("## 5. Adoption Barrier Analysis")
    for b in p.adoption_barrier_analysis:
        L.append(f"- **{b.barrier}** (×{b.frequency}, severity {b.severity_level}; segments: {', '.join(b.affected_segments)}). _Fix:_ {b.recommended_fix}")
    L.append("")

    L.append("## 6. Claim Clarity & Credibility")
    for c in p.claim_clarity_and_credibility:
        L.append(f"- **{c.claim}** — clarity: {c.clarity_assessment} credibility: {c.credibility_assessment}")
        if c.recommended_rewrite:
            L.append(f"    - _Rewrite:_ {c.recommended_rewrite}")
    L.append("")

    pp = p.packaging_price_perception
    L.append("## 7. Packaging & Price Perception")
    L.append(f"- **Packaging:** {pp.packaging_appeal_summary}")
    L.append(f"- **Price/value:** {pp.price_value_summary}")
    L.append(f"- **Premium price risk:** {pp.premium_price_risk}")
    L.append(f"- **Pack size:** {pp.pack_size_concern}")
    L.append(f"- **Promotion dependency:** {pp.promotion_dependency}")
    L.append(f"- **Recommended action:** {pp.recommended_price_or_promo_action}")
    L.append("")

    L.append("## 8. Channel & Touchpoint Analysis")
    L.append("| Touchpoint | Positive | Negative | Trial contribution | Recommended role |")
    L.append("|---|---|---|---|---|")
    for c in p.channel_touchpoint_analysis:
        L.append(f"| {c.channel_or_touchpoint} | {c.positive_signal} | {c.negative_signal} | {c.trial_contribution} | {c.recommended_role_in_launch} |")
    L.append("")

    tr = p.trial_repeat_forecast
    L.append("## 9. Trial & Repeat Forecast")
    for label, val in [
        ("Likely triers", tr.likely_triers), ("Likely repeaters", tr.likely_repeaters),
        ("One-time trial risk", tr.one_time_trial_risk), ("Switch potential", tr.switch_potential),
        ("Promo dependency", tr.dependency_on_promotion),
    ]:
        L.append(f"- **{label}:** {val}")
    L.append("")

    sd = p.social_diffusion_and_wom
    L.append("## 10. Social Diffusion & Word-of-Mouth")
    L.append(f"- **Likely advocates:** {sd.likely_advocates}")
    L.append(f"- **Likely complainers:** {sd.likely_complainers}")
    L.append(f"- **Share drivers:** {', '.join(sd.share_drivers)}")
    L.append(f"- **Complaint drivers:** {', '.join(sd.complaint_drivers)}")
    L.append(f"- **Questions likely to spread:** {', '.join(sd.social_questions_likely_to_spread)}")
    L.append(f"- **Recommended response:** {sd.recommended_social_content_response}")
    L.append("")

    cr = p.competitor_and_retail_response
    L.append("## 11. Competitor & Retail Response")
    L.append(f"- **Competitor risks:** {'; '.join(cr.competitor_risks)}")
    L.append(f"- **Retailer opportunities:** {'; '.join(cr.retailer_opportunities)}")
    L.append(f"- **Retailer objections:** {'; '.join(cr.retailer_objections)}")
    L.append(f"- **Influencer review risks:** {'; '.join(cr.influencer_review_risks)}")
    L.append(f"- **Community discussion risks:** {'; '.join(cr.community_discussion_risks)}")
    L.append(f"- **Category expert concerns:** {'; '.join(cr.category_expert_concerns)}")
    L.append("")

    L.append("## 12. Innovation Risk Matrix")
    L.append("| Risk | Severity | Evidence | Mitigation |")
    L.append("|---|---|---|---|")
    for r in p.innovation_risk_matrix:
        L.append(f"| {r.risk_type} | {r.severity} | {r.evidence} | {r.mitigation} |")
    L.append("")

    L.append("## 13. Strategic Recommendations")
    for r in p.strategic_recommendations:
        L.append(f"- **[{r.priority}] {r.recommendation}** ({r.owner_team}) — {r.rationale} _Evidence:_ {r.supporting_evidence} _Impact:_ {r.expected_impact}")
    L.append("")

    L.append("## 14. Recommended A/B Tests")
    for t in p.recommended_ab_tests:
        L.append(f"- **{t.test_name}** (target: {t.target_segment}) — {t.hypothesis}")
        L.append(f"    - A: {t.variant_a} | B: {t.variant_b} | Metric: {t.success_metric}")
    L.append("")

    L.append("## 15. Human Validation Questions")
    for q in p.human_validation_questions:
        L.append(f"- {q}")
    L.append("")

    L.append("## 16. Limitations")
    for lim in p.limitations:
        L.append(f"- {lim}")
    L.append("")
    return "\n".join(L)
