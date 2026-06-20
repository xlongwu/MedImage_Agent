import { getJson, postJson } from "./client";

export type AdvisorStatus = {
  llm_enabled?: boolean;
  config?: {
    provider?: string;
    model?: string;
  };
};

export type AdvisorResult = Record<string, unknown> & {
  fallback?: boolean;
  error?: string;
};

export function getAdvisorStatus(baseUrl: string): Promise<AdvisorStatus> {
  return getJson<AdvisorStatus>("/api/advisor/status", { baseUrl });
}

export function runAdvisor(
  baseUrl: string,
  advisorType: string,
  payload: unknown,
): Promise<AdvisorResult> {
  return postJson<AdvisorResult>(`/api/advisor/${encodeURIComponent(advisorType)}`, payload, {
    baseUrl,
  });
}
