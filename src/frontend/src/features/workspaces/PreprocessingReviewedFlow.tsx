import { useEffect, useMemo, useState } from "react";

import {
  getNativeGpuDetection,
  getLatestNativeFullPreprocessingRun,
  getNativeFullPreprocessingProgress,
  getNativeFullPreprocessingReport,
  getNativeFullPreprocessingValidation,
  runNativeFullPreprocessingDryRun,
} from "../../lib/api/preprocessing";
import type {
  NativeFullPreprocConfirmations,
  NativeFullPreprocRequest,
  NativeFullPreprocResponse,
  NativeGpuDetection,
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
import { useI18n } from "../../i18n/useI18n";
import type { I18nContextValue } from "../../i18n/context";
import type { MessageKey } from "../../i18n/messages/en";

type Profile = NonNullable<PreprocessingPipelineExecuteRequest["pipeline_profile"]>;
type ConfirmationKey = keyof NonNullable<PreprocessingPipelineExecuteRequest["confirmations"]>;
type NativeConfirmationKey = keyof NativeFullPreprocConfirmations;
type NativeAction = "" | "dry-run" | "validation" | "report";

type Props = {
  baseUrl: string;
  hasPreprocessingRun: boolean;
  inventory: ProjectInventory;
  preprocessingRunId?: string | null;
  projectId: string | null;
  onOpenDataConversion: () => void;
};

const PROFILE_OPTIONS = [
  { labelKey: "preprocessing.flow.profileMinimal", value: "fc_minimal" },
  { labelKey: "preprocessing.flow.profileDparsfa", value: "dparsfa_like" },
  { labelKey: "preprocessing.flow.profileCustom", value: "custom" },
] satisfies Array<{ labelKey: MessageKey; value: Profile }>;

const CONFIRMATIONS: Array<{
  key: ConfirmationKey;
  labelKey: MessageKey;
  detailKey: MessageKey;
}> = [
  {
    key: "confirm_rawdata_readonly",
    labelKey: "preprocessing.flow.confirmRawLabel",
    detailKey: "preprocessing.flow.confirmRawDetail",
  },
  {
    key: "confirm_reviewed_execution",
    labelKey: "preprocessing.flow.confirmReviewedLabel",
    detailKey: "preprocessing.flow.confirmReviewedDetail",
  },
  {
    key: "confirm_external_tools_if_needed",
    labelKey: "preprocessing.flow.confirmExternalLabel",
    detailKey: "preprocessing.flow.confirmExternalDetail",
  },
  {
    key: "confirm_research_use_only",
    labelKey: "preprocessing.flow.confirmResearchLabel",
    detailKey: "preprocessing.flow.confirmResearchDetail",
  },
  {
    key: "confirm_no_clinical_use",
    labelKey: "preprocessing.flow.confirmClinicalLabel",
    detailKey: "preprocessing.flow.confirmClinicalDetail",
  },
];

const NATIVE_CONFIRMATIONS: Array<{
  key: NativeConfirmationKey;
  labelKey: MessageKey;
  detailKey: MessageKey;
}> = [
  {
    key: "confirm_reviewed_native_execution",
    labelKey: "preprocessing.flow.nativeReviewedLabel",
    detailKey: "preprocessing.flow.nativeReviewedDetail",
  },
  {
    key: "confirm_rawdata_readonly",
    labelKey: "preprocessing.flow.nativeRawLabel",
    detailKey: "preprocessing.flow.nativeRawDetail",
  },
  {
    key: "confirm_no_external_tools",
    labelKey: "preprocessing.flow.nativeExternalLabel",
    detailKey: "preprocessing.flow.nativeExternalDetail",
  },
  {
    key: "confirm_research_use_only",
    labelKey: "preprocessing.flow.nativeResearchLabel",
    detailKey: "preprocessing.flow.nativeResearchDetail",
  },
  {
    key: "confirm_no_clinical_use",
    labelKey: "preprocessing.flow.nativeClinicalLabel",
    detailKey: "preprocessing.flow.nativeClinicalDetail",
  },
];

const STAGE_ROWS: Array<{
  stageId: string;
  labelKey: MessageKey;
  backend: string;
  fcMinimal: boolean;
  dparsfaLike: boolean;
  noteKey: MessageKey;
  state: "computed" | "external" | "optional" | "report" | "gate";
}> = [
  {
    stageId: "input_validation",
    labelKey: "preprocessing.flow.stageInputInventory",
    backend: "registry",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteRegisteredInput",
    state: "gate",
  },
  {
    stageId: "dummy_scan_removal",
    labelKey: "preprocessing.flow.stageDummyRemoval",
    backend: "auto",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteDummyRemoval",
    state: "optional",
  },
  {
    stageId: "realignment",
    labelKey: "preprocessing.flow.stageRealignment",
    backend: "Native Python",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteRealignment",
    state: "computed",
  },
  {
    stageId: "t1_coregistration",
    labelKey: "preprocessing.flow.stageT1Coregistration",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteCoregistration",
    state: "optional",
  },
  {
    stageId: "segmentation",
    labelKey: "preprocessing.flow.stageSegmentation",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteSegmentation",
    state: "optional",
  },
  {
    stageId: "normalization",
    labelKey: "preprocessing.flow.stageNormalization",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteNormalization",
    state: "optional",
  },
  {
    stageId: "spatial_smoothing",
    labelKey: "preprocessing.flow.stageSmoothing",
    backend: "Native Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteSmoothing",
    state: "optional",
  },
  {
    stageId: "nuisance_regression",
    labelKey: "preprocessing.flow.stageNuisance",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteNuisance",
    state: "computed",
  },
  {
    stageId: "temporal_filtering",
    labelKey: "preprocessing.flow.stageFiltering",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteFiltering",
    state: "computed",
  },
  {
    stageId: "alff_falff",
    labelKey: "preprocessing.flow.stageAlff",
    backend: "Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteAlff",
    state: "optional",
  },
  {
    stageId: "reho",
    labelKey: "preprocessing.flow.stageReho",
    backend: "Python",
    fcMinimal: false,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteReho",
    state: "optional",
  },
  {
    stageId: "functional_connectivity",
    labelKey: "preprocessing.flow.stageFc",
    backend: "Python",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteFc",
    state: "computed",
  },
  {
    stageId: "subject_qc",
    labelKey: "preprocessing.flow.stageSubjectQc",
    backend: "registry",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteSubjectQc",
    state: "report",
  },
  {
    stageId: "group_summary",
    labelKey: "preprocessing.flow.stageReport",
    backend: "report",
    fcMinimal: true,
    dparsfaLike: true,
    noteKey: "preprocessing.flow.noteReport",
    state: "report",
  },
];

export function PreprocessingReviewedFlow({
  baseUrl,
  hasPreprocessingRun,
  inventory,
  onOpenDataConversion,
  preprocessingRunId,
  projectId,
}: Props) {
  const { t } = useI18n();
  const [profile, setProfile] = useState<Profile>("fc_minimal");
  const [templatePath, setTemplatePath] = useState("");
  const [atlasPath, setAtlasPath] = useState("");
  const [labelsPath, setLabelsPath] = useState("");
  const [fallbackTr, setFallbackTr] = useState("");
  const [previewLimit, setPreviewLimit] = useState("");
  const [includeGlobalSignal, setIncludeGlobalSignal] = useState(false);
  const result: PreprocessingPipelineExecuteResponse | null = null;
  const [nativeAction, setNativeAction] = useState<NativeAction>("");
  const [nativeResult, setNativeResult] = useState<NativeFullPreprocResponse | null>(null);
  const [nativeValidation, setNativeValidation] = useState<Record<string, unknown> | null>(null);
  const [nativeReport, setNativeReport] = useState<Record<string, unknown> | null>(null);
  const [nativeError, setNativeError] = useState("");
  const [nativeProgress, setNativeProgress] = useState<Record<string, unknown> | null>(null);
  const [cpuMode, setCpuMode] = useState<"serial" | "process" | "auto">("serial");
  const [computeBackend, setComputeBackend] = useState<"cpu" | "gpu" | "auto">("cpu");
  const [gpuDetection, setGpuDetection] = useState<NativeGpuDetection | null>(null);

  const visibleStages = useMemo(
    () =>
      STAGE_ROWS.filter((stage) => {
        if (profile === "dparsfa_like") return stage.dparsfaLike;
        if (profile === "custom") return stage.fcMinimal || stage.state === "optional";
        return stage.fcMinimal;
      }),
    [profile],
  );

  const nativeRunId = nativeResult?.run_id || preprocessingRunId || "";
  const canNativeDryRun = Boolean(projectId && nativeRunId && !nativeAction);
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

  useEffect(() => {
    let cancelled = false;
    void getNativeGpuDetection(baseUrl)
      .then((result) => {
        if (!cancelled) setGpuDetection(result);
      })
      .catch(() => {
        if (!cancelled) setGpuDetection(null);
      });
    return () => {
      cancelled = true;
    };
  }, [baseUrl]);

  useEffect(() => {
    if (!projectId || !nativeResult?.run_id || !["queued", "running"].includes(nativeResult.status))
      return;
    let stopped = false;
    const refresh = () => {
      void getNativeFullPreprocessingProgress(baseUrl, projectId, nativeResult.run_id)
        .then((progress) => {
          if (!stopped) setNativeProgress(progress);
        })
        .catch((): undefined => undefined);
      void getLatestNativeFullPreprocessingRun(baseUrl, projectId)
        .then((run) => {
          if (
            !stopped &&
            run.run_id === nativeResult.run_id &&
            !["queued", "running"].includes(run.status)
          )
            setNativeResult(run);
        })
        .catch((): undefined => undefined);
    };
    refresh();
    const timer = window.setInterval(refresh, 3000);
    return () => {
      stopped = true;
      window.clearInterval(timer);
    };
  }, [baseUrl, nativeResult?.run_id, nativeResult?.status, projectId]);

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
          templatePath,
          cpuMode,
          computeBackend,
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
      setNativeValidation(
        await getNativeFullPreprocessingValidation(baseUrl, projectId, nativeRunId),
      );
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
    <section className={styles.reviewedFlow} aria-label={t("preprocessing.flow.reviewed")}>
      <ConversionHandoffCard inventory={inventory} onOpenDataConversion={onOpenDataConversion} />

      <Card className={styles.pipelineBuilderCard} tone="muted">
        <div className={styles.sectionHeader}>
          <div>
            <h3>{t("preprocessing.flow.pipelineBuilder")}</h3>
            <p>{t("preprocessing.flow.pipelineBuilderDescription")}</p>
          </div>
          <Badge tone="info">{t("preprocessing.flow.reviewedBadge")}</Badge>
        </div>
        <SegmentedControl
          aria-label={t("preprocessing.flow.pipelineProfile")}
          options={PROFILE_OPTIONS.map((option) => ({
            label: t(option.labelKey),
            value: option.value,
          }))}
          value={profile}
          onChange={(value) => setProfile(value as Profile)}
        />
        <div className={styles.builderGrid}>
          <label className={styles.fieldShell}>
            <span>{t("preprocessing.flow.templatePath")}</span>
            <input
              value={templatePath}
              onChange={(event) => setTemplatePath(event.target.value)}
              placeholder={t("preprocessing.flow.templatePlaceholder")}
            />
          </label>
          <label className={styles.fieldShell}>
            <span>{t("preprocessing.flow.atlasPath")}</span>
            <input
              value={atlasPath}
              onChange={(event) => setAtlasPath(event.target.value)}
              placeholder={t("preprocessing.flow.atlasPlaceholder")}
            />
          </label>
          <label className={styles.fieldShell}>
            <span>{t("preprocessing.flow.labelsPath")}</span>
            <input
              value={labelsPath}
              onChange={(event) => setLabelsPath(event.target.value)}
              placeholder={t("preprocessing.flow.labelsPlaceholder")}
            />
          </label>
          <label className={styles.fieldShell}>
            <span>{t("preprocessing.flow.fallbackTr")}</span>
            <input
              inputMode="decimal"
              value={fallbackTr}
              onChange={(event) => setFallbackTr(event.target.value)}
              placeholder={t("preprocessing.flow.fallbackTrPlaceholder")}
            />
          </label>
          <label className={styles.fieldShell}>
            <span>{t("preprocessing.flow.previewLimit")}</span>
            <input
              inputMode="numeric"
              value={previewLimit}
              onChange={(event) => setPreviewLimit(event.target.value)}
              placeholder={t("preprocessing.flow.previewLimitPlaceholder")}
            />
          </label>
        </div>
        <label className={styles.inlineCheck}>
          <input
            type="checkbox"
            checked={includeGlobalSignal}
            onChange={(event) => setIncludeGlobalSignal(event.target.checked)}
          />
          <span>{t("preprocessing.flow.globalSignal")}</span>
        </label>
        <Table caption={t("preprocessing.flow.reviewedStages")}>
          <thead>
            <tr>
              <th>{t("preprocessing.flow.stage")}</th>
              <th>{t("preprocessing.flow.backend")}</th>
              <th>{t("preprocessing.flow.state")}</th>
              <th>{t("preprocessing.flow.reviewNote")}</th>
            </tr>
          </thead>
          <tbody>
            {visibleStages.map((stage) => (
              <tr key={stage.stageId}>
                <td>{t(stage.labelKey)}</td>
                <td>{stage.backend}</td>
                <td>
                  <Badge tone={stageStateTone(stage.state)} size="sm">
                    {stageStateLabel(stage.state, t)}
                  </Badge>
                </td>
                <td>{t(stage.noteKey)}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card className={styles.executionGateCard}>
        <div className={styles.sectionHeader}>
          <div>
            <h3>{t("preprocessing.flow.executionGate")}</h3>
            <p>{t("preprocessing.flow.executionGateDescription")}</p>
          </div>
          <Badge tone="warning">{t("preprocessing.flow.agentApprovalRequired")}</Badge>
        </div>
        <div className={styles.gateSummary} aria-label={t("preprocessing.flow.gateReadiness")}>
          <div>
            <span>{t("preprocessing.flow.project")}</span>
            <strong>{projectId ? t("preprocessing.selected") : t("preprocessing.missing")}</strong>
          </div>
          <div>
            <span>{t("preprocessing.flow.preprocessingRun")}</span>
            <strong>
              {preprocessingRunId ??
                (hasPreprocessingRun
                  ? t("preprocessing.flow.idUnavailable")
                  : t("preprocessing.required"))}
            </strong>
          </div>
          <div>
            <span>{t("preprocessing.flow.profile")}</span>
            <strong>{profileLabel(profile, t)}</strong>
          </div>
        </div>
        <div className={styles.confirmationList} aria-label={t("preprocessing.flow.confirmations")}>
          {CONFIRMATIONS.map((item) => (
            <label className={styles.confirmationItem} key={item.key}>
              <input type="checkbox" checked={false} disabled readOnly />
              <span>
                <strong>{t(item.labelKey)}</strong>
                <small>{t(item.detailKey)}</small>
              </span>
            </label>
          ))}
        </div>
        <div className={styles.reviewedActions}>
          <Button variant="primary" disabled>
            {t("preprocessing.flow.submit")}
          </Button>
          <span>{t("preprocessing.flow.executionViaAgentOnly")}</span>
        </div>
      </Card>

      <NativeFullWorkflowCard
        canDryRun={canNativeDryRun}
        canRefresh={canRefreshNative}
        error={nativeError}
        onDryRun={runNativeDryRun}
        onRefreshReport={refreshNativeReport}
        onRefreshValidation={refreshNativeValidation}
        pendingAction={nativeAction}
        report={nativeReport}
        result={nativeResult}
        progress={nativeProgress}
        cpuMode={cpuMode}
        onCpuModeChange={setCpuMode}
        computeBackend={computeBackend}
        onComputeBackendChange={setComputeBackend}
        gpuDetection={gpuDetection}
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
  const { t } = useI18n();
  return (
    <Card className={styles.handoffCard}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>{t("preprocessing.flow.handoff")}</h3>
          <p>{t("preprocessing.flow.handoffDescription")}</p>
        </div>
        <Badge tone={inventory.hasConvertedData ? "success" : "warning"}>
          {inventory.hasConvertedData
            ? t("preprocessing.statusRegistered")
            : t("preprocessing.required")}
        </Badge>
      </div>
      <div className={styles.handoffMetrics} aria-label={t("preprocessing.flow.handoff")}>
        <div>
          <span>{t("preprocessing.flow.subjects")}</span>
          <strong>{inventory.convertedSubjects}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.niftiFiles")}</span>
          <strong>{inventory.niftiFileCount.toLocaleString()}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.state")}</span>
          <strong>{inventory.dataStateLabel}</strong>
        </div>
      </div>
      <Button variant="secondary" onClick={onOpenDataConversion}>
        {t("preprocessing.flow.reviewConversion")}
      </Button>
    </Card>
  );
}

function NativeFullWorkflowCard({
  canDryRun,
  canRefresh,
  error,
  onDryRun,
  onRefreshReport,
  onRefreshValidation,
  pendingAction,
  report,
  result,
  progress,
  cpuMode,
  onCpuModeChange,
  computeBackend,
  onComputeBackendChange,
  gpuDetection,
  runId,
  validation,
}: {
  canDryRun: boolean;
  canRefresh: boolean;
  error: string;
  onDryRun: () => void;
  onRefreshReport: () => void;
  onRefreshValidation: () => void;
  pendingAction: NativeAction;
  report: Record<string, unknown> | null;
  result: NativeFullPreprocResponse | null;
  progress: Record<string, unknown> | null;
  cpuMode: "serial" | "process" | "auto";
  onCpuModeChange: (mode: "serial" | "process" | "auto") => void;
  computeBackend: "cpu" | "gpu" | "auto";
  onComputeBackendChange: (backend: "cpu" | "gpu" | "auto") => void;
  gpuDetection: NativeGpuDetection | null;
  runId: string;
  validation: Record<string, unknown> | null;
}) {
  const { t } = useI18n();
  const status = result?.status ?? "not_started";

  return (
    <Card className={styles.dashboardCard} aria-label={t("preprocessing.flow.nativeWorkflow")}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>{t("preprocessing.flow.nativeTitle")}</h3>
          <p>{t("preprocessing.flow.nativeDescription")}</p>
        </div>
        <Badge tone={statusTone(status)}>{status}</Badge>
      </div>

      <div className={styles.gateSummary} aria-label={t("preprocessing.flow.nativeSummary")}>
        <div>
          <span>{t("preprocessing.flow.run")}</span>
          <strong>{runId || t("preprocessing.required")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.artifacts")}</span>
          <strong>{result ? result.artifact_count : t("preprocessing.flow.awaitingRun")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.gate")}</span>
          <strong>{t("preprocessing.flow.agentApprovalRequired")}</strong>
        </div>
      </div>

      <div
        className={styles.confirmationList}
        aria-label={t("preprocessing.flow.nativeConfirmations")}
      >
        {NATIVE_CONFIRMATIONS.map((item) => (
          <label className={styles.confirmationItem} key={item.key}>
            <input type="checkbox" checked={false} disabled readOnly />
            <span>
              <strong>{t(item.labelKey)}</strong>
              <small>{t(item.detailKey)}</small>
            </span>
          </label>
        ))}
      </div>

      <label className={styles.fieldShell}>
        <span>CPU scheduling mode</span>
        <select
          aria-label="CPU scheduling mode"
          value={cpuMode}
          onChange={(event) => onCpuModeChange(event.target.value as typeof cpuMode)}
        >
          <option value="serial">serial (default)</option>
          <option value="process">process</option>
          <option value="auto">auto</option>
        </select>
      </label>
      <div className={styles.gateSummary} aria-label="Native GPU capability">
        <div>
          <span>GPU device</span>
          <strong>
            {gpuDetection?.gpu_available
              ? gpuDetection.device_name || gpuDetection.device_id || "CUDA device"
              : "Unavailable"}
          </strong>
        </div>
        <div>
          <span>CuPy</span>
          <strong>{gpuDetection?.cupy_available ? "available" : "unavailable"}</strong>
        </div>
        <div>
          <span>Free VRAM</span>
          <strong>
            {gpuDetection?.free_vram_bytes
              ? `${Math.round(gpuDetection.free_vram_bytes / 1024 / 1024)} MiB`
              : "-"}
          </strong>
        </div>
      </div>
      <label className={styles.fieldShell}>
        <span>GPU compute backend</span>
        <select
          aria-label="GPU compute backend"
          value={computeBackend}
          onChange={(event) => onComputeBackendChange(event.target.value as typeof computeBackend)}
        >
          <option value="cpu">CPU (default, reference)</option>
          <option value="gpu">GPU (reviewed CuPy execution; no fallback)</option>
          <option value="auto">Auto (falls back visibly to CPU)</option>
        </select>
        <small>
          GPU applies only to released numerical stages. ReHo remains CPU until separately
          validated.
        </small>
      </label>
      {progress ? (
        <div className={styles.gateSummary} aria-label="Native preprocessing live progress">
          <div>
            <span>Subjects</span>
            <strong>
              {String(progress.completed_subjects ?? 0)} / {String(progress.total_subjects ?? "?")}
            </strong>
          </div>
          <div>
            <span>Live status</span>
            <strong>{String(progress.status ?? "queued")}</strong>
          </div>
          <div>
            <span>Last heartbeat</span>
            <strong>{String(progress.heartbeat_at ?? "-")}</strong>
          </div>
        </div>
      ) : null}

      <div className={styles.reviewedActions}>
        <Button variant="secondary" onClick={onDryRun} disabled={!canDryRun}>
          {pendingAction === "dry-run"
            ? t("preprocessing.flow.planning")
            : t("preprocessing.flow.runNativeDryRun")}
        </Button>
        <Button variant="primary" disabled>
          {t("preprocessing.flow.executeNative")}
        </Button>
        <Button variant="secondary" onClick={onRefreshValidation} disabled={!canRefresh}>
          {pendingAction === "validation"
            ? t("preprocessing.flow.refreshing")
            : t("preprocessing.flow.refreshValidation")}
        </Button>
        <Button variant="secondary" onClick={onRefreshReport} disabled={!canRefresh}>
          {pendingAction === "report"
            ? t("preprocessing.flow.refreshing")
            : t("preprocessing.flow.refreshReport")}
        </Button>
        <span>{t("preprocessing.flow.executionViaAgentOnly")}</span>
      </div>
      {error ? <div className={styles.inlineError}>{error}</div> : null}

      <Table caption={t("preprocessing.flow.nativeResults")}>
        <thead>
          <tr>
            <th>{t("preprocessing.flow.stage")}</th>
            <th>{t("preprocessing.flow.status")}</th>
            <th>Backend</th>
            <th>{t("preprocessing.flow.artifacts")}</th>
            <th>{t("preprocessing.flow.issue")}</th>
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
                <td>{stage.backend}</td>
                <td>{stage.output_artifacts.length}</td>
                <td>{firstNativeIssue(stage)}</td>
              </tr>
            ))
          ) : (
            <TableEmpty colSpan={5}>{t("preprocessing.flow.nativeRowsEmpty")}</TableEmpty>
          )}
        </tbody>
      </Table>

      <div className={styles.reportRail} aria-label={t("preprocessing.flow.nativeOutputs")}>
        <div>
          <span>{t("preprocessing.flow.validation")}</span>
          <strong>
            {formatUnknown(validation?.validation_report_path) ||
              result?.validation_report_path ||
              t("preprocessing.flow.notGenerated")}
          </strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.report")}</span>
          <strong>
            {formatUnknown(report?.final_report_path) ||
              result?.final_report_path ||
              t("preprocessing.flow.notGenerated")}
          </strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.blocked")}</span>
          <strong>
            {Array.isArray(result?.blocked_stages)
              ? result?.blocked_stages.length
              : t("preprocessing.flow.awaitingRun")}
          </strong>
        </div>
      </div>
    </Card>
  );
}

function PipelineDashboard({ result }: { result: PreprocessingPipelineExecuteResponse | null }) {
  const { t } = useI18n();
  if (!result) {
    return (
      <Card className={styles.dashboardCard}>
        <EmptyState
          title={t("preprocessing.flow.noExecution")}
          description={t("preprocessing.flow.noExecutionDescription")}
        />
      </Card>
    );
  }

  return (
    <Card className={styles.dashboardCard} aria-label={t("preprocessing.flow.dashboard")}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>{t("preprocessing.flow.dashboard")}</h3>
          <p>{t("preprocessing.flow.dashboardDescription")}</p>
        </div>
        <Badge tone={statusTone(result.status)}>{result.status}</Badge>
      </div>
      <div className={styles.statusStrip} aria-label={t("preprocessing.flow.executionSummary")}>
        <SummaryMetric
          label={t("preprocessing.flow.completed")}
          value={result.completed_stages.length}
          tone="success"
        />
        <SummaryMetric
          label={t("preprocessing.flow.blocked")}
          value={result.blocked_stages.length}
          tone="warning"
        />
        <SummaryMetric
          label={t("preprocessing.flow.failed")}
          value={result.failed_stages.length}
          tone="danger"
        />
        <SummaryMetric
          label={t("preprocessing.flow.metadataOnly")}
          value={result.metadata_only_stages.length}
          tone="info"
        />
        <SummaryMetric
          label={t("preprocessing.flow.previewOnly")}
          value={result.preview_only_stages.length}
          tone="info"
        />
      </div>
      <Table caption={t("preprocessing.flow.timeline")}>
        <thead>
          <tr>
            <th>{t("preprocessing.flow.stage")}</th>
            <th>{t("preprocessing.flow.status")}</th>
            <th>{t("preprocessing.flow.artifacts")}</th>
            <th>{t("preprocessing.flow.issue")}</th>
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
            <TableEmpty colSpan={4}>{t("preprocessing.flow.noStageRows")}</TableEmpty>
          )}
        </tbody>
      </Table>
      <div className={styles.reportRail} aria-label={t("preprocessing.flow.reportOutputs")}>
        <div>
          <span>{t("preprocessing.flow.report")}</span>
          <strong>{result.report_path || t("preprocessing.flow.notGenerated")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.validation")}</span>
          <strong>{result.validation_status || t("preprocessing.flow.notRun")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.registry")}</span>
          <strong>{result.artifact_registry_path || t("common.unavailable")}</strong>
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
  const { t } = useI18n();
  const nativeArtifacts = nativeFcResult?.output_artifacts ?? [];
  const nativeFcArtifacts = nativeArtifacts.filter((artifact) =>
    ["fc_matrix", "fisher_z_matrix", "roi_timeseries", "roi_labels"].includes(
      String(artifact.artifact_type || ""),
    ),
  );
  const status =
    fcResult?.status ??
    nativeFcResult?.status ??
    (result || nativeResult ? "not_started" : "waiting");
  const artifactCount = fcResult?.output_artifact_ids.length || nativeFcArtifacts.length || 0;
  const pipelineMatrixShape = extractMatrixShape(fcResult?.result);
  const matrixShape = pipelineMatrixShape || extractNativeMatrixShape(nativeFcResult);
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
    t("preprocessing.flow.awaitingAtlas");
  const previewOnly =
    status === "preview_only" || result?.preview_only_stages.includes("functional_connectivity");
  const nativeIssue = nativeFcResult ? firstNativeIssue(nativeFcResult) : "";

  return (
    <Card className={styles.fcCard} aria-label={t("preprocessing.flow.fcPanel")}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>{t("preprocessing.flow.fcResults")}</h3>
          <p>{t("preprocessing.flow.fcDescription")}</p>
        </div>
        <Badge tone={statusTone(status)}>{previewOnly ? "preview_only" : status}</Badge>
      </div>
      <div className={styles.fcMetrics}>
        <div>
          <span>{t("preprocessing.flow.atlas")}</span>
          <strong>{previewOnly ? t("preprocessing.flow.syntheticPreview") : atlasName}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.roiCount")}</span>
          <strong>{roiCount ?? t("preprocessing.flow.awaitingEvidence")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.matrixShape")}</span>
          <strong>{matrixShape || t("preprocessing.flow.awaitingEvidence")}</strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.qc")}</span>
          <strong>
            {qcStatus ||
              (status === "succeeded"
                ? t("preprocessing.flow.backendComputed")
                : t("preprocessing.flow.reviewRequired"))}
          </strong>
        </div>
      </div>
      <div className={styles.fcArtifactSummary} aria-label={t("preprocessing.flow.fcSummary")}>
        <div>
          <span>{t("preprocessing.flow.atlasSource")}</span>
          <strong>
            {atlasSource ||
              (previewOnly ? "synthetic_x_chunk" : t("preprocessing.flow.providedAtlas"))}
          </strong>
        </div>
        <div>
          <span>{t("preprocessing.flow.registeredArtifacts")}</span>
          <strong>{artifactCount}</strong>
        </div>
      </div>
      <Table caption={t("preprocessing.flow.fcHandoff")}>
        <thead>
          <tr>
            <th>{t("preprocessing.flow.artifact")}</th>
            <th>{t("preprocessing.flow.availability")}</th>
            <th>{t("preprocessing.flow.links")}</th>
          </tr>
        </thead>
        <tbody>
          {fcResult?.output_artifact_ids.length ? (
            fcResult.output_artifact_ids.map((artifactId) => (
              <tr key={artifactId}>
                <td>{artifactId}</td>
                <td>
                  <Badge tone="info" size="sm">
                    {t("preprocessing.flow.backendArtifact")}
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
                        {t("preprocessing.flow.metadata")}
                      </a>
                      {" | "}
                      <a
                        href={artifactFileHref(baseUrl, projectId, preprocessingRunId, artifactId)}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {t("preprocessing.flow.file")}
                      </a>
                    </>
                  ) : (
                    t("preprocessing.flow.awaitingRun")
                  )}
                </td>
              </tr>
            ))
          ) : nativeFcArtifacts.length ? (
            nativeFcArtifacts.map((artifact, index) => (
              <tr key={`${String(artifact.artifact_type || "artifact")}-${index}`}>
                <td>
                  {String(
                    artifact.artifact_type ||
                      artifact.artifact_id ||
                      t("preprocessing.flow.nativeArtifact"),
                  )}
                </td>
                <td>
                  <Badge tone="info" size="sm">
                    {t("preprocessing.flow.nativeArtifact")}
                  </Badge>
                </td>
                <td>{formatUnknown(artifact.path) || t("preprocessing.flow.pathUnavailable")}</td>
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
            <TableEmpty colSpan={3}>{t("preprocessing.flow.fcEmpty")}</TableEmpty>
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

function buildNativeRequest({
  atlasPath,
  fallbackTr,
  includeGlobalSignal,
  labelsPath,
  preprocessingRunId,
  profile,
  templatePath,
  cpuMode = "serial",
  computeBackend = "cpu",
}: {
  atlasPath: string;
  fallbackTr: string;
  includeGlobalSignal: boolean;
  labelsPath: string;
  preprocessingRunId: string;
  profile: Profile;
  templatePath: string;
  cpuMode?: "serial" | "process" | "auto";
  computeBackend?: "cpu" | "gpu" | "auto";
}): NativeFullPreprocRequest {
  const tr = parseOptionalNumber(fallbackTr);
  return {
    run_id: preprocessingRunId,
    template: templatePath.trim() || undefined,
    atlas: atlasPath.trim() || undefined,
    atlas_labels: labelsPath.trim() || undefined,
    tr,
    include_global_signal: includeGlobalSignal,
    stage_overrides: nativeStageOverrides(profile),
    cpu_policy: { mode: cpuMode },
    compute_policy: { backend: computeBackend },
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

function profileLabel(profile: Profile, t: I18nContextValue["t"]): string {
  const match = PROFILE_OPTIONS.find((item) => item.value === profile);
  return match ? t(match.labelKey) : profile;
}

function stageStateLabel(
  state: (typeof STAGE_ROWS)[number]["state"],
  t: I18nContextValue["t"],
): string {
  const labels = {
    computed: t("preprocessing.flow.stateComputed"),
    external: t("preprocessing.flow.stateGated"),
    optional: t("preprocessing.flow.stateOptional"),
    report: t("preprocessing.flow.stateReport"),
    gate: t("preprocessing.flow.stateGate"),
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
  if (!value || typeof value !== "object") return "";
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
    if (nested) return nested;
  }
  return "";
}

function extractNativeMatrixShape(stage?: NativeFullStageApiResult): string {
  const resultShape = extractMatrixShape(stage?.result);
  if (resultShape) return resultShape;
  for (const artifact of stage?.output_artifacts ?? []) {
    const artifactShape = extractMatrixShape(artifact);
    if (artifactShape) return artifactShape;
  }
  return "";
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
