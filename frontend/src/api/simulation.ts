import { api } from "./client";
import type { EventsSummaryOut, SimulationRunIn, SimulationRunOut } from "../types/api";

export const runSimulation = (projectId: string, payload?: SimulationRunIn) =>
  api.post<SimulationRunOut>(`/projects/${projectId}/simulate`, payload ?? {});

export const getEventsSummary = (projectId: string) =>
  api.get<EventsSummaryOut>(`/projects/${projectId}/events/summary`);
