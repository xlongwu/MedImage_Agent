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

export async function createImportDiagnosticsPackage(
  baseUrl: string,
  projectId = "brain-tumor-study",
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package?project_id=${encodeURIComponent(projectId)}`,
    { method: "POST" },
  );
}

export async function diagnoseRun(baseUrl: string, runId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/runs/${encodeURIComponent(runId)}/diagnosis`,
  );
}

export async function getDatasetImportHistory(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/imports?project_id=${encodeURIComponent(projectId)}`,
  );
}

export async function getLatestImportDiagnosticsPackage(
  baseUrl: string,
  projectId = "brain-tumor-study",
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package/latest?project_id=${encodeURIComponent(projectId)}`,
  );
}

export async function getRetryRun(baseUrl: string, retryRunId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/retry-runs/${encodeURIComponent(retryRunId)}`,
  );
}

export async function inspectRun(baseUrl: string, runId: string) {
  return requestJson<RunInspection>(baseUrl, `/api/runs/${encodeURIComponent(runId)}`);
}

export async function listRuns(baseUrl: string) {
  return requestJson<{ ok: boolean; runs: Array<Record<string, unknown>> }>(baseUrl, "/api/runs");
}

export async function readLog(baseUrl: string, path: string) {
  return requestJson<{
    ok: boolean;
    path: string;
    relative_path: string;
    content: string;
    size_bytes: number;
  }>(baseUrl, `/api/logs/read?path=${encodeURIComponent(path)}`);
}

export async function retryDryRun(baseUrl: string, runId: string, retryRunId?: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/dry-run", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, retry_run_id: retryRunId }),
  });
}

export async function retryExecute(
  baseUrl: string,
  runId: string,
  projectConfigPath: string,
  retryRunId?: string,
  approved = false,
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/execute", {
    method: "POST",
    body: JSON.stringify({
      run_id: runId,
      project_config_path: projectConfigPath,
      retry_run_id: retryRunId,
      approved,
    }),
  });
}

export async function verifyImportDiagnosticsPackage(
  baseUrl: string,
  projectId = "brain-tumor-study",
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package/verify?project_id=${encodeURIComponent(projectId)}`,
    { method: "POST" },
  );
}
