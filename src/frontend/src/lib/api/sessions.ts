import { getJson, postJson } from "./client";

export interface SessionStats {
  total_runs?: number;
  success_runs?: number;
  total_nodes?: number;
  failed_nodes?: number;
  total_errors?: number;
}

export interface SessionRunSummary {
  run_id: string;
  pipeline_id?: string;
  status?: string;
  started_at?: string;
  duration_seconds?: number;
}

export interface SessionRunsResponse {
  ok?: boolean;
  stats?: SessionStats;
  runs?: SessionRunSummary[];
}

export interface SessionSearchResult {
  record_type?: string;
  title?: string;
  snippet?: string;
}

export interface SessionQueryResponse {
  ok?: boolean;
  results?: SessionSearchResult[];
}

export function getSessionRuns(baseUrl: string, status?: string): Promise<SessionRunsResponse> {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return getJson<SessionRunsResponse>(`/api/sessions/runs${params}`, { baseUrl });
}

export function postSessionIndex(baseUrl: string): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>("/api/sessions/index", {}, { baseUrl });
}

export function querySessions(baseUrl: string, q: string): Promise<SessionQueryResponse> {
  return getJson<SessionQueryResponse>(`/api/sessions/query?q=${encodeURIComponent(q)}&limit=50`, { baseUrl });
}
