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
} from "./types";

declare global {
  interface Window {
    __MEDIMAGE_DESKTOP_CONFIG__?: {
      backendBaseUrl: string;
    };
    MEDIMAGE_API_BASE_URL?: string;
    MEDIMAGE_DESKTOP_RUNTIME?: {
      apiBaseUrl: string;
      platform: string;
      backend: {
        managed: boolean;
        ready: boolean;
        status: string;
        pid: number | null;
        logPath: string;
        executablePath?: string;
        port?: number | null;
      };
    };
    medimageDesktop?: {
      runtime: Window["MEDIMAGE_DESKTOP_RUNTIME"];
      getBackendBaseUrl?: () => Promise<string>;
      getRuntime?: () => Promise<Window["MEDIMAGE_DESKTOP_RUNTIME"]>;
    };
  }
}

export const DEFAULT_API_BASE =
  window.__MEDIMAGE_DESKTOP_CONFIG__?.backendBaseUrl ||
  window.MEDIMAGE_API_BASE_URL ||
  window.MEDIMAGE_DESKTOP_RUNTIME?.apiBaseUrl ||
  import.meta.env.VITE_API_BASE_URL ||
  "http://127.0.0.1:8000";

async function requestJson<T>(
  baseUrl: string,
  path: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers || {})
    },
    ...options
  });

  const text = await response.text();
  let payload: unknown;

  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { ok: false, error: text };
  }

  if (!response.ok) {
    const detailValue =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? (payload as { detail: unknown }).detail
        : text;
    const detail =
      typeof detailValue === "string"
        ? detailValue
        : JSON.stringify(detailValue, null, 2);
    throw new Error(detail || `HTTP ${response.status}`);
  }

  return payload as T;
}

export async function getHealth(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/health");
}

export async function getProjectConfig(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/project-config");
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

export async function getProjectBidsValidation(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<BidsValidationResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/bids-validation`
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

export async function getProjectNiftiQcSnapshot(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<NiftiQcSnapshotResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/nifti-qc/snapshot`,
  );
}

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

export async function generateRsfmriQcPlanningReport(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<RsfmriQcPlanningReportResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/rsfmri-qc/planning-report`,
    { method: "POST" },
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

export async function runProjectDicomConversionPreflight(
  baseUrl: string,
  projectId: string,
) {
  return requestJson<import("./types").DicomConversionPreflightResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/conversion/preflight`,
    { method: "POST" },
  );
}

export async function listPipelinePresets(baseUrl: string) {
  return requestJson<{ ok: boolean; presets: PipelinePreset[] }>(
    baseUrl,
    "/api/pipeline-presets",
  );
}

export async function getPipelinePreset(baseUrl: string, presetId: string) {
  return requestJson<{ ok: boolean; preset: PipelinePreset }>(
    baseUrl,
    `/api/pipeline-presets/${encodeURIComponent(presetId)}`,
  );
}

export async function instantiatePipelinePreset(
  baseUrl: string,
  projectId: string,
  presetId: string,
  payload?: Record<string, unknown>,
) {
  return requestJson<PipelinePresetInstantiateResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/pipeline-presets/${encodeURIComponent(presetId)}/instantiate`,
    { method: "POST", body: JSON.stringify(payload ?? {}) },
  );
}

export async function createProjectFromDirectory(
  baseUrl: string,
  payload: ProjectCreateRequest
): Promise<ProjectCreateResponse> {
  return requestJson<ProjectCreateResponse>(baseUrl, "/api/projects/create", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function saveReviewedPlan(
  baseUrl: string,
  projectId: string,
  payload: {
    plan: Record<string, unknown>;
    project_config_path: string;
    validation?: Record<string, unknown>;
    goal?: string;
    provider?: string;
    status?: string;
    warnings?: string[];
  }
) {
  return requestJson<{ ok: boolean; reviewed_plan: ReviewedPlanRecord }>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/plans`,
    { method: "POST", body: JSON.stringify(payload) }
  );
}

export async function listProjectReviewedPlans(baseUrl: string, projectId: string) {
  return requestJson<{
    ok: boolean;
    project_id: string;
    reviewed_plans: ReviewedPlanRecord[];
  }>(baseUrl, `/api/projects/${encodeURIComponent(projectId)}/plans`);
}

export async function getProjectReviewedPlan(
  baseUrl: string,
  projectId: string,
  reviewedPlanId: string
) {
  return requestJson<{ ok: boolean; reviewed_plan: ReviewedPlanRecord }>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/plans/${encodeURIComponent(reviewedPlanId)}`
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

export async function listProjectRuns(
  baseUrl: string,
  projectId: string,
  reviewedPlanId?: string
) {
  return listProjectRunLinks(baseUrl, projectId, reviewedPlanId);
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

export async function listPipelines(baseUrl: string) {
  return requestJson<{ ok: boolean; pipelines: string[] }>(
    baseUrl,
    "/api/pipelines"
  );
}

export async function getExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/dashboard"
  );
}

export async function refreshExperimentDashboard(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/dashboard/refresh",
    { method: "POST" }
  );
}

export async function getPipeline(baseUrl: string, pipelineName: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/pipelines/${encodeURIComponent(pipelineName)}`
  );
}

export async function createAgentPlan(
  baseUrl: string,
  payload: AgentPlanRequest
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/agent/plan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiSubjectSmooth(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    subject_id?: string;
    input_bold?: string;
    function_name?: string;
    fwhm?: number[];
    approved?: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/subject-smooth", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function generateDpabiSubjectWrapperReport(
  baseUrl: string,
  payload: {
    project_config_path?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/subject-wrapper-report", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function executeAgentPlan(
  baseUrl: string,
  payload: AgentExecuteRequest
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/agent/execute", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAgentRun(baseUrl: string, agentRunId: string) {
  return requestJson<AgentRun>(
    baseUrl,
    `/api/agent-runs/${encodeURIComponent(agentRunId)}`
  );
}

export async function getDatasetEvaluationReport(baseUrl: string) {
  return requestJson<DatasetEvaluationReport>(
    baseUrl,
    "/api/reports/dataset-evaluation"
  );
}

export async function listRuns(baseUrl: string) {
  return requestJson<{ ok: boolean; runs: Array<Record<string, unknown>> }>(
    baseUrl,
    "/api/runs"
  );
}

export async function inspectRun(baseUrl: string, runId: string) {
  return requestJson<RunInspection>(
    baseUrl,
    `/api/runs/${encodeURIComponent(runId)}`
  );
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

export async function diagnoseRun(baseUrl: string, runId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/runs/${encodeURIComponent(runId)}/diagnosis`
  );
}

export async function retryDryRun(
  baseUrl: string,
  runId: string,
  retryRunId?: string
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/dry-run", {
    method: "POST",
    body: JSON.stringify({ run_id: runId, retry_run_id: retryRunId })
  });
}

export async function retryExecute(
  baseUrl: string,
  runId: string,
  projectConfigPath: string,
  retryRunId?: string,
  approved = false
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/retry/execute", {
    method: "POST",
    body: JSON.stringify({
      run_id: runId,
      project_config_path: projectConfigPath,
      retry_run_id: retryRunId,
      approved
    })
  });
}

export async function getRetryRun(baseUrl: string, retryRunId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/retry-runs/${encodeURIComponent(retryRunId)}`
  );
}

export async function createSchedulerPlan(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/scheduler/plan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

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

export async function runDpabiCapability(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/capability", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiScaffold(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/scaffold", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiInputManifest(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    dataset_index?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/input-manifest", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiPreflight(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    dataset_index?: string;
    capabilities_path?: string;
    manifest_path?: string;
    wrapper_config_template_path?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/preflight", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiRunPlan(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    capabilities_path?: string;
    manifest_path?: string;
    preflight_path?: string;
    params_path?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/run-plan", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiSandboxSmoke(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    approved?: boolean;
    approved_by?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/sandbox-smoke", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiSignatureProbe(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/signature-probe", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function generateDpabiWrapperContracts(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/wrapper-contracts", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function runDpabiSingleFunctionSandbox(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    function_name?: string;
    approved?: boolean;
    approved_by?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/single-function-sandbox", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function generateDpabiWrapperValidationMatrix(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    signatures_path?: string;
    contracts_path?: string;
    sandbox_result_path?: string;
    subject_wrapper_summary_path?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/wrapper-validation-matrix", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function generateDpabiTemplateLibrary(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/template-library", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function listDpabiTemplates(
  baseUrl: string,
  workDir: string = "./work"
) {
  return requestJson<Record<string, unknown>>(baseUrl, `/api/dpabi/templates?work_dir=${encodeURIComponent(workDir)}`, {
    method: "GET"
  });
}

export async function instantiateDpabiTemplate(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    template_id?: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name?: string | null;
    fwhm?: number[] | null;
    subjects?: string[] | null;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/template-instantiate", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function executeDpabiTemplate(
  baseUrl: string,
  payload: {
    project_config_path?: string;
    work_dir?: string;
    log_dir?: string;
    instance_id?: string;
    approved?: boolean;
    approved_by?: string;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/dpabi/template-execute", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getDpabiTemplateWizardOptions(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/options"
  );
}

export async function previewDpabiTemplateWizard(
  baseUrl: string,
  payload: {
    template_id: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name: string;
    fwhm: number[];
    subjects: string[];
    scheduler: Record<string, unknown>;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/preview",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function createDpabiTemplateWizardInstance(
  baseUrl: string,
  payload: {
    template_id: string;
    instance_id?: string | null;
    run_id?: string | null;
    function_name: string;
    fwhm: number[];
    subjects: string[];
    scheduler: Record<string, unknown>;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/create",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getDpabiTemplateWizardLatest(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/dpabi/template-wizard/latest"
  );
}

export async function getExperimentsRunIndex(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/run-index"
  );
}

export async function createExperimentRecord(
  baseUrl: string,
  payload: {
    experiment_id: string;
    name: string;
    run_ids: string[];
    tags: string[];
    notes: string;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/record",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function compareExperimentRuns(
  baseUrl: string,
  payload: {
    experiment_id: string;
    run_ids: string[];
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/experiments/compare",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getExperimentRecord(baseUrl: string, experimentId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/experiments/record/${experimentId}`
  );
}

export async function getExperimentComparison(baseUrl: string, experimentId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/experiments/comparison/${experimentId}`
  );
}

export async function getArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/artifacts");
}

export async function refreshArtifacts(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/artifacts/refresh",
    { method: "POST" }
  );
}

export async function previewArtifact(baseUrl: string, path: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/artifacts/preview",
    {
      method: "POST",
      body: JSON.stringify({ path })
    }
  );
}

export async function listBundles(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/bundles");
}

export async function createBundle(
  baseUrl: string,
  payload: {
    bundle_id?: string;
    include_logs?: boolean;
    include_reports?: boolean;
    include_artifact_index?: boolean;
    max_file_size_bytes?: number;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/bundles/create",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function inspectBundle(baseUrl: string, bundleId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/bundles/${encodeURIComponent(bundleId)}`
  );
}

export async function getReleaseReadinessV1(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/release/readiness");
}

export async function getRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/preprocessing-plan"
  );
}

export async function refreshRsfmriPreprocessingPlan(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/preprocessing-plan/refresh",
    { method: "POST" }
  );
}

export async function runRsfmriSpmRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-realign-motion-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSpmRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-realign-motion-qc"
  );
}

export async function runRsfmriSpmSliceTiming(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-slice-timing/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSpmSliceTiming(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/spm-slice-timing"
  );
}

export async function runRsfmriStRealignMotionQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/st-realign-motion-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriStRealignMotionQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/st-realign-motion-qc"
  );
}

export async function runRsfmriCoregistrationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/coregistration-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriCoregistrationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/coregistration-qc"
  );
}

export async function runRsfmriSegmentationTissueQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/segmentation-tissue-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriSegmentationTissueQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/segmentation-tissue-qc"
  );
}

export async function runRsfmriNormalizationQc(
  baseUrl: string,
  payload: {
    project_config_path: string;
    pipeline_path: string;
    approved: boolean;
  }
) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    "/api/rsfmri/normalization-qc/run",
    {
      method: "POST",
      body: JSON.stringify(payload)
    }
  );
}

export async function getRsfmriNormalizationQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/normalization-qc");
}

export async function runRsfmriSmoothingQc(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/smoothing-qc/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriSmoothingQc(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/smoothing-qc");
}

export async function runRsfmriNuisanceRegression(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/nuisance-regression/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriNuisanceRegression(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/nuisance-regression");
}

export async function runRsfmriTemporalFiltering(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/temporal-filtering/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriTemporalFiltering(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/temporal-filtering");
}

export async function runRsfmriAlffFalff(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/alff-falff/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriAlffFalff(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/alff-falff");
}

export async function runRsfmriReho(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/reho/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriReho(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/reho");
}

export async function runRsfmriFunctionalConnectivity(baseUrl: string, payload: { project_config_path: string; pipeline_path: string; approved: boolean }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/functional-connectivity/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriFunctionalConnectivity(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/functional-connectivity");
}

export async function runRsfmriGroupSummary(baseUrl: string, payload: { project_config_path: string; pipeline_path: string }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/group-summary/run", { method: "POST", body: JSON.stringify(payload) });
}

export async function getRsfmriGroupSummary(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/group-summary");
}

export async function runRsfmriReportExport(baseUrl: string, payload: { project_config_path: string; pipeline_path: string }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-export/run", { method: "POST", body: JSON.stringify(payload) });
}
export async function getLatestRsfmriReportExport(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-export/latest");
}
export async function listRsfmriReportExports(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-export/list");
}

export async function runRsfmriReportValidation(baseUrl: string, payload: { project_config_path: string; pipeline_path: string }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validator/run", { method: "POST", body: JSON.stringify(payload) });
}
export async function getLatestRsfmriReportValidation(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validator/latest");
}
export async function listRsfmriReportValidations(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/rsfmri/report-validator/list");
}

export async function runReleaseReadiness(baseUrl: string, payload: { project_config_path: string; pipeline_path: string }) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/release-readiness/run", { method: "POST", body: JSON.stringify(payload) });
}
export async function getReleaseReadiness(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/release-readiness");
}

export async function getDeploymentProfile(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/deployment/profile");
}

export async function getDesktopConfig(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/desktop/config");
}

export async function getDesktopHealth(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/desktop/health");
}

export async function saveDesktopConfig(
  baseUrl: string,
  payload: Record<string, unknown>
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/desktop/config", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getImageValidationReport(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/images/validation?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function getImageManifestReport(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/images/manifest?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function getDatasetImportHistory(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/imports?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function createImportDiagnosticsPackage(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package?project_id=${encodeURIComponent(projectId)}`,
    { method: "POST" }
  );
}

export async function getLatestImportDiagnosticsPackage(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package/latest?project_id=${encodeURIComponent(projectId)}`
  );
}

export async function verifyImportDiagnosticsPackage(baseUrl: string, projectId = "brain-tumor-study") {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/datasets/diagnostics/package/verify?project_id=${encodeURIComponent(projectId)}`,
    { method: "POST" }
  );
}

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

export async function getSessionRuns(baseUrl: string, status?: string) {
  const params = status ? `?status=${encodeURIComponent(status)}` : "";
  return requestJson<Record<string, unknown>>(baseUrl, `/api/sessions/runs${params}`);
}

export async function postSessionIndex(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/sessions/index", { method: "POST" });
}

export async function querySessions(baseUrl: string, q: string) {
  return requestJson<Record<string, unknown>>(baseUrl, `/api/sessions/query?q=${encodeURIComponent(q)}&limit=50`);
}

// === Tool Catalog ===

export async function fetchToolCatalog(baseUrl: string) {
  return requestJson<{ ok: boolean; count: number; items: Array<Record<string, unknown>> }>(
    baseUrl,
    "/api/tools/catalog"
  );
}

// === LLM Planner ===

export async function generatePlanFromGoal(
  baseUrl: string,
  payload: {
    goal: string;
    provider?: string;
    project_id?: string;
    project_config_path?: string;
    constraints?: Record<string, unknown>;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/planner/plan-from-goal", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// === Plan Validator ===

export async function validatePlan(
  baseUrl: string,
  plan: Record<string, unknown>
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/plans/validate", {
    method: "POST",
    body: JSON.stringify({ plan }),
  });
}

// === Approval Gate ===

export async function checkApprovalGate(
  baseUrl: string,
  payload: {
    plan: Record<string, unknown>;
    validation: Record<string, unknown>;
    approval: Record<string, unknown> | null;
  }
) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/approval/check", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

// === Execute Reviewed ===

// === Audit Record ===

export async function fetchAuditRecord(baseUrl: string, auditId: string) {
  return requestJson<Record<string, unknown>>(
    baseUrl,
    `/api/audit/records/${encodeURIComponent(auditId)}`
  );
}

// === Execute Reviewed ===

export async function executeReviewedDryRun(
  baseUrl: string,
  payload: {
    plan: Record<string, unknown>;
    approval: Record<string, unknown> | null;
    project_id?: string;
    reviewed_plan_id?: string;
    project_config_path?: string;
    persist_audit?: boolean;
    actor?: string;
  }
) {
  return requestJson<ExecuteReviewedResponse>(baseUrl, "/api/plans/execute-reviewed", {
    method: "POST",
    body: JSON.stringify({ ...payload, dry_run: true }),
  });
}

export async function executeReviewedPlan(
  baseUrl: string,
  payload: {
    plan: Record<string, unknown>;
    approval: Record<string, unknown> | null;
    project_id?: string;
    reviewed_plan_id?: string;
    project_config_path: string;
    actor?: string;
  }
) {
  return requestJson<ExecuteReviewedResponse>(baseUrl, "/api/plans/execute-reviewed", {
    method: "POST",
    body: JSON.stringify({
      plan: payload.plan,
      approval: payload.approval,
      project_id: payload.project_id,
      reviewed_plan_id: payload.reviewed_plan_id,
      project_config_path: payload.project_config_path,
      dry_run: false,
      confirm_execution: true,
      persist_audit: true,
      write_pipeline_yaml: true,
      actor: payload.actor ?? "frontend-user",
    }),
  });
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
