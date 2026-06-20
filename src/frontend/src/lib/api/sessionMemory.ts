import type {
  AgentExecuteRequest,
  AgentPlanRequest,
  AgentRun,
  BidsValidationResponse,
  ConversionDryRunRequest,
  ConversionDryRunResponse,
  BoldReferenceReadinessResponse,
  DataReadinessResponse,
  MotionMetricsDraftResponse,
  MotionQcReadinessResponse,
  SpmRealignDryRunResponse,
  SpmRealignWrapperSkeletonResponse,
  NiftiQcSnapshotResponse,
  NiftiThumbnailResponse,
  QcDashboardReportResponse,
  QcDashboardFingerprintResponse,
  RsfmriQcPlanningReportResponse,
  PipelinePreset,
  PipelinePresetInstantiateResponse,
  DatasetEvaluationReport,
  ExecuteReviewedResponse,
  ProjectCreateRequest,
  ProjectCreateResponse,
  ProjectRunArtifactsResponse,
  ProjectRunDetailResponse,
  ProjectRunEventsResponse,
  ProjectRunLogsResponse,
  ReviewedPlanRecord,
  RunArtifactPreviewResponse,
  RunLinkRecord,
  RunInspection,
  ProjectRunStateTimelineResponse,
} from "../../types";
import { requestJson } from "./legacyCore";

export async function getSessionRuns(baseUrl: string, status?: string) {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson<Record<string, unknown>>(baseUrl, `/api/sessions/runs${params}`);
}

export async function postSessionIndex(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/sessions/index", { method: "POST" });
}

export async function querySessions(baseUrl: string, q: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/sessions/query?q=${encodeURIComponent(q)}&limit=50`,
  );
}

// === Tool Catalog ===
