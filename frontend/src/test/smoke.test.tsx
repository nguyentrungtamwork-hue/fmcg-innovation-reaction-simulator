import { describe, it, expect, vi, beforeEach } from "vitest";
import { useState } from "react";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";

// --- module mocks (no backend required) ------------------------------------
vi.mock("../api/projects", () => ({
  getProjects: vi.fn(() => Promise.resolve([{ id: "p1", name: "Demo", category: null, market: null, status: "draft", created_at: "", updated_at: "" }])),
  createProject: vi.fn(),
  getProject: vi.fn(() => Promise.resolve({
    project: { id: "p1", name: "Demo", category: null, market: null, status: "draft", created_at: "", updated_at: "" },
    has_brief: false, has_ontology: false, agents_count: 0, events_count: 0, has_report: false,
  })),
  exportProjectBundle: vi.fn(() => Promise.resolve({ export_version: "1.0", project_id: "p1", data: {} })),
  importProject: vi.fn(() => Promise.resolve({ status: "imported", new_project_id: "p2", counts: { agents: 50, events: 330 }, warnings: [] })),
  deleteProject: vi.fn(() => Promise.resolve({ status: "deleted", project_id: "p1", counts: {} })),
  projectExportUrl: vi.fn(() => "http://localhost:8000/api/v1/projects/p1/export?format=zip"),
  getDecisionPack: vi.fn(() => Promise.resolve({
    project_id: "p1", generated_at: "2026-06-08T00:00:00Z",
    header: { project_name: "Demo", concept_name: "Demo Cool", category: "RTD tea", recommendation_status: "validate_before_move_forward", overall_score: 64.2, confidence_label: "medium" },
    executive_summary: { recommended_decision: "Validate the key risks first.", rationale: "Repeat is constrained.", conditions_before_launch: ["Run a sensory test."], decision_caveats: ["Simulated."], context: "Positive but repeat-constrained.", concept_summary: "Demo Cool", decision_point: "Validate before moving forward." },
    scorecard: { overall_score: 64.2, trial_potential_score: 46, repeat_potential_score: 13, risk_score: 55, confidence_label: "medium", disclaimer: "Heuristic, not a forecast." },
    confidence: { overall_confidence: 0.65, confidence_label: "medium", confidence_risks: [], how_to_improve_confidence: [] },
    top_findings: [{ finding_title: "Early adopters lead", explanation: "x", supporting_metric: "trial 0.46" }],
    biggest_risks: [{ risk_title: "Repeat risk", severity: "high", why_it_matters: "y", mitigation: "Sensory test." }],
    next_best_actions: [{ priority: "P0", action: "Run a sensory test.", owner_team: "R&D" }],
    scenario_summary: { count: 1, scenarios: [{ scenario_name: "-10% price", delta_summary: "trial +0.05", conclusion: "Helps trial." }] },
    sensitivity_summary: { available: false, note: "Run on demand." },
    assumptions_summary: { high_impact_count: 2, medium_impact_count: 3, low_impact_count: 1, top_assumptions: [{ assumption: "No real data", impact: "high", recommended_validation: "survey" }] },
    evidence_pack: [{ category: "Segment evidence", items: ["Early Adopters: trial 0.46"] }],
    decision_history: [{ entry_type: "note", title: "Kickoff", body: "", created_at: "2026-06-01T00:00:00Z" }],
    limitations: ["Exploratory decision support.", "Heuristic, not a forecast."],
  })),
  getDecisionPackMarkdown: vi.fn(() => Promise.resolve("# Decision Pack — Demo\n## Recommendation\n...")),
}));
vi.mock("../api/pipeline", async () => {
  const actual: any = await vi.importActual("../api/pipeline");
  return {
    ...actual,
    getPipelineStatus: vi.fn(() => Promise.resolve({
      project_id: "p1", project_name: "Demo",
      pipeline_stage: "briefing_ready", pipeline_stage_label: "Briefing Ready",
      pipeline_stage_source: "inferred", pipeline_stage_updated_at: null, pipeline_stage_note: null,
      inferred_stage: "briefing_ready", decision_board_label: "go", recommended_stage: "go",
      next_recommended_action: { label: "Open the Decision Pack and prepare leadership review.", surface: "decision-pack" },
    })),
    updatePipelineStatus: vi.fn((pid: string, payload: any) => Promise.resolve({
      project_id: pid, project_name: "Demo",
      pipeline_stage: payload.pipeline_stage, pipeline_stage_label: actual.STAGE_LABELS[payload.pipeline_stage],
      pipeline_stage_source: payload.source ?? "manual", pipeline_stage_updated_at: "2026-06-08T00:00:00Z",
      pipeline_stage_note: payload.note ?? null,
      inferred_stage: "briefing_ready", decision_board_label: "go", recommended_stage: "go",
      next_recommended_action: { label: "x", surface: "home" },
    })),
    getPipelineBoard: vi.fn(() => Promise.resolve({
      generated_at: "2026-06-08T00:00:00Z",
      columns: actual.PIPELINE_STAGES.map((s: string) => ({
        stage: s, label: actual.STAGE_LABELS[s],
        items: s === "briefing_ready" ? [
          { project_id: "p1", project_name: "Alpha", pipeline_stage: s, pipeline_stage_source: "inferred", decision_board_label: "go", overall_score: 64, top_risk: "Repeat", next_recommended_action: { label: "Open the Decision Pack.", surface: "decision-pack" }, has_decision_pack: true },
        ] : [],
      })),
      summary: { total_projects: 1, new_count: 0, brief_submitted_count: 0, ready_for_simulation_count: 0, simulated_count: 0, report_ready_count: 0, briefing_ready_count: 1, leadership_review_count: 0, validate_count: 0, revise_count: 0, go_count: 0, hold_count: 0, archived_count: 0 },
    })),
    applyDecisionBoardToPipeline: vi.fn(() => Promise.resolve({ changed: 1, skipped_manual: 0, skipped_no_board: 0, unchanged: 0, changes: [{ project_id: "p1", project_name: "Alpha", new_stage: "go" }] })),
    getActivity: vi.fn(() => Promise.resolve({
      items: [
        { id: "a1", timestamp: "2026-06-08T10:00:00Z", project_id: "p1", project_name: "Alpha", activity_type: "stage_change", title: "Pipeline stage changed to Validate", description: "Stage changed from Briefing Ready to Validate.", stage: "validate", tags: ["pipeline", "stage-change", "validate"], related_url: "/projects/p1/decisions" },
        { id: "a2", timestamp: "2026-06-07T09:00:00Z", project_id: "p2", project_name: "Beta", activity_type: "decision", title: "Decision Board applied: Go", description: "Stage set to Go.", stage: "go", tags: ["pipeline", "decision-board", "go"], related_url: "/projects/p2/decisions" },
      ],
      total_returned: 2,
    })),
  };
});
vi.mock("../api/samples", () => ({
  getSamples: vi.fn(() => Promise.resolve({ samples: [
    { sample_id: "ready_to_drink_tea", name: "VerdeCalm Herbal Cool Tea", category: "Ready-to-drink beverage", short_description: "A 50%-less-sugar herbal RTD tea.", target_consumer: "Office workers", key_claim: "50% less sugar", price_positioning: "premium", channels: ["CVS"], known_risks: ["price"], recommended_demo_path: ["workflow"], what_to_observe: "trial vs repeat" },
    { sample_id: "healthy_snack", name: "CrispRoot Baked Veggie Crisps", category: "Healthy snack", short_description: "Baked veggie crisps.", target_consumer: "Millennials", key_claim: "40% less fat", price_positioning: "premium", channels: ["Supermarkets"], known_risks: ["taste"], recommended_demo_path: ["report"], what_to_observe: "health barrier" },
  ] })),
  getSample: vi.fn(() => Promise.resolve({ sample_id: "ready_to_drink_tea", name: "VerdeCalm Herbal Cool Tea", category: "Ready-to-drink beverage", short_description: "x", target_consumer: "y", key_claim: "z", price_positioning: "p", channels: [], known_risks: [], recommended_demo_path: ["workflow"], what_to_observe: "w", sample_brief_text: "# Brief", structured: {} })),
  loadSample: vi.fn(() => Promise.resolve({ project_id: "p9", status: "loaded", completed_steps: ["project_created", "brief_submitted"], next_url: "/projects/p9/workflow", warnings: [] })),
}));
vi.mock("../api/ontology", () => ({
  getOntology: vi.fn(() => Promise.reject(new Error("none"))),
  submitBrief: vi.fn(),
  analyzeOntology: vi.fn(),
}));
vi.mock("../api/agents", () => ({
  getAgentsSummary: vi.fn(() => Promise.reject(new Error("none"))),
  generateAgents: vi.fn(),
  getAgent: vi.fn(() => Promise.resolve({
    id: "a1", project_id: "p1", agent_type: "consumer", name: "Consumer 1", segment_name: "Early Adopters",
    role: null, source_mode: "fallback", confidence_score: 0.7, profile: { price_sensitivity: 0.5 },
    memory: ["m1"], simulation_memory: ["s1"], action_history: [{ round: 1, action: "purchase_trial" }],
  })),
  listAgents: vi.fn(() => Promise.resolve([])),
}));
vi.mock("../api/events", () => ({
  listEvents: vi.fn(() => Promise.resolve([
    { id: "e1", round_number: 1, stage_name: "Concept", agent_id: "a1", agent_type: "consumer", segment_name: "Early Adopters", touchpoint: "TikTok", action_type: "purchase_trial", content_seen: null, reasoning: "x", generated_reaction: "Looks worth a try", emotional_tone: "curious", confidence_score: 0.7, sentiment_score: 0.4, trial_probability: 0.5, purchase_intent_score: 0.4, repeat_probability: 0.2, trust_change: 0, barrier_detected: null, trigger_detected: "Less sugar", scores: {}, timestamp: "2026-06-01T00:00:00Z" },
  ])),
  getEvent: vi.fn(),
}));
vi.mock("../api/simulation", () => ({
  getEventsSummary: vi.fn(() => Promise.reject(new Error("none"))),
  runSimulation: vi.fn(),
}));
vi.mock("../api/reports", () => ({
  getReport: vi.fn(),
  getReportSummary: vi.fn(() => Promise.reject(new Error("none"))),
  getReportMarkdown: vi.fn(),
  generateReport: vi.fn(),
}));
const SAMPLE_SCENARIO = {
  scenario_id: "s1", project_id: "p1", scenario_name: "10% price reduction", description: "",
  overrides: { price_change_pct: -10 },
  baseline_summary: { trial_probability: 0.46, repeat_probability: 0.13 },
  scenario_summary: { trial_probability: 0.49, repeat_probability: 0.14 },
  delta_summary: "Trial +0.03",
  key_metric_changes: { trial_probability_delta: 0.03, purchase_intent_delta: 0.0, repeat_probability_delta: 0.01, sentiment_delta: 0.01, complaint_delta: -1, recommend_delta: 2, switch_delta: 0, trial_count_delta: 3, top_segments_improved: ["Early Adopters"], top_segments_declined: [] },
  segment_changes: [{ segment_name: "Early Adopters", baseline_trial_probability: 0.46, scenario_trial_probability: 0.49, trial_probability_delta: 0.03, sentiment_delta: 0.01 }],
  action_distribution_changes: { purchase_trial: 3 }, trigger_changes: {}, barrier_changes: {},
  recommendation_changes: ["Trial improves"], conclusion: "'10% price reduction' improves trial.", created_at: "2026-06-01T00:00:00Z",
};
vi.mock("../api/scenarios", () => ({
  listScenarios: vi.fn(() => Promise.resolve([])),
  runScenario: vi.fn(() => Promise.resolve(SAMPLE_SCENARIO)),
  getScenario: vi.fn(() => Promise.resolve(SAMPLE_SCENARIO)),
  deleteScenario: vi.fn(),
  getScenarioDelta: vi.fn(),
}));
vi.mock("../api/system", () => ({
  getSystemStatus: vi.fn(() =>
    Promise.resolve({
      app_name: "FMCG", version: "0.1.0", environment: "test",
      llm_configured: false, database: "sqlite", database_type: "sqlite", demo_mode: true,
      frontend_origin_configured: false, live_streaming_supported: true, e2e_configured: true,
    })
  ),
  getReadyz: vi.fn(() => Promise.resolve({
    status: "ready", database: { connected: true, type: "sqlite", checks: [] },
    app: { version: "0.1.0", environment: "test", demo_mode: true },
  })),
  getDiagnostics: vi.fn(() => Promise.resolve({
    status: "ok", request_id: "req-123",
    app: { name: "FMCG", version: "0.1.0" },
    database: { connected: true, project_count: 2, event_count: 330, live_run_count: 1 },
    features: { simulation: true, live_streaming: true, briefing: true, portfolio: true, e2e_configured: true },
    warnings: [],
    recent_error_count: 1, recent_warning_count: 0, last_error: null, log_retention_limit: 500,
  })),
  getSystemLogs: vi.fn(() => Promise.resolve({ items: [], total_returned: 0, limit: 50 })),
  getRecentErrors: vi.fn(() => Promise.resolve({ items: [], total_returned: 0, limit: 10 })),
}));
const SAMPLE_SCORECARD = {
  project_id: "p1", project_name: "Alpha", snapshot_id: null, snapshot_name: null,
  overall_score: 64.2, confidence_score: 0.65, trial_potential_score: 46, repeat_potential_score: 13,
  sentiment_score: 39, advocacy_score: 30, risk_score: 55, claim_credibility_score: 60,
  price_value_score: 60, channel_fit_score: 70, assumption_risk_score: 75, sensitivity_risk_score: 40,
  top_opportunity: "Beachhead segment", top_risk: "Repeat risk", best_segment: "Early Adopters",
  weakest_segment: "Skeptics", strongest_trigger: "Less sugar", strongest_barrier: "Price",
  recommended_next_step: "De-risk repeat.", ranking_explanation: "overall = … = 64.2/100.",
  confidence_label: "medium", disclaimer: "Heuristic, not a forecast.",
};
vi.mock("../api/portfolio", () => ({
  getPortfolio: vi.fn(() =>
    Promise.resolve({
      projects: [
        { project_id: "p1", project_name: "Alpha", status: "draft", has_report: true, has_simulation: true,
          overall_score: 64.2, confidence_score: 0.65, trial_potential_score: 46, repeat_potential_score: 13,
          risk_score: 55, top_opportunity: "Beachhead", top_risk: "Repeat", recommended_next_step: "Validate." },
      ],
      summary: { total_projects: 1, report_ready_projects: 1, highest_score_project: "Alpha", highest_risk_project: "Alpha", best_trial_project: "Alpha", best_repeat_project: "Alpha" },
    })
  ),
  comparePortfolio: vi.fn(),
  getScorecard: vi.fn(() => Promise.resolve(SAMPLE_SCORECARD)),
  createSnapshot: vi.fn(),
  listSnapshots: vi.fn(() => Promise.resolve([])),
  getSnapshot: vi.fn(),
  deleteSnapshot: vi.fn(),
  getDecisionBoard: vi.fn(() => Promise.resolve({
    generated_at: "2026-06-08T00:00:00Z",
    summary: { total_projects: 2, go_count: 1, validate_count: 1, revise_count: 0, hold_count: 0, incomplete_count: 0, report_ready_projects: 2, top_project: "Alpha", highest_risk_project: "Beta", most_ready_project: "Alpha", most_needs_validation_project: "Beta" },
    items: [
      { project_id: "p1", project_name: "Alpha", decision_label: "go", overall_score: 64.2, confidence_score: 0.65, confidence_label: "medium", trial_potential_score: 46, repeat_potential_score: 33, risk_score: 50, risk_level: "medium", top_opportunity: "Beachhead", top_risk: "Repeat", recommended_next_step: "Advance to pilot.", owner_team: "Consumer Insights", decision_reason: "Strong overall.", has_decision_pack: true, decision_pack_url: "/projects/p1/decision-pack" },
      { project_id: "p2", project_name: "Beta", decision_label: "validate", overall_score: 52, confidence_score: 0.4, confidence_label: "low", trial_potential_score: 40, repeat_potential_score: 18, risk_score: 60, risk_level: "medium", top_opportunity: "Trial", top_risk: "Claim", recommended_next_step: "Validate first.", owner_team: "Marketing & Regulatory", decision_reason: "Needs validation.", has_decision_pack: true, decision_pack_url: "/projects/p2/decision-pack" },
    ],
    rankings: { best_overall: [{ project_name: "Alpha", value: 64.2 }], best_trial: [{ project_name: "Alpha", value: 46 }], best_repeat: [{ project_name: "Alpha", value: 33 }], lowest_risk: [{ project_name: "Alpha", value: 50 }], highest_confidence: [{ project_name: "Alpha", value: 0.65 }] },
    portfolio_recommendation: "1 concept(s) ready to advance.",
    limitations: ["Heuristic decision-support — not a validated market forecast."],
  })),
  getDecisionBoardMarkdown: vi.fn(() => Promise.resolve("# Portfolio Decision Board\n...")),
}));
const SAMPLE_BRIEFING = {
  project_id: "p1", briefing_id: "b1", status: "generated", source_mode: "deterministic",
  audience: "executive", tone: "concise", generated_at: "2026-06-01T00:00:00Z",
  markdown: "# Executive Launch Briefing\n## Next Best Actions\n- [P0] Do X",
  summary: { recommendation_status: "validate_before_move_forward", overall_score: 64.2, confidence_label: "medium", headline: "Validate first.", top_action: "Run a sensory test." },
  briefing_payload: {
    briefing_header: { project_name: "Alpha", product_or_concept_name: "Alpha Cool", generated_at: "2026-06-01T00:00:00Z", audience: "executive", confidence_label: "medium", overall_score: 64.2, recommendation_status: "validate_before_move_forward" },
    situation: { one_paragraph_context: "Positive but repeat-constrained.", category_or_market_context: "RTD tea · Vietnam", concept_summary: "Alpha", current_decision_point: "Validate before moving forward." },
    top_findings: [{ finding_title: "Early adopters lead", explanation: "x", supporting_metric: "trial 0.46", supporting_evidence: [], affected_segments: ["Early Adopters"], confidence_level: "medium", business_implication: "Lead here." }],
    biggest_risks: [{ risk_title: "Repeat risk", severity: "high", why_it_matters: "x", affected_segments: [], supporting_evidence: [], mitigation: "Sensory test." }],
    readiness_assessment: { trial_readiness: "caution", repeat_readiness: "not_ready", claim_readiness: "caution", channel_readiness: "ready", confidence_readiness: "caution", overall_readiness: "caution", readiness_reasoning: "Mixed." },
    what_changed_recently: { has_history: false, latest_snapshot_comparison: "No prior snapshot.", scorecard_drift: "n/a", changed_recommendation: "n/a", major_timeline_events: [] },
    decision_recommendation: { recommended_decision: "Validate the key risks before moving forward.", rationale: "Repeat constrained.", conditions_before_launch: ["Run sensory test."], decision_caveats: ["Simulated."] },
    next_best_actions: [{ priority: "P0", action: "Run a 2-cell sensory test.", owner_team: "R&D", effort: "medium", expected_impact: "Protects repeat.", evidence_basis: "barrier", suggested_timing: "Before launch", validation_method: "sensory test" }],
    validation_plan: [{ question: "Is taste repeat-worthy?", recommended_method: "sensory test", success_metric: "≥ norm", priority: "P0" }],
    evidence_pack: { event_evidence: [], segment_evidence: ["Early Adopters: trial 0.46"], scorecard_evidence: ["Overall 64.2/100"], assumption_evidence: [], scenario_or_sensitivity_evidence: ["No scenarios."], decision_history_evidence: ["No decision history."] },
    limitations: ["Exploratory decision support.", "Real consumer validation required."],
  },
};
vi.mock("../api/briefing", () => ({
  generateBriefing: vi.fn(() => Promise.resolve(SAMPLE_BRIEFING)),
  getBriefing: vi.fn(() => Promise.reject(new Error("none"))),
  askBriefing: vi.fn(() => Promise.resolve({
    project_id: "p1", question: "Why this recommendation?", intent: "explain_recommendation_status", source_mode: "deterministic",
    answer: { direct_answer: "Because repeat is constrained.", audience_framing: "For leadership.", supporting_evidence: [], related_next_actions: ["Run a sensory test."], related_risks: ["Repeat risk"], confidence_score: 0.6, limitations: ["Exploratory."], recommended_follow_up: ["What evidence supports this?"] },
  })),
  tailorBriefing: vi.fn(() => Promise.resolve({
    project_id: "p1", audience: "brand_team", tone: "concise", source_mode: "deterministic", markdown: "# Briefing — Brand Team",
    tailored_payload: { headline: "[Brand Team] Validate first", audience_priority: "Sharpen positioning.", what_this_audience_needs_to_know: ["Lead segment"], role_specific_risks: ["Repeat risk"], role_specific_actions: ["Substantiate claim"], evidence_to_show: ["Overall 64/100"], what_not_to_overclaim: ["Exploratory."], talk_track: ["For Brand."] },
  })),
  generateBoardSummary: vi.fn(() => Promise.resolve({
    project_id: "p1", source_mode: "deterministic", markdown: "# Board Summary — One Page",
    summary_payload: { headline_recommendation: "Validate before moving forward.", decision_status: "validate_before_move_forward", one_sentence_concept: "Alpha", three_key_findings: ["A", "B", "C"], top_three_risks: ["R1"], decision_gate: "Validate taste.", next_three_actions: ["Sensory test"], validation_needed: ["Taste?"], confidence_and_caveat: "Medium.", evidence_refs: ["complain · R6"] },
  })),
}));
const STUDIO_STATE = {
  project: { id: "p1", name: "Alpha", category: "RTD tea", market: "Vietnam", status: "draft" },
  agents: [
    { id: "a1", name: "Consumer 1", agent_type: "consumer", segment_name: "Early Adopters", role: null, confidence_score: 0.7 },
    { id: "m1", name: "Retailer", agent_type: "market_actor", segment_name: null, role: "Retailer", confidence_score: 0.6 },
  ],
  events: [
    { id: "e1", round_number: 1, stage_name: "Concept", agent_id: "a1", agent_type: "consumer", segment_name: "Early Adopters", touchpoint: "TikTok", action_type: "purchase_trial", generated_reaction: "Looks worth a try", reasoning: "x", emotional_tone: "curious", confidence_score: 0.7, sentiment_score: 0.4, trial_probability: 0.5, purchase_intent_score: 0.4, repeat_probability: 0.2, barrier_detected: null, trigger_detected: "Less sugar" },
    { id: "e2", round_number: 2, stage_name: "Comms", agent_id: "a1", agent_type: "consumer", segment_name: "Early Adopters", touchpoint: "Shelf", action_type: "complain", generated_reaction: "Too pricey", reasoning: "y", emotional_tone: "skeptical", confidence_score: 0.6, sentiment_score: -0.2, trial_probability: 0.3, purchase_intent_score: 0.2, repeat_probability: 0.1, barrier_detected: "Premium price", trigger_detected: null },
  ],
  events_summary: { total_events: 2, consumer_events: 2, market_actor_events: 0, rounds_run: 6, action_distribution: { purchase_trial: 1, complain: 1 }, per_round: [], segment_summary: {}, top_barriers: [], top_triggers: [] },
  rounds: [
    { round_number: 1, stage_name: "Concept", consumer_events: 1, market_actor_events: 0, action_distribution: { purchase_trial: 1 }, avg_sentiment: 0.4, avg_trial_probability: 0.5 },
    { round_number: 2, stage_name: "Comms", consumer_events: 1, market_actor_events: 0, action_distribution: { complain: 1 }, avg_sentiment: -0.2, avg_trial_probability: 0.3 },
  ],
  graph: {
    nodes: [
      { id: "a1", label: "Consumer 1", type: "consumer", group: "Early Adopters", event_count: 2, avg_sentiment: 0.1, dominant_action: "purchase_trial" },
      { id: "m1", label: "Retailer", type: "market_actor", group: "Retailer", event_count: 0, avg_sentiment: 0, dominant_action: null },
    ],
    edges: [{ source: "m1", target: "a1", reason: "market-actor round impact (round 1)", round_number: 1 }],
    note: "Interaction links are visualization aids … not real direct conversations.",
  },
};
vi.mock("../api/studio", () => ({
  getStudioState: vi.fn(() => Promise.resolve(STUDIO_STATE)),
}));
const SAMPLE_LIVE_RUN = {
  run_id: "r1", project_id: "p1", status: "completed", rounds: 6, seed: 42, event_delay_ms: 0,
  total_events_expected: 330, total_events_emitted: 330, current_round: 6, error_message: null,
  started_at: "2026-06-01T00:00:00Z", last_event_at: "2026-06-01T00:01:00Z", completed_at: "2026-06-01T00:01:00Z",
  created_at: "2026-06-01T00:00:00Z", updated_at: "2026-06-01T00:01:00Z",
  is_stale: false, can_cancel: false, can_replay_persisted_events: true, stream_url: null,
};
vi.mock("../api/liveSimulation", () => ({
  startLiveSimulation: vi.fn(() => Promise.resolve({ run_id: "r1", status: "running", stream_url: "/stream" })),
  streamUrl: vi.fn(() => "http://test/stream"),
  listLiveRuns: vi.fn(() => Promise.resolve([SAMPLE_LIVE_RUN])),
  cancelLiveRun: vi.fn(() => Promise.resolve(SAMPLE_LIVE_RUN)),
}));
const OVERVIEW = {
  project: { id: "p1", name: "Alpha", category: "RTD tea", market: "Vietnam", status: "draft" },
  pipeline_status: { has_brief: true, has_ontology: true, has_agents: true, has_simulation: false, has_report: false, has_briefing: false },
  counts: { agents: 55, events: 0, snapshots: 0, scenarios: 0, decisions: 0 },
  latest_scorecard: null,
  latest_briefing_summary: null,
  latest_live_run: null,
  next_recommended_action: { action: "run_live_simulation", label: "Run the simulation (try Live Mode)", surface: "studio", reason: "Agents are ready — run it." },
  recent_activity: [{ timestamp: "2026-06-01T00:00:00Z", type: "agents_generated", title: "Agents generated", description: "55 agents" }],
};
vi.mock("../api/overview", () => ({
  getOverview: vi.fn(() => Promise.resolve(OVERVIEW)),
}));

class MockEventSource {
  static last: MockEventSource | null = null;
  url: string;
  listeners: Record<string, ((e: { data: string }) => void)[]> = {};
  onerror: ((e: unknown) => void) | null = null;
  constructor(url: string) {
    this.url = url;
    MockEventSource.last = this;
  }
  addEventListener(type: string, handler: (e: { data: string }) => void) {
    (this.listeners[type] ||= []).push(handler);
  }
  emit(type: string, data: unknown) {
    (this.listeners[type] || []).forEach((h) => h({ data: JSON.stringify(data) }));
  }
  close() {}
}
(globalThis as unknown as { EventSource: unknown }).EventSource = MockEventSource;
vi.mock("../api/history", () => ({
  snapshotDiff: vi.fn(),
  createDecision: vi.fn(),
  listDecisions: vi.fn(() => Promise.resolve([])),
  deleteDecision: vi.fn(),
  getTimeline: vi.fn(() =>
    Promise.resolve({
      project_id: "p1",
      timeline: [
        { timestamp: "2026-06-01T00:00:00Z", type: "project_created", title: "Project created", description: "Demo", related_id: null, metadata: {} },
        { timestamp: "2026-06-01T01:00:00Z", type: "report_generated", title: "Report generated", description: "", related_id: "r1", metadata: {} },
      ],
    })
  ),
}));
vi.mock("../api/insights", () => ({
  runSensitivity: vi.fn(),
  getConfidence: vi.fn(() =>
    Promise.resolve({
      project_id: "p1", overall_confidence: 0.62, confidence_label: "medium",
      drivers: [
        { factor: "ontology_completeness", score: 0.7, weight: 0.18, explanation: "12 entities" },
        { factor: "agent_coverage", score: 1.0, weight: 0.15, explanation: "50 agents" },
      ],
      confidence_risks: ["No real sales data"],
      how_to_improve_confidence: ["Run real A/B tests"],
      disclaimer: "Exploratory only.",
    })
  ),
  getAssumptions: vi.fn(() =>
    Promise.resolve({
      project_id: "p1",
      assumptions: [
        { category: "model", assumption: "Rule engine, not fitted.", source: "simulation_engine", impact: "high", recommended_validation: "Calibrate." },
      ],
      summary: { high_impact_count: 1, medium_impact_count: 0, low_impact_count: 0 },
    })
  ),
}));

import App from "../App";
import Layout from "../components/Layout";
import ProjectListPage from "../pages/ProjectListPage";
import ProjectWorkflowPage from "../pages/ProjectWorkflowPage";
import ReportPage from "../pages/ReportPage";
import QAConsolePage from "../pages/QAConsolePage";
import ScenarioLabPage from "../pages/ScenarioLabPage";
import ErrorState from "../components/ErrorState";
import ErrorBoundary from "../components/ErrorBoundary";
import { getRecentErrors } from "../api/system";
import DataToolsPage from "../pages/DataToolsPage";
import { exportProjectBundle, importProject } from "../api/projects";
import SampleLibraryPage from "../pages/SampleLibraryPage";
import DecisionPackPage from "../pages/DecisionPackPage";
import PortfolioDecisionBoardPage from "../pages/PortfolioDecisionBoardPage";
import PipelineBoardPage from "../pages/PipelineBoardPage";
import PortfolioActivityPage from "../pages/PortfolioActivityPage";
import { updatePipelineStatus, applyDecisionBoardToPipeline, getPipelineBoard } from "../api/pipeline";
import OnboardingPanel from "../components/OnboardingPanel";
import HelpTooltip from "../components/HelpTooltip";
import GlossaryModal from "../components/GlossaryModal";
import { loadSample } from "../api/samples";
import TourProvider, { useTour } from "../tours/TourProvider";
import DemoControlPanel from "../components/DemoControlPanel";
import MetricCard from "../components/MetricCard";
import EvidenceChip from "../components/EvidenceChip";
import SensitivityPage from "../pages/SensitivityPage";
import ConfidencePanel from "../components/ConfidencePanel";
import AssumptionsLedger from "../components/AssumptionsLedger";
import { MiniLineChart, MiniBarChart } from "../components/charts";
import PortfolioPage from "../pages/PortfolioPage";
import ComparePage from "../pages/ComparePage";
import ScorecardCard from "../components/ScorecardCard";
import SnapshotPanel from "../components/SnapshotPanel";
import SnapshotDiffPage from "../pages/SnapshotDiffPage";
import DecisionHistoryPage from "../pages/DecisionHistoryPage";
import BriefingPage from "../pages/BriefingPage";
import AgentStudioPage from "../pages/AgentStudioPage";
import ProjectHomePage from "../pages/ProjectHomePage";
import AgentDrawer from "../components/AgentDrawer";
import EventExplorerPage from "../pages/EventExplorerPage";
import { getStudioState } from "../api/studio";
import { ApiError } from "../api/client";
import { getReport } from "../api/reports";

function renderAt(path: string, element: React.ReactNode, pattern: string) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path={pattern} element={element} />
      </Routes>
    </MemoryRouter>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Phase 9 frontend smoke tests", () => {
  it("1. App renders", () => {
    render(
      <MemoryRouter initialEntries={["/"]}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText(/FMCG Reaction Simulator/i)).toBeInTheDocument();
  });

  it("2. Layout renders navigation", () => {
    renderAt("/", <Layout />, "/");
    expect(screen.getByRole("link", { name: "Projects" })).toBeInTheDocument();
  });

  it("3. ProjectListPage renders create project UI", () => {
    renderAt("/", <ProjectListPage />, "/");
    expect(screen.getByText(/New project/i)).toBeInTheDocument();
    expect(screen.getByPlaceholderText(/FreshPlus Herbal Cool launch/i)).toBeInTheDocument();
  });

  it("4. ProjectWorkflowPage renders the 8-step workflow", () => {
    renderAt("/projects/p1/workflow", <ProjectWorkflowPage />, "/projects/:projectId/workflow");
    expect(screen.getByText("Create Project")).toBeInTheDocument();
    expect(screen.getByText("Scenario Testing")).toBeInTheDocument();
    expect(screen.getByText("Generate Report")).toBeInTheDocument();
  });

  it("5. ReportPage renders an error state when no report exists", async () => {
    (getReport as unknown as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new ApiError(409, "report_required"));
    renderAt("/projects/p1/report", <ReportPage />, "/projects/:projectId/report");
    expect(await screen.findByText(/Generate the strategic report first/i)).toBeInTheDocument();
  });

  it("6. QAConsolePage renders preset questions", () => {
    renderAt("/projects/p1/qa", <QAConsolePage />, "/projects/:projectId/qa");
    expect(screen.getByRole("button", { name: /Why is repeat purchase low/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Interview 3 skeptical consumers/i })).toBeInTheDocument();
  });

  it("7. ScenarioLabPage renders scenario form controls", () => {
    renderAt("/projects/p1/scenarios", <ScenarioLabPage />, "/projects/:projectId/scenarios");
    expect(screen.getByText("New scenario")).toBeInTheDocument();
    expect(screen.getByText("Price change %")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run scenario/i })).toBeInTheDocument();
  });

  it("8. ErrorState maps backend error codes to friendly messages", () => {
    render(<ErrorState error={new ApiError(409, "events_required")} />);
    expect(screen.getByText(/Run the simulation first/i)).toBeInTheDocument();
    expect(screen.getByText(/events_required/)).toBeInTheDocument();
  });

  it("9. MetricCard renders label/value/change", () => {
    render(<MetricCard label="Trial prob. Δ" value="+0.031" hint="vs baseline" tone="up" />);
    expect(screen.getByText("Trial prob. Δ")).toBeInTheDocument();
    expect(screen.getByText("+0.031")).toBeInTheDocument();
    expect(screen.getByText("vs baseline")).toBeInTheDocument();
  });

  it("10. EvidenceChip renders event metadata", () => {
    render(
      <EvidenceChip
        ev={{
          event_id: "e1",
          round_number: 4,
          agent_id: "a1",
          segment_name: "Value Seekers",
          action_type: "purchase_trial",
          short_reaction_excerpt: "Looks worth a try",
        }}
      />
    );
    expect(screen.getByRole("button", { name: /R4/ })).toBeInTheDocument();
    expect(screen.getByText(/Purchase Trial/i)).toBeInTheDocument();
  });

  // --- Phase 11 ---
  it("11. SensitivityPage renders", () => {
    renderAt("/projects/p1/sensitivity", <SensitivityPage />, "/projects/:projectId/sensitivity");
    expect(screen.getByRole("heading", { name: /Sensitivity sweep/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Run sensitivity sweep/i })).toBeInTheDocument();
  });

  it("12. ConfidencePanel renders factor drivers", async () => {
    render(<ConfidencePanel projectId="p1" />);
    expect(await screen.findByText(/Confidence calibration/i)).toBeInTheDocument();
    expect(await screen.findByText(/Ontology Completeness/i)).toBeInTheDocument();
  });

  it("13. AssumptionsLedger renders assumptions", async () => {
    render(<AssumptionsLedger projectId="p1" />);
    expect(await screen.findByText(/Assumptions ledger/i)).toBeInTheDocument();
    expect(await screen.findByText(/Rule engine, not fitted/i)).toBeInTheDocument();
  });

  it("14. EvidenceChip supports drilldown actions", () => {
    render(
      <MemoryRouter>
        <EvidenceChip
          projectId="p1"
          ev={{ event_id: "e1", round_number: 4, agent_id: "a1", segment_name: "Value Seekers", action_type: "purchase_trial", short_reaction_excerpt: "x" }}
        />
      </MemoryRouter>
    );
    fireEvent.click(screen.getByRole("button", { name: /R4/ }));
    expect(screen.getByRole("link", { name: /Open event/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open agent/i })).toBeInTheDocument();
  });

  it("15. MiniLineChart renders an SVG", () => {
    const { container } = render(
      <MiniLineChart points={[{ x: 0, y: 0.4 }, { x: -10, y: 0.46 }]} />
    );
    expect(container.querySelector("svg")).toBeTruthy();
    expect(container.querySelector("path")).toBeTruthy();
  });

  // --- Phase 12 ---
  it("16. PortfolioPage renders", async () => {
    renderAt("/portfolio", <PortfolioPage />, "/portfolio");
    expect(await screen.findByText(/Innovation portfolio/i)).toBeInTheDocument();
    expect((await screen.findAllByText("Alpha")).length).toBeGreaterThan(0);
  });

  it("17. ComparePage renders selector UI", async () => {
    renderAt("/compare", <ComparePage />, "/compare");
    expect(await screen.findByText(/Compare concepts/i)).toBeInTheDocument();
    expect(await screen.findByText("Alpha")).toBeInTheDocument();
  });

  it("18. ScorecardCard renders scores", () => {
    render(<ScorecardCard sc={SAMPLE_SCORECARD} />);
    expect(screen.getByText("64.2")).toBeInTheDocument();
    expect(screen.getByText(/De-risk repeat/i)).toBeInTheDocument();
  });

  it("19. Report snapshot panel renders scorecard", async () => {
    render(
      <MemoryRouter>
        <SnapshotPanel projectId="p1" />
      </MemoryRouter>
    );
    expect(await screen.findByText(/Concept scorecard/i)).toBeInTheDocument();
  });

  // --- Phase 13 ---
  it("20. SnapshotDiffPage renders", async () => {
    renderAt("/projects/p1/snapshots/diff", <SnapshotDiffPage />, "/projects/:projectId/snapshots/diff");
    expect(await screen.findByRole("heading", { name: /Snapshot diff/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Compare$/i })).toBeInTheDocument();
  });

  it("21. DecisionHistoryPage renders timeline + add form", async () => {
    renderAt("/projects/p1/decisions", <DecisionHistoryPage />, "/projects/:projectId/decisions");
    expect(await screen.findByRole("heading", { name: /Decision history/i })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { name: /^Timeline$/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Add entry/i })).toBeInTheDocument();
  });

  it("22. MiniBarChart renders delta bars", () => {
    const { container } = render(
      <MiniBarChart bars={[{ label: "trial", value: 5.2 }, { label: "risk", value: 3.1 }]} />
    );
    expect(container.querySelector("svg")).toBeTruthy();
    expect(container.querySelectorAll("rect").length).toBe(2);
  });

  // --- Phase 14 ---
  it("23. BriefingPage renders with audience/tone controls", async () => {
    renderAt("/projects/p1/briefing", <BriefingPage />, "/projects/:projectId/briefing");
    expect(await screen.findByRole("heading", { name: /Executive launch briefing/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Audience/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Tone/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Generate briefing/i })).toBeInTheDocument();
  });

  it("24. BriefingPage shows next-best-actions + downloads after generate", async () => {
    renderAt("/projects/p1/briefing", <BriefingPage />, "/projects/:projectId/briefing");
    fireEvent.click(await screen.findByRole("button", { name: /Generate briefing/i }));
    expect(await screen.findByText(/Next best actions/i)).toBeInTheDocument();
    expect(await screen.findByText(/Run a 2-cell sensory test/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download Markdown/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Print briefing/i })).toBeInTheDocument();
  });

  // --- Phase 15 ---
  it("25. Briefing Ask tab answers with evidence/limitations", async () => {
    renderAt("/projects/p1/briefing", <BriefingPage />, "/projects/:projectId/briefing");
    fireEvent.click(await screen.findByRole("tab", { name: /Ask Briefing/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Why this recommendation/i }));
    expect(await screen.findByText(/Because repeat is constrained/i)).toBeInTheDocument();
    expect(await screen.findByText(/Limitations/i)).toBeInTheDocument();
  });

  it("26. Briefing Tailor tab renders audience controls + output", async () => {
    renderAt("/projects/p1/briefing", <BriefingPage />, "/projects/:projectId/briefing");
    fireEvent.click(await screen.findByRole("tab", { name: /Tailor by Audience/i }));
    expect(await screen.findByLabelText(/Audience/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Generate tailored briefing/i }));
    expect(await screen.findByText(/\[Brand Team\] Validate first/i)).toBeInTheDocument();
  });

  it("27. Briefing Board Summary tab generates a one-pager", async () => {
    renderAt("/projects/p1/briefing", <BriefingPage />, "/projects/:projectId/briefing");
    fireEvent.click(await screen.findByRole("tab", { name: /Board Summary/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Generate board summary/i }));
    expect(await screen.findByText(/Validate before moving forward/i)).toBeInTheDocument();
    expect(await screen.findByText(/3 key findings/i)).toBeInTheDocument();
  });

  // --- Phase 16 ---
  it("28. Agent Studio renders canvas, playback, timeline, stream, filters (Workbench)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByRole("heading", { name: /Agent Interaction Map/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /Agent network/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("tab", { name: /^Workbench$/i }));
    expect(await screen.findByRole("button", { name: /^Play$/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Round timeline/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Studio filters/i)).toBeInTheDocument();
  });

  it("29. Agent Studio playback reveals event cards (Workbench)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /^Workbench$/i }));
    const instant = await screen.findByRole("button", { name: /Instant/i });
    fireEvent.click(instant);
    fireEvent.click(screen.getByRole("button", { name: /^Play$/i }));
    expect(await screen.findByText(/Looks worth a try/i)).toBeInTheDocument();
  });

  it("30. Agent Studio shows empty state that guides the next step", async () => {
    (getStudioState as unknown as ReturnType<typeof vi.fn>).mockResolvedValueOnce({ ...STUDIO_STATE, events: [], graph: { nodes: [], edges: [], note: "n" } });
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/Get this simulation ready/i)).toBeInTheDocument();
    expect(await screen.findByText(/Submit a brief/i)).toBeInTheDocument();
  });

  // --- Phase 17 ---
  it("31. Agent Studio header shows simulation status + totals", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/^Ready$/i)).toBeInTheDocument();
    expect(await screen.findByText(/Agents: 2/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /^Briefing$/i })).toBeInTheDocument();
  });

  it("32. Agent Studio shows keyboard hints (Workbench)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /^Workbench$/i }));
    expect(await screen.findByText(/Space play\/pause/i)).toBeInTheDocument();
  });

  it("33. Agent Studio legend explains heuristic edges", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/Heuristic edge/i)).toBeInTheDocument();
  });

  // --- Phase 32: MiroFish-style Studio redesign ---
  it("33a. Studio renders Graph/Split/Workbench layout tabs", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByRole("tab", { name: /^Graph$/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Split$/i })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: /^Workbench$/i })).toBeInTheDocument();
  });

  it("33b. Studio graph panel shows map controls (Refresh + edge labels)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByRole("heading", { name: /Agent Interaction Map/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Refresh map/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Show edge labels/i)).toBeInTheDocument();
  });

  it("33c. Studio process panel renders pipeline step cards (Split)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByRole("heading", { name: /Ontology Extraction/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Reaction Simulation/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Executive Briefing/i })).toBeInTheDocument();
  });

  it("33d. Studio system console renders", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/System Dashboard/i)).toBeInTheDocument();
    expect(await screen.findByText(/Graph data loaded/i)).toBeInTheDocument();
  });

  it("33e. Clicking a graph node opens the agent inspector", async () => {
    const { container } = renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    await screen.findByRole("img", { name: /Agent network/i });
    const circle = container.querySelector("svg circle");
    expect(circle).toBeTruthy();
    fireEvent.click(circle!);
    expect(await screen.findByRole("dialog", { name: /Agent detail/i })).toBeInTheDocument();
  });

  it("33f. Edge-label toggle turns labels on", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    const toggle = await screen.findByLabelText(/Show edge labels/i);
    fireEvent.click(toggle);
    expect((toggle as HTMLInputElement).checked).toBe(true);
  });

  // --- Phase 33: MiroFish-inspired stance + status polish ---
  it("33g. Studio header shows step indicator + live status", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    const status = await screen.findByLabelText(/Studio status/i);
    // OVERVIEW pipeline: brief/ontology/agents done, simulation is first incomplete → 4/6
    expect(status).toHaveTextContent("4/6");
    expect(status).toHaveTextContent("Simulation");
    expect(status).toHaveTextContent(/Standby/i);
  });

  it("33h. Graph legend explains stance colors (Advocate/Neutral/Skeptic)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect((await screen.findAllByText("Advocate")).length).toBeGreaterThan(0);
    expect(screen.getByText("Neutral")).toBeInTheDocument();
    expect(screen.getByText("Skeptic")).toBeInTheDocument();
    expect(screen.getByText("Market actor")).toBeInTheDocument();
  });

  it("33i. Process cards use COMPLETE/WAITING badge vocabulary (Split)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect((await screen.findAllByText("COMPLETE")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("WAITING").length).toBeGreaterThan(0);
  });

  it("33j. Revealed reactions carry a stance badge (Workbench)", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /^Workbench$/i }));
    fireEvent.click(await screen.findByRole("button", { name: /Instant/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Play$/i }));
    await screen.findByText(/Looks worth a try/i);
    // e1 sentiment 0.4 → Advocate, e2 sentiment -0.2 → Skeptic
    expect((await screen.findAllByText("Skeptic")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Advocate").length).toBeGreaterThan(0);
  });

  it("33k. System console shows a live line counter", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/\d+ lines/i)).toBeInTheDocument();
  });

  it("33l. Graph color-by selector switches node taxonomy + legend", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    const group = await screen.findByRole("group", { name: /Color nodes by/i });
    // default = Stance
    expect(within(group).getByRole("button", { name: /^Stance$/i })).toHaveAttribute("aria-pressed", "true");
    // switch to Type → legend shows agent-type entries
    const typeBtn = within(group).getByRole("button", { name: /^Type$/i });
    fireEvent.click(typeBtn);
    expect(typeBtn).toHaveAttribute("aria-pressed", "true");
    expect(await screen.findByText("Consumer")).toBeInTheDocument();
    // switch to Action → legend shows action entries
    fireEvent.click(within(group).getByRole("button", { name: /^Action$/i }));
    expect(await screen.findByText("Trial")).toBeInTheDocument();
    expect(screen.getByText("Complaint")).toBeInTheDocument();
  });

  it("33m. Graph map shows node/edge counts", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByText(/2 nodes · 1 edges/i)).toBeInTheDocument();
  });

  // --- Phase 18 ---
  it("34. Agent Studio renders Replay/Live mode switch + live controls", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /Live Mode/i }));
    expect(await screen.findByRole("button", { name: /Start Live Simulation/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/Event delay/i)).toBeInTheDocument();
  });

  it("35. Live mode streams an event and shows completion actions", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /Live Mode/i }));
    fireEvent.click(screen.getByRole("button", { name: /Start Live Simulation/i }));

    await waitFor(() => expect(MockEventSource.last).toBeTruthy());
    const es = MockEventSource.last!;
    act(() => {
      es.emit("run_started", { run_id: "r1", project_id: "p1", type: "run_started", sequence: 1, round_number: 0, stage_name: "", progress: { round: 0, rounds_total: 6, events_emitted: 0, events_expected: 330, percent: 0 }, payload: {} });
      es.emit("event_generated", { run_id: "r1", project_id: "p1", type: "event_generated", sequence: 2, round_number: 1, stage_name: "Concept", progress: { round: 1, rounds_total: 6, events_emitted: 1, events_expected: 330, percent: 0.3 }, payload: { event_id: "e1", agent_id: "a1", agent_type: "consumer", segment_name: "Early Adopters", action_type: "purchase_trial", generated_reaction: "Looks worth a try", sentiment_score: 0.4 } });
    });
    expect(await screen.findByText(/Looks worth a try/i)).toBeInTheDocument();

    act(() => {
      es.emit("run_completed", { run_id: "r1", project_id: "p1", type: "run_completed", sequence: 3, round_number: 6, stage_name: "", progress: { round: 6, rounds_total: 6, events_emitted: 330, events_expected: 330, percent: 100 }, payload: { total_events: 330, status: "completed" } });
    });
    expect(await screen.findByText(/Live run complete/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Generate Report/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Replay saved events/i })).toBeInTheDocument();
  });

  // --- Phase 19 ---
  it("36. Project Home renders status + next-step CTA", async () => {
    renderAt("/projects/p1/home", <ProjectHomePage />, "/projects/:projectId/home");
    expect(await screen.findByText(/What to do next/i)).toBeInTheDocument();
    expect(await screen.findByText(/Run the simulation/i)).toBeInTheDocument();
    expect(screen.getByText(/Pipeline status/i)).toBeInTheDocument();
  });

  it("37. Live Run History panel renders runs", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /Live Mode/i }));
    expect(await screen.findByText(/Live run history/i)).toBeInTheDocument();
    expect((await screen.findAllByText(/completed/i)).length).toBeGreaterThan(0);
  });

  it("38. Global jump control + Glossary render in Layout", async () => {
    renderAt("/", <Layout />, "/");
    expect(await screen.findByLabelText(/Global jump/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Glossary$/i })).toBeInTheDocument();
  });

  it("39. Glossary modal opens from the footer link", async () => {
    renderAt("/", <Layout />, "/");
    fireEvent.click(await screen.findByRole("button", { name: /^Glossary$/i }));
    expect(await screen.findByRole("dialog", { name: /Glossary/i })).toBeInTheDocument();
    expect(screen.getByText(/Replay vs Live Mode/i)).toBeInTheDocument();
  });

  // --- Phase 20 ---
  it("40. AgentDrawer closes on Escape", async () => {
    const onClose = vi.fn();
    render(<MemoryRouter><AgentDrawer projectId="p1" agentId="a1" onClose={onClose} /></MemoryRouter>);
    expect(await screen.findByText("Consumer 1")).toBeInTheDocument();
    act(() => { window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })); });
    expect(onClose).toHaveBeenCalled();
  });

  it("41. Glossary modal closes with Escape", async () => {
    renderAt("/", <Layout />, "/");
    fireEvent.click(await screen.findByRole("button", { name: /^Glossary$/i }));
    expect(await screen.findByRole("dialog", { name: /Glossary/i })).toBeInTheDocument();
    fireEvent.keyDown(document.body, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog", { name: /Glossary/i })).not.toBeInTheDocument());
  });

  it("42. Global jump exposes surface selection + Go", async () => {
    renderAt("/", <Layout />, "/");
    const jump = await screen.findByLabelText(/Global jump/i);
    expect(jump).toBeInTheDocument();
    expect(screen.getByLabelText(/Surface/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Go$/i })).toBeInTheDocument();
  });

  it("43. Event Explorer renders pagination + filter controls", async () => {
    renderAt("/projects/p1/events", <EventExplorerPage />, "/projects/:projectId/events");
    expect(await screen.findByText(/Page size/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Round/i)).toBeInTheDocument();
    expect(await screen.findByText(/Early Adopters/i)).toBeInTheDocument();
  });

  it("44. Agent Studio renders under reduced motion", async () => {
    const orig = window.matchMedia;
    (window as unknown as { matchMedia: unknown }).matchMedia = (q: string) => ({
      matches: true, media: q, onchange: null, addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
    });
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    expect(await screen.findByRole("img", { name: /Agent network/i })).toBeInTheDocument();
    (window as unknown as { matchMedia: unknown }).matchMedia = orig;
  });

  it("45. Live mode shows disconnect/failure guidance", async () => {
    renderAt("/projects/p1/studio", <AgentStudioPage />, "/projects/:projectId/studio");
    fireEvent.click(await screen.findByRole("tab", { name: /Live Mode/i }));
    fireEvent.click(screen.getByRole("button", { name: /Start Live Simulation/i }));
    await waitFor(() => expect(MockEventSource.last).toBeTruthy());
    act(() => {
      MockEventSource.last!.emit("run_failed", { run_id: "r1", project_id: "p1", type: "run_failed", sequence: 1, round_number: 0, stage_name: "", progress: { round: 0, rounds_total: 6, events_emitted: 0, events_expected: 330, percent: 0 }, payload: { error: "boom" } });
    });
    expect(await screen.findByText(/Stream interrupted/i)).toBeInTheDocument();
  });

  it("46. Scenario Lab renders delta after running a scenario", async () => {
    renderAt("/projects/p1/scenarios", <ScenarioLabPage />, "/projects/:projectId/scenarios");
    fireEvent.click(await screen.findByRole("button", { name: /Run scenario/i }));
    expect(await screen.findByText(/improves trial/i)).toBeInTheDocument();
    expect(await screen.findByText(/Baseline vs scenario/i)).toBeInTheDocument();
  });

  // --- Phase 21: focus management + skip link ---
  it("47. AgentDrawer traps focus while open", async () => {
    render(<MemoryRouter><AgentDrawer projectId="p1" agentId="a1" onClose={() => {}} /></MemoryRouter>);
    const dialog = await screen.findByRole("dialog", { name: /Agent detail/i });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
  });

  it("48. AgentDrawer restores focus to the trigger after close", async () => {
    function Wrapper() {
      const [id, setId] = useState<string | null>(null);
      return (
        <MemoryRouter>
          <button onClick={() => setId("a1")}>open drawer</button>
          <AgentDrawer projectId="p1" agentId={id} onClose={() => setId(null)} />
        </MemoryRouter>
      );
    }
    render(<Wrapper />);
    const trigger = screen.getByRole("button", { name: /open drawer/i });
    trigger.focus();
    fireEvent.click(trigger);
    const dialog = await screen.findByRole("dialog", { name: /Agent detail/i });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
    act(() => { window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })); });
    await waitFor(() => expect(document.activeElement).toBe(trigger));
  });

  it("49. Glossary modal traps + restores focus", async () => {
    renderAt("/", <Layout />, "/");
    const gbtn = await screen.findByRole("button", { name: /^Glossary$/i });
    gbtn.focus();
    fireEvent.click(gbtn);
    const dialog = await screen.findByRole("dialog", { name: /Glossary/i });
    await waitFor(() => expect(dialog.contains(document.activeElement)).toBe(true));
    act(() => { window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" })); });
    await waitFor(() => expect(document.activeElement).toBe(gbtn));
  });

  it("50. Skip-to-content link + main landmark exist", async () => {
    const { container } = renderAt("/", <Layout />, "/");
    expect(await screen.findByRole("link", { name: /Skip to content/i })).toBeInTheDocument();
    expect(container.querySelector("#main-content")).toBeTruthy();
    expect(container.querySelector('main[role="main"]')).toBeTruthy();
  });

  // --- Phase 23: observability ---
  it("51. Diagnostics panel renders backend status + retry", async () => {
    renderAt("/", <Layout />, "/");
    fireEvent.click(await screen.findByRole("button", { name: /^Diagnostics$/i }));
    const dialog = await screen.findByRole("dialog", { name: /Diagnostics/i });
    expect(dialog).toBeInTheDocument();
    expect(await screen.findByText("req-123")).toBeInTheDocument();
    expect(await screen.findByText(/Baseline events/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry status check/i })).toBeInTheDocument();
  });

  it("52. ErrorBoundary catches a render crash", () => {
    const Boom = () => { throw new Error("boom"); };
    render(<ErrorBoundary><Boom /></ErrorBoundary>);
    expect(screen.getByText(/Something went wrong while rendering this page/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/i })).toBeInTheDocument();
  });

  it("53. ErrorState shows the request reference ID", () => {
    render(<ErrorState error={new ApiError(500, "internal_error", "Server error", "req-xyz")} />);
    expect(screen.getByText(/Reference ID: req-xyz/i)).toBeInTheDocument();
  });

  // --- Phase 24: persistent log trail UI ---
  it("54. Diagnostics panel renders recent errors when present", async () => {
    vi.mocked(getRecentErrors).mockResolvedValueOnce({
      items: [
        {
          id: "l1", timestamp: "2026-06-06T00:00:00Z", level: "error", event_type: "http_error",
          request_id: "req-abc", project_id: null, run_id: null, scenario_id: null,
          path: "/api/v1/projects/x", method: "GET", status_code: 404, code: "project_not_found",
          message: "project_not_found", metadata: {},
        },
      ],
      total_returned: 1, limit: 10,
    });
    renderAt("/", <Layout />, "/");
    fireEvent.click(await screen.findByRole("button", { name: /^Diagnostics$/i }));
    await screen.findByRole("dialog", { name: /Diagnostics/i });
    expect(await screen.findByText(/Recent Errors/i)).toBeInTheDocument();
    expect(await screen.findByText(/error · http_error/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Refresh logs/i })).toBeInTheDocument();
  });

  it("55. Diagnostics panel shows the no-recent-errors empty state", async () => {
    renderAt("/", <Layout />, "/");
    fireEvent.click(await screen.findByRole("button", { name: /^Diagnostics$/i }));
    await screen.findByRole("dialog", { name: /Diagnostics/i });
    expect(await screen.findByText(/No recent errors/i)).toBeInTheDocument();
  });

  it("56. ErrorState exposes a copyable request ID button", () => {
    render(<ErrorState error={new ApiError(500, "internal_error", "Server error", "req-xyz")} />);
    expect(screen.getByRole("button", { name: /Copy request ID/i })).toBeInTheDocument();
  });

  it("57. ErrorState copy button writes the request ID to the clipboard", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    render(<ErrorState error={new ApiError(500, "internal_error", "Server error", "req-xyz")} />);
    fireEvent.click(screen.getByRole("button", { name: /Copy request ID/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("req-xyz"));
  });

  // --- Phase 25: data tools ---
  it("58. Data Tools page renders export + import sections", async () => {
    renderAt("/data-tools", <DataToolsPage />, "/data-tools");
    expect(await screen.findByRole("heading", { name: /Data Tools/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Export a project/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Import \/ restore a project/i })).toBeInTheDocument();
  });

  it("59. Data Tools export button calls the export API", async () => {
    (URL as unknown as { createObjectURL: () => string }).createObjectURL = vi.fn(() => "blob:x");
    (URL as unknown as { revokeObjectURL: () => void }).revokeObjectURL = vi.fn();
    renderAt("/data-tools", <DataToolsPage />, "/data-tools");
    const btn = await screen.findByRole("button", { name: /Export project \(JSON\)/i });
    fireEvent.click(btn);
    await waitFor(() => expect(exportProjectBundle).toHaveBeenCalledWith("p1"));
  });

  it("60. Data Tools import form handles a mocked success", async () => {
    renderAt("/data-tools", <DataToolsPage />, "/data-tools");
    const ta = await screen.findByLabelText(/Import bundle JSON/i);
    fireEvent.change(ta, { target: { value: '{"export_version":"1.0","data":{}}' } });
    fireEvent.click(screen.getByRole("button", { name: /^Import project$/i }));
    await waitFor(() => expect(importProject).toHaveBeenCalled());
    expect(await screen.findByText(/Imported as new project/i)).toBeInTheDocument();
  });

  it("61. Project Home shows an Export Project button + Data Tools link", async () => {
    renderAt("/projects/p1/home", <ProjectHomePage />, "/projects/:projectId/home");
    expect(await screen.findByRole("button", { name: /Export Project/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Data Tools/i })).toBeInTheDocument();
  });

  // --- Phase 26: onboarding, samples, help ---
  it("62. Sample Library page renders cards", async () => {
    renderAt("/samples", <SampleLibraryPage />, "/samples");
    expect(await screen.findByRole("heading", { name: /Sample Library/i })).toBeInTheDocument();
    expect(await screen.findByText(/VerdeCalm Herbal Cool Tea/i)).toBeInTheDocument();
    expect(screen.getByText(/CrispRoot Baked Veggie Crisps/i)).toBeInTheDocument();
  });

  it("63. Sample Library search filters cards", async () => {
    renderAt("/samples", <SampleLibraryPage />, "/samples");
    await screen.findByText(/VerdeCalm Herbal Cool Tea/i);
    fireEvent.change(screen.getByPlaceholderText(/Search samples/i), { target: { value: "crisp" } });
    expect(screen.queryByText(/VerdeCalm Herbal Cool Tea/i)).not.toBeInTheDocument();
    expect(screen.getByText(/CrispRoot Baked Veggie Crisps/i)).toBeInTheDocument();
  });

  it("64. Sample Library load button calls API and shows project links", async () => {
    renderAt("/samples", <SampleLibraryPage />, "/samples");
    await screen.findByText(/VerdeCalm Herbal Cool Tea/i);
    fireEvent.click(screen.getAllByRole("button", { name: /^Load as new project$/i })[0]);
    await waitFor(() => expect(loadSample).toHaveBeenCalled());
    expect(await screen.findByRole("button", { name: /Open Project Home/i })).toBeInTheDocument();
  });

  it("65. Onboarding checklist renders and can be dismissed", () => {
    localStorage.removeItem("onboarding_seen");
    renderAt("/", <OnboardingPanel />, "/");
    expect(screen.getByRole("heading", { name: /get to your first insight/i })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Dismiss onboarding/i }));
    expect(screen.queryByRole("heading", { name: /get to your first insight/i })).not.toBeInTheDocument();
    expect(localStorage.getItem("onboarding_seen")).toBe("true");
  });

  it("66. HelpTooltip shows content when opened", () => {
    render(<HelpTooltip term="ontology" label="ontology" />);
    fireEvent.click(screen.getByRole("button", { name: /Help: ontology/i }));
    expect(screen.getByRole("tooltip")).toHaveTextContent(/structured map/i);
  });

  it("67. Glossary search filters terms", () => {
    render(<GlossaryModal open onClose={() => {}} />);
    fireEvent.change(screen.getByPlaceholderText(/Search terms/i), { target: { value: "repeat" } });
    expect(screen.getByText(/Repeat probability/i)).toBeInTheDocument();
    expect(screen.queryByText(/^Ontology$/)).not.toBeInTheDocument();
  });

  // --- Phase 27: guided tours + demo auto-play ---
  function TourStarter({ tourId }: { tourId: string }) {
    const { startTour } = useTour();
    return <button onClick={() => startTour(tourId)}>start-{tourId}</button>;
  }
  function renderTour(tourId: string) {
    return render(
      <MemoryRouter initialEntries={["/"]}>
        <TourProvider><TourStarter tourId={tourId} /></TourProvider>
      </MemoryRouter>
    );
  }

  it("68. Tour overlay renders when a tour starts", () => {
    localStorage.clear();
    renderTour("first_time");
    fireEvent.click(screen.getByText("start-first_time"));
    expect(screen.getByRole("dialog", { name: /Guided tour/i })).toBeInTheDocument();
    expect(screen.getByText(/Welcome to the FMCG Innovation Reaction Simulator/i)).toBeInTheDocument();
  });

  it("69. Tour Next / Back / Skip work", () => {
    localStorage.clear();
    renderTour("first_time");
    fireEvent.click(screen.getByText("start-first_time"));
    fireEvent.click(screen.getByRole("button", { name: /^Next$/i }));
    expect(screen.getByText(/Start from a sample concept/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /^Back$/i }));
    expect(screen.getByText(/Welcome to the FMCG/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Skip tour/i }));
    expect(screen.queryByRole("dialog", { name: /Guided tour/i })).not.toBeInTheDocument();
    expect(localStorage.getItem("guided_tour_seen")).toBe("true");
  });

  it("70. Finishing a tour persists completion", () => {
    localStorage.clear();
    renderTour("studio"); // 5 steps
    fireEvent.click(screen.getByText("start-studio"));
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /^Next$/i }));
    fireEvent.click(screen.getByRole("button", { name: /^Finish$/i }));
    expect(localStorage.getItem("guided_tour_seen")).toBe("true");
    expect(localStorage.getItem("guided_tour_current_step")).toBeNull();
  });

  it("71. Demo control panel renders", () => {
    render(<MemoryRouter><TourProvider><DemoControlPanel /></TourProvider></MemoryRouter>);
    expect(screen.getByRole("button", { name: /Play Demo \(Quick\)/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Start First-Time Tour/i })).toBeInTheDocument();
  });

  it("72. Play Demo calls the sample load API", async () => {
    render(<MemoryRouter><TourProvider><DemoControlPanel /></TourProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: /Play Demo \(Quick\)/i }));
    await waitFor(() => expect(loadSample).toHaveBeenCalledWith("ready_to_drink_tea", { run_pipeline: false }));
  });

  it("73. Agent Studio tour includes the heuristic-edge disclaimer", () => {
    localStorage.clear();
    renderTour("studio");
    fireEvent.click(screen.getByText("start-studio"));
    for (let i = 0; i < 4; i++) fireEvent.click(screen.getByRole("button", { name: /^Next$/i }));
    expect(screen.getByText(/heuristic visual groupings/i)).toBeInTheDocument();
  });

  it("74. Reset tour state clears localStorage keys", () => {
    localStorage.setItem("guided_tour_seen", "true");
    localStorage.setItem("onboarding_seen", "true");
    render(<MemoryRouter><TourProvider><DemoControlPanel /></TourProvider></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: /Reset onboarding\/tour state/i }));
    expect(localStorage.getItem("guided_tour_seen")).toBeNull();
    expect(localStorage.getItem("onboarding_seen")).toBeNull();
  });

  // --- Phase 28: decision pack ---
  it("75. Decision Pack page renders header + read-only badge", async () => {
    renderAt("/projects/p1/decision-pack", <DecisionPackPage />, "/projects/:projectId/decision-pack");
    expect(await screen.findByRole("heading", { name: /^Decision Pack$/i })).toBeInTheDocument();
    expect(screen.getByText("Read-only")).toBeInTheDocument();
  });

  it("76. Decision Pack shows print + download buttons", async () => {
    renderAt("/projects/p1/decision-pack", <DecisionPackPage />, "/projects/:projectId/decision-pack");
    await screen.findByRole("heading", { name: /^Decision Pack$/i });
    expect(screen.getByRole("button", { name: /Print \/ Save as PDF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download Markdown/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download JSON/i })).toBeInTheDocument();
  });

  it("77. Decision Pack renders key sections", async () => {
    renderAt("/projects/p1/decision-pack", <DecisionPackPage />, "/projects/:projectId/decision-pack");
    await screen.findByRole("heading", { name: /^Decision Pack$/i });
    expect(screen.getByRole("heading", { name: /Top Findings/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Biggest Risks/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Next Best Actions/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Evidence Pack/i })).toBeInTheDocument();
  });

  it("78. Decision Pack copy-link button handles clipboard", async () => {
    const writeText = vi.fn(() => Promise.resolve());
    Object.assign(navigator, { clipboard: { writeText } });
    renderAt("/projects/p1/decision-pack", <DecisionPackPage />, "/projects/:projectId/decision-pack");
    await screen.findByRole("heading", { name: /^Decision Pack$/i });
    fireEvent.click(screen.getByRole("button", { name: /Copy local read-only link/i }));
    await waitFor(() => expect(writeText).toHaveBeenCalled());
  });

  // --- Phase 29: portfolio decision board ---
  it("79. Decision Board page renders header + summary cards", async () => {
    renderAt("/portfolio/decision-board", <PortfolioDecisionBoardPage />, "/portfolio/decision-board");
    expect(await screen.findByRole("heading", { name: /Portfolio Decision Board/i })).toBeInTheDocument();
    expect(screen.getByText("Read-only")).toBeInTheDocument();
    // summary metric labels (Go/Validate/…) appear as MetricCard labels
    expect(screen.getAllByText(/^Go$/i).length).toBeGreaterThan(0);
  });

  it("80. Decision Board renders the decision table with projects", async () => {
    renderAt("/portfolio/decision-board", <PortfolioDecisionBoardPage />, "/portfolio/decision-board");
    await screen.findByRole("heading", { name: /Portfolio Decision Board/i });
    expect(screen.getByRole("heading", { name: /^Decision Board$/i })).toBeInTheDocument();
    expect(screen.getAllByText("Alpha").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Beta").length).toBeGreaterThan(0);
  });

  it("81. Decision Board shows a Decision Pack link for ready projects", async () => {
    renderAt("/portfolio/decision-board", <PortfolioDecisionBoardPage />, "/portfolio/decision-board");
    await screen.findByRole("heading", { name: /Portfolio Decision Board/i });
    const links = screen.getAllByRole("link", { name: /Decision Pack →/i });
    expect(links.length).toBeGreaterThanOrEqual(1);
    expect(links[0]).toHaveAttribute("href", "/projects/p1/decision-pack");
  });

  it("82. Decision Board shows print + download buttons", async () => {
    renderAt("/portfolio/decision-board", <PortfolioDecisionBoardPage />, "/portfolio/decision-board");
    await screen.findByRole("heading", { name: /Portfolio Decision Board/i });
    expect(screen.getByRole("button", { name: /Print \/ Save as PDF/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download Markdown/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Download JSON/i })).toBeInTheDocument();
  });

  // --- Phase 30: pipeline board ---
  it("83. Pipeline Board page renders header + summary cards", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    expect(await screen.findByRole("heading", { name: /Innovation Pipeline Board/i })).toBeInTheDocument();
    expect(screen.getByText(/Apply Decision Board/i)).toBeInTheDocument();
  });

  it("84. Pipeline Board renders stage columns and a project card", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    expect(screen.getAllByText(/Briefing Ready/i).length).toBeGreaterThan(0);
    expect(screen.getByText("Alpha")).toBeInTheDocument();
  });

  it("85. Update Stage modal opens, saves, calls API", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    fireEvent.click(screen.getByRole("button", { name: /^Update Stage$/i }));
    expect(await screen.findByRole("dialog", { name: /Update pipeline stage/i })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText(/New stage/i), { target: { value: "validate" } });
    fireEvent.click(screen.getByRole("button", { name: /^Save stage$/i }));
    await waitFor(() => expect(updatePipelineStatus).toHaveBeenCalledWith(
      "p1", expect.objectContaining({ pipeline_stage: "validate", source: "manual" })
    ));
  });

  it("86. Apply Decision Board button calls API", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    fireEvent.click(screen.getByRole("button", { name: /Apply Decision Board/i }));
    await waitFor(() => expect(applyDecisionBoardToPipeline).toHaveBeenCalled());
  });

  it("87. Project Home shows pipeline stage badge + Update Stage button", async () => {
    renderAt("/projects/p1/home", <ProjectHomePage />, "/projects/:projectId/home");
    expect(await screen.findByText(/Pipeline stage:/i)).toBeInTheDocument();
    expect(screen.getAllByText(/Briefing Ready/i).length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /^Update Stage$/i })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open Pipeline Board/i })).toBeInTheDocument();
  });

  // --- Phase 31: activity + pipeline filters ---
  it("88. Pipeline filter bar renders", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    expect(screen.getByLabelText(/^Search$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Stage$/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^Decision$/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Clear filters/i })).toBeInTheDocument();
  });

  it("89. Changing a pipeline filter re-fetches with that filter", async () => {
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    (getPipelineBoard as any).mockClear();
    fireEvent.change(screen.getByLabelText(/^Search$/i), { target: { value: "alpha" } });
    await waitFor(() =>
      expect(getPipelineBoard).toHaveBeenCalledWith(expect.objectContaining({ search: "alpha" }))
    );
  });

  it("90. Clear filters button resets URL filters", async () => {
    renderAt("/portfolio/pipeline?stage=validate", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    fireEvent.click(screen.getByRole("button", { name: /Clear filters/i }));
    await waitFor(() =>
      expect(getPipelineBoard).toHaveBeenLastCalledWith({})
    );
  });

  it("91. Pipeline card shows 'Recently changed' badge for recent stage updates", async () => {
    (getPipelineBoard as any).mockResolvedValueOnce({
      generated_at: "2026-06-08T00:00:00Z",
      columns: [{ stage: "validate", label: "Validate", items: [
        { project_id: "p1", project_name: "Alpha", pipeline_stage: "validate", pipeline_stage_source: "manual",
          pipeline_stage_updated_at: new Date().toISOString(),
          decision_board_label: "validate", overall_score: 60, risk_score: 50, owner_team: "Consumer Insights",
          top_risk: "Repeat", next_recommended_action: { label: "Validate", surface: "decision-pack" }, has_decision_pack: true },
      ] }],
      summary: { total_projects: 1, total_projects_unfiltered: 1, validate_count: 1, go_count: 0, hold_count: 0, archived_count: 0,
        new_count: 0, brief_submitted_count: 0, ready_for_simulation_count: 0, simulated_count: 0, report_ready_count: 0, briefing_ready_count: 0, leadership_review_count: 0, revise_count: 0 },
    });
    renderAt("/portfolio/pipeline", <PipelineBoardPage />, "/portfolio/pipeline");
    await screen.findByRole("heading", { name: /Innovation Pipeline Board/i });
    expect(await screen.findByText(/Recently changed/i)).toBeInTheDocument();
  });

  it("92. Project Home shows the Recent pipeline activity panel", async () => {
    renderAt("/projects/p1/home", <ProjectHomePage />, "/projects/:projectId/home");
    expect(await screen.findByText(/Recent pipeline activity/i)).toBeInTheDocument();
    expect(await screen.findByText(/Pipeline stage changed to Validate/i)).toBeInTheDocument();
  });

  it("93. Portfolio Activity page renders the feed", async () => {
    renderAt("/portfolio/activity", <PortfolioActivityPage />, "/portfolio/activity");
    expect(await screen.findByRole("heading", { name: /Portfolio Activity/i })).toBeInTheDocument();
    expect(await screen.findByText(/Pipeline stage changed to Validate/i)).toBeInTheDocument();
    expect(screen.getByText(/Decision Board applied: Go/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^Refresh$/i })).toBeInTheDocument();
  });
});
