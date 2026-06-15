"""Deterministic market-actor action logic for the simulation engine.

Each market actor (Retailer, Competitor, Influencer, SocialCommunity,
CategoryExpert) takes exactly one structured action per round. The chosen
action is grounded in the actor's `evaluation_criteria` and the round's
aggregated consumer signal (interest, trial intent, sentiment, dominant
barrier/trigger). All logic is deterministic given the seed + aggregate.
"""
from __future__ import annotations

import random

from app.services.simulation_scoring import ROUND_STAGES, SimContext, clamp


def _tone(sentiment: float) -> str:
    if sentiment >= 0.62:
        return "positive"
    if sentiment >= 0.45:
        return "curious"
    if sentiment >= 0.35:
        return "hesitant"
    return "skeptical"


def market_actor_action(
    profile: dict,
    role: str,
    ctx: SimContext,
    round_no: int,
    aggregate: dict,
    seed: int,
    idx: int,
) -> dict:
    """Return an event dict for one market actor in one round.

    `aggregate` carries the round's consumer signal:
      avg_interest, avg_trial_prob, avg_sentiment, positive_share,
      top_barrier, top_trigger, n.
    """
    rng = random.Random(seed * 7919 + idx * 53 + round_no)
    jitter = rng.uniform(-0.03, 0.03)

    interest = aggregate.get("avg_interest", 0.4)
    trial = aggregate.get("avg_trial_prob", 0.35)
    sentiment = aggregate.get("avg_sentiment", 0.45)
    positive_share = aggregate.get("positive_share", 0.4)
    top_barrier = aggregate.get("top_barrier") or ctx.top_barrier
    top_trigger = aggregate.get("top_trigger") or ctx.top_trigger

    influence = float(profile.get("influence_power", 0.5))
    trust = float(profile.get("trust_level", 0.6))

    action = "observe"
    reasoning = ""
    reaction = ""
    barrier = None
    trigger = None
    impact = clamp(0.0, -1.0, 1.0)  # signed launch impact for this action

    if role == "Retailer":
        if trial >= 0.5 and positive_share >= 0.45:
            action = "expand_shelf_facings"
            trigger = "strong early sell-through signal"
            impact = clamp(0.15 + 0.2 * trial + jitter, -1.0, 1.0)
            reaction = "Sell-through looks promising — I'll give it premium facings."
        elif trial >= 0.35:
            action = "maintain_listing_watch"
            reaction = "Keeping it on shelf but watching rotation closely."
            impact = clamp(0.02 + jitter, -1.0, 1.0)
        else:
            action = "threaten_delist"
            barrier = top_barrier or "weak velocity vs category median"
            impact = clamp(-0.2 - 0.2 * (0.5 - trial) + jitter, -1.0, 1.0)
            reaction = "Rotation is below par — at risk of de-listing within 8 weeks."
    elif role == "Competitor":
        if interest >= 0.45 or trial >= 0.4:
            action = "launch_defensive_promo" if round_no >= 3 else "seed_doubt_content"
            barrier = "competitor pressure on price / credibility"
            impact = clamp(-0.12 - 0.18 * interest + jitter, -1.0, 1.0)
            reaction = (
                "New entrant is gaining attention — countering with a defensive promo."
                if round_no >= 3
                else "Seeding comparison content to question their cooling claim."
            )
        else:
            action = "monitor_entrant"
            impact = clamp(jitter, -1.0, 1.0)
            reaction = "Low traction so far — just monitoring for now."
    elif role == "Influencer":
        believable = ctx.claim_credibility >= 0.55 and not (ctx.taste_risk and round_no >= 5)
        if round_no <= 2:
            action = "preview_teaser" if interest >= 0.4 else "skip_coverage"
            trigger = top_trigger if interest >= 0.4 else None
            impact = clamp((0.1 if interest >= 0.4 else -0.02) + jitter, -1.0, 1.0)
            reaction = (
                "Teasing this to my audience — looks review-worthy."
                if interest >= 0.4
                else "Not compelling enough to cover yet."
            )
        elif believable and sentiment >= 0.5:
            action = "post_positive_review"
            trigger = top_trigger or "acceptable taste + clean pack story"
            impact = clamp(0.12 + 0.25 * influence + jitter, -1.0, 1.0)
            reaction = "Tried it on camera — genuinely liked it, posting a positive review."
        else:
            action = "post_critical_review"
            barrier = top_barrier or ("herbal taste concern" if ctx.taste_risk else "claim doubt")
            impact = clamp(-0.1 - 0.2 * influence + jitter, -1.0, 1.0)
            reaction = "Honest take: the taste/claim didn't land for me."
    elif role == "SocialCommunity":
        if positive_share >= 0.5:
            action = "amplify_positive_wom"
            trigger = top_trigger or "organic recommendations"
            impact = clamp(0.1 + 0.2 * positive_share + jitter, -1.0, 1.0)
            reaction = "Comment section is mostly positive — people sharing use occasions."
        elif positive_share >= 0.3:
            action = "debate_taste_vs_claim"
            barrier = top_barrier or "mixed taste reactions"
            impact = clamp(-0.02 + jitter, -1.0, 1.0)
            reaction = "Split opinions — some love it, some question the claim."
        else:
            action = "amplify_complaints"
            barrier = top_barrier or "recurring taste / price complaints"
            impact = clamp(-0.12 - 0.15 * (0.5 - positive_share) + jitter, -1.0, 1.0)
            reaction = "Complaints are recurring and getting amplified."
    elif role == "CategoryExpert":
        if ctx.claim_clarity >= 0.6 and ctx.differentiation >= 0.6:
            action = "validate_claim"
            trigger = "RTB is solid and differentiated"
            impact = clamp(0.08 + 0.15 * trust + jitter, -1.0, 1.0)
            reaction = "The reason-to-believe holds up against category benchmarks."
        elif ctx.claim_clarity < 0.5:
            action = "flag_claim_clarity_risk"
            barrier = "claim phrasing is vague / hard to substantiate"
            impact = clamp(-0.1 - 0.1 * (0.5 - ctx.claim_clarity) + jitter, -1.0, 1.0)
            reaction = "The cooling claim needs clearer substantiation and disclosure."
        else:
            action = "recommend_claim_rewrite"
            barrier = top_barrier or "claim could be sharper"
            impact = clamp(-0.02 + jitter, -1.0, 1.0)
            reaction = "Differentiation is okay but the claim wording could be sharper."

    impact = round(impact, 3)
    sentiment_score = clamp(0.5 + 0.5 * impact)
    tone = _tone(sentiment_score)
    confidence = clamp(0.55 + 0.3 * influence + 0.1 * trust)

    crit = ", ".join((profile.get("evaluation_criteria") or [])[:3])
    parts = [
        f"Market actor '{role}' at stage '{ROUND_STAGES[round_no]}'.",
        f"Aggregate consumer signal: interest={round(interest, 3)}, "
        f"trial_prob={round(trial, 3)}, positive_share={round(positive_share, 3)}.",
    ]
    if crit:
        parts.append(f"Evaluated against: {crit}.")
    if trigger:
        parts.append(f"Trigger: {trigger}.")
    if barrier:
        parts.append(f"Barrier: {barrier}.")
    parts.append(f"→ chose '{action}' (launch_impact={impact}).")
    reasoning = " ".join(parts)

    return {
        "action_type": action,
        "reasoning": reasoning,
        "generated_reaction": reaction,
        "emotional_tone": tone,
        "sentiment_score": sentiment_score,
        "trust_change": impact,
        "confidence_score": confidence,
        "barrier_detected": barrier,
        "trigger_detected": trigger,
        "scores": {
            "launch_impact": impact,
            "influence_power": round(influence, 3),
            "trust_level": round(trust, 3),
            "aggregate_interest": round(interest, 3),
            "aggregate_trial_prob": round(trial, 3),
            "aggregate_positive_share": round(positive_share, 3),
        },
    }
