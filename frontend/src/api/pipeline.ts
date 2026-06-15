import { api } from "./client";

export interface PipelineStatus {
  project_id: string;
  project_name?: string;
  pipeline_stage: string;
  pipeline_stage_label: string;
  pipeline_stage_source: string;
  pipeline_stage_updated_at: string | null;
  pipeline_stage_note: string | null;
  inferred_stage: string;
  decision_board_label: string | null;
  recommended_stage: string;
  next_recommended_action: { label: string; surface: string };
}

export interface PipelineCardItem {
  project_id: string;
  project_name: string;
  pipeline_stage: string;
  pipeline_stage_source: string;
  pipeline_stage_updated_at?: string | null;
  decision_board_label: string | null;
  overall_score: number | null;
  risk_score?: number | null;
  owner_team?: string | null;
  top_risk: string | null;
  next_recommended_action: { label: string; surface: string };
  has_decision_pack: boolean;
}

export interface PipelineBoardFilters {
  stage?: string;
  decision_label?: string;
  min_score?: number;
  max_risk?: number;
  owner_team?: string;
  search?: string;
  include_archived?: boolean;
}

export interface PipelineColumn {
  stage: string;
  label: string;
  items: PipelineCardItem[];
}

export interface PipelineBoard {
  generated_at: string;
  columns: PipelineColumn[];
  summary: Record<string, number>;
}

export interface ApplyDecisionBoardResult {
  changed: number;
  skipped_manual: number;
  skipped_no_board: number;
  unchanged: number;
  changes: { project_id: string; project_name: string; new_stage: string }[];
}

export const PIPELINE_STAGES = [
  "new_concept",
  "brief_submitted",
  "ready_for_simulation",
  "simulated",
  "report_ready",
  "briefing_ready",
  "leadership_review",
  "validate",
  "revise",
  "go",
  "hold",
  "archived",
] as const;

export const STAGE_LABELS: Record<string, string> = {
  new_concept: "New Concept",
  brief_submitted: "Brief Submitted",
  ready_for_simulation: "Ready for Simulation",
  simulated: "Simulated",
  report_ready: "Report Ready",
  briefing_ready: "Briefing Ready",
  leadership_review: "Leadership Review",
  validate: "Validate",
  revise: "Revise",
  go: "Go",
  hold: "Hold",
  archived: "Archived",
};

export const getPipelineStatus = (projectId: string) =>
  api.get<PipelineStatus>(`/projects/${projectId}/pipeline-status`);

export const updatePipelineStatus = (
  projectId: string,
  payload: { pipeline_stage: string; note?: string; source?: string }
) => api.patch<PipelineStatus>(`/projects/${projectId}/pipeline-status`, payload);

export const getPipelineBoard = (filters: PipelineBoardFilters = {}) => {
  const params = new URLSearchParams();
  if (filters.stage) params.set("stage", filters.stage);
  if (filters.decision_label) params.set("decision_label", filters.decision_label);
  if (filters.min_score != null) params.set("min_score", String(filters.min_score));
  if (filters.max_risk != null) params.set("max_risk", String(filters.max_risk));
  if (filters.owner_team) params.set("owner_team", filters.owner_team);
  if (filters.search) params.set("search", filters.search);
  if (filters.include_archived === false) params.set("include_archived", "false");
  const qs = params.toString();
  return api.get<PipelineBoard>(`/portfolio/pipeline${qs ? `?${qs}` : ""}`);
};

export interface ActivityItem {
  id: string;
  timestamp: string | null;
  project_id: string;
  project_name: string;
  activity_type: string;
  title: string;
  description: string;
  stage: string | null;
  tags: string[];
  related_url: string;
}

export interface ActivityList {
  items: ActivityItem[];
  total_returned: number;
}

export const getActivity = (
  opts: { event_type?: string; project_id?: string; stage?: string; limit?: number } = {}
) => {
  const params = new URLSearchParams();
  if (opts.event_type) params.set("event_type", opts.event_type);
  if (opts.project_id) params.set("project_id", opts.project_id);
  if (opts.stage) params.set("stage", opts.stage);
  if (opts.limit != null) params.set("limit", String(opts.limit));
  const qs = params.toString();
  return api.get<ActivityList>(`/portfolio/activity${qs ? `?${qs}` : ""}`);
};

export const applyDecisionBoardToPipeline = (
  payload: { project_ids?: string[]; only_if_not_manual?: boolean } = {}
) => api.post<ApplyDecisionBoardResult>("/portfolio/pipeline/apply-decision-board", payload);
