import { api } from "./client";
import type { AgentGenerateOut, AgentOut, AgentSummaryOut } from "../types/api";

export const generateAgents = (projectId: string, payload?: Record<string, unknown>) =>
  api.post<AgentGenerateOut>(`/projects/${projectId}/agents/generate`, payload ?? {});

export const getAgentsSummary = (projectId: string) =>
  api.get<AgentSummaryOut>(`/projects/${projectId}/agents/summary`);

export const listAgents = (projectId: string, agentType?: string) =>
  api.get<AgentOut[]>(
    `/projects/${projectId}/agents${agentType ? `?agent_type=${encodeURIComponent(agentType)}` : ""}`
  );

export const getAgent = (projectId: string, agentId: string) =>
  api.get<AgentOut>(`/projects/${projectId}/agents/${agentId}`);
