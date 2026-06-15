import { api } from "./client";
import type { ScenarioListItem, ScenarioRunIn, ScenarioRunOut } from "../types/api";

export const runScenario = (projectId: string, payload: ScenarioRunIn) =>
  api.post<ScenarioRunOut>(`/projects/${projectId}/scenario`, payload);

export const listScenarios = (projectId: string) =>
  api.get<ScenarioListItem[]>(`/projects/${projectId}/scenarios`);

export const getScenario = (projectId: string, scenarioId: string) =>
  api.get<ScenarioRunOut>(`/projects/${projectId}/scenarios/${scenarioId}`);

export const getScenarioDelta = (projectId: string, scenarioId: string) =>
  api.get<Record<string, unknown>>(`/projects/${projectId}/scenarios/${scenarioId}/delta`);

export const deleteScenario = (projectId: string, scenarioId: string) =>
  api.del<{ deleted: string }>(`/projects/${projectId}/scenarios/${scenarioId}`);
