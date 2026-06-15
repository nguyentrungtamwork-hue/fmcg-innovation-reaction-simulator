import { api } from "./client";
import type { StudioState } from "../types/api";

export const getStudioState = (projectId: string) =>
  api.get<StudioState>(`/projects/${projectId}/studio/state`);
