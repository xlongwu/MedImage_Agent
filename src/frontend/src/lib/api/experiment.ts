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

export async function compareExperimentRuns(
  baseUrl: string,
  payload: {
    experiment_id: string;
    run_ids: string[];
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/compare", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function createExperimentRecord(
  baseUrl: string,
  payload: {
    experiment_id: string;
    name: string;
    run_ids: string[];
    tags: string[];
    notes: string;
  },
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/record", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export async function getExperimentComparison(baseUrl: string, experimentId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/experiments/comparison/${experimentId}`,
  );
}

export async function getExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/dashboard");
}

export async function getExperimentRecord(baseUrl: string, experimentId: string) {
  return requestJson<Record<string, unknown>>(baseUrl, `/api/experiments/record/${experimentId}`);
}

export async function getExperimentsRunIndex(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/run-index");
}

export async function refreshExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/experiments/dashboard/refresh", {
    method: "POST",
  });
}
