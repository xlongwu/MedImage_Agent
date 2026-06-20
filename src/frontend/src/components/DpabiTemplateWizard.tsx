import React, { useState, useEffect } from "react";
import {
  getDpabiTemplateWizardOptions,
  previewDpabiTemplateWizard,
  createDpabiTemplateWizardInstance,
  executeDpabiTemplate,
} from "../lib/api/legacy";

interface TemplateItem {
  template_id?: string;
  function_name?: string;
  template_type?: string;
  requires_approval?: boolean;
}

interface WizardOptions {
  ok?: boolean;
  templates?: TemplateItem[];
  functions?: string[];
  default_subjects?: string[];
  default_fwhm?: number[];
  default_scheduler?: {
    mode?: string;
    max_workers?: number;
    matlab_max_workers?: number;
  };
  safety?: {
    synthetic_only?: boolean;
    requires_approval?: boolean;
    approved_by_default?: boolean;
    full_dpabi_execution?: boolean;
    dparsf_run_allowed?: boolean;
    dparsfa_run_allowed?: boolean;
    dpabi_gui_allowed?: boolean;
  };
  warnings?: string[];
  errors?: string[];
}

interface PreviewResult {
  ok?: boolean;
  mode?: string;
  will_execute?: boolean;
  template_id?: string;
  instance_id?: string | null;
  run_id?: string | null;
  function_name?: string;
  fwhm?: number[];
  subjects?: string[];
  scheduler?: {
    mode?: string;
    max_workers?: number;
    matlab_max_workers?: number;
  };
  safety?: {
    requires_approval?: boolean;
    approved?: boolean;
    execution_allowed?: boolean;
    synthetic_only?: boolean;
    full_dpabi_execution?: boolean;
    dparsf_run_allowed?: boolean;
    dparsfa_run_allowed?: boolean;
    dpabi_gui_allowed?: boolean;
    rawdata_modified?: boolean;
    files_deleted?: boolean;
  };
  outputs?: string[];
  warnings?: string[];
  errors?: string[];
}

interface CreateResult {
  ok?: boolean;
  mode?: string;
  template_id?: string;
  instance_id?: string;
  run_id?: string;
  pipeline_path?: string;
  manifest_path?: string;
  review_path?: string;
  outputs?: string[];
  errors?: string[];
  warnings?: string[];
}

interface ExecuteResult {
  ok?: boolean;
  mode?: string;
  instance_id?: string;
  run_id?: string;
  status?: string;
  execution_summary?: {
    ok?: boolean;
    status?: string;
  };
  errors?: string[];
}

interface DpabiTemplateWizardProps {
  baseUrl: string;
}

export function DpabiTemplateWizard({ baseUrl }: DpabiTemplateWizardProps) {
  const [options, setOptions] = useState<WizardOptions | null>(null);
  const [loadingOptions, setLoadingOptions] = useState(false);

  const [templateId, setTemplateId] = useState<string>("dpabi_y_smooth_subject_wrapper_template");
  const [instanceId, setInstanceId] = useState<string>("instance_wizard_001");
  const [runId, setRunId] = useState<string>("");
  const [functionName, setFunctionName] = useState<string>("y_Smooth");
  const [fwhmX, setFwhmX] = useState<number>(4);
  const [fwhmY, setFwhmY] = useState<number>(4);
  const [fwhmZ, setFwhmZ] = useState<number>(4);
  const [subjects, setSubjects] = useState<string>("sub-001, sub-002");
  const [schedulerMode, setSchedulerMode] = useState<string>("local_parallel");
  const [maxWorkers, setMaxWorkers] = useState<number>(2);
  const [matlabMaxWorkers, setMatlabMaxWorkers] = useState<number>(1);
  const [approvedBy, setApprovedBy] = useState<string>("local-user");

  const [previewResult, setPreviewResult] = useState<PreviewResult | null>(null);
  const [loadingPreview, setLoadingPreview] = useState(false);

  const [createResult, setCreateResult] = useState<CreateResult | null>(null);
  const [loadingCreate, setLoadingCreate] = useState(false);

  const [executeResult, setExecuteResult] = useState<ExecuteResult | null>(null);
  const [loadingExecute, setLoadingExecute] = useState(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleLoadOptions();
  }, [baseUrl]);

  const handleLoadOptions = async () => {
    setLoadingOptions(true);
    setError(null);
    try {
      const result = (await getDpabiTemplateWizardOptions(baseUrl)) as WizardOptions;
      setOptions(result);
      if (result.default_subjects) {
        setSubjects(result.default_subjects.join(", "));
      }
      if (result.default_fwhm) {
        setFwhmX(result.default_fwhm[0]);
        setFwhmY(result.default_fwhm[1]);
        setFwhmZ(result.default_fwhm[2]);
      }
      if (result.default_scheduler) {
        setSchedulerMode(result.default_scheduler.mode || "local_parallel");
        setMaxWorkers(result.default_scheduler.max_workers || 2);
        setMatlabMaxWorkers(result.default_scheduler.matlab_max_workers || 1);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingOptions(false);
    }
  };

  const getPayload = () => ({
    template_id: templateId,
    instance_id: instanceId || null,
    run_id: runId || null,
    function_name: functionName,
    fwhm: [fwhmX, fwhmY, fwhmZ],
    subjects: subjects
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
    scheduler: {
      mode: schedulerMode,
      max_workers: maxWorkers,
      matlab_max_workers: matlabMaxWorkers,
    },
  });

  const handlePreview = async () => {
    setLoadingPreview(true);
    setError(null);
    setPreviewResult(null);
    try {
      const result = (await previewDpabiTemplateWizard(baseUrl, getPayload())) as PreviewResult;
      setPreviewResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingPreview(false);
    }
  };

  const handleCreate = async () => {
    setLoadingCreate(true);
    setError(null);
    setCreateResult(null);
    try {
      const result = (await createDpabiTemplateWizardInstance(
        baseUrl,
        getPayload(),
      )) as CreateResult;
      setCreateResult(result);
      if (result.instance_id) {
        setInstanceId(result.instance_id);
      }
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingCreate(false);
    }
  };

  const handleExecute = async () => {
    if (!createResult?.instance_id) {
      setError("Please create an instance first.");
      return;
    }
    setLoadingExecute(true);
    setError(null);
    setExecuteResult(null);
    try {
      const result = (await executeDpabiTemplate(baseUrl, {
        instance_id: createResult.instance_id,
        approved: true,
        approved_by: approvedBy,
      })) as ExecuteResult;
      setExecuteResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingExecute(false);
    }
  };

  return (
    <div style={{ padding: 16, borderTop: "2px solid #2196f3", marginTop: 24 }}>
      <h2>DPABI Template Wizard</h2>

      <div style={{ marginBottom: 16 }}>
        <button onClick={handleLoadOptions} disabled={loadingOptions} style={{ marginRight: 8 }}>
          {loadingOptions ? "Loading..." : "Reload Options"}
        </button>
      </div>

      {options?.safety && (
        <div
          style={{
            padding: 12,
            background: "#e3f2fd",
            borderRadius: 4,
            marginBottom: 16,
          }}
        >
          <h4>Safety Gates</h4>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>Synthetic only: {options.safety.synthetic_only ? "Yes" : "No"}</li>
            <li>Requires approval: {options.safety.requires_approval ? "Yes" : "No"}</li>
            <li>Full DPABI execution: {options.safety.full_dpabi_execution ? "Yes" : "No"}</li>
            <li>DPARSF_run allowed: {options.safety.dparsf_run_allowed ? "Yes" : "No"}</li>
            <li>DPABI GUI allowed: {options.safety.dpabi_gui_allowed ? "Yes" : "No"}</li>
          </ul>
        </div>
      )}

      <div style={{ marginBottom: 16 }}>
        <h3>Template Configuration</h3>

        <label style={{ display: "block", marginBottom: 8 }}>
          Template ID:
          <select
            value={templateId}
            onChange={(e) => setTemplateId(e.target.value)}
            style={{ marginLeft: 8, width: 300 }}
          >
            {options?.templates?.map((t) => (
              <option key={t.template_id} value={t.template_id}>
                {t.template_id}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Instance ID:
          <input
            type="text"
            value={instanceId}
            onChange={(e) => setInstanceId(e.target.value)}
            style={{ marginLeft: 8, width: 250 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Run ID (optional):
          <input
            type="text"
            value={runId}
            onChange={(e) => setRunId(e.target.value)}
            style={{ marginLeft: 8, width: 250 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Function Name:
          <select
            value={functionName}
            onChange={(e) => setFunctionName(e.target.value)}
            style={{ marginLeft: 8, width: 150 }}
          >
            {options?.functions?.map((fn) => (
              <option key={fn} value={fn}>
                {fn}
              </option>
            ))}
          </select>
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          FWHM (X, Y, Z):
          <input
            type="number"
            value={fwhmX}
            onChange={(e) => setFwhmX(parseFloat(e.target.value) || 0)}
            style={{ marginLeft: 8, width: 60 }}
          />
          <input
            type="number"
            value={fwhmY}
            onChange={(e) => setFwhmY(parseFloat(e.target.value) || 0)}
            style={{ marginLeft: 4, width: 60 }}
          />
          <input
            type="number"
            value={fwhmZ}
            onChange={(e) => setFwhmZ(parseFloat(e.target.value) || 0)}
            style={{ marginLeft: 4, width: 60 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Subjects (comma-separated):
          <input
            type="text"
            value={subjects}
            onChange={(e) => setSubjects(e.target.value)}
            style={{ marginLeft: 8, width: 300 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Scheduler Mode:
          <select
            value={schedulerMode}
            onChange={(e) => setSchedulerMode(e.target.value)}
            style={{ marginLeft: 8, width: 150 }}
          >
            <option value="local_parallel">local_parallel</option>
            <option value="sequential">sequential</option>
          </select>
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Max Workers (1-8):
          <input
            type="number"
            min={1}
            max={8}
            value={maxWorkers}
            onChange={(e) => setMaxWorkers(parseInt(e.target.value) || 1)}
            style={{ marginLeft: 8, width: 60 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          MATLAB Max Workers (1-{maxWorkers}):
          <input
            type="number"
            min={1}
            max={maxWorkers}
            value={matlabMaxWorkers}
            onChange={(e) => setMatlabMaxWorkers(parseInt(e.target.value) || 1)}
            style={{ marginLeft: 8, width: 60 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Approved By:
          <input
            type="text"
            value={approvedBy}
            onChange={(e) => setApprovedBy(e.target.value)}
            style={{ marginLeft: 8, width: 150 }}
          />
        </label>
      </div>

      <div style={{ marginBottom: 16 }}>
        <button
          onClick={handlePreview}
          disabled={loadingPreview}
          style={{ backgroundColor: "#2196f3", color: "white", marginRight: 8 }}
        >
          {loadingPreview ? "Previewing..." : "Preview"}
        </button>
        <button
          onClick={handleCreate}
          disabled={loadingCreate}
          style={{ backgroundColor: "#ff9800", color: "white", marginRight: 8 }}
        >
          {loadingCreate ? "Creating..." : "Create Instance"}
        </button>
        <button
          onClick={handleExecute}
          disabled={loadingExecute || !createResult?.instance_id}
          style={{ backgroundColor: "#e91e63", color: "white" }}
        >
          {loadingExecute ? "Executing..." : "Execute (Approved)"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {previewResult && (
        <div style={{ marginBottom: 24, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
          <h3>Preview Result</h3>
          <div
            style={{
              padding: 8,
              background: previewResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            <strong>Status:</strong> {previewResult.ok ? "OK" : "Failed"}
          </div>
          <p>
            <strong>Template ID:</strong> {previewResult.template_id}
          </p>
          <p>
            <strong>Instance ID:</strong> {previewResult.instance_id}
          </p>
          <p>
            <strong>Function:</strong> {previewResult.function_name}
          </p>
          <p>
            <strong>Subjects:</strong> {previewResult.subjects?.join(", ")}
          </p>
          <p>
            <strong>Will Execute:</strong> {previewResult.will_execute ? "Yes" : "No"}
          </p>

          {previewResult.safety && (
            <div style={{ marginTop: 12 }}>
              <h4>Safety Status</h4>
              <ul>
                <li>Requires approval: {previewResult.safety.requires_approval ? "Yes" : "No"}</li>
                <li>Approved: {previewResult.safety.approved ? "Yes" : "No"}</li>
                <li>Execution allowed: {previewResult.safety.execution_allowed ? "Yes" : "No"}</li>
                <li>Synthetic only: {previewResult.safety.synthetic_only ? "Yes" : "No"}</li>
              </ul>
            </div>
          )}

          {previewResult.errors && previewResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {previewResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {createResult && (
        <div style={{ marginBottom: 24, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
          <h3>Create Instance Result</h3>
          <div
            style={{
              padding: 8,
              background: createResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            <strong>Status:</strong> {createResult.ok ? "OK" : "Failed"}
          </div>
          <p>
            <strong>Template ID:</strong> {createResult.template_id}
          </p>
          <p>
            <strong>Instance ID:</strong> {createResult.instance_id}
          </p>
          <p>
            <strong>Run ID:</strong> {createResult.run_id}
          </p>

          {createResult.pipeline_path && (
            <p>
              <strong>Pipeline:</strong> <code>{createResult.pipeline_path}</code>
            </p>
          )}
          {createResult.manifest_path && (
            <p>
              <strong>Manifest:</strong> <code>{createResult.manifest_path}</code>
            </p>
          )}
          {createResult.review_path && (
            <p>
              <strong>Review:</strong> <code>{createResult.review_path}</code>
            </p>
          )}

          {createResult.errors && createResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {createResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {executeResult && (
        <div style={{ marginBottom: 24, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
          <h3>Execute Result</h3>
          <div
            style={{
              padding: 8,
              background: executeResult.ok ? "#e6f7e6" : "#ffe6e6",
              borderRadius: 4,
              marginBottom: 8,
            }}
          >
            <strong>Status:</strong> {executeResult.ok ? "OK" : "Failed"}
          </div>
          <p>
            <strong>Instance ID:</strong> {executeResult.instance_id}
          </p>
          <p>
            <strong>Run ID:</strong> {executeResult.run_id}
          </p>
          <p>
            <strong>Status:</strong> {executeResult.status}
          </p>

          {executeResult.execution_summary && (
            <div style={{ marginTop: 12 }}>
              <h4>Execution Summary</h4>
              <p>Status: {executeResult.execution_summary.status}</p>
            </div>
          )}

          {executeResult.errors && executeResult.errors.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4>Errors</h4>
              <ul>
                {executeResult.errors.map((e, idx) => (
                  <li key={idx} style={{ color: "red" }}>
                    {e}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
