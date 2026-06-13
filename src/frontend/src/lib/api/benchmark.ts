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

export async function detectGpu(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/gpu/detect");
}

export async function runGpuBenchmark(
  baseUrl: string,
  payload: {
    subject_id?: string;
    input_nii?: string;
    derivatives_dir?: string;
    tr?: number;
    freq_band?: number[];
    prefer_gpu?: boolean;
    require_gpu?: boolean;
    benchmark_compare_cpu_gpu?: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/gpu/benchmark", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}
