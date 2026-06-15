import { api } from "./client";
import type { LiveRun, LiveStartIn, LiveStartOut } from "../types/api";

export const startLiveSimulation = (projectId: string, payload: LiveStartIn) =>
  api.post<LiveStartOut>(`/projects/${projectId}/live-simulation/start`, payload);

export const listLiveRuns = (projectId: string) =>
  api.get<LiveRun[]>(`/projects/${projectId}/live-simulation/runs`);

export const cancelLiveRun = (projectId: string, runId: string) =>
  api.post<LiveRun>(`/projects/${projectId}/live-simulation/${runId}/cancel`, {});

/** Full EventSource URL for the run's SSE stream (api.baseUrl already includes /api/v1). */
export const streamUrl = (projectId: string, runId: string) =>
  `${api.baseUrl}/projects/${projectId}/live-simulation/${runId}/stream`;
