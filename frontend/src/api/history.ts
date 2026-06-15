import { api } from "./client";
import type {
  DecisionCreate,
  DecisionOut,
  DiffRequest,
  SnapshotDiffOut,
  TimelineOut,
} from "../types/api";

export const snapshotDiff = (projectId: string, payload: DiffRequest) =>
  api.post<SnapshotDiffOut>(`/projects/${projectId}/snapshots/diff`, payload);

export const createDecision = (projectId: string, payload: DecisionCreate) =>
  api.post<DecisionOut>(`/projects/${projectId}/decisions`, payload);

export const listDecisions = (projectId: string) =>
  api.get<DecisionOut[]>(`/projects/${projectId}/decisions`);

export const deleteDecision = (projectId: string, entryId: string) =>
  api.del<{ deleted: string }>(`/projects/${projectId}/decisions/${entryId}`);

export const getTimeline = (projectId: string) =>
  api.get<TimelineOut>(`/projects/${projectId}/timeline`);
