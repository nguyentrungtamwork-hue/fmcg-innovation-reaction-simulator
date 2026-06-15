import { api } from "./client";
import type {
  CompareIn,
  CompareOut,
  PortfolioOut,
  Scorecard,
  SnapshotCreate,
  SnapshotListItem,
  SnapshotOut,
} from "../types/api";

export const getPortfolio = () => api.get<PortfolioOut>("/portfolio");

export const getDecisionBoard = (projectIds?: string[]) => {
  const qs = projectIds && projectIds.length ? `?project_ids=${encodeURIComponent(projectIds.join(","))}` : "";
  return api.get<Record<string, any>>(`/portfolio/decision-board${qs}`);
};

export const getDecisionBoardMarkdown = () => api.getText(`/portfolio/decision-board/markdown`);

export const comparePortfolio = (payload: CompareIn) =>
  api.post<CompareOut>("/portfolio/compare", payload);

export const getScorecard = (projectId: string) =>
  api.get<Scorecard>(`/projects/${projectId}/scorecard`);

export const createSnapshot = (projectId: string, payload: SnapshotCreate) =>
  api.post<SnapshotOut>(`/projects/${projectId}/snapshots`, payload);

export const listSnapshots = (projectId: string) =>
  api.get<SnapshotListItem[]>(`/projects/${projectId}/snapshots`);

export const getSnapshot = (projectId: string, snapshotId: string) =>
  api.get<SnapshotOut>(`/projects/${projectId}/snapshots/${snapshotId}`);

export const deleteSnapshot = (projectId: string, snapshotId: string) =>
  api.del<{ deleted: string }>(`/projects/${projectId}/snapshots/${snapshotId}`);
