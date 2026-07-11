import { useEffect, useMemo, useState } from "react";

import {
  executeNativeFullPreprocessing,
  executeReviewedPreprocessingPipeline,
  getLatestNativeFullPreprocessingRun,
  getNativeFullPreprocessingReport,
  getNativeFullPreprocessingValidation,
  runNativeFullPreprocessingDryRun,
} from "../../lib/api/preprocessing";
import type {
  NativeFullPreprocConfirmations,
  NativeFullPreprocRequest,
  NativeFullPreprocResponse,
  NativeFullStageApiResult,
  PreprocessingPipelineExecuteRequest,
  PreprocessingPipelineExecuteResponse,
  PreprocessingPipelineStageResult,
} from "../../types";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  SegmentedControl,
  Table,
  TableEmpty,
} from "../../components/ui";
import type { BadgeProps } from "../../components/ui";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import styles from "./PreprocessingWorkspace.module.css";

type Profile = NonNullable<PreprocessingPipelineExecuteRequest["pipeline_profile"]>;
type ConfirmationKey = keyof NonNullable<PreprocessingPipelineExecuteRequest["confirmations"]>;
type NativeConfirmationKey = keyof NativeFullPreprocConfirmations;
type NativeAction = "" | "dry-run" | "execute" | "validation" | "report";

type Props = {
  baseUrl: string;
  hasPreprocessingRun: boolean;
  inventory: ProjectInventory;
  preprocessingRunId?: string | null;
  projectId: string | null;
  onOpenDataConversion: () => void;
};

const PROFILE_OPTIONS = [
  { label: "Minimal FC", value: "fc_minimal" },
  { label: "DPARSFA-like", value: "dparsfa_like" },
  { label: "Custom", value: "custom" },
];

const CONFIRMATIONS: Array<{
  key: ConfirmationKey;
  label: string;
  detail: string;
}> = [
  {
    key: "confirm_rawdata_readonly",
    label: "Rawdata stays read-only",
    detail: "Only project workspace derivatives may be written.",
  },
  {
    key: "confirm_reviewed_execution",
    label: "Reviewed execution request",
    detail: "The request uses the backend reviewed orchestrator.",
  },
  {
    key: "confirm_external_tools_if_needed",
    label: "External-tool gates acknowledged",
    detail: "SPM/MATLAB stages remain blocked without backend approval and env gates.",
  },
  {
    key: "confirm_research_use_only",
    label: "Research use only",
    detail: "No clinical diagnosis, treatment, or decision-support claim.",
  },
  {
    key: "confirm_no_clinical_use",
    label: "No clinical use",
    detail: "Outputs require scientific review before interpretation.",
  },
];

const NATIVE_CONFIRMATIONS: Array<{
  key: NativeConfirmationKey;
  label: string;
  detail: string;
}> = [
  {
    key: "confirm_reviewed_native_execution",
    label: "Reviewed native execution",
    detail: "The full native runner receives a reviewed request, not free-form commands.",
  },
  {
    key: "confirm_rawdata_readonly",
    label: "Native rawdata read-only",
    detail: "Native preprocessing writes only derivatives under the project workspace.",
  },
  {
    key: "confirm_no_external_tools",
    label: "No external tools",
    detail: "MATLAB, SPM, DPABI, shell converters, and third-party tools remain disabled.",
  },
  {
    key: "confirm_research_use_only",
    label: "Native research use only",
    detail: "Outputs are research artifacts and are not clinical evidence.",
  },
  {
    key: "confirm_no_clinical_use",
    label: "Native no clinical use",
    detail: "No diagnosis, treatment, or decision-support claim is made.",
  },
];

const STAGE_ROWS: Array<{
  stageId: string;
  label: string;
  backend: string;
  fcMinimal: boolean;
  dparsfaLike: boolean;
  note: string;
  state: "computed" | "external" | "optional" | "report" | "gate";
}> = [
  {
    stageId: "input_validation",
    label: "Input inventory",
    backend: "registry",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Requires registered converted BIDS/NIfTI input.",
    state: "gate",
  },
  {
    stageId: "dummy_scan_removal",
    label: "Dummy scan removal",
    backend: "auto",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Skipped unless requested by reviewed parameters.",
    state: "optional",
  },
  {
    stageId: "realignment",
    label: "Realignment",
    backend: "Native Python",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Native default uses the current simplified motion-correction kernel.",
    state: "computed",
  },
  {
    stageId: "t1_coregistration",
    label: "T1 coregistration",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional affine coregistration; external SPM remains explicit and gated.",
    state: "optional",
  },
  {
    stageId: "segmentation",
    label: "Segmentation",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional intensity-based segmentation for WM/CSF nuisance masks.",
    state: "optional",
  },
  {
    stageId: "normalization",
    label: "Normalization",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional affine normalization; nonlinear SPM-equivalence is not claimed.",
    state: "optional",
  },
  {
    stageId: "spatial_smoothing",
    label: "Smoothing",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional native smoothing; external SPM smoothing stays opt-in.",
    state: "optional",
  },
  {
    stageId: "nuisance_regression",
    label: "Nuisance regression",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Consumes realigned BOLD and motion parameters.",
    state: "computed",
  },
  {
    stageId: "temporal_filtering",
    label: "Temporal filtering",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Requires TR from sidecar or explicit reviewed value.",
    state: "computed",
  },
  {
    stageId: "alff_falff",
    label: "ALFF / fALFF",
    backend: "Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional derived maps; computed status is not validation.",
    state: "optional",
  },
  {
    stageId: "reho",
    label: "ReHo",
    backend: "Python",
    fcMinimal: false,
    dparsfaLike: true,
    note: "Optional derived map with CPU golden validation.",
    state: "optional",
  },
  {
    stageId: "functional_connectivity",
    label: "Functional connectivity",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Formal FC requires a real atlas artifact or reviewed atlas path.",
    state: "computed",
  },
  {
    stageId: "subject_qc",
    label: "Subject QC",
    backend: "registry",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Summarizes computed artifacts without inventing pass/fail state.",
    state: "report",
  },
  {
    stageId: "group_summary",
    label: "Pipeline report",
    backend: "report",
    fcMinimal: true,
    dparsfaLike: true,
    note: "Exports report and validation records when backend evidence exists.",
    state: "report",
  },
];

const defaultConfirmations: Record<ConfirmationKey, boolean> = {
  confirm_rawdata_readonly: false,
  confirm_reviewed_execution: false,
  confirm_external_tools_if_needed: false,
  confirm_research_use_only: false,
  confirm_no_clinical_use: false,
};

const defaultNativeConfirmations: Record<NativeConfirmationKey, boolean> = {
  confirm_reviewed_native_execution: false,
  confirm_rawdata_readonly: false,
  confirm_no_external_tools: false,
  confirm_research_use_only: false,
  confirm_no_clinical_use: false,
};

export function PreprocessingReviewedFlow({
  baseUrl,
  hasPreprocessingRun,
  inventory,
  onOpenDataConversion,
  preprocessingRunId,
  projectId,
}: Props) {
  const [profile, setProfile] = useState<Profile>("fc_minimal");
  const [atlasPath, setAtlasPath] = useState("");
  const [labelsPath, setLabelsPath] = useState("");
  const [fallbackTr, setFallbackTr] = useState("");
  const [previewLimit, setPreviewLimit] = useState("");
  const [includeGlobalSignal, setIncludeGlobalSignal] = useState(false);
  const [confirmations, setConfirmations] =
    useState<Record<ConfirmationKey, boolean>>(defaultConfirmations);
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<PreprocessingPipelineExecuteResponse | null>(null);
  const [error, setError] = useState("");
  const [nativeConfirmations, setNativeConfirmations] =
    useState<Record<NativeConfirmationKey, boolean>>(defaultNativeConfirmations);
  const [nativeAction, setNativeAction] = useState<NativeAction>("");
  const [nativeResult, setNativeResult] = useState<NativeFullPreprocResponse | null>(null);
  const [nativeValidation, setNativeValidation] = useState<Record<string, unknown> | null>(null);
  const [nativeReport, setNativeReport] = useState<Record<string, unknown> | null>(null);
  const [nativeError, setNativeError] = useState("");

  const visibleStages = useMemo(
    () =>
      STAGE_ROWS.filter((stage) => {
        if (profile === "dparsfa_like") return stage.dparsfaLike;
        if (profile === "custom") return stage.fcMinimal || stage.state === "optional";
        return stage.fcMinimal;
      }),
    [profile],
  );

  const allConfirmationsChecked = CONFIRMATIONS.every((item) => confirmations[item.key]);
  const allNativeConfirmationsChecked = NATIVE_CONFIRMATIONS.every(
    (item) => nativeConfirmations[item.key],
  );
  const canSubmit = Boolean(
    projectId && preprocessingRunId && allConfirmationsChecked && !submitting,
  );
  const nativeRunId = nativeResult?.run_id || preprocessingRunId || "";
  const canNativeDryRun = Boolean(projectId && nativeRunId && !nativeAction);
  const canNativeExecute = Boolean(canNativeDryRun && allNativeConfirmationsChecked);
  const canRefreshNative = Boolean(projectId && nativeRunId && !nativeAction);
  const fcResult = result?.stage_results.find(
    (stage) => stage.stage_id === "functional_connectivity",
  );
  const nativeFcResult = nativeResult?.stage_results.find(
    (stage) => stage.stage_id === "functional_connectivity",
  );

  useEffect(() => {
    if (!projectId || nativeResult) return;
    let cancelled = false;
    void Promise.resolve(getLatestNativeFullPreprocessingRun(baseUrl, projectId))
      .then((response) => {
        if (!cancelled && response?.run_id) {
          setNativeResult(response);
        }
      })
      .catch(() => {
        // The latest native manifest is optional; an empty project should stay quiet.
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl, projectId, nativeResult]);

  const executeReviewedFlow = async () => {
    if (!projectId || !preprocessingRunId || !canSubmit) return;
    setSubmitting(true);
    setError("");
    setResult(null);
    try {
      const response = await executeReviewedPreprocessingPipeline(
        baseUrl,
        projectId,
        preprocessingRunId,
        buildReviewedRequest({
          atlasPath,
          confirmations,
          fallbackTr,
          includeGlobalSignal,
          labelsPath,
          previewLimit,
          profile,
        }),
      );
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  const runNativeDryRun = async () => {
    if (!projectId || !nativeRunId || !canNativeDryRun) return;
    setNativeAction("dry-run");
    setNativeError("");
    setNativeValidation(null);
    setNativeReport(null);
    try {
      const response = await runNativeFullPreprocessingDryRun(
        baseUrl,
        projectId,
        buildNativeRequest({
          atlasPath,
          fallbackTr,
          includeGlobalSignal,
          labelsPath,
          preprocessingRunId: nativeRunId,
          profile,
        }),
      );
      setNativeResult(response);
    } catch (err) {
      setNativeError(err instanceof Error ? err.message : String(err));
    } finally {
      setNativeAction("");
    }
  };

  const executeNativeFlow = async () => {
    if (!projectId || !nativeRunId || !canNativeExecute) return;
    setNativeAction("execute");
    setNativeError("");
    setNativeValidation(null);
    setNativeReport(null);
    try {
      const response = await executeNativeFullPreprocessing(
        baseUrl,
        projectId,
        buildNativeRequest({
          atlasPath,
          confirmations: nativeConfirmations,
          fallbackTr,
          includeGlobalSignal,
          labelsPath,
          preprocessingRunId: nativeRunId,
          profile,
        }),
      );
      setNativeResult(response);
    } catch (err) {
      setNativeError(err instanceof Error ? err.message : String(err));
    } finally {
      setNativeAction("");
    }
  };

  const refreshNativeValidation = async () => {
    if (!projectId || !nativeRunId || !canRefreshNative) return;
    setNativeAction("validation");
    setNativeError("");
    try {
      setNativeValidation(await getNativeFullPreprocessingValidation(baseUrl, projectId, nativeRunId));
    } catch (err) {
      setNativeError(err instanceof Error ? err.message : String(err));
    } finally {
      setNativeAction("");
    }
  };

  const refreshNativeReport = async () => {
    if (!projectId || !nativeRunId || !canRefreshNative) return;
    setNativeAction("report");
    setNativeError("");
    try {
      setNativeReport(await getNativeFullPreprocessingReport(baseUrl, projectId, nativeRunId));
    } catch (err) {
      setNativeError(err instanceof Error ? err.message : String(err));
    } finally {
      setNativeAction("");
    }
  };

  return (
    <section className={styles.reviewedFlow} aria-label="Reviewed preprocessing flow">
      <ConversionHandoffCard inventory={inventory} onOpenDataConversion={onOpenDataConversion} />

      <Card className={styles.pipelineBuilderCard} tone="muted">
        <div className={styles.sectionHeader}>
          <div>
            <h3>Pipeline builder</h3>
            <p>Profile, backend policy, atlas, nuisance, and filtering settings for review.</p>
          </div>
          <Badge tone="info">Reviewed</Badge>
        </div>
        <SegmentedControl
          aria-label="Preprocessing pipeline profile"
          options={PROFILE_OPTIONS}
          value={profile}
          onChange={(value) => setProfile(value as Profile)}
        />
        <div className={styles.builderGrid}>
          <label className={styles.fieldShell}>
            <span>Atlas path</span>
            <input
              value={atlasPath}
              onChange={(event) => setAtlasPath(event.target.value)}
              placeholder="registered atlas artifact or reviewed local path"
            />
          </label>
          <label className={styles.fieldShell}>
            <span>Labels path</span>
            <input
              value={labelsPath}
              onChange={(event) => setLabelsPath(event.target.value)}
              placeholder="TSV or JSON labels"
            />
          </label>
          <label className={styles.fieldShell}>
            <span>Fallback TR</span>
            <input
              inputMode="decimal"
              value={fallbackTr}
              onChange={(event) => setFallbackTr(event.target.value)}
              placeholder="blank unless explicitly reviewed"
            />
          </label>
          <label className={styles.fieldShell}>
            <span>Preview limit</span>
            <input
              inputMode="numeric"
              value={previewLimit}
              onChange={(event) => setPreviewLimit(event.target.value)}
              placeholder="blank for full discovered scope"
            />
          </label>
        </div>
        <label className={styles.inlineCheck}>
          <input
            type="checkbox"
            checked={includeGlobalSignal}
            onChange={(event) => setIncludeGlobalSignal(event.target.checked)}
          />
          <span>Include global signal regressor</span>
        </label>
        <Table caption="Reviewed preprocessing stages">
          <thead>
            <tr>
              <th>Stage</th>
              <th>Backend</th>
              <th>State</th>
              <th>Review note</th>
            </tr>
          </thead>
          <tbody>
            {visibleStages.map((stage) => (
              <tr key={stage.stageId}>
                <td>{stage.label}</td>
                <td>{stage.backend}</td>
                <td>
                  <Badge tone={stageStateTone(stage.state)} size="sm">
                    {stageStateLabel(stage.state)}
                  </Badge>
                </td>
                <td>{stage.note}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card className={styles.executionGateCard}>
        <div className={styles.sectionHeader}>
          <div>
            <h3>Reviewed execution gate</h3>
            <p>All confirmations are explicit before the backend orchestrator can be called.</p>
          </div>
          <Badge tone={canSubmit ? "success" : "warning"}>{canSubmit ? "Ready" : "Blocked"}</Badge>
        </div>
        <div className={styles.gateSummary} aria-label="Reviewed gate readiness">
          <div>
            <span>Project</span>
            <strong>{projectId ? "Selected" : "Missing"}</strong>
          </div>
          <div>
            <span>Preprocessing run</span>
            <strong>
              {preprocessingRunId ?? (hasPreprocessingRun ? "ID unavailable" : "Required")}
            </strong>
          </div>
          <div>
            <span>Profile</span>
            <strong>{profileLabel(profile)}</strong>
          </div>
        </div>
        <div className={styles.confirmationList} aria-label="Reviewed execution confirmations">
          {CONFIRMATIONS.map((item) => (
            <label className={styles.confirmationItem} key={item.key}>
              <input
                type="checkbox"
                checked={confirmations[item.key]}
                onChange={() =>
                  setConfirmations((current) => ({
                    ...current,
                    [item.key]: !current[item.key],
                  }))
                }
              />
              <span>
                <strong>{item.label}</strong>
                <small>{item.detail}</small>
              </span>
            </label>
          ))}
        </div>
        <div className={styles.reviewedActions}>
          <Button variant="primary" onClick={executeReviewedFlow} disabled={!canSubmit}>
            {submitting ? "Submitting..." : "Submit reviewed execution"}
          </Button>
          <span>
            {preprocessingRunId
              ? "Backend status, artifacts, and report generation remain authoritative."
              : "Create or restore a preprocessing run before execution can be submitted."}
          </span>
        </div>
        {error ? <div className={styles.inlineError}>{error}</div> : null}
      </Card>

      <NativeFullWorkflowCard
        allConfirmationsChecked={allNativeConfirmationsChecked}
        canDryRun={canNativeDryRun}
        canExecute={canNativeExecute}
        canRefresh={canRefreshNative}
        confirmations={nativeConfirmations}
        error={nativeError}
        onConfirmationToggle={(key) =>
          setNativeConfirmations((current) => ({ ...current, [key]: !current[key] }))
        }
        onDryRun={runNativeDryRun}
        onExecute={executeNativeFlow}
        onRefreshReport={refreshNativeReport}
        onRefreshValidation={refreshNativeValidation}
        pendingAction={nativeAction}
        report={nativeReport}
        result={nativeResult}
        runId={nativeRunId}
        validation={nativeValidation}
      />

      {result || !nativeResult ? <PipelineDashboard result={result} /> : null}
      <FcResultsPanel
        atlasPath={atlasPath}
        baseUrl={baseUrl}
        fcResult={fcResult}
        nativeFcResult={nativeFcResult}
        nativeResult={nativeResult}
        preprocessingRunId={preprocessingRunId}
        projectId={projectId}
        result={result}
      />
    </section>
  );
}

function ConversionHandoffCard({
  inventory,
  onOpenDataConversion,
}: {
  inventory: ProjectInventory;
  onOpenDataConversion: () => void;
}) {
  return (
    <Card className={styles.handoffCard}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>DICOM conversion handoff</h3>
          <p>Converted BIDS/NIfTI evidence is the preprocessing input boundary.</p>
        </div>
        <Badge tone={inventory.hasConvertedData ? "success" : "warning"}>
          {inventory.hasConvertedData ? "Registered" : "Required"}
        </Badge>
      </div>
      <div className={styles.handoffMetrics} aria-label="DICOM conversion handoff">
        <div>
          <span>Subjects</span>
          <strong>{inventory.convertedSubjects}</strong>
        </div>
        <div>
          <span>NIfTI files</span>
          <strong>{inventory.niftiFileCount.toLocaleString()}</strong>
        </div>
        <div>
          <span>State</span>
          <strong>{inventory.dataStateLabel}</strong>
        </div>
      </div>
      <Button variant="secondary" onClick={onOpenDataConversion}>
        Review conversion input
      </Button>
    </Card>
  );
}

function NativeFullWorkflowCard({
  allConfirmationsChecked,
  canDryRun,
  canExecute,
  canRefresh,
  confirmations,
  error,
  onConfirmationToggle,
  onDryRun,
  onExecute,
  onRefreshReport,
  onRefreshValidation,
  pendingAction,
  report,
  result,
  runId,
  validation,
}: {
  allConfirmationsChecked: boolean;
  canDryRun: boolean;
  canExecute: boolean;
  canRefresh: boolean;
  confirmations: Record<NativeConfirmationKey, boolean>;
  error: string;
  onConfirmationToggle: (key: NativeConfirmationKey) => void;
  onDryRun: () => void;
  onExecute: () => void;
  onRefreshReport: () => void;
  onRefreshValidation: () => void;
  pendingAction: NativeAction;
  report: Record<string, unknown> | null;
  result: NativeFullPreprocResponse | null;
  runId: string;
  validation: Record<string, unknown> | null;
}) {
  const status = result?.status ?? "not_started";

  return (
    <Card className={styles.dashboardCard} aria-label="Native full preprocessing workflow">
      <div className={styles.sectionHeader}>
        <div>
          <h3>Native full preprocessing</h3>
          <p>Dry-run, execute, validation, and report calls use the native API boundary.</p>
        </div>
        <Badge tone={statusTone(status)}>{status}</Badge>
      </div>

      <div className={styles.gateSummary} aria-label="Native full run summary">
        <div>
          <span>Run</span>
          <strong>{runId || "Required"}</strong>
        </div>
        <div>
          <span>Artifacts</span>
          <strong>{result ? result.artifact_count : "Awaiting run"}</strong>
        </div>
        <div>
          <span>Gate</span>
          <strong>{allConfirmationsChecked ? "Ready" : "Confirmations required"}</strong>
        </div>
      </div>

      <div className={styles.confirmationList} aria-label="Native full safety confirmations">
        {NATIVE_CONFIRMATIONS.map((item) => (
          <label className={styles.confirmationItem} key={item.key}>
            <input
              type="checkbox"
              checked={confirmations[item.key]}
              onChange={() => onConfirmationToggle(item.key)}
            />
            <span>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </span>
          </label>
        ))}
      </div>

      <div className={styles.reviewedActions}>
        <Button variant="secondary" onClick={onDryRun} disabled={!canDryRun}>
          {pendingAction === "dry-run" ? "Planning..." : "Run native dry-run"}
        </Button>
        <Button variant="primary" onClick={onExecute} disabled={!canExecute}>
          {pendingAction === "execute" ? "Executing..." : "Execute native full preprocessing"}
        </Button>
        <Button variant="secondary" onClick={onRefreshValidation} disabled={!canRefresh}>
          {pendingAction === "validation" ? "Refreshing..." : "Refresh native validation"}
        </Button>
        <Button variant="secondary" onClick={onRefreshReport} disabled={!canRefresh}>
          {pendingAction === "report" ? "Refreshing..." : "Refresh native report"}
        </Button>
      </div>
      {error ? <div className={styles.inlineError}>{error}</div> : null}

      <Table caption="Native full preprocessing stage results">
        <thead>
          <tr>
            <th>Stage</th>
            <th>Status</th>
            <th>Artifacts</th>
            <th>Issue</th>
          </tr>
        </thead>
        <tbody>
          {result?.stage_results.length ? (
            result.stage_results.map((stage) => (
              <tr key={stage.stage_id}>
                <td>{stage.display_name || stage.stage_id}</td>
                <td>
                  <Badge tone={statusTone(stage.status)} size="sm">
                    {stage.status}
                  </Badge>
                </td>
                <td>{stage.output_artifacts.length}</td>
                <td>{firstNativeIssue(stage)}</td>
              </tr>
            ))
          ) : (
            <TableEmpty colSpan={4}>
              Native dry-run and execution stage rows appear after the backend returns a manifest.
            </TableEmpty>
          )}
        </tbody>
      </Table>

      <div className={styles.reportRail} aria-label="Native validation and report outputs">
        <div>
          <span>Validation</span>
          <strong>
            {formatUnknown(validation?.validation_report_path) ||
              result?.validation_report_path ||
              "Not generated"}
          </strong>
        </div>
        <div>
          <span>Report</span>
          <strong>
            {formatUnknown(report?.final_report_path) || result?.final_report_path || "Not generated"}
          </strong>
        </div>
        <div>
          <span>Blocked</span>
          <strong>
            {Array.isArray(result?.blocked_stages) ? result?.blocked_stages.length : "Awaiting run"}
          </strong>
        </div>
      </div>
    </Card>
  );
}

function PipelineDashboard({ result }: { result: PreprocessingPipelineExecuteResponse | null }) {
  if (!result) {
    return (
      <Card className={styles.dashboardCard}>
        <EmptyState
          title="No reviewed execution submitted"
          description="Dashboard rows appear only after the backend reviewed orchestrator returns persisted stage status."
        />
      </Card>
    );
  }

  return (
    <Card className={styles.dashboardCard} aria-label="Pipeline run dashboard">
      <div className={styles.sectionHeader}>
        <div>
          <h3>Pipeline run dashboard</h3>
          <p>Stage status, warnings, blocking issues, and report paths returned by the backend.</p>
        </div>
        <Badge tone={statusTone(result.status)}>{result.status}</Badge>
      </div>
      <div className={styles.statusStrip} aria-label="Reviewed execution summary">
        <SummaryMetric label="Completed" value={result.completed_stages.length} tone="success" />
        <SummaryMetric label="Blocked" value={result.blocked_stages.length} tone="warning" />
        <SummaryMetric label="Failed" value={result.failed_stages.length} tone="danger" />
        <SummaryMetric
          label="Metadata-only"
          value={result.metadata_only_stages.length}
          tone="info"
        />
        <SummaryMetric label="Preview-only" value={result.preview_only_stages.length} tone="info" />
      </div>
      <Table caption="Reviewed execution stage timeline">
        <thead>
          <tr>
            <th>Stage</th>
            <th>Status</th>
            <th>Artifacts</th>
            <th>Issue</th>
          </tr>
        </thead>
        <tbody>
          {result.stage_results.length ? (
            result.stage_results.map((stage) => (
              <tr key={stage.stage_id}>
                <td>{stage.name || stage.stage_id}</td>
                <td>
                  <Badge tone={statusTone(stage.status)} size="sm">
                    {stage.status}
                  </Badge>
                </td>
                <td>{stage.output_artifact_ids.length}</td>
                <td>{firstIssue(stage)}</td>
              </tr>
            ))
          ) : (
            <TableEmpty colSpan={4}>No stage rows were returned by the backend.</TableEmpty>
          )}
        </tbody>
      </Table>
      <div className={styles.reportRail} aria-label="Report and validation outputs">
        <div>
          <span>Report</span>
          <strong>{result.report_path || "Not generated"}</strong>
        </div>
        <div>
          <span>Validation</span>
          <strong>{result.validation_status || "Not run"}</strong>
        </div>
        <div>
          <span>Registry</span>
          <strong>{result.artifact_registry_path || "Unavailable"}</strong>
        </div>
      </div>
    </Card>
  );
}

function FcResultsPanel({
  atlasPath,
  baseUrl,
  fcResult,
  nativeFcResult,
  nativeResult,
  preprocessingRunId,
  projectId,
  result,
}: {
  atlasPath: string;
  baseUrl: string;
  fcResult?: PreprocessingPipelineStageResult;
  nativeFcResult?: NativeFullStageApiResult;
  nativeResult: NativeFullPreprocResponse | null;
  preprocessingRunId?: string | null;
  projectId: string | null;
  result: PreprocessingPipelineExecuteResponse | null;
}) {
  const nativeArtifacts = nativeFcResult?.output_artifacts ?? [];
  const nativeFcArtifacts = nativeArtifacts.filter((artifact) =>
    ["fc_matrix", "fisher_z_matrix", "roi_timeseries", "roi_labels"].includes(
      String(artifact.artifact_type || ""),
    ),
  );
  const status =
    fcResult?.status ?? nativeFcResult?.status ?? (result || nativeResult ? "not_started" : "waiting");
  const artifactCount = fcResult?.output_artifact_ids.length || nativeFcArtifacts.length || 0;
  const pipelineMatrixShape = extractMatrixShape(fcResult?.result);
  const matrixShape =
    pipelineMatrixShape !== "Awaiting backend evidence"
      ? pipelineMatrixShape
      : extractNativeMatrixShape(nativeFcResult);
  const roiCount =
    extractNumber(fcResult?.result, ["roi_count"]) ??
    extractNumber(nativeFcResult?.result, ["roi_count"]);
  const qcStatus =
    extractString(fcResult?.result, ["fc_qc_status", "qc_status", "status"]) ||
    extractString(nativeFcResult?.result, ["fc_qc_status", "qc_status", "status"]);
  const atlasSource =
    extractString(fcResult?.result, ["atlas_source"]) ||
    extractString(nativeFcResult?.result, ["atlas_source"]);
  const atlasName =
    atlasPath.trim() ||
    extractString(fcResult?.result, ["atlas_file", "atlas_path", "atlas"]) ||
    extractString(nativeFcResult?.result, ["atlas_file", "atlas_path", "atlas"]) ||
    "Awaiting atlas evidence";
  const previewOnly =
    status === "preview_only" || result?.preview_only_stages.includes("functional_connectivity");
  const nativeIssue = nativeFcResult ? firstNativeIssue(nativeFcResult) : "";

  return (
    <Card className={styles.fcCard} aria-label="FC results panel">
      <div className={styles.sectionHeader}>
        <div>
          <h3>FC results</h3>
          <p>Matrix, Fisher-z, ROI time series, labels, and provenance stay artifact-backed.</p>
        </div>
        <Badge tone={statusTone(status)}>{previewOnly ? "preview_only" : status}</Badge>
      </div>
      <div className={styles.fcMetrics}>
        <div>
          <span>Atlas</span>
          <strong>{previewOnly ? "Synthetic preview" : atlasName}</strong>
        </div>
        <div>
          <span>ROI count</span>
          <strong>{roiCount ?? "Awaiting backend evidence"}</strong>
        </div>
        <div>
          <span>Matrix shape</span>
          <strong>{matrixShape}</strong>
        </div>
        <div>
          <span>QC</span>
          <strong>
            {qcStatus || (status === "succeeded" ? "Backend computed" : "Review required")}
          </strong>
        </div>
      </div>
      <div className={styles.fcArtifactSummary} aria-label="FC artifact summary">
        <div>
          <span>Atlas source</span>
          <strong>{atlasSource || (previewOnly ? "synthetic_x_chunk" : "provided atlas")}</strong>
        </div>
        <div>
          <span>Registered artifacts</span>
          <strong>{artifactCount}</strong>
        </div>
      </div>
      <Table caption="FC artifact handoff">
        <thead>
          <tr>
            <th>Artifact</th>
            <th>Availability</th>
            <th>Links</th>
          </tr>
        </thead>
        <tbody>
          {fcResult?.output_artifact_ids.length ? (
            fcResult.output_artifact_ids.map((artifactId) => (
              <tr key={artifactId}>
                <td>{artifactId}</td>
                <td>
                  <Badge tone="info" size="sm">
                    backend artifact
                  </Badge>
                </td>
                <td>
                  {projectId && preprocessingRunId ? (
                    <>
                      <a
                        href={artifactMetadataHref(
                          baseUrl,
                          projectId,
                          preprocessingRunId,
                          artifactId,
                        )}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Metadata
                      </a>
                      {" | "}
                      <a
                        href={artifactFileHref(baseUrl, projectId, preprocessingRunId, artifactId)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        File
                      </a>
                    </>
                  ) : (
                    "Awaiting run"
                  )}
                </td>
              </tr>
            ))
          ) : nativeFcArtifacts.length ? (
            nativeFcArtifacts.map((artifact, index) => (
              <tr key={`${String(artifact.artifact_type || "artifact")}-${index}`}>
                <td>{String(artifact.artifact_type || artifact.artifact_id || "native artifact")}</td>
                <td>
                  <Badge tone="info" size="sm">
                    native artifact
                  </Badge>
                </td>
                <td>{formatUnknown(artifact.path) || "Path unavailable"}</td>
              </tr>
            ))
          ) : nativeIssue && nativeIssue !== "-" ? (
            <tr>
              <td>functional_connectivity</td>
              <td>
                <Badge tone={statusTone(status)} size="sm">
                  {status}
                </Badge>
              </td>
              <td>{nativeIssue}</td>
            </tr>
          ) : (
            <TableEmpty colSpan={3}>
              FC downloads appear only after the backend registers matrix, Fisher-z, ROI timeseries,
              labels, and provenance artifacts.
            </TableEmpty>
          )}
        </tbody>
      </Table>
    </Card>
  );
}

function SummaryMetric({
  label,
  tone,
  value,
}: {
  label: string;
  tone: BadgeProps["tone"];
  value: number;
}) {
  return (
    <div data-tone={tone}>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function buildReviewedRequest({
  atlasPath,
  confirmations,
  fallbackTr,
  includeGlobalSignal,
  labelsPath,
  previewLimit,
  profile,
}: {
  atlasPath: string;
  confirmations: Record<ConfirmationKey, boolean>;
  fallbackTr: string;
  includeGlobalSignal: boolean;
  labelsPath: string;
  previewLimit: string;
  profile: Profile;
}): PreprocessingPipelineExecuteRequest {
  return {
    pipeline_profile: profile,
    start_from: "existing_preprocessing_input",
    backend_policy: {
      slice_timing: "native_python",
      motion_correction: "native_python",
      t1_coregistration: profile === "dparsfa_like" ? "native_python" : "skip",
      segmentation: profile === "dparsfa_like" ? "native_python" : "skip",
      normalization: profile === "dparsfa_like" ? "native_python" : "skip",
      spatial_smoothing: profile === "dparsfa_like" ? "native_python" : "skip",
      nuisance_regression: "python",
      temporal_filtering: "python",
      functional_connectivity: "python",
      alff_falff: "python",
      reho: "python",
    },
    stages:
      profile === "custom"
        ? {
            input_validation: "enabled",
            realignment: "enabled",
            nuisance_regression: "enabled",
            temporal_filtering: "enabled",
            functional_connectivity: "enabled",
            subject_qc: "enabled",
            group_summary: "enabled",
            alff_falff: "auto",
            reho: "auto",
          }
        : {},
    atlas: {
      atlas_path: atlasPath.trim(),
      labels_path: labelsPath.trim(),
      atlas_space: "native_or_matched",
      allow_resample: false,
    },
    nuisance: {
      model: "friston24",
      include_wm_csf: profile === "dparsfa_like",
      include_global_signal: includeGlobalSignal,
      include_linear_trend: true,
      include_intercept: true,
    },
    filtering: {
      low_hz: 0.01,
      high_hz: 0.08,
      fallback_tr: parseOptionalNumber(fallbackTr),
      tr: null,
    },
    execution_limits: {
      preview_limit: parseOptionalInteger(previewLimit),
      max_subjects: null,
    },
    confirmations,
    resume: true,
    rerun_policy: "skip_succeeded",
    generate_report: true,
    run_validation: true,
  };
}

function buildNativeRequest({
  atlasPath,
  confirmations,
  fallbackTr,
  includeGlobalSignal,
  labelsPath,
  preprocessingRunId,
  profile,
}: {
  atlasPath: string;
  confirmations?: Record<NativeConfirmationKey, boolean>;
  fallbackTr: string;
  includeGlobalSignal: boolean;
  labelsPath: string;
  preprocessingRunId: string;
  profile: Profile;
}): NativeFullPreprocRequest {
  const tr = parseOptionalNumber(fallbackTr);
  return {
    run_id: preprocessingRunId,
    atlas: atlasPath.trim() || undefined,
    atlas_labels: labelsPath.trim() || undefined,
    tr,
    include_global_signal: includeGlobalSignal,
    stage_overrides: nativeStageOverrides(profile),
    confirmations,
  };
}

function nativeStageOverrides(profile: Profile): Record<string, boolean> {
  if (profile === "dparsfa_like") {
    return {
      atlas_resampling: true,
      roi_timeseries: true,
      functional_connectivity: true,
      alff: true,
      falff: true,
      reho: true,
      subject_qc: true,
      group_summary: true,
    };
  }
  if (profile === "custom") {
    return {
      functional_connectivity: true,
      alff: true,
      falff: true,
      reho: true,
      subject_qc: true,
      group_summary: true,
    };
  }
  return {
    t1_coregistration: false,
    segmentation: false,
    normalization: false,
    smoothing: false,
    alff: false,
    falff: false,
    reho: false,
    functional_connectivity: true,
    subject_qc: true,
    group_summary: true,
  };
}

function parseOptionalNumber(value: string): number | null {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : null;
}

function parseOptionalInteger(value: string): number | null {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function firstIssue(stage: PreprocessingPipelineStageResult): string {
  return (
    stage.blocking_issues[0] || stage.errors[0] || stage.warnings[0] || stage.skipped_reason || "-"
  );
}

function firstNativeIssue(stage: NativeFullPreprocResponse["stage_results"][number]): string {
  return (
    stage.blocking_issues[0] ||
    stage.errors[0] ||
    stage.warnings[0] ||
    stage.validation_errors[0] ||
    "-"
  );
}

function formatUnknown(value: unknown): string {
  return typeof value === "string" && value.trim() ? value : "";
}

function profileLabel(profile: Profile): string {
  const match = PROFILE_OPTIONS.find((item) => item.value === profile);
  return match?.label ?? profile;
}

function stageStateLabel(state: (typeof STAGE_ROWS)[number]["state"]): string {
  const labels = {
    computed: "computed path",
    external: "gated",
    optional: "optional",
    report: "report",
    gate: "gate",
  };
  return labels[state];
}

function stageStateTone(state: (typeof STAGE_ROWS)[number]["state"]): BadgeProps["tone"] {
  if (state === "computed") return "success";
  if (state === "external") return "warning";
  if (state === "optional") return "info";
  return "neutral";
}

function statusTone(status?: string | null): BadgeProps["tone"] {
  const normalized = String(status || "").toLowerCase();
  if (["succeeded", "success", "ready", "computed"].includes(normalized)) return "success";
  if (["failed", "error"].includes(normalized)) return "danger";
  if (["blocked", "partial", "metadata_only"].includes(normalized)) return "warning";
  if (["preview_only", "skipped", "waiting", "not_started"].includes(normalized)) return "info";
  return "neutral";
}

function extractString(value: unknown, keys: string[]): string {
  if (!value || typeof value !== "object") return "";
  const record = value as Record<string, unknown>;
  for (const key of keys) {
    const item = record[key];
    if (typeof item === "string" && item.trim()) return item;
  }
  for (const item of Object.values(record)) {
    const nested = extractString(item, keys);
    if (nested) return nested;
  }
  return "";
}

function extractNumber(value: unknown, keys: string[]): number | null {
  if (!value || typeof value !== "object") return null;
  const record = value as Record<string, unknown>;
  for (const key of keys) {
    const item = record[key];
    const parsed = Number(item);
    if (Number.isFinite(parsed)) return parsed;
  }
  for (const item of Object.values(record)) {
    const nested = extractNumber(item, keys);
    if (nested !== null) return nested;
  }
  return null;
}

function extractMatrixShape(value: unknown): string {
  if (!value || typeof value !== "object") return "Awaiting backend evidence";
  const record = value as Record<string, unknown>;
  for (const key of ["matrix_shape", "shape", "fc_matrix_shape"]) {
    const item = record[key];
    if (Array.isArray(item) && item.length >= 2) {
      return `${item[0]} x ${item[1]}`;
    }
    if (typeof item === "string" && item.trim()) {
      return item;
    }
  }
  for (const item of Object.values(record)) {
    const nested = extractMatrixShape(item);
    if (nested !== "Awaiting backend evidence") return nested;
  }
  return "Awaiting backend evidence";
}

function extractNativeMatrixShape(stage?: NativeFullStageApiResult): string {
  const resultShape = extractMatrixShape(stage?.result);
  if (resultShape !== "Awaiting backend evidence") return resultShape;
  for (const artifact of stage?.output_artifacts ?? []) {
    const artifactShape = extractMatrixShape(artifact);
    if (artifactShape !== "Awaiting backend evidence") return artifactShape;
  }
  return "Awaiting backend evidence";
}

function artifactMetadataHref(
  baseUrl: string,
  projectId: string,
  preprocessingRunId: string,
  artifactId: string,
): string {
  const root = baseUrl.replace(/\/$/, "");
  return `${root}/api/projects/${encodeURIComponent(projectId)}/preprocessing/runs/${encodeURIComponent(preprocessingRunId)}/artifacts/${encodeURIComponent(artifactId)}`;
}

function artifactFileHref(
  baseUrl: string,
  projectId: string,
  preprocessingRunId: string,
  artifactId: string,
): string {
  return `${artifactMetadataHref(baseUrl, projectId, preprocessingRunId, artifactId)}/file`;
}
