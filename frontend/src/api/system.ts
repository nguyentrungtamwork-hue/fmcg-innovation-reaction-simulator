import { api } from "./client";
import type { AppLogList, Diagnostics, ReadyZ, SystemStatus } from "../types/api";

export const getSystemStatus = () => api.get<SystemStatus>("/system/status");

// /readyz lives at the server root, not under /api/v1 · strip the api prefix.
export const getReadyz = () => {
  const root = api.baseUrl.replace(/\/api\/v1$/, "");
  return fetch(`${root}/readyz`).then((r) => r.json() as Promise<ReadyZ>);
};

export const getDiagnostics = () => api.get<Diagnostics>("/system/diagnostics");

export interface SystemLogsQuery {
  level?: string;
  event_type?: string;
  request_id?: string;
  project_id?: string;
  limit?: number;
}

export const getSystemLogs = (q: SystemLogsQuery = {}) => {
  const params = new URLSearchParams();
  if (q.level) params.set("level", q.level);
  if (q.event_type) params.set("event_type", q.event_type);
  if (q.request_id) params.set("request_id", q.request_id);
  if (q.project_id) params.set("project_id", q.project_id);
  if (q.limit != null) params.set("limit", String(q.limit));
  const qs = params.toString();
  return api.get<AppLogList>(`/system/logs${qs ? `?${qs}` : ""}`);
};

export const getRecentErrors = () => api.get<AppLogList>("/system/logs/recent-errors");
