import { api } from "./client";
import type { QuestionIn, QuestionOut } from "../types/api";

export const askQuestion = (projectId: string, payload: QuestionIn) =>
  api.post<QuestionOut>(`/projects/${projectId}/ask`, payload);
