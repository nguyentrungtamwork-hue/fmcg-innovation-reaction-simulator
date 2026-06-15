import { api } from "./client";
import type { AssumptionsOut, ConfidenceOut, SensitivityIn, SensitivityOut } from "../types/api";

export const runSensitivity = (projectId: string, payload: SensitivityIn) =>
  api.post<SensitivityOut>(`/projects/${projectId}/sensitivity`, payload);

export const getConfidence = (projectId: string) =>
  api.get<ConfidenceOut>(`/projects/${projectId}/confidence`);

export const getAssumptions = (projectId: string) =>
  api.get<AssumptionsOut>(`/projects/${projectId}/assumptions`);
