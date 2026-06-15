import { api } from "./client";
import type { BriefIn, BriefOut, OntologyOut } from "../types/api";

export const submitBrief = (projectId: string, payload: BriefIn) =>
  api.post<BriefOut>(`/projects/${projectId}/brief`, payload);

export const analyzeOntology = (projectId: string) =>
  api.post<OntologyOut>(`/projects/${projectId}/analyze`);

export const getOntology = (projectId: string) =>
  api.get<OntologyOut>(`/projects/${projectId}/ontology`);
