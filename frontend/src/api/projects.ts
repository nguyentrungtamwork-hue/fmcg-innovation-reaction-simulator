import { api } from "./client";
import type { Project, ProjectCreate, ProjectEnvelope } from "../types/api";

export const getProjects = () => api.get<Project[]>("/projects");

export const createProject = (payload: ProjectCreate) =>
  api.post<Project>("/projects", payload);

export const getProject = (projectId: string) =>
  api.get<ProjectEnvelope>(`/projects/${projectId}`);

export interface ProjectImportResult {
  status: string;
  new_project_id: string;
  counts: Record<string, number>;
  warnings: string[];
}

export interface ProjectDeleteResult {
  status: string;
  project_id: string;
  counts: Record<string, number>;
}

/** URL for the export download (opened directly by the browser). */
export const projectExportUrl = (
  projectId: string,
  opts: { format?: "json" | "zip"; include_logs?: boolean; include_events?: boolean; include_artifacts?: boolean } = {}
) => {
  const params = new URLSearchParams();
  if (opts.format) params.set("format", opts.format);
  if (opts.include_logs != null) params.set("include_logs", String(opts.include_logs));
  if (opts.include_events != null) params.set("include_events", String(opts.include_events));
  if (opts.include_artifacts != null) params.set("include_artifacts", String(opts.include_artifacts));
  const qs = params.toString();
  return `${api.baseUrl}/projects/${projectId}/export${qs ? `?${qs}` : ""}`;
};

/** Fetch the export bundle as a JS object (used by the Data Tools "download" helper). */
export const exportProjectBundle = (projectId: string) =>
  api.get<Record<string, unknown>>(`/projects/${projectId}/export`);

export const importProject = (
  bundle: unknown,
  opts: { mode?: string; new_project_name?: string; preserve_original_ids?: boolean } = {}
) => api.post<ProjectImportResult>("/projects/import", { bundle, ...opts });

export const deleteProject = (projectId: string) =>
  api.del<ProjectDeleteResult>(`/projects/${projectId}`);

export const getDecisionPack = (projectId: string) =>
  api.get<Record<string, any>>(`/projects/${projectId}/decision-pack`);

export const getDecisionPackMarkdown = (projectId: string) =>
  api.getText(`/projects/${projectId}/decision-pack/markdown`);
