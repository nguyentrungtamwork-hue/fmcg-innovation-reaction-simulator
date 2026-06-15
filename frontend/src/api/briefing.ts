import { api } from "./client";
import type {
  BriefingAskIn,
  BriefingAskOut,
  BriefingGenerateIn,
  BriefingOut,
  BoardSummaryOut,
  TailorIn,
  TailorOut,
} from "../types/api";

export const generateBriefing = (projectId: string, payload: BriefingGenerateIn) =>
  api.post<BriefingOut>(`/projects/${projectId}/briefing/generate`, payload);

export const getBriefing = (projectId: string) =>
  api.get<BriefingOut>(`/projects/${projectId}/briefing`);

export const askBriefing = (projectId: string, payload: BriefingAskIn) =>
  api.post<BriefingAskOut>(`/projects/${projectId}/briefing/ask`, payload);

export const tailorBriefing = (projectId: string, payload: TailorIn) =>
  api.post<TailorOut>(`/projects/${projectId}/briefing/tailor`, payload);

export const generateBoardSummary = (projectId: string) =>
  api.post<BoardSummaryOut>(`/projects/${projectId}/briefing/board-summary`, {});
