import { api } from "./client";

export interface SampleSummary {
  sample_id: string;
  name: string;
  category: string;
  short_description: string;
  target_consumer: string;
  key_claim: string;
  price_positioning: string;
  channels: string[];
  known_risks: string[];
  recommended_demo_path: string[];
  what_to_observe: string;
}

export interface SampleDetail extends SampleSummary {
  sample_brief_text: string;
  structured: Record<string, unknown>;
}

export interface SampleLoadResult {
  project_id: string;
  status: string;
  completed_steps: string[];
  next_url: string;
  warnings: string[];
}

export const getSamples = () => api.get<{ samples: SampleSummary[] }>("/system/samples");

export const getSample = (sampleId: string) => api.get<SampleDetail>(`/system/samples/${sampleId}`);

export const loadSample = (
  sampleId: string,
  opts: { project_name?: string; run_pipeline?: boolean } = {}
) => api.post<SampleLoadResult>(`/system/samples/${sampleId}/load`, opts);
