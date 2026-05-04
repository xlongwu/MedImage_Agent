import type {
  AgentExecuteRequest,
  AgentPlanRequest,
  AgentRun,
  DatasetEvaluationReport,
  RunInspection
} from "./types";

export const DEFAULT_API_BASE = "http://127.0.0.1:8000";

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
    const detail =
      typeof payload === "object" && payload !== null && "detail" in payload
        ? JSON.stringify((payload as { detail: unknown }).detail, null, 2)
        : text;
    throw new Error(detail || `HTTP ${response.status}`);
  }

  return payload as T;
}

export async function getHealth(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/health");
}

export async function getProjectConfig(baseUrl: string) {
  return requestJson<Record<string, unknown>>(baseUrl, "/api/project-config");
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
