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

export async function createPreprocessingRun(
  baseUrl: string, projectId: string,
  body: { preprocessing_input_dir?: string; confirm_use_converted_input?: boolean; confirm_no_rawdata_modification?: boolean; confirm_python_only_execution?: boolean; confirm_no_spm_matlab?: boolean },
) {
  return requestJson<import("../../types").PreprocessingRunCreateResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function executeNuisanceRegressionSandbox(
  baseUrl: string, projectId: string, preprocessingRunId: string,
  body: { dry_run_id: string; functional_input_dir?: string; confirm_sandbox_copy?: boolean; confirm_no_rawdata_modification?: boolean; confirm_previous_stage_readonly?: boolean; confirm_nuisance_regression_only?: boolean; confirm_no_full_preprocessing?: boolean; confirm_research_use_only?: boolean },
) {
  return requestJson<import("../../types").NuisanceSandboxExecutionResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/nuisance-regression/execute-sandbox`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function executePreprocessingPythonPreflight(
  baseUrl: string, projectId: string, preprocessingRunId: string,
) {
  return requestJson<import("../../types").PreprocessingRunExecuteResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/execute-python-preflight`,
    { method: "POST" },
  );
}

export async function executeSpmSandboxSliceTimingRealign(
  baseUrl: string, projectId: string, preprocessingRunId: string,
  body: { dry_run_id: string; preprocessing_input_dir?: string; confirm_sandbox_copy?: boolean; confirm_no_rawdata_modification?: boolean; confirm_slice_timing_realign_only?: boolean; confirm_no_full_preprocessing?: boolean; confirm_research_use_only?: boolean },
) {
  return requestJson<import("../../types").SpmSandboxExecutionResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/spm/slice-timing-realign/execute-sandbox`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function generateMotionMetricsDraft(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<MotionMetricsDraftResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/motion-qc/metrics-draft`,
    { method: "POST" },
  );
}

export async function generateSpmRealignWrapperSkeleton(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<SpmRealignWrapperSkeletonResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/spm-realign/wrapper-skeleton`,
    { method: "POST" },
  );
}

export async function getPreprocessingPipelineReport(
  baseUrl: string, projectId: string, preprocessingRunId: string,
) {
  return requestJson<Record<string, unknown>>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/report`,
  );
}

export async function getPreprocessingPipelineValidation(
  baseUrl: string, projectId: string, preprocessingRunId: string,
) {
  return requestJson<Record<string, unknown>>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/validation`,
  );
}

export async function getPreprocessingPlanPreview(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<import("../../types").PreprocessingPlanPreviewResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/preprocessing/plan/preview`,
    { method: "POST" },
  );
}

export async function getPreprocessingRunStatus(
  baseUrl: string, projectId: string, preprocessingRunId: string,
) {
  return requestJson<import("../../types").PreprocessingRunStatusResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}`,
  );
}

export async function getProjectBoldReferenceReadiness(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<BoldReferenceReadinessResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/bold-reference/readiness`
  );
}

export async function getProjectMotionQcReadiness(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<MotionQcReadinessResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/motion-qc/readiness`
  );
}

export async function getProjectNiftiQcSnapshot(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<NiftiQcSnapshotResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/nifti-qc/snapshot`,
  );
}

export async function getProjectNiftiThumbnail(
  baseUrl: string,
  projectId: string,
  imageId: string,
  options?: {
    view?: "axial" | "coronal" | "sagittal" | "all";
    volumeIndex?: number;
    size?: number;
  },
) {
  const params = new URLSearchParams();
  if (options?.view) params.set("view", options.view);
  if (options?.volumeIndex !== undefined) params.set("volume_index", String(options.volumeIndex));
  if (options?.size !== undefined) params.set("size", String(options.size));
  const qs = params.toString();
  return requestJson<NiftiThumbnailResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/nifti-qc/images/${encodeURIComponent(imageId)}/thumbnail${qs ? "?" + qs : ""}`,
  );
}

export async function registerConvertedPreprocessingInput(
  baseUrl: string,
  projectId: string,
  body: { conversion_run_id: string; converted_bids_dir?: string; mode?: string; confirm_rawdata_readonly?: boolean; confirm_use_converted_outputs?: boolean },
) {
  return requestJson<import("../../types").PreprocessingInputRegistrationResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/preprocessing/input/register-converted`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function registerSandboxSpmOutputs(
  baseUrl: string, projectId: string, preprocessingRunId: string,
  body: { execution_id: string; confirm_sandbox_outputs?: boolean; confirm_rawdata_readonly?: boolean; confirm_converted_input_readonly?: boolean; confirm_no_additional_execution?: boolean; confirm_use_as_next_stage_input?: boolean },
) {
  return requestJson<import("../../types").StageOutputRegistrationResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/stage-outputs/register-sandbox-spm`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runFilteringDryRun(
  baseUrl: string, projectId: string, preprocessingRunId: string,
  body: { functional_input_dir?: string; low_cut_hz?: number; high_cut_hz?: number; confirm_dry_run_only?: boolean },
) {
  return requestJson<import("../../types").FilteringDryRunResponse>(
    baseUrl, `/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/temporal-filtering/dry-run`,
    { method: "POST", body: JSON.stringify(body) },
  );
}

export async function runSpmRealignDryRun(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<SpmRealignDryRunResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/spm-realign/dry-run`,
    { method: "POST" },
  );
}
