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

export async function createProjectFromDirectory(
  baseUrl: string,
  payload: ProjectCreateRequest
): Promise<ProjectCreateResponse> {
  return requestJson<ProjectCreateResponse>(baseUrl, "/api/projects/create", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getProjectRun(
  baseUrl: string,
  projectId: string,
  runId: string
) {
  return requestJson<ProjectRunDetailResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}`
  );
}

export async function getProjectRunArtifact(
  baseUrl: string,
  projectId: string,
  runId: string,
  artifactId: string
) {
  return requestJson<RunArtifactPreviewResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}/artifacts/${encodeURIComponent(artifactId)}`
  );
}

export async function getProjectRunStateTimeline(
  baseUrl: string,
  projectId: string,
  runId: string,
) {
  return requestJson<ProjectRunStateTimelineResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}/state-timeline`,
  );
}

export async function listProjectRunArtifacts(
  baseUrl: string,
  projectId: string,
  runId: string
) {
  return requestJson<ProjectRunArtifactsResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}/artifacts`
  );
}

export async function listProjectRunEvents(
  baseUrl: string,
  projectId: string,
  runId: string,
) {
  return requestJson<ProjectRunEventsResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}/events`
  );
}

export async function listProjectRunLinks(
  baseUrl: string,
  projectId: string,
  reviewedPlanId?: string
) {
  const query = reviewedPlanId
    ? `?reviewed_plan_id=${encodeURIComponent(reviewedPlanId)}`
    : "";
  return requestJson<{ ok: boolean; project_id: string; runs: RunLinkRecord[] }>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs${query}`
  );
}

export async function listProjectRunLogs(
  baseUrl: string,
  projectId: string,
  runId: string,
  options?: { maxBytes?: number; includeContent?: boolean },
) {
  const params = new URLSearchParams();
  if (options?.maxBytes !== undefined) {
    params.set("max_bytes", String(options.maxBytes));
  }
  if (options?.includeContent !== undefined) {
    params.set("include_content", String(options.includeContent));
  }
  const query = params.size ? `?${params.toString()}` : "";
  return requestJson<ProjectRunLogsResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/runs/${encodeURIComponent(runId)}/logs${query}`
  );
}

export async function listProjectRuns(
  baseUrl: string,
  projectId: string,
  reviewedPlanId?: string
) {
  return listProjectRunLinks(baseUrl, projectId, reviewedPlanId);
}
