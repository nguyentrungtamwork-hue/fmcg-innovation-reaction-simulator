import { api } from "./client";
import type { EventFilters, EventOut } from "../types/api";

export function listEvents(projectId: string, filters: EventFilters = {}): Promise<EventOut[]> {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") params.append(k, String(v));
  });
  const qs = params.toString();
  return api.get<EventOut[]>(`/projects/${projectId}/events${qs ? `?${qs}` : ""}`);
}

export const getEvent = (projectId: string, eventId: string) =>
  api.get<EventOut>(`/projects/${projectId}/events/${eventId}`);
