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

export async function generateQcDashboardReport(
  baseUrl: string,
  projectId: string,
  options?: { cacheMode?: "off" | "prefer" | "refresh" },
) {
  const params = new URLSearchParams();
  if (options?.cacheMode && options.cacheMode !== "off") {
    params.set("cache", options.cacheMode);
  }
  const qs = params.toString();
  return requestJson<QcDashboardReportResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/qc-dashboard/report${qs ? "?" + qs : ""}`,
    { method: "POST" },
  );
}

export async function getDatasetEvaluationReport(baseUrl: string) {
  return requestJson<DatasetEvaluationReport>(
    baseUrl,
    "/api/reports/dataset-evaluation"
  );
}

export async function getImageManifestReport(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/images/manifest?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function getImageValidationReport(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/images/validation?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function getLatestQcDashboardReport(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<QcDashboardReportResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/qc-dashboard/report/latest`,
  );
}

export async function getQcDashboardFingerprint(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<QcDashboardFingerprintResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/qc-dashboard/fingerprint`,
  );
}
