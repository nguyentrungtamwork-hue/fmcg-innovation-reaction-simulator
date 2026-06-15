import { api } from "./client";
import type { OverviewOut } from "../types/api";

export const getOverview = (projectId: string) =>
  api.get<OverviewOut>(`/projects/${projectId}/overview`);
