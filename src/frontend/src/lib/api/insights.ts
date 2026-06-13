import { getJson, postJson } from "./client";

export interface InsightsSummary {
  total_runs?: number;
  success_rate?: number;
  failure_rate?: number;
  avg_duration_seconds?: number;
  total_errors_logged?: number;
}

export interface InsightTrendPoint {
  run_id: string;
  status: "SUCCESS" | "PARTIAL" | "FAILED" | string;
}

export interface InsightNodeTiming {
  node_id: string;
  avg_duration?: number;
  count?: number;
  failure_rate?: number;
}

export interface InsightFailedNode {
  node_id: string;
  failed?: number;
  total?: number;
  failure_rate?: number;
}

export interface InsightErrorCategory {
  category: string;
  count?: number;
}

export interface InsightsDashboard {
  summary?: InsightsSummary;
  recent_trend?: InsightTrendPoint[];
  slowest_nodes?: InsightNodeTiming[];
  most_failed_nodes?: InsightFailedNode[];
  top_error_categories?: InsightErrorCategory[];
}

export function getInsights(baseUrl: string): Promise<InsightsDashboard> {
  return getJson<InsightsDashboard>("/api/insights", { baseUrl });
}

export function buildInsights(baseUrl: string): Promise<Record<string, unknown>> {
  return postJson<Record<string, unknown>>("/api/insights/build", {}, { baseUrl });
}
