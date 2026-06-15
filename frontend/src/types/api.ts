// Types mirroring the FastAPI backend (Phases 1-7). Kept intentionally close to
// the Pydantic schemas so the API client stays type-safe.

export interface ApiErrorBody {
  detail?: { code?: string; message?: string; request_id?: string } | string;
}

export interface ReadyZ {
  status: string;
  database: { connected: boolean; type: string; checks: { name: string; ok: boolean }[] };
  app: { version: string; environment: string; demo_mode: boolean };
}

export interface AppLogEntry {
  id: string;
  timestamp: string | null;
  level: string;
  event_type: string;
  request_id: string | null;
  project_id: string | null;
  run_id: string | null;
  scenario_id: string | null;
  path: string | null;
  method: string | null;
  status_code: number | null;
  code: string | null;
  message: string;
  metadata: Record<string, unknown>;
}

export interface AppLogList {
  items: AppLogEntry[];
  total_returned: number;
  limit: number;
}

export interface Diagnostics {
  status: string;
  request_id: string | null;
  app: Record<string, unknown>;
  database: { connected: boolean; project_count: number; event_count: number; live_run_count: number; app_log_count?: number };
  features: Record<string, boolean>;
  warnings: string[];
  recent_error_count?: number;
  recent_warning_count?: number;
  last_error?: AppLogEntry | null;
  log_retention_limit?: number;
}

export interface SystemStatus {
  app_name: string;
  version: string;
  environment: string;
  llm_configured: boolean;
  database: string;
  database_type?: string;
  demo_mode: boolean;
  frontend_origin_configured?: boolean;
  live_streaming_supported?: boolean;
  e2e_configured?: boolean;
}

// --- projects --------------------------------------------------------------
export interface Project {
  id: string;
  name: string;
  category: string | null;
  market: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface ProjectEnvelope {
  project: Project;
  has_brief: boolean;
  has_ontology: boolean;
  agents_count: number;
  events_count: number;
  has_report: boolean;
}

export interface ProjectCreate {
  name: string;
  category?: string | null;
  market?: string | null;
}

// --- brief -----------------------------------------------------------------
export interface BriefIn {
  raw_text?: string;
  brand?: string | null;
  product_name?: string | null;
  category?: string | null;
  benefit?: string | null;
  functional_claims?: string[];
  emotional_claims?: string[];
  packaging?: string | null;
  price?: string | null;
  pack_size?: string | null;
  target_consumers?: string | null;
  usage_occasions?: string[];
  channels?: string[];
  launch_market?: string | null;
  competitors?: string[];
  media_plan?: string | null;
  sampling_plan?: string | null;
  promotion_plan?: string | null;
  known_risks?: string[];
}

export interface BriefOut {
  brief_id: string;
  stored: boolean;
  field_count: number;
}

// --- ontology --------------------------------------------------------------
export interface OntologyEntity {
  type: string;
  name: string;
  attributes: Record<string, unknown>;
}

export interface OntologyRelationship {
  from: string;
  to: string;
  type: string;
  attributes: Record<string, unknown>;
}

export interface ClaimAnalysisItem {
  claim: string;
  clarity: string;
  credibility: string;
  differentiation: string;
  risks: string[];
  recommended_rewrite: string | null;
}

export interface OntologyOut {
  ontology_id: string;
  project_id: string;
  brief_id: string | null;
  source_mode: string;
  confidence_score: number;
  entities: OntologyEntity[];
  relationships: OntologyRelationship[];
  market_assumptions: string[];
  missing_information: string[];
  risk_signals: string[];
  purchase_triggers: string[];
  adoption_barriers: string[];
  claim_analysis: ClaimAnalysisItem[];
}

// --- agents ----------------------------------------------------------------
export interface AgentGenerateOut {
  total_agents: number;
  consumer_agents: number;
  market_actor_agents: number;
  segment_distribution: Record<string, number>;
  source_mode: string;
}

export interface AgentSummaryOut {
  total_agents: number;
  consumer_agents: number;
  market_actor_agents: number;
  segment_distribution: Record<string, number>;
  average_trait_scores: Record<string, number>;
  top_trial_barriers: [string, number][];
  top_trust_drivers: [string, number][];
  top_channel_preferences: [string, number][];
}

export interface AgentOut {
  id: string;
  project_id: string;
  agent_type: "consumer" | "market_actor";
  name: string;
  segment_name: string | null;
  role: string | null;
  source_mode: string;
  confidence_score: number;
  profile: Record<string, unknown>;
  memory: unknown[];
  simulation_memory: unknown[];
  action_history: unknown[];
}

export interface EventOut {
  id: string;
  round_number: number;
  stage_name: string;
  agent_id: string;
  agent_type: string;
  segment_name: string | null;
  touchpoint: string | null;
  action_type: string;
  content_seen: string | null;
  reasoning: string | null;
  generated_reaction: string | null;
  emotional_tone: string | null;
  confidence_score: number | null;
  sentiment_score: number | null;
  trial_probability: number | null;
  purchase_intent_score: number | null;
  repeat_probability: number | null;
  trust_change: number | null;
  barrier_detected: string | null;
  trigger_detected: string | null;
  scores: Record<string, unknown>;
  timestamp: string;
}

export interface EventFilters {
  round_number?: number;
  action_type?: string;
  agent_id?: string;
  agent_type?: string;
  segment_name?: string;
  limit?: number;
  offset?: number;
}

// --- simulation ------------------------------------------------------------
export interface RoundSummary {
  round_number: number;
  stage_name: string;
  consumer_events: number;
  market_actor_events: number;
  action_distribution: Record<string, number>;
  avg_sentiment: number;
  avg_trial_probability: number;
}

export interface SimulationRunIn {
  rounds?: number;
  deterministic?: boolean;
  seed?: number;
  include_market_actors?: boolean;
  force_rerun?: boolean;
}

export interface SimulationRunOut {
  simulation_status: string;
  source_mode: string;
  rounds_run: number;
  total_events: number;
  consumer_events: number;
  market_actor_events: number;
  action_distribution: Record<string, number>;
  segment_summary: Record<string, Record<string, number>>;
  top_barriers: [string, number][];
  top_triggers: [string, number][];
  per_round: RoundSummary[];
}

export interface EventsSummaryOut {
  total_events: number;
  consumer_events: number;
  market_actor_events: number;
  rounds_run: number;
  action_distribution: Record<string, number>;
  per_round: RoundSummary[];
  segment_summary: Record<string, Record<string, number>>;
  top_barriers: [string, number][];
  top_triggers: [string, number][];
}

// --- report ----------------------------------------------------------------
export interface EvidenceRef {
  event_id: string;
  round_number: number;
  agent_id: string;
  segment_name: string | null;
  action_type: string;
  short_reaction_excerpt: string;
}

export interface ExecutiveSummary {
  overall_market_reaction: string;
  top_opportunity: string;
  top_risk: string;
  estimated_trial_potential: string;
  estimated_repeat_potential: string;
  key_recommendation: string;
  confidence_score: number;
  important_assumptions: string[];
}

export interface SegmentReaction {
  segment_name: string;
  number_of_agents: number;
  average_trial_probability: number;
  average_purchase_intent_score: number;
  average_repeat_probability: number;
  average_sentiment_score: number;
  strongest_trigger: string | null;
  strongest_barrier: string | null;
  dominant_actions: string[];
  representative_reaction: string;
  recommended_message_angle: string;
  confidence_score: number;
}

export interface TriggerAnalysis {
  trigger: string;
  frequency: number;
  affected_segments: string[];
  related_touchpoints: string[];
  evidence_events: EvidenceRef[];
  strategic_implication: string;
}

export interface BarrierAnalysis {
  barrier: string;
  frequency: number;
  affected_segments: string[];
  related_touchpoints: string[];
  evidence_events: EvidenceRef[];
  severity_level: string;
  recommended_fix: string;
}

export interface RiskItem {
  risk_type: string;
  severity: string;
  evidence: string;
  affected_segments: string[];
  mitigation: string;
}

export interface Recommendation {
  priority: string;
  recommendation: string;
  rationale: string;
  supporting_evidence: string;
  expected_impact: string;
  owner_team: string;
}

export interface ABTest {
  test_name: string;
  hypothesis: string;
  variant_a: string;
  variant_b: string;
  target_segment: string;
  success_metric: string;
  why_this_test_matters: string;
}

export interface TrialRepeatForecast {
  likely_triers: string;
  likely_repeaters: string;
  one_time_trial_risk: string;
  switch_potential: string;
  dependency_on_promotion: string;
  confidence_score: number;
}

export interface ReportPayload {
  executive_summary: ExecutiveSummary;
  launch_funnel_summary: {
    action_distribution: Record<string, number>;
    round_summary: { round_number: number; stage_name: string; avg_sentiment: number; avg_trial_probability: number }[];
    [k: string]: unknown;
  };
  segment_reaction_map: SegmentReaction[];
  purchase_trigger_analysis: TriggerAnalysis[];
  adoption_barrier_analysis: BarrierAnalysis[];
  claim_clarity_and_credibility: {
    claim: string;
    clarity_assessment: string;
    credibility_assessment: string;
    recommended_rewrite: string | null;
  }[];
  trial_repeat_forecast: TrialRepeatForecast;
  innovation_risk_matrix: RiskItem[];
  strategic_recommendations: Recommendation[];
  recommended_ab_tests: ABTest[];
  human_validation_questions: string[];
  limitations: string[];
  [k: string]: unknown;
}

export interface ReportSummaryOut {
  overall_market_reaction: string;
  top_opportunity: string;
  top_risk: string;
  top_segments: Record<string, unknown>[];
  top_triggers: Record<string, unknown>[];
  top_barriers: Record<string, unknown>[];
  key_recommendations: string[];
}

export interface ReportGenerateOut {
  project_id: string;
  report_id: string;
  status: string;
  source_mode: string;
  confidence_score: number;
  generated_at: string;
  report_payload: ReportPayload;
  markdown_report: string;
  summary: ReportSummaryOut;
}

// --- Q&A -------------------------------------------------------------------
export interface QAEvidenceRef {
  event_id: string;
  round_number: number;
  agent_id: string;
  segment_name: string | null;
  action_type: string;
  short_reaction_excerpt: string;
}

export interface InterviewAnswer {
  agent_id: string;
  segment_name: string | null;
  persona_label: string;
  answer: string;
  evidence_from_agent_memory: string[];
}

export interface QAAnswer {
  direct_answer: string;
  evidence_summary: string;
  supporting_events: QAEvidenceRef[];
  supporting_segments: string[];
  confidence_score: number;
  limitations: string[];
  recommended_next_action: string[];
  selected_agents: string[];
  simulated_interview_answers: InterviewAnswer[];
}

export interface QuestionIn {
  question: string;
  use_llm?: boolean;
  include_evidence?: boolean;
  max_evidence_events?: number;
}

export interface QuestionOut {
  project_id: string;
  question: string;
  intent: string;
  answer: QAAnswer;
  source_mode: string;
}

// --- scenarios -------------------------------------------------------------
export interface ScenarioOverrides {
  price_change_pct?: number;
  claim_credibility_boost?: number;
  sampling_boost?: number;
  promotion_boost?: number;
  channel_focus?: string | null;
  competitor_pressure_boost?: number;
  packaging_appeal_boost?: number;
  social_proof_boost?: number;
  sensory_risk_reduction?: number;
  retailer_support_boost?: number;
}

export interface ScenarioRunIn {
  scenario_name: string;
  description?: string;
  overrides: ScenarioOverrides;
  rounds?: number;
  seed?: number;
  generate_delta_report?: boolean;
}

export interface MetricChanges {
  trial_probability_delta: number;
  purchase_intent_delta: number;
  repeat_probability_delta: number;
  sentiment_delta: number;
  complaint_delta: number;
  recommend_delta: number;
  switch_delta: number;
  trial_count_delta: number;
  top_segments_improved: string[];
  top_segments_declined: string[];
}

export interface SegmentChange {
  segment_name: string;
  baseline_trial_probability: number;
  scenario_trial_probability: number;
  trial_probability_delta: number;
  sentiment_delta: number;
}

export interface ScenarioRunOut {
  scenario_id: string;
  project_id: string;
  scenario_name: string;
  description: string;
  overrides: ScenarioOverrides;
  baseline_summary: Record<string, unknown>;
  scenario_summary: Record<string, unknown>;
  delta_summary: string;
  key_metric_changes: MetricChanges;
  segment_changes: SegmentChange[];
  action_distribution_changes: Record<string, number>;
  trigger_changes: Record<string, number>;
  barrier_changes: Record<string, number>;
  recommendation_changes: string[];
  conclusion: string;
  created_at: string | null;
}

export interface ScenarioListItem {
  scenario_id: string;
  scenario_name: string;
  description: string;
  baseline_event_count: number;
  scenario_event_count: number;
  created_at: string;
}

// --- insights (Phase 11) ---------------------------------------------------
export interface SweepPoint {
  value: number;
  trial_probability: number;
  repeat_probability: number;
  purchase_intent: number;
  sentiment: number;
  recommend_rate: number;
  complaint_rate: number;
  top_improved_segments: string[];
  top_declined_segments: string[];
  interpretation: string;
}

export interface LeverSweep {
  lever: string;
  points: SweepPoint[];
  best_point: SweepPoint | null;
  diminishing_return_point: SweepPoint | null;
  strategic_read: string;
}

export interface SensitivityOut {
  project_id: string;
  baseline_summary: Record<string, unknown>;
  sweeps: LeverSweep[];
  overall_recommendation: string;
  limitations: string[];
}

export interface SensitivityIn {
  levers?: Record<string, number[]>;
  seed?: number;
  rounds?: number;
}

export interface ConfidenceDriver {
  factor: string;
  score: number;
  weight: number;
  explanation: string;
}

export interface ConfidenceOut {
  project_id: string;
  overall_confidence: number;
  confidence_label: string;
  drivers: ConfidenceDriver[];
  confidence_risks: string[];
  how_to_improve_confidence: string[];
  disclaimer: string;
}

export interface AssumptionItem {
  category: string;
  assumption: string;
  source: string;
  impact: string;
  recommended_validation: string;
}

export interface AssumptionsOut {
  project_id: string;
  assumptions: AssumptionItem[];
  summary: {
    high_impact_count: number;
    medium_impact_count: number;
    low_impact_count: number;
  };
}

// --- portfolio / scorecards / snapshots (Phase 12) -------------------------
export interface Scorecard {
  project_id: string;
  project_name: string;
  snapshot_id: string | null;
  snapshot_name: string | null;
  overall_score: number;
  confidence_score: number;
  trial_potential_score: number;
  repeat_potential_score: number;
  sentiment_score: number;
  advocacy_score: number;
  risk_score: number;
  claim_credibility_score: number;
  price_value_score: number;
  channel_fit_score: number;
  assumption_risk_score: number;
  sensitivity_risk_score: number;
  top_opportunity: string;
  top_risk: string;
  best_segment: string;
  weakest_segment: string;
  strongest_trigger: string;
  strongest_barrier: string;
  recommended_next_step: string;
  ranking_explanation: string;
  confidence_label: string;
  disclaimer: string;
}

export interface SnapshotListItem {
  snapshot_id: string;
  snapshot_name: string;
  description: string;
  source_report_id: string | null;
  source_project_status: string | null;
  created_at: string;
}

export interface SnapshotOut {
  snapshot_id: string;
  project_id: string;
  snapshot_name: string;
  description: string;
  source_report_id: string | null;
  source_project_status: string | null;
  report_payload: Record<string, unknown>;
  markdown: string;
  scorecard: Scorecard;
  created_at: string;
}

export interface SnapshotCreate {
  snapshot_name: string;
  description?: string;
}

export interface PortfolioProjectRow {
  project_id: string;
  project_name: string;
  status: string;
  has_report: boolean;
  has_simulation: boolean;
  overall_score: number | null;
  confidence_score: number | null;
  trial_potential_score: number | null;
  repeat_potential_score: number | null;
  risk_score: number | null;
  top_opportunity: string | null;
  top_risk: string | null;
  recommended_next_step: string | null;
}

export interface PortfolioOut {
  projects: PortfolioProjectRow[];
  summary: {
    total_projects: number;
    report_ready_projects: number;
    highest_score_project: string | null;
    highest_risk_project: string | null;
    best_trial_project: string | null;
    best_repeat_project: string | null;
  };
}

export interface CompareIn {
  project_ids: string[];
  snapshot_ids?: string[];
  include_snapshots?: boolean;
}

export interface CompareItem {
  type: string;
  project_id: string;
  snapshot_id: string | null;
  name: string;
  scorecard: Scorecard;
}

export interface CompareOut {
  items: CompareItem[];
  comparison_summary: {
    best_overall: string | null;
    best_trial: string | null;
    best_repeat: string | null;
    lowest_risk: string | null;
    highest_confidence: string | null;
    most_needs_validation: string | null;
  };
  dimension_rankings: Record<string, string[]>;
  recommendation: string;
}

// --- snapshot diff + decision history (Phase 13) ---------------------------
export interface DiffSide {
  type: "active_report" | "snapshot";
  snapshot_id?: string | null;
}

export interface DiffRequest {
  left: DiffSide;
  right: DiffSide;
}

export interface NumericDelta {
  left: number;
  right: number;
  delta: number;
}

export interface DimensionChange {
  dimension: string;
  delta: number;
  direction: string;
  interpretation: string;
}

export interface SectionChange {
  section: string;
  change_type: string;
  summary: string;
}

export interface RecommendationChange {
  left_recommendation: string;
  right_recommendation: string;
  changed: boolean;
  interpretation: string;
}

export interface RiskChanges {
  reduced_risks: string[];
  new_or_increased_risks: string[];
  unchanged_risks: string[];
}

export interface DiffSegmentChange {
  segment_name: string;
  trial_delta: number;
  repeat_delta: number;
  sentiment_delta: number;
  interpretation: string;
}

export interface SnapshotDiffOut {
  project_id: string;
  left: { type: string; name: string; created_at: string | null };
  right: { type: string; name: string; created_at: string | null };
  scorecard_delta: Record<string, NumericDelta>;
  dimension_changes: DimensionChange[];
  changed_sections: SectionChange[];
  recommendation_changes: RecommendationChange;
  risk_changes: RiskChanges;
  segment_changes: DiffSegmentChange[];
  plain_english_summary: string;
  decision_implication: string;
  limitations: string[];
}

export interface DecisionCreate {
  entry_type: string;
  title: string;
  body?: string;
  related_snapshot_id?: string | null;
  related_scenario_id?: string | null;
  related_report_id?: string | null;
  tags?: string[];
}

export interface DecisionOut {
  id: string;
  project_id: string;
  entry_type: string;
  title: string;
  body: string;
  related_snapshot_id: string | null;
  related_scenario_id: string | null;
  related_report_id: string | null;
  tags: string[];
  created_at: string;
  updated_at: string;
}

export interface TimelineItem {
  timestamp: string;
  type: string;
  title: string;
  description: string;
  related_id: string | null;
  metadata: Record<string, unknown>;
}

export interface TimelineOut {
  project_id: string;
  timeline: TimelineItem[];
}

// --- executive briefing (Phase 14) -----------------------------------------
export interface BriefingGenerateIn {
  audience?: string;
  tone?: string;
  include_evidence?: boolean;
  include_decision_history?: boolean;
  include_next_actions?: boolean;
  use_llm_rewrite?: boolean;
  force_regenerate?: boolean;
}

export interface BriefingFinding {
  finding_title: string;
  explanation: string;
  supporting_metric: string;
  supporting_evidence: QAEvidenceRef[];
  affected_segments: string[];
  confidence_level: string;
  business_implication: string;
}

export interface BriefingRisk {
  risk_title: string;
  severity: string;
  why_it_matters: string;
  affected_segments: string[];
  supporting_evidence: QAEvidenceRef[];
  mitigation: string;
}

export interface NextBestAction {
  priority: string;
  action: string;
  owner_team: string;
  effort: string;
  expected_impact: string;
  evidence_basis: string;
  suggested_timing: string;
  validation_method: string;
}

export interface ValidationItem {
  question: string;
  recommended_method: string;
  success_metric: string;
  priority: string;
}

export interface BriefingPayload {
  briefing_header: {
    project_name: string;
    product_or_concept_name: string;
    generated_at: string;
    audience: string;
    confidence_label: string;
    overall_score: number;
    recommendation_status: string;
  };
  situation: {
    one_paragraph_context: string;
    category_or_market_context: string;
    concept_summary: string;
    current_decision_point: string;
  };
  top_findings: BriefingFinding[];
  biggest_risks: BriefingRisk[];
  readiness_assessment: {
    trial_readiness: string;
    repeat_readiness: string;
    claim_readiness: string;
    channel_readiness: string;
    confidence_readiness: string;
    overall_readiness: string;
    readiness_reasoning: string;
  };
  what_changed_recently: {
    has_history: boolean;
    latest_snapshot_comparison: string;
    scorecard_drift: string;
    changed_recommendation: string;
    major_timeline_events: string[];
  };
  decision_recommendation: {
    recommended_decision: string;
    rationale: string;
    conditions_before_launch: string[];
    decision_caveats: string[];
  };
  next_best_actions: NextBestAction[];
  validation_plan: ValidationItem[];
  evidence_pack: {
    event_evidence: QAEvidenceRef[];
    segment_evidence: string[];
    scorecard_evidence: string[];
    assumption_evidence: string[];
    scenario_or_sensitivity_evidence: string[];
    decision_history_evidence: string[];
  };
  limitations: string[];
}

export interface BriefingOut {
  project_id: string;
  briefing_id: string;
  status: string;
  source_mode: string;
  audience: string;
  tone: string;
  generated_at: string;
  briefing_payload: BriefingPayload;
  markdown: string;
  summary: {
    recommendation_status: string;
    overall_score: number;
    confidence_label: string;
    headline: string;
    top_action: string | null;
  };
}

// --- Phase 15: briefing Q&A / tailor / board summary -----------------------
export interface BriefingAskIn {
  question: string;
  audience?: string;
  tone?: string;
  include_evidence?: boolean;
  max_evidence_items?: number;
  use_llm_rewrite?: boolean;
}

export interface BriefingAnswer {
  direct_answer: string;
  audience_framing: string;
  supporting_evidence: QAEvidenceRef[];
  related_next_actions: string[];
  related_risks: string[];
  confidence_score: number;
  limitations: string[];
  recommended_follow_up: string[];
}

export interface BriefingAskOut {
  project_id: string;
  question: string;
  intent: string;
  answer: BriefingAnswer;
  source_mode: string;
}

export interface TailorIn {
  audience?: string;
  tone?: string;
  format?: string;
  include_evidence?: boolean;
  use_llm_rewrite?: boolean;
}

export interface TailoredPayload {
  headline: string;
  audience_priority: string;
  what_this_audience_needs_to_know: string[];
  role_specific_risks: string[];
  role_specific_actions: string[];
  evidence_to_show: string[];
  what_not_to_overclaim: string[];
  talk_track: string[];
}

export interface TailorOut {
  project_id: string;
  audience: string;
  tone: string;
  tailored_payload: TailoredPayload;
  markdown: string;
  source_mode: string;
}

export interface BoardSummaryPayload {
  headline_recommendation: string;
  decision_status: string;
  one_sentence_concept: string;
  three_key_findings: string[];
  top_three_risks: string[];
  decision_gate: string;
  next_three_actions: string[];
  validation_needed: string[];
  confidence_and_caveat: string;
  evidence_refs: string[];
}

export interface BoardSummaryOut {
  project_id: string;
  summary_payload: BoardSummaryPayload;
  markdown: string;
  source_mode: string;
}

// --- Agent Studio (Phase 16) -----------------------------------------------
export interface StudioNode {
  id: string;
  label: string;
  type: "consumer" | "market_actor";
  group: string;
  event_count: number;
  avg_sentiment: number;
  dominant_action: string | null;
}

export interface StudioEdge {
  source: string;
  target: string;
  reason: string;
  round_number: number;
}

export interface StudioGraph {
  nodes: StudioNode[];
  edges: StudioEdge[];
  note: string;
}

export interface StudioEvent {
  id: string;
  round_number: number;
  stage_name: string;
  agent_id: string;
  agent_type: string;
  segment_name: string | null;
  touchpoint: string | null;
  action_type: string;
  generated_reaction: string | null;
  reasoning: string | null;
  emotional_tone: string | null;
  confidence_score: number | null;
  sentiment_score: number | null;
  trial_probability: number | null;
  purchase_intent_score: number | null;
  repeat_probability: number | null;
  barrier_detected: string | null;
  trigger_detected: string | null;
}

export interface LiveStartIn {
  rounds?: number;
  deterministic?: boolean;
  seed?: number;
  include_market_actors?: boolean;
  force_rerun?: boolean;
  event_delay_ms?: number;
}

export interface LiveStartOut {
  run_id: string;
  status: string;
  stream_url: string;
}

export interface LiveProgress {
  round: number;
  rounds_total: number;
  events_emitted: number;
  events_expected: number;
  percent: number;
}

export interface LiveStreamMessage {
  run_id: string;
  project_id: string;
  type: string;
  timestamp: string;
  sequence: number;
  round_number: number;
  stage_name: string;
  progress: LiveProgress;
  payload: Record<string, any>;
}

export interface LiveRun {
  run_id: string;
  project_id: string;
  status: string;
  rounds: number;
  seed: number;
  event_delay_ms: number;
  total_events_expected: number;
  total_events_emitted: number;
  current_round: number;
  error_message: string | null;
  started_at: string | null;
  last_event_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  is_stale: boolean;
  can_cancel: boolean;
  can_replay_persisted_events: boolean;
  stream_url: string | null;
}

export interface NextAction {
  action: string;
  label: string;
  surface: string;
  reason: string;
}

export interface OverviewOut {
  project: { id: string; name: string; category: string | null; market: string | null; status: string };
  pipeline_status: {
    has_brief: boolean;
    has_ontology: boolean;
    has_agents: boolean;
    has_simulation: boolean;
    has_report: boolean;
    has_briefing: boolean;
  };
  counts: { agents: number; events: number; snapshots: number; scenarios: number; decisions: number };
  latest_scorecard: Scorecard | null;
  latest_briefing_summary: {
    recommendation_status: string;
    overall_score: number;
    confidence_label: string;
    headline: string;
    top_action: string | null;
  } | null;
  latest_live_run: LiveRun | null;
  next_recommended_action: NextAction;
  recent_activity: { timestamp: string | null; type: string; title: string; description: string }[];
}

export interface StudioState {
  project: { id: string; name: string; category: string | null; market: string | null; status: string };
  agents: { id: string; name: string; agent_type: string; segment_name: string | null; role: string | null; confidence_score: number }[];
  events: StudioEvent[];
  events_summary: EventsSummaryOut;
  rounds: RoundSummary[];
  graph: StudioGraph;
}
