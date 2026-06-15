# FMCG_SIMULATION_PRINCIPLES.md

## Purpose
Define the consumer-behavior principles that govern how the simulator reasons about FMCG innovation adoption. Every agent action, scoring weight, and report claim must trace back to one of these principles.

## 1. The Adoption Funnel (the spine of the simulation)

We model six stages, each mapped 1:1 to a simulation round:

| Round | Stage | What happens | Key question |
|---|---|---|---|
| 1 | Pre-launch concept exposure | Consumer encounters the concept/teaser. | Is this *relevant* to me? |
| 2 | Launch communication | Consumer sees ads, claims, pack, price. | Do I *understand and believe* it? |
| 3 | Shelf / e-commerce exposure | Consumer sees the product in context. | Is it *available, findable, attractive*? |
| 4 | Trial decision | Buy / wait / compare / reject. | Is it *worth trying*? |
| 5 | Post-trial reaction | Satisfaction, disappointment, confusion. | Did it *meet expectations*? |
| 6 | Social diffusion | Share, review, complain, recommend. | Will I *talk about it and repeat*? |

Adoption is a *funnel with leakage* at every stage. A strong concept can die at shelf; a weak concept can survive on promotion. The report must surface where leakage is largest.

## 2. Core Behavioral Drivers

Every consumer-agent decision is influenced by a weighted combination of:

- **Relevance** to current need-state and usage occasion.
- **Comprehension** — does the claim parse in <3 seconds?
- **Credibility** — is the reason-to-believe (RTB) plausible to this segment?
- **Differentiation** — does it feel different from current repertoire?
- **Price-value perception** — is the price justified by the perceived benefit?
- **Packaging signal** — does the pack telegraph quality/positioning correctly?
- **Channel fit** — is it available where I shop?
- **Promotion pull** — does the offer create urgency or remove risk?
- **Social proof** — is anyone I trust trying it?
- **Risk perception** — sensory risk, health risk, money risk.
- **Habit inertia** — loyalty to current brand.
- **Novelty seeking** — desire to try new things.

These are not independent. Credibility multiplies relevance; price tolerance is conditional on credibility; social proof can override price sensitivity.

## 3. Segment-Conditioned Reactions

Consumer reactions are never universal. The same claim ("less sugar, naturally cooling") will:
- Excite the **Health-Conscious** segment if RTB is clear.
- Confuse the **Value-Seeking Practical** segment if the price premium isn't justified.
- Be ignored by the **Brand-Loyal Conservative** unless their current brand fails them.
- Be over-shared by the **Early Adopter** even before trial.
- Be questioned by the **Skeptical Reviewer-Dependent** until KOLs validate.

The simulator must produce *segment-specific* outputs, not averaged ones. Averages hide the launch-critical minority.

## 4. Barriers vs Triggers

A **trigger** is an attribute that crosses a threshold and *creates* trial intent (e.g., trusted KOL endorsement, free sample, urgent promo, relevant occasion).

A **barrier** is an attribute that *blocks* trial even when triggers exist (e.g., suspect claim, wrong channel, off-putting pack, price too high vs perceived risk).

Triggers and barriers are *not* opposites. A product can have many triggers and one fatal barrier; the report must call this out.

## 5. Claim Dynamics

Claims have three independent properties:
- **Clarity** — does the consumer parse it correctly?
- **Credibility** — does the consumer believe it?
- **Differentiation** — does it stand apart from competitors' claims?

A claim that is clear but not credible breeds skepticism. A claim that is credible but not differentiated breeds shrug. The simulator must score each axis separately.

## 6. Channel and Touchpoint Influence

Different touchpoints serve different funnel stages:
- **TikTok short video** → awareness + curiosity (Round 1–2).
- **Facebook post / KOL review** → comprehension + credibility (Round 2).
- **Supermarket / convenience shelf** → trial conversion (Round 3–4).
- **TikTok Shop / e-commerce** → trial + repeat (Round 3–5).
- **Sampling booth** → risk removal (Round 4).
- **Word-of-mouth / community** → diffusion + repeat (Round 5–6).

A channel imbalance (e.g., heavy TikTok with weak shelf presence) creates a *funnel mismatch*: awareness without conversion.

## 7. Competitor Pressure

Competitors are not static. When a new entrant credibly threatens share, incumbents respond with:
- Price cuts / multi-pack promos.
- Comparative claim content.
- Influencer seeding to dilute novelty.
- Retail visibility push.

The simulator models a lightweight competitor reaction in Round 6.

## 8. Memory and Repeat

Repeat purchase depends on:
- Whether trial expectations were met (Round 5 outcome).
- Whether the product fits the *occasion* repeatedly, not just once.
- Whether there is a habit-forming reason (taste, ritual, social identity).
- Whether the consumer has been re-exposed (re-targeting, in-store visibility).

A high trial rate with low repeat is the classic FMCG failure mode and must be flagged explicitly.

## 9. Risks the Simulator Must Surface
- **Concept-claim mismatch** (innovation sounds different from what it is).
- **Premium without RTB** (price unsupported by perceived benefit).
- **Channel-segment mismatch** (target shops elsewhere).
- **Sensory risk** (taste/texture/smell expected to disappoint).
- **Backlash risk** (claim challenged by community or expert).
- **Trial-without-repeat** (one-and-done).
- **Competitor neutralization** (incumbent matches the benefit cheaper).

## 10. Epistemic Honesty

The simulator produces **decision-support hypotheses**, not forecasts. Every report must:
- State assumptions explicitly.
- Quantify uncertainty (e.g., "estimated trial 22–34% among Segment X, conditional on TikTok reach").
- Recommend human-validation steps (survey, focus group, retail test).
