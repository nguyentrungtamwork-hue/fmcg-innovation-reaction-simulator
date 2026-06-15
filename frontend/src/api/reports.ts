import { api } from "./client";
import type { ReportGenerateOut, ReportSummaryOut } from "../types/api";

export const generateReport = (projectId: string) =>
  api.post<ReportGenerateOut>(`/projects/${projectId}/report/generate`, {});

export const getReport = (projectId: string) =>
  api.get<ReportGenerateOut>(`/projects/${projectId}/report`);

export const getReportSummary = (projectId: string) =>
  api.get<ReportSummaryOut>(`/projects/${projectId}/report/summary`);

export const getReportMarkdown = (projectId: string) =>
  api.getText(`/projects/${projectId}/report/markdown`);
