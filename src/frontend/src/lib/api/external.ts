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

export async function getExternalSmokeStatus(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/external-smoke/status");
}

export async function runExternalSmoke(
  baseUrl: string,
  payload: {
    target?: string;
    mode?: string;
    config_path?: string;
    approved?: boolean;
    approved_by?: string;
    dpabi_function?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/external-smoke/run", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

// === SessionDB ===
