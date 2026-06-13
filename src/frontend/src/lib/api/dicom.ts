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

export async function getDicomPreflight(
  baseUrl: string,
  projectId = "brain-tumor-study",
  path = "data/DemoData",
  maxFiles = 2000
) {
  const params = new URLSearchParams({
    project_id: projectId,
    max_files: String(maxFiles)
  });
  if (path.trim()) {
    params.set("path", path.trim());
  }
  return requestJson<Record<string, unknown>>(baseUrl, `/api/datasets/dicom/preflight?${params.toString()}`);
}

export async function getProjectBidsValidation(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<BidsValidationResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/bids-validation`
  );
}

export async function getProjectDataReadiness(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<DataReadinessResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/data-readiness`
  );
}

export async function getProjectDicomConversionReleaseReadiness(
  baseUrl: string,
  projectId: string,
  conversionRunId: string,
) {
  return requestJson<import("../../types").DicomConversionReleaseReadinessReport>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/release-readiness/${encodeURIComponent(conversionRunId)}`,
  );
}

export async function persistProjectDicomConversionPlan(
  baseUrl: string,
  projectId: string,
  body: Record<string, unknown>,
) {
  return requestJson<import("../../types").DicomConversionPlanPersistenceResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/approval/persist-plan`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runConversionDryRun(
  baseUrl: string,
  projectId: string,
  payload?: ConversionDryRunRequest,
) {
  return requestJson<ConversionDryRunResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/dry-run`,
    { method: "POST", body: JSON.stringify(payload ?? {}) },
  );
}

export async function runProjectDicomConversionExecute(
  baseUrl: string,
  projectId: string,
  body: Record<string, unknown>,
) {
  return requestJson<import("../../types").DicomConversionPublicExecutionResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/execute`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runProjectDicomConversionPreflight(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<import("../../types").DicomConversionPreflightResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/preflight`,
    { method: "POST" },
  );
}
