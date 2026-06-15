# SCORING_LOGIC.md

## Purpose
Document how a consumer agent decides what to do in each round. The goal is *transparent*, *grounded*, *non-random* reasoning. Every event in the log must be reproducible from agent profile + brief + round context + memory.

## Decision Pipeline (per agent, per round)

```
1. Retrieve context
   - agent profile
   - prior memory entries for this agent
   - round stage definition
   - touchpoint seen this round
   - product brief slice relevant to the touchpoint
   - market signals so far (aggregated from prior events)

2. Compute perception scores  (LLM-assisted, structured output)
   - relevance_score          [0..1]
   - clarity_score            [0..1]
   - credibility_score        [0..1]
   - differentiation_score    [0..1]
   - price_value_score        [0..1]
   - pack_appeal_score        [0..1]
   - channel_fit_score        [0..1]
   - social_proof_score       [0..1]
   - risk_score               [0..1]   (higher = more perceived risk)

3. Apply agent-weight modifiers
   Each agent has trait weights (e.g., novelty_seeking_level, claim_skepticism_level,
   price_sensitivity). These bias the raw perception scores:

     adjusted_credibility = credibility_score * (1 - 0.5 * claim_skepticism_level)
     adjusted_price_value = price_value_score * (1 - 0.6 * price_sensitivity)
     adjusted_relevance   = relevance_score   * (occasion_match ? 1.2 : 0.8)

4. Combine into stage-specific composites
   The funnel stage decides which composite drives the action:

   Round 1 (concept):       interest = adjusted_relevance * clarity
   Round 2 (comms):         intent_signal = interest * adjusted_credibility * differentiation
   Round 3 (shelf):         findability = channel_fit * pack_appeal
   Round 4 (trial):         trial_prob =
                              w1*intent_signal + w2*findability + w3*social_proof
                              - w4*risk - w5*price_sensitivity_gap
   Round 5 (post-trial):    satisfaction = expectation_match - sensory_gap
                            repeat_prob = satisfaction * occasion_repeatability
   Round 6 (diffusion):     share_prob   = satisfaction * social_influence_sensitivity
                            complain_prob = (1 - satisfaction) * voice_propensity

   Weights w1..w5 are segment-conditioned (see weight tables below).

5. Choose action (deterministic given scores + thresholds)
   - Each stage has a small allowed action set (see §Action Sets).
   - The action is chosen by thresholding the composite scores.
   - The LLM is asked to generate (a) reasoning text, (b) generated_comment_if_any,
     (c) key_trigger, (d) key_barrier — all grounded in the score story.

6. Log event and update memory
   - Write event row.
   - Append a short memory note to the agent: what they saw, what they felt, what they decided.
   - Update shared market signal aggregates (sentiment, top objections).
```

## Segment Weight Tables (defaults)

| Segment | w_intent | w_findability | w_social | w_risk | w_price |
|---|---|---|---|---|---|
| Early Adopter | 0.30 | 0.15 | 0.25 | 0.10 | 0.10 |
| Value-Seeking Practical | 0.20 | 0.20 | 0.10 | 0.15 | 0.35 |
| Brand-Loyal Conservative | 0.20 | 0.15 | 0.10 | 0.30 | 0.15 |
| Health-Conscious | 0.30 | 0.10 | 0.15 | 0.25 | 0.10 |
| Convenience-Driven | 0.20 | 0.30 | 0.15 | 0.10 | 0.15 |

(MVP ships these 5; additional 3 segments from the long spec use interpolated weights.)

## Action Sets (per stage)

- **Round 1**: `view`, `ignore`, `like`, `save_for_later`, `comment_positive`, `comment_negative`.
- **Round 2**: + `compare_with_current_brand`, `ask_price`, `request_review`.
- **Round 3**: + `ask_where_to_buy`, `wait_for_promotion`.
- **Round 4**: `add_to_cart`, `purchase_trial`, `reject_before_trial`, `wait_for_promotion`, `compare_with_current_brand`.
- **Round 5**: `try_product` then one of `repeat_purchase_intent`, `no_repeat_intent`, `complain`, `recommend`.
- **Round 6**: `share_with_friend`, `recommend`, `complain`, `switch_brand`, `stay_with_current_brand`.

## Thresholds (defaults; configurable)
- `trial_prob ≥ 0.55` → `purchase_trial`
- `0.35 ≤ trial_prob < 0.55` → `wait_for_promotion` or `compare_with_current_brand`
- `trial_prob < 0.35` → `reject_before_trial`
- `repeat_prob ≥ 0.5` → `repeat_purchase_intent`
- `share_prob ≥ 0.5` → `share_with_friend` or `recommend`
- `complain_prob ≥ 0.5` → `complain`

## Why this is not "random LLM"
- Scores are produced via structured outputs (JSON schema), not free text.
- Action choice is rule-based on the scores; the LLM only generates *justification text* after the action is fixed.
- Same agent + same context + same seed → same scores (modulo LLM nondeterminism, which we control with `temperature=0.2` and a deterministic seed where supported).
- Every event row carries the raw scores → reports can be re-derived without re-running the LLM.

## Calibration Hooks (post-MVP)
- Allow user to upload past launch outcomes; fit segment weights via simple regression.
- Surface calibration confidence in the report.

---

## Phase 5 — As-Implemented Formulas (`services/simulation_scoring.py`)

The deterministic fallback engine that ships in Phase 5. All scores are clamped to
`[0,1]` (rounded to 3 dp) unless noted. A tiny seeded jitter `±0.04`
(`rng = Random(seed*1009 + agent_idx*31 + round_no)`) breaks ties without
destabilizing aggregate counts. All **8** segments ship with explicit weights
(no interpolation), see `SEGMENT_WEIGHTS`.

**Market context** (`build_context`) derives from the ontology: `premium`,
`has_promo`, `has_sampling`, `health_flag`, `taste_risk`, channel list,
`claim_clarity` / `claim_credibility` / `differentiation` (from `claim_analysis`),
and `risk_intensity = clamp(0.2 + 0.08·#risk_signals + 0.05·#barriers)`.

**Perception scores** (per agent per round):
```
relevance    = 0.35 + 0.25·novelty + (0.20·health if health_flag) - 0.12·loyalty + (0.10 if triggers) + jitter
clarity      = claim_clarity - 0.12·skepticism + jitter
credibility  = claim_credibility·(1 - 0.5·skepticism) + jitter
price_value  = (premium ? 0.75 - 0.55·price_sens : 0.85 - 0.25·price_sens) + (promo bonus) + jitter
channel_fit  = 0.35 + 0.45·channel_match + 0.15·convenience + jitter
pack_appeal  = 0.5 + 0.3·packaging_sensitivity + jitter
awareness    = 0.3 + 0.35·social_sens + 0.2·novelty + 0.15·channel_match + jitter
risk         = risk_intensity·(0.6 + 0.4·skepticism) + (0.1·price_sens if premium)
social_proof = SOCIAL_PROOF_BY_ROUND[r]·(0.5 + 0.5·social_sens)   # round baselines 0.10→0.70
```

**Composites** (additive blends — chosen over pure products to keep signal spread):
```
interest      = 0.2 + 0.5·relevance + 0.3·clarity
intent_signal = 0.5·interest + 0.3·credibility + 0.2·differentiation
findability   = channel_fit·(0.6 + 0.4·pack_appeal)
```

**Trial probability** (segment-weighted):
```
pos      = w_intent·intent_signal + w_find·findability + w_social·social_proof
pos_norm = pos / (w_intent + w_find + w_social)
penalty  = (w_risk·risk + w_price·(1 - price_value)) / (w_risk + w_price)
trial_prob = clamp(pos_norm - 0.35·penalty + (0.10 if has_promo and promo_sens>0.6))
```

**Sentiment / tone / confidence:**
```
sentiment  = 0.45 + 0.5·(round_metric - 0.5) + 0.2·(credibility - 0.5) - 0.2·risk + jitter
tone       = enthusiastic≥0.72 / positive≥0.58 / curious≥0.45 / hesitant≥0.32 / skeptical
confidence = 0.5 + 0.3·|round_metric-0.5|·2 + 0.1·(1 - skepticism)
trust_change = clamp(0.12·(credibility-0.5) - 0.18·risk + (0.06 if trigger), -0.3, 0.3)
```

**Action thresholds (rule-based on the scores):**
- **R1 (concept):** `like`/`save_for_later` if interest≥0.55 & awareness≥0.45; `view` if ≥0.4; `comment_positive`/`ignore` if ≥0.3; else `ignore`/`comment_negative`.
- **R2 (comms):** `request_review` if review_dependency>0.65 & credibility<0.7; `like`/`save_for_later` if intent_signal≥0.5 & clarity≥0.55; `ask_price` if price_sens>0.6; `comment_negative` if skepticism>0.6; else `compare_with_current_brand`.
- **R3 (shelf):** `wait_for_promotion` if promo_sens>0.6 & has_promo & trial_prob<0.55; `add_to_cart` if findability≥0.55 & trial_prob≥0.5 & commerce channel; `ask_where_to_buy` if findability≥0.5; `compare_with_current_brand` if ≥0.35; else `ignore`.
- **R4 (trial):** `purchase_trial` if trial_prob≥0.48; band 0.30–0.48 → `wait_for_promotion`/`request_review`/`compare_with_current_brand`; else `reject_before_trial`.
- **R5 (post-trial):** purchasers compute `satisfaction = 0.45 + 0.3·credibility + 0.15·(1-skepticism) - sensory_gap`; `repeat_purchase_intent`/`recommend` if satisfaction≥0.55 & repeat_prob≥0.45; `no_repeat_intent` if ≥0.42; else `complain`. Non-purchasers → `stay_with_current_brand`.
- **R6 (diffusion):** purchasers with satisfaction≥0.55 → `share_with_friend`/`recommend`; <0.42 → `complain`; curious non-purchasers (novelty>0.6, loyalty<0.4) → `switch_brand`; else `stay_with_current_brand`.

**Market actors** (`services/simulation_market_actors.py`): each of the 5 actors takes one
action per round driven by the round's aggregated consumer signal (`avg_interest`,
`avg_trial_prob`, `avg_sentiment`, `positive_share`, dominant barrier/trigger) and its own
`influence_power` / `trust_level` / `evaluation_criteria`. Each action carries a signed
`launch_impact` in `[-1,1]` (stored as `trust_change`), e.g. Retailer
`expand_shelf_facings` vs `threaten_delist`, Competitor `seed_doubt_content` /
`launch_defensive_promo`, Influencer `post_positive_review` / `post_critical_review`,
SocialCommunity `amplify_positive_wom` / `amplify_complaints`, CategoryExpert
`validate_claim` / `flag_claim_clarity_risk`.

---

## Confidence calibration (Phase 11)

The `GET /confidence` endpoint explains *why* confidence is high/medium/low. It is a **separate
explainability view** and does NOT alter the report's own confidence score or any reaction score.

`overall_confidence = Σ (driver.score × driver.weight)`, each `score ∈ [0,1]`. Drivers + weights:

| Driver | Weight | Score basis |
|---|---|---|
| ontology_completeness | 0.18 | `0.4 + 0.04·#entities + (0.2 if claims analyzed)`, clamped |
| agent_coverage | 0.15 | `#consumer_agents / 50` |
| event_volume | 0.12 | `#baseline_events / 330` |
| segment_diversity | 0.12 | `#distinct_segments / 8` |
| evidence_density | 0.13 | `events_with_trigger_or_barrier / events` |
| claim_richness | 0.10 | `#analyzed_claims / 3` |
| information_gaps | 0.10 | `1 − #missing_information / 8` |
| grounding_mode | 0.05 | `1.0` if LLM-enhanced else `0.6` (deterministic fallback) |
| real_world_data | 0.05 | fixed `0.3` — no real sales/social data caps confidence |

Label thresholds: `< 0.5` low, `< 0.75` medium, else high. The endpoint also returns
`confidence_risks` (what pulls it down) and `how_to_improve_confidence` (actionable next steps).
The `real_world_data` factor is deliberately capped at 0.3 so the view can never imply the output
is validated against reality — it remains **exploratory decision support**.

---

## Concept scorecard (Phase 12)

`GET /scorecard` builds a transparent decision-support heuristic from EXISTING data (report
payload + ontology + confidence + assumptions ledger). It does NOT change any reaction score.

All sub-scores are normalized to **0–100** (confidence is 0–1, used as `×100` in the formula):

| Sub-score | Source |
|---|---|
| trial_potential | agent-weighted mean `average_trial_probability` across segments × 100 |
| repeat_potential | agent-weighted mean `average_repeat_probability` × 100 |
| sentiment | agent-weighted mean sentiment, normalized to 0–100 |
| advocacy | `(recommend + share_with_friend) / consumers` from the funnel action distribution |
| claim_credibility | ontology claim_analysis credibility (believable 1.0 / questionable 0.5 / unbelievable 0.0) avg × 100 |
| price_value | keyword score of report `premium_price_risk` (high 35 / medium 60 / low 82) |
| channel_fit | ontology channel_analysis mean `fit_score` × 100 |
| risk (↑ worse) | innovation risk matrix severities (high 1.0 / med 0.6 / low 0.3) avg × 100 |
| assumption_risk (↑ worse) | ledger avg severity (high 1.0 / med 0.5 / low 0.2) × 100 |
| sensitivity_risk (↑ worse) | proxy: `0.6·(trial−repeat gap) + 0.4·promotion_dependency` × 100 (NOT a full sweep) |
| confidence | `GET /confidence` `overall_confidence` (0–1) |

**Overall (0–100, clamped):**
```
overall = 0.20·trial + 0.20·repeat + 0.15·sentiment + 0.10·advocacy
        + 0.10·claim_credibility + 0.10·channel_fit + 0.15·(confidence×100)
        − 0.15·risk − 0.10·assumption_risk − 0.05·sensitivity_risk
```

`recommended_next_step` targets the weakest of {repeat, claim credibility, price/value, trial,
confidence}. `ranking_explanation` prints every weighted term so the score is never a black box.
This is **a decision-support heuristic, not a validated market forecast** — always shown with that
disclaimer.

---

## Recommendation status (Phase 14)

The executive briefing assigns a deterministic recommendation status from the concept
scorecard (no new scoring; it only reads scorecard fields). Evaluated in precedence order:

```
hold                          if overall < 35  OR (risk ≥ 70 AND confidence == low)
                                 OR (trial < 25 AND overall < 45)
revise_and_retest             elif risk ≥ 65  OR claim_credibility < 40
                                 OR (repeat < 20 AND assumption_risk ≥ 70)
move_forward                  elif overall ≥ 60 AND confidence ∈ {medium, high}
                                 AND risk < 60 AND repeat ≥ 35
validate_before_move_forward  otherwise (the default middle path)
```
(`overall`, `trial`, `repeat`, `claim_credibility`, `risk`, `assumption_risk` are 0–100 scorecard
sub-scores; `confidence` is the calibration label.) Readiness chips map each dimension to
ready / caution / not_ready, and `overall_readiness` follows the status
(move_forward→ready, validate→caution, revise/hold→not_ready).

**Next-best-actions** are assembled deterministically from: high/medium adoption barriers (P0/P1),
report strategic recommendations (priority-mapped), the weakest scorecard dimension ("test first",
P0), confidence "how to improve", and the top high-impact assumption — then **deduplicated** (by
normalized text prefix), **prioritized** (severity → trial/repeat impact → confidence → effort →
owner clarity), tagged with an `owner_team` + `effort`, and capped at 5–10 specific actions.
The briefing remains **exploratory decision support, not a validated forecast.**
