import React, { useState } from "react";
import { runDpabiCapability, runDpabiScaffold, runDpabiInputManifest, runDpabiPreflight, runDpabiRunPlan, runDpabiSandboxSmoke, runDpabiSignatureProbe, generateDpabiWrapperContracts, runDpabiSingleFunctionSandbox, runDpabiSubjectSmooth, generateDpabiSubjectWrapperReport, generateDpabiWrapperValidationMatrix, generateDpabiTemplateLibrary, listDpabiTemplates, instantiateDpabiTemplate, executeDpabiTemplate } from "../api";

interface FunctionItem {
  name: string;
  category: string;
  exists: boolean;
  which_path?: string;
}

interface CapabilityResult {
  ok?: boolean;
  matlab_version?: string;
  dpabi_dir?: string;
  functions?: FunctionItem[];
  summary?: {
    found_count: number;
    missing_count: number;
    total_checked: number;
    dpabi_entrypoint_found?: boolean;
    dpabi_entrypoint_path?: string;
  };
  errors?: string[];
  warnings?: string[];
  result_json?: string;
}

interface ScaffoldResult {
  ok?: boolean;
  outputs?: string[];
  metrics?: {
    functions_total?: number;
    functions_found?: number;
    functions_missing?: number;
    dpabi_entrypoint_found?: boolean;
  };
  errors?: string[];
  warnings?: string[];
}

interface SubjectItem {
  subject_id: string;
  dataset_status: string;
  status: string;
  t1w?: string;
  bold?: string;
  bold_json?: string;
  tr?: number;
  issues: string[];
}

interface ManifestResult {
  ok?: boolean;
  dataset_index?: string;
  workspace_dir?: string;
  subjects_total?: number;
  subjects_ready?: number;
  subjects?: SubjectItem[];
  errors?: string[];
  warnings?: string[];
  manifest_path?: string;
}

interface CheckItem {
  name: string;
  ok: boolean;
  message: string;
  blocking: boolean;
}

interface SubjectCheckItem {
  subject_id: string;
  t1w_exists: boolean;
  bold_exists: boolean;
  has_tr: boolean;
  tr?: number;
}

interface PreflightResult {
  ok?: boolean;
  status?: string;
  capabilities_path?: string;
  manifest_path?: string;
  batch_config_draft?: string;
  subjects_ready?: number;
  checks?: CheckItem[];
  subject_checks?: SubjectCheckItem[];
  errors?: string[];
  warnings?: string[];
}

interface PlannedStep {
  step_id: string;
  action: string;
  status: string;
  requires_approval?: boolean;
}

interface RunPlanResult {
  ok?: boolean;
  status?: string;
  mode?: string;
  requires_approval?: boolean;
  approved?: boolean;
  execution_allowed?: boolean;
  subjects_ready?: number;
  dpabi_entrypoint_found?: boolean;
  planned_steps?: PlannedStep[];
  blocking_errors?: string[];
  warnings?: string[];
  run_plan_path?: string;
  report_path?: string;
}

interface SandboxMetrics {
  y_Read_found?: boolean;
  y_Write_found?: boolean;
  rest_readfile_found?: boolean;
  rest_writefile_found?: boolean;
  spm_write_vol_found?: boolean;
  read_write_test_attempted?: boolean;
  read_write_test_success?: boolean;
  used_function_family?: string;
  input_exists?: boolean;
  output_exists?: boolean;
}

interface SandboxResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  dpabi_dir?: string;
  sandbox_dir?: string;
  matlab_version?: string;
  outputs?: string[];
  metrics?: SandboxMetrics;
  errors?: string[];
  warnings?: string[];
  returncode?: number;
  approval_record?: string;
  audit_json?: string;
  audit_report?: string;
}

interface SignatureFunction {
  name: string;
  category: string;
  exists: boolean;
  which_path?: string;
  nargin?: number;
  nargout?: number;
  help_excerpt?: string;
  probe_errors?: string[];
}

interface SignatureResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  dpabi_dir?: string;
  matlab_version?: string;
  functions?: SignatureFunction[];
  summary?: {
    found_count: number;
    missing_count: number;
    signature_count: number;
    total_checked: number;
  };
  errors?: string[];
  warnings?: string[];
  result_json?: string;
}

interface ContractItem {
  function_name: string;
  category: string;
  exists: boolean;
  nargin?: number;
  nargout?: number;
  safety_classification: string;
  wrapper_candidate: boolean;
  blocked_reason?: string;
  recommended_next_step: string;
}

interface ContractsResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  contracts_total?: number;
  wrapper_candidates?: number;
  blocked_total?: number;
  contracts?: ContractItem[];
  outputs?: string[];
  contracts_json?: string;
  contracts_yaml?: string;
  report_md?: string;
  errors?: string[];
  warnings?: string[];
}

interface SingleFunctionMetrics {
  function_found?: boolean;
  function_path?: string;
  input_exists?: boolean;
  wrapper_call_attempted?: boolean;
  wrapper_call_success?: boolean;
  call_pattern?: string;
  output_exists?: boolean;
}

interface SingleFunctionResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  function_name?: string;
  dpabi_dir?: string;
  sandbox_dir?: string;
  matlab_version?: string;
  outputs?: string[];
  metrics?: SingleFunctionMetrics;
  errors?: string[];
  warnings?: string[];
  returncode?: number;
  approval_record?: string;
  audit_json?: string;
  audit_report?: string;
}

interface SubjectSmoothMetrics {
  function_found?: boolean;
  function_path?: string;
  wrapper_call_attempted?: boolean;
  wrapper_call_success?: boolean;
  call_pattern?: string;
  output_exists?: boolean;
  fwhm?: number[];
}

interface SubjectSmoothResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  subject_id?: string;
  function_name?: string;
  input_nii?: string;
  output_nii?: string;
  outputs?: string[];
  metrics?: SubjectSmoothMetrics;
  errors?: string[];
  warnings?: string[];
  returncode?: number;
  result_json?: string;
  prepared_input?: string;
}

interface SubjectWrapperReportResult {
  ok?: boolean;
  summary_json?: string;
  report_md?: string;
  subjects_total?: number;
  subjects_success?: number;
  subjects_failed?: number;
}

interface MatrixRow {
  function_name?: string;
  category?: string;
  exists?: boolean;
  wrapper_candidate?: boolean;
  sandbox_passed?: boolean;
  subject_passed?: boolean;
  readiness?: string;
  recommended_next_step?: string;
}

interface ValidationMatrixResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  matrix_total?: number;
  promotable_total?: number;
  blocked_total?: number;
  manual_review_total?: number;
  rows?: MatrixRow[];
  outputs?: string[];
  metrics?: {
    matrix_total?: number;
    promotable_total?: number;
    blocked_total?: number;
    manual_review_total?: number;
  };
  warnings?: string[];
  errors?: string[];
}

interface TemplateItem {
  template_id?: string;
  function_name?: string;
  template_path?: string;
  template_type?: string;
  synthetic_only?: boolean;
  requires_approval?: boolean;
  approved_by_default?: boolean;
}

interface TemplateLibraryResult {
  ok?: boolean;
  node_id?: string;
  backend?: string;
  matrix_path?: string;
  templates_total?: number;
  templates?: TemplateItem[];
  skipped?: { function_name?: string; reason?: string }[];
  outputs?: string[];
  metrics?: {
    templates_total?: number;
    skipped_total?: number;
  };
  warnings?: string[];
  errors?: string[];
}

interface TemplateInstanceResult {
  ok?: boolean;
  mode?: string;
  template_id?: string;
  instance_id?: string;
  run_id?: string;
  outputs?: string[];
  pipeline_path?: string;
  manifest_path?: string;
  review_path?: string;
  warnings?: string[];
  errors?: string[];
}

interface TemplateExecuteResult {
  ok?: boolean;
  mode?: string;
  instance_id?: string;
  run_id?: string;
  status?: string;
  outputs?: string[];
  execution_summary?: {
    ok?: boolean;
    instance_id?: string;
    run_id?: string;
    status?: string;
  };
  warnings?: string[];
  errors?: string[];
}

interface DpabiCapabilityPanelProps {
  baseUrl: string;
}

export function DpabiCapabilityPanel({ baseUrl }: DpabiCapabilityPanelProps) {
  const [projectConfigPath, setProjectConfigPath] = useState<string>(
    "examples/project_config_dataset.yaml"
  );
  const [approvedBy, setApprovedBy] = useState<string>("local-user");
  const [loadingCapability, setLoadingCapability] = useState(false);
  const [loadingScaffold, setLoadingScaffold] = useState(false);
  const [loadingManifest, setLoadingManifest] = useState(false);
  const [loadingPreflight, setLoadingPreflight] = useState(false);
  const [loadingRunPlan, setLoadingRunPlan] = useState(false);
  const [loadingSandbox, setLoadingSandbox] = useState(false);
  const [loadingSignature, setLoadingSignature] = useState(false);
  const [loadingContracts, setLoadingContracts] = useState(false);
  const [capabilityResult, setCapabilityResult] = useState<CapabilityResult | null>(null);
  const [scaffoldResult, setScaffoldResult] = useState<ScaffoldResult | null>(null);
  const [manifestResult, setManifestResult] = useState<ManifestResult | null>(null);
  const [preflightResult, setPreflightResult] = useState<PreflightResult | null>(null);
  const [runPlanResult, setRunPlanResult] = useState<RunPlanResult | null>(null);
  const [sandboxResult, setSandboxResult] = useState<SandboxResult | null>(null);
  const [signatureResult, setSignatureResult] = useState<SignatureResult | null>(null);
  const [contractsResult, setContractsResult] = useState<ContractsResult | null>(null);
  const [singleFunctionResult, setSingleFunctionResult] = useState<SingleFunctionResult | null>(null);
  const [functionName, setFunctionName] = useState<string>("y_Smooth");
  const [loadingSingleFunction, setLoadingSingleFunction] = useState(false);
  const [subjectId, setSubjectId] = useState<string>("sub-01");
  const [inputBold, setInputBold] = useState<string>("examples/synthetic_bids/rawdata/sub-01/func/sub-01_task-rest_bold.nii.gz");
  const [subjectSmoothResult, setSubjectSmoothResult] = useState<SubjectSmoothResult | null>(null);
  const [subjectWrapperReportResult, setSubjectWrapperReportResult] = useState<SubjectWrapperReportResult | null>(null);
  const [loadingSubjectSmooth, setLoadingSubjectSmooth] = useState(false);
  const [loadingSubjectReport, setLoadingSubjectReport] = useState(false);
  const [validationMatrixResult, setValidationMatrixResult] = useState<ValidationMatrixResult | null>(null);
  const [loadingValidationMatrix, setLoadingValidationMatrix] = useState(false);
  const [templateLibraryResult, setTemplateLibraryResult] = useState<TemplateLibraryResult | null>(null);
  const [loadingTemplateLibrary, setLoadingTemplateLibrary] = useState(false);
  const [templatesList, setTemplatesList] = useState<TemplateItem[]>([]);
  const [loadingTemplatesList, setLoadingTemplatesList] = useState(false);
  const [templateInstanceResult, setTemplateInstanceResult] = useState<TemplateInstanceResult | null>(null);
  const [loadingTemplateInstance, setLoadingTemplateInstance] = useState(false);
  const [templateExecuteResult, setTemplateExecuteResult] = useState<TemplateExecuteResult | null>(null);
  const [loadingTemplateExecute, setLoadingTemplateExecute] = useState(false);
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>("dpabi_y_smooth_subject_wrapper_template");
  const [instanceId, setInstanceId] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  const handleRunCapability = async () => {
    setLoadingCapability(true);
    setError(null);
    setCapabilityResult(null);
    try {
      const result = (await runDpabiCapability(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as CapabilityResult;
      setCapabilityResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingCapability(false);
    }
  };

  const handleRunScaffold = async () => {
    setLoadingScaffold(true);
    setError(null);
    setScaffoldResult(null);
    try {
      const result = (await runDpabiScaffold(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as ScaffoldResult;
      setScaffoldResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingScaffold(false);
    }
  };

  const handleRunInputManifest = async () => {
    setLoadingManifest(true);
    setError(null);
    setManifestResult(null);
    try {
      const result = (await runDpabiInputManifest(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        dataset_index: "./work/dataset_index/dataset_index.json",
      })) as ManifestResult;
      setManifestResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingManifest(false);
    }
  };

  const handleRunPreflight = async () => {
    setLoadingPreflight(true);
    setError(null);
    setPreflightResult(null);
    try {
      const result = (await runDpabiPreflight(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        dataset_index: "./work/dataset_index/dataset_index.json",
        capabilities_path: "./work/dpabi/dpabi_capabilities.json",
        manifest_path: "./work/dpabi/dpabi_input_manifest.json",
        wrapper_config_template_path: "./work/dpabi/dpabi_wrapper_config_template.yaml",
      })) as PreflightResult;
      setPreflightResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingPreflight(false);
    }
  };

  const handleRunRunPlan = async () => {
    setLoadingRunPlan(true);
    setError(null);
    setRunPlanResult(null);
    try {
      const result = (await runDpabiRunPlan(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        capabilities_path: "./work/dpabi/dpabi_capabilities.json",
        manifest_path: "./work/dpabi/dpabi_input_manifest.json",
        preflight_path: "./work/dpabi/dpabi_preflight_report.json",
        params_path: "./work/dpabi/dpabi_params_review.yaml",
      })) as RunPlanResult;
      setRunPlanResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingRunPlan(false);
    }
  };

  const handleRunSandbox = async () => {
    setLoadingSandbox(true);
    setError(null);
    setSandboxResult(null);
    try {
      const result = (await runDpabiSandboxSmoke(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        approved: true,
        approved_by: approvedBy,
      })) as SandboxResult;
      setSandboxResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingSandbox(false);
    }
  };

  const handleRunSignatureProbe = async () => {
    setLoadingSignature(true);
    setError(null);
    setSignatureResult(null);
    try {
      const result = (await runDpabiSignatureProbe(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as SignatureResult;
      setSignatureResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingSignature(false);
    }
  };

  const handleGenerateContracts = async () => {
    setLoadingContracts(true);
    setError(null);
    setContractsResult(null);
    try {
      const result = (await generateDpabiWrapperContracts(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as ContractsResult;
      setContractsResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingContracts(false);
    }
  };

  const handleRunSingleFunction = async () => {
    setLoadingSingleFunction(true);
    setError(null);
    setSingleFunctionResult(null);
    try {
      const result = (await runDpabiSingleFunctionSandbox(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        function_name: functionName,
        approved: true,
        approved_by: approvedBy,
      })) as SingleFunctionResult;
      setSingleFunctionResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingSingleFunction(false);
    }
  };

  const handleRunSubjectSmooth = async () => {
    setLoadingSubjectSmooth(true);
    setError(null);
    setSubjectSmoothResult(null);
    try {
      const result = (await runDpabiSubjectSmooth(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        subject_id: subjectId,
        input_bold: inputBold,
        function_name: functionName,
        fwhm: [4, 4, 4],
        approved: true,
      })) as SubjectSmoothResult;
      setSubjectSmoothResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingSubjectSmooth(false);
    }
  };

  const handleGenerateSubjectReport = async () => {
    setLoadingSubjectReport(true);
    setError(null);
    setSubjectWrapperReportResult(null);
    try {
      const result = (await generateDpabiSubjectWrapperReport(baseUrl, {
        project_config_path: projectConfigPath,
      })) as SubjectWrapperReportResult;
      setSubjectWrapperReportResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingSubjectReport(false);
    }
  };

  const handleGenerateValidationMatrix = async () => {
    setLoadingValidationMatrix(true);
    setError(null);
    setValidationMatrixResult(null);
    try {
      const result = (await generateDpabiWrapperValidationMatrix(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as ValidationMatrixResult;
      setValidationMatrixResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingValidationMatrix(false);
    }
  };

  const handleGenerateTemplateLibrary = async () => {
    setLoadingTemplateLibrary(true);
    setError(null);
    setTemplateLibraryResult(null);
    try {
      const result = (await generateDpabiTemplateLibrary(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
      })) as TemplateLibraryResult;
      setTemplateLibraryResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingTemplateLibrary(false);
    }
  };

  const handleListTemplates = async () => {
    setLoadingTemplatesList(true);
    setError(null);
    try {
      const result = (await listDpabiTemplates(baseUrl, "./work")) as { templates?: TemplateItem[] };
      setTemplatesList(result.templates || []);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingTemplatesList(false);
    }
  };

  const handleInstantiateTemplate = async () => {
    setLoadingTemplateInstance(true);
    setError(null);
    setTemplateInstanceResult(null);
    try {
      const result = (await instantiateDpabiTemplate(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        template_id: selectedTemplateId,
        instance_id: instanceId || undefined,
        function_name: functionName,
        fwhm: [4, 4, 4],
        subjects: ["sub-001", "sub-002"],
      })) as TemplateInstanceResult;
      setTemplateInstanceResult(result);
      if (result.instance_id) {
        setInstanceId(result.instance_id);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingTemplateInstance(false);
    }
  };

  const handleExecuteTemplate = async () => {
    setLoadingTemplateExecute(true);
    setError(null);
    setTemplateExecuteResult(null);
    try {
      const result = (await executeDpabiTemplate(baseUrl, {
        project_config_path: projectConfigPath,
        work_dir: "./work",
        log_dir: "./logs",
        instance_id: instanceId,
        approved: true,
        approved_by: approvedBy,
      })) as TemplateExecuteResult;
      setTemplateExecuteResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingTemplateExecute(false);
    }
  };

  return (
    <div style={{ padding: 16 }}>
      <h2>DPABI Capability Inspector</h2>
      <div style={{ marginBottom: 16 }}>
        <label style={{ display: "block", marginBottom: 8 }}>
          Project Config Path:
          <input
            type="text"
            value={projectConfigPath}
            onChange={(e) => setProjectConfigPath(e.target.value)}
            style={{ marginLeft: 8, width: 400 }}
          />
        </label>
        <label style={{ display: "block", marginBottom: 8 }}>
          Approved By:
          <input
            type="text"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            style={{ marginLeft: 8, width: 200 }}
          />
        </label>
        <label style={{ display: "block", marginBottom: 8 }}>
          Function Name:
          <select
            value={functionName}
            onChange={(e) => setFunctionName(e.target.value)}
            style={{ marginLeft: 8, width: 200 }}
          >
            <option value="y_Smooth">y_Smooth</option>
            <option value="rest_Smooth">rest_Smooth</option>
          </select>
        </label>
        <label style={{ display: "block", marginBottom: 8 }}>
          Subject ID:
          <input
            type="text"
            value={subjectId}
            onChange={(e) => setSubjectId(e.target.value)}
            style={{ marginLeft: 8, width: 200 }}
          />
        </label>
        <label style={{ display: "block", marginBottom: 8 }}>
          Input BOLD:
          <input
            type="text"
            value={inputBold}
            onChange={(e) => setInputBold(e.target.value)}
            style={{ marginLeft: 8, width: 500 }}
          />
        </label>
      </div>
      <div style={{ marginBottom: 16 }}>
        <button
          onClick={handleRunCapability}
          disabled={loadingCapability}
          style={{ marginRight: 8 }}
        >
          {loadingCapability ? "Running..." : "Inspect DPABI Capabilities"}
        </button>
        <button
          onClick={handleRunScaffold}
          disabled={loadingScaffold}
          style={{ marginRight: 8 }}
        >
          {loadingScaffold ? "Running..." : "Generate Wrapper Scaffold"}
        </button>
        <button
          onClick={handleRunInputManifest}
          disabled={loadingManifest}
          style={{ marginRight: 8 }}
        >
          {loadingManifest ? "Running..." : "Build Input Manifest"}
        </button>
        <button
          onClick={handleRunPreflight}
          disabled={loadingPreflight}
          style={{ marginRight: 8 }}
        >
          {loadingPreflight ? "Running..." : "Run Preflight"}
        </button>
        <button
          onClick={handleRunRunPlan}
          disabled={loadingRunPlan}
          style={{ marginRight: 8 }}
        >
          {loadingRunPlan ? "Running..." : "Generate Run Plan"}
        </button>
        <button
          onClick={handleRunSandbox}
          disabled={loadingSandbox}
          style={{ backgroundColor: "#ff9800", color: "white", marginRight: 8 }}
        >
          {loadingSandbox ? "Running..." : "Approved Sandbox Smoke Run"}
        </button>
        <button
          onClick={handleRunSignatureProbe}
          disabled={loadingSignature}
          style={{ marginRight: 8 }}
        >
          {loadingSignature ? "Running..." : "Probe Function Signatures"}
        </button>
        <button
          onClick={handleGenerateContracts}
          disabled={loadingContracts}
          style={{ backgroundColor: "#4caf50", color: "white", marginRight: 8 }}
        >
          {loadingContracts ? "Running..." : "Generate Wrapper Contracts"}
        </button>
        <button
          onClick={handleRunSingleFunction}
          disabled={loadingSingleFunction}
          style={{ backgroundColor: "#2196f3", color: "white", marginRight: 8 }}
        >
          {loadingSingleFunction ? "Running..." : "Run Single-Function Sandbox"}
        </button>
        <button
          onClick={handleRunSubjectSmooth}
          disabled={loadingSubjectSmooth}
          style={{ backgroundColor: "#9c27b0", color: "white", marginRight: 8 }}
        >
          {loadingSubjectSmooth ? "Running..." : "Run Subject Smooth"}
        </button>
        <button
          onClick={handleGenerateSubjectReport}
          disabled={loadingSubjectReport}
          style={{ backgroundColor: "#607d8b", color: "white", marginRight: 8 }}
        >
          {loadingSubjectReport ? "Running..." : "Generate Subject Report"}
        </button>
        <button
          onClick={handleGenerateValidationMatrix}
          disabled={loadingValidationMatrix}
          style={{ backgroundColor: "#ff9800", color: "white", marginRight: 8 }}
        >
          {loadingValidationMatrix ? "Running..." : "Generate Validation Matrix"}
        </button>
        <button
          onClick={handleGenerateTemplateLibrary}
          disabled={loadingTemplateLibrary}
          style={{ backgroundColor: "#795548", color: "white", marginRight: 8 }}
        >
          {loadingTemplateLibrary ? "Running..." : "Generate Template Library"}
        </button>
        <button
          onClick={handleListTemplates}
          disabled={loadingTemplatesList}
          style={{ backgroundColor: "#607d8b", color: "white", marginRight: 8 }}
        >
          {loadingTemplatesList ? "Loading..." : "List Templates"}
        </button>
        <button
          onClick={handleInstantiateTemplate}
          disabled={loadingTemplateInstance}
          style={{ backgroundColor: "#ff5722", color: "white", marginRight: 8 }}
        >
          {loadingTemplateInstance ? "Instantiating..." : "Instantiate Template"}
        </button>
        <button
          onClick={handleExecuteTemplate}
          disabled={loadingTemplateExecute || !instanceId}
          style={{ backgroundColor: "#e91e63", color: "white" }}
        >
          {loadingTemplateExecute ? "Executing..." : "Execute Template (Approved)"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {capabilityResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Capability Result</h3>
          <div
            style={{
              padding: 12,
              background: capabilityResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {capabilityResult.ok ? "OK" : "Failed"}
          </div>

          {capabilityResult.matlab_version && (
            <p>
              <strong>MATLAB Version:</strong> {capabilityResult.matlab_version}
            </p>
          )}
          {capabilityResult.dpabi_dir && (
            <p>
              <strong>DPABI Directory:</strong> {capabilityResult.dpabi_dir}
            </p>
          )}

          {capabilityResult.summary && (
            <div style={{ marginTop: 12 }}>
              <h4>Summary</h4>
              <ul>
                <li>Total Checked: {capabilityResult.summary.total_checked}</li>
                <li>Found: {capabilityResult.summary.found_count}</li>
                <li>Missing: {capabilityResult.summary.missing_count}</li>
                <li>
                  DPABI Entrypoint Found: {capabilityResult.summary.dpabi_entrypoint_found ? "Yes" : "No"}
                </li>
                {capabilityResult.summary.dpabi_entrypoint_path && (
                  <li>Entrypoint Path: {capabilityResult.summary.dpabi_entrypoint_path}</li>
                )}
              </ul>
            </div>
          )}

          {capabilityResult.functions && capabilityResult.functions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Functions</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Name</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Category</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Exists</th>
                  </tr>
                </thead>
                <tbody>
                  {capabilityResult.functions.map((fn, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{fn.name}</td>
                      <td style={{ padding: 8 }}>{fn.category}</td>
                      <td style={{ padding: 8 }}>{fn.exists ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {capabilityResult.warnings && capabilityResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {capabilityResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {capabilityResult.errors && capabilityResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {capabilityResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {capabilityResult.result_json && (
            <p style={{ marginTop: 12 }}>
              <strong>Result JSON:</strong> {capabilityResult.result_json}
            </p>
          )}
        </div>
      )}

      {scaffoldResult && (
        <div>
          <h3>DPABI Wrapper Scaffold Result</h3>
          <div
            style={{
              padding: 12,
              background: scaffoldResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {scaffoldResult.ok ? "OK" : "Failed"}
          </div>

          {scaffoldResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Metrics</h4>
              <ul>
                <li>Total Functions: {scaffoldResult.metrics.functions_total}</li>
                <li>Found: {scaffoldResult.metrics.functions_found}</li>
                <li>Missing: {scaffoldResult.metrics.functions_missing}</li>
                <li>
                  DPABI Entrypoint Found: {scaffoldResult.metrics.dpabi_entrypoint_found ? "Yes" : "No"}
                </li>
              </ul>
            </div>
          )}

          {scaffoldResult.outputs && scaffoldResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Files</h4>
              <ul>
                {scaffoldResult.outputs.map((o, idx) => (
                  <li key={idx}>
                    <code>{o}</code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scaffoldResult.warnings && scaffoldResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {scaffoldResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>
                    {w}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {scaffoldResult.errors && scaffoldResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {scaffoldResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {manifestResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Input Manifest Result</h3>
          <div
            style={{
              padding: 12,
              background: manifestResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {manifestResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Dataset Index:</strong> {manifestResult.dataset_index}</p>
          <p><strong>Workspace:</strong> {manifestResult.workspace_dir}</p>
          <p><strong>Subjects Total:</strong> {manifestResult.subjects_total}</p>
          <p><strong>Subjects Ready:</strong> {manifestResult.subjects_ready}</p>

          {manifestResult.subjects && manifestResult.subjects.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Subjects</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Subject ID</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Has T1w</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Has BOLD</th>
                    <th style={{ textAlign: "left", padding: 8 }}>TR</th>
                  </tr>
                </thead>
                <tbody>
                  {manifestResult.subjects.map((subj, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{subj.subject_id}</td>
                      <td style={{ padding: 8 }}>{subj.status}</td>
                      <td style={{ padding: 8 }}>{subj.t1w ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{subj.bold ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{subj.tr ?? "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {manifestResult.warnings && manifestResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {manifestResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {manifestResult.errors && manifestResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {manifestResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {manifestResult.manifest_path && (
            <p style={{ marginTop: 12 }}>
              <strong>Manifest Path:</strong> {manifestResult.manifest_path}
            </p>
          )}
        </div>
      )}

      {preflightResult && (
        <div>
          <h3>DPABI Preflight Result</h3>
          <div
            style={{
              padding: 12,
              background: preflightResult.status === "PASS" ? "#e6f7e6" : preflightResult.status === "WARNING" ? "#fff3cd" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {preflightResult.status}
          </div>

          <p><strong>Subjects Ready:</strong> {preflightResult.subjects_ready}</p>
          <p><strong>Capabilities:</strong> {preflightResult.capabilities_path}</p>
          <p><strong>Manifest:</strong> {preflightResult.manifest_path}</p>
          <p><strong>Batch Config Draft:</strong> {preflightResult.batch_config_draft}</p>

          {preflightResult.checks && preflightResult.checks.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Checks</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Check</th>
                    <th style={{ textAlign: "left", padding: 8 }}>OK</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Blocking</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Message</th>
                  </tr>
                </thead>
                <tbody>
                  {preflightResult.checks.map((check, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{check.name}</td>
                      <td style={{ padding: 8 }}>{check.ok ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{check.blocking ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{check.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {preflightResult.subject_checks && preflightResult.subject_checks.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Subject Checks</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Subject</th>
                    <th style={{ textAlign: "left", padding: 8 }}>T1w Exists</th>
                    <th style={{ textAlign: "left", padding: 8 }}>BOLD Exists</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Has TR</th>
                    <th style={{ textAlign: "left", padding: 8 }}>TR</th>
                  </tr>
                </thead>
                <tbody>
                  {preflightResult.subject_checks.map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{item.subject_id}</td>
                      <td style={{ padding: 8 }}>{item.t1w_exists ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{item.bold_exists ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{item.has_tr ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{item.tr ?? "N/A"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {preflightResult.warnings && preflightResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {preflightResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {preflightResult.errors && preflightResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {preflightResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {runPlanResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Run Plan Result</h3>
          <div
            style={{
              padding: 12,
              background: runPlanResult.status === "BLOCKED" ? "#ffe6e6" : runPlanResult.status === "WARNING" ? "#fff3e6" : "#e6f7e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {runPlanResult.status}
          </div>

          <p><strong>Mode:</strong> {runPlanResult.mode}</p>
          <p><strong>Subjects Ready:</strong> {runPlanResult.subjects_ready}</p>
          <p><strong>Requires Approval:</strong> {runPlanResult.requires_approval ? "Yes" : "No"}</p>
          <p><strong>Approved:</strong> {runPlanResult.approved ? "Yes" : "No"}</p>
          <p><strong>Execution Allowed:</strong> {runPlanResult.execution_allowed ? "Yes" : "No"}</p>
          <p><strong>DPABI Entrypoint Found:</strong> {runPlanResult.dpabi_entrypoint_found ? "Yes" : "No"}</p>

          {runPlanResult.planned_steps && runPlanResult.planned_steps.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Planned Steps</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Step ID</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Action</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Status</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Requires Approval</th>
                  </tr>
                </thead>
                <tbody>
                  {runPlanResult.planned_steps.map((step, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{step.step_id}</td>
                      <td style={{ padding: 8 }}>{step.action}</td>
                      <td style={{ padding: 8 }}>{step.status}</td>
                      <td style={{ padding: 8 }}>{step.requires_approval ? "Yes" : "No"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {runPlanResult.blocking_errors && runPlanResult.blocking_errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Blocking Errors</h4>
              <ul>
                {runPlanResult.blocking_errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}

          {runPlanResult.warnings && runPlanResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {runPlanResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {runPlanResult.run_plan_path && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Run Plan JSON:</strong> {runPlanResult.run_plan_path}</p>
            </div>
          )}

          {runPlanResult.report_path && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Report Markdown:</strong> {runPlanResult.report_path}</p>
            </div>
          )}
        </div>
      )}

      {sandboxResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Sandbox Smoke Run Result</h3>
          <div
            style={{
              padding: 12,
              background: sandboxResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {sandboxResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Node ID:</strong> {sandboxResult.node_id}</p>
          <p><strong>Backend:</strong> {sandboxResult.backend}</p>
          <p><strong>MATLAB Version:</strong> {sandboxResult.matlab_version}</p>
          <p><strong>Return Code:</strong> {sandboxResult.returncode}</p>

          {sandboxResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Metrics</h4>
              <ul>
                <li>y_Read found: {sandboxResult.metrics.y_Read_found ? "Yes" : "No"}</li>
                <li>y_Write found: {sandboxResult.metrics.y_Write_found ? "Yes" : "No"}</li>
                <li>rest_readfile found: {sandboxResult.metrics.rest_readfile_found ? "Yes" : "No"}</li>
                <li>rest_writefile found: {sandboxResult.metrics.rest_writefile_found ? "Yes" : "No"}</li>
                <li>spm_write_vol found: {sandboxResult.metrics.spm_write_vol_found ? "Yes" : "No"}</li>
                <li>Read/Write test attempted: {sandboxResult.metrics.read_write_test_attempted ? "Yes" : "No"}</li>
                <li>Read/Write test success: {sandboxResult.metrics.read_write_test_success ? "Yes" : "No"}</li>
                {sandboxResult.metrics.used_function_family && (
                  <li>Used function family: {sandboxResult.metrics.used_function_family}</li>
                )}
                <li>Input exists: {sandboxResult.metrics.input_exists ? "Yes" : "No"}</li>
                <li>Output exists: {sandboxResult.metrics.output_exists ? "Yes" : "No"}</li>
              </ul>
            </div>
          )}

          {sandboxResult.outputs && sandboxResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Outputs</h4>
              <ul>
                {sandboxResult.outputs.map((output, idx) => (
                  <li key={idx}>{output}</li>
                ))}
              </ul>
            </div>
          )}

          {sandboxResult.approval_record && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Approval Record:</strong> {sandboxResult.approval_record}</p>
            </div>
          )}

          {sandboxResult.audit_json && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Audit JSON:</strong> {sandboxResult.audit_json}</p>
            </div>
          )}

          {sandboxResult.audit_report && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Audit Report:</strong> {sandboxResult.audit_report}</p>
            </div>
          )}

          {sandboxResult.warnings && sandboxResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {sandboxResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {sandboxResult.errors && sandboxResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {sandboxResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {signatureResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Function Signature Probe Result</h3>
          <div
            style={{
              padding: 12,
              background: signatureResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {signatureResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Node ID:</strong> {signatureResult.node_id}</p>
          <p><strong>Backend:</strong> {signatureResult.backend}</p>
          <p><strong>MATLAB Version:</strong> {signatureResult.matlab_version}</p>

          {signatureResult.summary && (
            <div style={{ marginTop: 12 }}>
              <h4>Summary</h4>
              <ul>
                <li>Found: {signatureResult.summary.found_count}</li>
                <li>Missing: {signatureResult.summary.missing_count}</li>
                <li>Signatures: {signatureResult.summary.signature_count}</li>
                <li>Total Checked: {signatureResult.summary.total_checked}</li>
              </ul>
            </div>
          )}

          {signatureResult.functions && signatureResult.functions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Functions</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Name</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Category</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Exists</th>
                    <th style={{ textAlign: "left", padding: 8 }}>nargin</th>
                    <th style={{ textAlign: "left", padding: 8 }}>nargout</th>
                  </tr>
                </thead>
                <tbody>
                  {signatureResult.functions.map((fn, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{fn.name}</td>
                      <td style={{ padding: 8 }}>{fn.category}</td>
                      <td style={{ padding: 8 }}>{fn.exists ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{fn.nargin ?? "-"}</td>
                      <td style={{ padding: 8 }}>{fn.nargout ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {signatureResult.result_json && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Signatures JSON:</strong> {signatureResult.result_json}</p>
            </div>
          )}

          {signatureResult.warnings && signatureResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {signatureResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {signatureResult.errors && signatureResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {signatureResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {contractsResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Wrapper Contracts Result</h3>
          <div
            style={{
              padding: 12,
              background: contractsResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {contractsResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Node ID:</strong> {contractsResult.node_id}</p>
          <p><strong>Backend:</strong> {contractsResult.backend}</p>
          <p><strong>Contracts Total:</strong> {contractsResult.contracts_total}</p>
          <p><strong>Wrapper Candidates:</strong> {contractsResult.wrapper_candidates}</p>
          <p><strong>Blocked Total:</strong> {contractsResult.blocked_total}</p>

          {contractsResult.contracts && contractsResult.contracts.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Wrapper Candidates</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Function</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Category</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Classification</th>
                    <th style={{ textAlign: "left", padding: 8 }}>nargin</th>
                    <th style={{ textAlign: "left", padding: 8 }}>nargout</th>
                  </tr>
                </thead>
                <tbody>
                  {contractsResult.contracts
                    .filter(c => c.wrapper_candidate)
                    .map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{item.function_name}</td>
                      <td style={{ padding: 8 }}>{item.category}</td>
                      <td style={{ padding: 8 }}>{item.safety_classification}</td>
                      <td style={{ padding: 8 }}>{item.nargin ?? "-"}</td>
                      <td style={{ padding: 8 }}>{item.nargout ?? "-"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {contractsResult.contracts && contractsResult.contracts.filter(c => c.blocked_reason).length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Blocked Functions</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Function</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Blocked Reason</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Next Step</th>
                  </tr>
                </thead>
                <tbody>
                  {contractsResult.contracts
                    .filter(c => c.blocked_reason)
                    .map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{item.function_name}</td>
                      <td style={{ padding: 8 }}>{item.blocked_reason}</td>
                      <td style={{ padding: 8 }}>{item.recommended_next_step}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {contractsResult.contracts_json && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Contracts JSON:</strong> {contractsResult.contracts_json}</p>
            </div>
          )}

          {contractsResult.contracts_yaml && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Contracts YAML:</strong> {contractsResult.contracts_yaml}</p>
            </div>
          )}

          {contractsResult.report_md && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Report Markdown:</strong> {contractsResult.report_md}</p>
            </div>
          )}

          {contractsResult.warnings && contractsResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {contractsResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {contractsResult.errors && contractsResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {contractsResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {singleFunctionResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Single-Function Sandbox Result</h3>
          <div
            style={{
              padding: 12,
              background: singleFunctionResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {singleFunctionResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Node ID:</strong> {singleFunctionResult.node_id}</p>
          <p><strong>Backend:</strong> {singleFunctionResult.backend}</p>
          <p><strong>Function Name:</strong> {singleFunctionResult.function_name}</p>
          <p><strong>MATLAB Version:</strong> {singleFunctionResult.matlab_version}</p>
          <p><strong>Return Code:</strong> {singleFunctionResult.returncode}</p>

          {singleFunctionResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Metrics</h4>
              <ul>
                <li>Function found: {singleFunctionResult.metrics.function_found ? "Yes" : "No"}</li>
                <li>Input exists: {singleFunctionResult.metrics.input_exists ? "Yes" : "No"}</li>
                <li>Wrapper call attempted: {singleFunctionResult.metrics.wrapper_call_attempted ? "Yes" : "No"}</li>
                <li>Wrapper call success: {singleFunctionResult.metrics.wrapper_call_success ? "Yes" : "No"}</li>
                {singleFunctionResult.metrics.call_pattern && (
                  <li>Call pattern: {singleFunctionResult.metrics.call_pattern}</li>
                )}
                <li>Output exists: {singleFunctionResult.metrics.output_exists ? "Yes" : "No"}</li>
              </ul>
            </div>
          )}

          {singleFunctionResult.approval_record && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Approval Record:</strong> {singleFunctionResult.approval_record}</p>
            </div>
          )}

          {singleFunctionResult.audit_json && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Audit JSON:</strong> {singleFunctionResult.audit_json}</p>
            </div>
          )}

          {singleFunctionResult.audit_report && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Audit Report:</strong> {singleFunctionResult.audit_report}</p>
            </div>
          )}

          {singleFunctionResult.warnings && singleFunctionResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {singleFunctionResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {singleFunctionResult.errors && singleFunctionResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {singleFunctionResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {subjectSmoothResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Subject Smooth Result</h3>
          <div
            style={{
              padding: 12,
              background: subjectSmoothResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {subjectSmoothResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Node ID:</strong> {subjectSmoothResult.node_id}</p>
          <p><strong>Backend:</strong> {subjectSmoothResult.backend}</p>
          <p><strong>Subject ID:</strong> {subjectSmoothResult.subject_id}</p>
          <p><strong>Function Name:</strong> {subjectSmoothResult.function_name}</p>
          <p><strong>Input NIfTI:</strong> {subjectSmoothResult.input_nii}</p>
          <p><strong>Output NIfTI:</strong> {subjectSmoothResult.output_nii}</p>
          <p><strong>Return Code:</strong> {subjectSmoothResult.returncode}</p>

          {subjectSmoothResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Metrics</h4>
              <ul>
                <li>Function found: {subjectSmoothResult.metrics.function_found ? "Yes" : "No"}</li>
                <li>Wrapper call attempted: {subjectSmoothResult.metrics.wrapper_call_attempted ? "Yes" : "No"}</li>
                <li>Wrapper call success: {subjectSmoothResult.metrics.wrapper_call_success ? "Yes" : "No"}</li>
                {subjectSmoothResult.metrics.call_pattern && (
                  <li>Call pattern: {subjectSmoothResult.metrics.call_pattern}</li>
                )}
                <li>Output exists: {subjectSmoothResult.metrics.output_exists ? "Yes" : "No"}</li>
                {subjectSmoothResult.metrics.fwhm && (
                  <li>FWHM: [{subjectSmoothResult.metrics.fwhm.join(", ")}]</li>
                )}
              </ul>
            </div>
          )}

          {subjectSmoothResult.warnings && subjectSmoothResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {subjectSmoothResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {subjectSmoothResult.errors && subjectSmoothResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {subjectSmoothResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {subjectWrapperReportResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Subject Wrapper Report</h3>
          <div
            style={{
              padding: 12,
              background: subjectWrapperReportResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {subjectWrapperReportResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Total Subjects:</strong> {subjectWrapperReportResult.subjects_total}</p>
          <p><strong>Success:</strong> {subjectWrapperReportResult.subjects_success}</p>
          <p><strong>Failed:</strong> {subjectWrapperReportResult.subjects_failed}</p>

          {subjectWrapperReportResult.summary_json && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Summary JSON:</strong> {subjectWrapperReportResult.summary_json}</p>
            </div>
          )}

          {subjectWrapperReportResult.report_md && (
            <div style={{ marginTop: 12 }}>
              <p><strong>Report Markdown:</strong> {subjectWrapperReportResult.report_md}</p>
            </div>
          )}
        </div>
      )}

      {validationMatrixResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Wrapper Validation Matrix</h3>
          <div
            style={{
              padding: 12,
              background: validationMatrixResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {validationMatrixResult.ok ? "OK" : "Failed"}
          </div>

          {validationMatrixResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Summary</h4>
              <ul>
                <li>Matrix Total: {validationMatrixResult.metrics.matrix_total}</li>
                <li>Promotable Total: {validationMatrixResult.metrics.promotable_total}</li>
                <li>Blocked Total: {validationMatrixResult.metrics.blocked_total}</li>
                <li>Manual Review Total: {validationMatrixResult.metrics.manual_review_total}</li>
              </ul>
            </div>
          )}

          {validationMatrixResult.rows && validationMatrixResult.rows.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Compatibility Matrix</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Function</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Category</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Exists</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Candidate</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Sandbox</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Subject</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Readiness</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Next Step</th>
                  </tr>
                </thead>
                <tbody>
                  {validationMatrixResult.rows.map((row, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{row.function_name}</td>
                      <td style={{ padding: 8 }}>{row.category}</td>
                      <td style={{ padding: 8 }}>{row.exists ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{row.wrapper_candidate ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{row.sandbox_passed ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>{row.subject_passed ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}>
                        <span style={{
                          color: row.readiness === "PROMOTABLE_TO_TEMPLATE" ? "green" :
                                 row.readiness === "BLOCKED" ? "red" :
                                 row.readiness === "MANUAL_REVIEW_REQUIRED" ? "orange" : "inherit"
                        }}>
                          {row.readiness}
                        </span>
                      </td>
                      <td style={{ padding: 8 }}>{row.recommended_next_step}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {validationMatrixResult.outputs && validationMatrixResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Files</h4>
              <ul>
                {validationMatrixResult.outputs.map((output, idx) => (
                  <li key={idx}><code>{output}</code></li>
                ))}
              </ul>
            </div>
          )}

          {validationMatrixResult.warnings && validationMatrixResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {validationMatrixResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {validationMatrixResult.errors && validationMatrixResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {validationMatrixResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {templateLibraryResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>DPABI Template Library</h3>
          <div
            style={{
              padding: 12,
              background: templateLibraryResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {templateLibraryResult.ok ? "OK" : "Failed"}
          </div>

          {templateLibraryResult.metrics && (
            <div style={{ marginTop: 12 }}>
              <h4>Summary</h4>
              <ul>
                <li>Templates Total: {templateLibraryResult.metrics.templates_total}</li>
                <li>Skipped Total: {templateLibraryResult.metrics.skipped_total}</li>
              </ul>
            </div>
          )}

          {templateLibraryResult.templates && templateLibraryResult.templates.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Templates</h4>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr style={{ borderBottom: "1px solid #ccc" }}>
                    <th style={{ textAlign: "left", padding: 8 }}>Template ID</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Function</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Type</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Requires Approval</th>
                    <th style={{ textAlign: "left", padding: 8 }}>Path</th>
                  </tr>
                </thead>
                <tbody>
                  {templateLibraryResult.templates.map((item, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={{ padding: 8 }}>{item.template_id}</td>
                      <td style={{ padding: 8 }}>{item.function_name}</td>
                      <td style={{ padding: 8 }}>{item.template_type}</td>
                      <td style={{ padding: 8 }}>{item.requires_approval ? "Yes" : "No"}</td>
                      <td style={{ padding: 8 }}><code>{item.template_path}</code></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {templateLibraryResult.skipped && templateLibraryResult.skipped.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Skipped Functions</h4>
              <ul>
                {templateLibraryResult.skipped.map((item, idx) => (
                  <li key={idx}>
                    {item.function_name}: {item.reason}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {templateLibraryResult.outputs && templateLibraryResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Files</h4>
              <ul>
                {templateLibraryResult.outputs.map((output, idx) => (
                  <li key={idx}><code>{output}</code></li>
                ))}
              </ul>
            </div>
          )}

          {templateLibraryResult.warnings && templateLibraryResult.warnings.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Warnings</h4>
              <ul>
                {templateLibraryResult.warnings.map((w, idx) => (
                  <li key={idx} style={{ color: "orange" }}>{w}</li>
                ))}
              </ul>
            </div>
          )}

          {templateLibraryResult.errors && templateLibraryResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {templateLibraryResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {templatesList.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <h3>Available Templates</h3>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ borderBottom: "1px solid #ccc" }}>
                <th style={{ textAlign: "left", padding: 8 }}>Template ID</th>
                <th style={{ textAlign: "left", padding: 8 }}>Function</th>
                <th style={{ textAlign: "left", padding: 8 }}>Type</th>
                <th style={{ textAlign: "left", padding: 8 }}>Requires Approval</th>
              </tr>
            </thead>
            <tbody>
              {templatesList.map((item, idx) => (
                <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={{ padding: 8 }}>{item.template_id}</td>
                  <td style={{ padding: 8 }}>{item.function_name}</td>
                  <td style={{ padding: 8 }}>{item.template_type}</td>
                  <td style={{ padding: 8 }}>{item.requires_approval ? "Yes" : "No"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {templateInstanceResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>Template Instance Result</h3>
          <div
            style={{
              padding: 12,
              background: templateInstanceResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {templateInstanceResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Template ID:</strong> {templateInstanceResult.template_id}</p>
          <p><strong>Instance ID:</strong> {templateInstanceResult.instance_id}</p>
          <p><strong>Run ID:</strong> {templateInstanceResult.run_id}</p>
          <p><strong>Mode:</strong> {templateInstanceResult.mode}</p>

          {templateInstanceResult.pipeline_path && (
            <p><strong>Pipeline:</strong> <code>{templateInstanceResult.pipeline_path}</code></p>
          )}
          {templateInstanceResult.manifest_path && (
            <p><strong>Manifest:</strong> <code>{templateInstanceResult.manifest_path}</code></p>
          )}
          {templateInstanceResult.review_path && (
            <p><strong>Review:</strong> <code>{templateInstanceResult.review_path}</code></p>
          )}

          {templateInstanceResult.outputs && templateInstanceResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Files</h4>
              <ul>
                {templateInstanceResult.outputs.map((output, idx) => (
                  <li key={idx}><code>{output}</code></li>
                ))}
              </ul>
            </div>
          )}

          {templateInstanceResult.errors && templateInstanceResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {templateInstanceResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {templateExecuteResult && (
        <div style={{ marginBottom: 24 }}>
          <h3>Template Execution Result</h3>
          <div
            style={{
              padding: 12,
              background: templateExecuteResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 12,
            }}
          >
            <strong>Status:</strong> {templateExecuteResult.ok ? "OK" : "Failed"}
          </div>

          <p><strong>Instance ID:</strong> {templateExecuteResult.instance_id}</p>
          <p><strong>Run ID:</strong> {templateExecuteResult.run_id}</p>
          <p><strong>Status:</strong> {templateExecuteResult.status}</p>
          <p><strong>Mode:</strong> {templateExecuteResult.mode}</p>

          {templateExecuteResult.outputs && templateExecuteResult.outputs.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Generated Files</h4>
              <ul>
                {templateExecuteResult.outputs.map((output, idx) => (
                  <li key={idx}><code>{output}</code></li>
                ))}
              </ul>
            </div>
          )}

          {templateExecuteResult.execution_summary && (
            <div style={{ marginTop: 12 }}>
              <h4>Execution Summary</h4>
              <p><strong>Status:</strong> {templateExecuteResult.execution_summary.status}</p>
            </div>
          )}

          {templateExecuteResult.errors && templateExecuteResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {templateExecuteResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
