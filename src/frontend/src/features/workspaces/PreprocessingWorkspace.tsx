import { useState } from "react";

import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import AdvancedPreprocessingPipelinePanel from "../../components/AdvancedPreprocessingPipelinePanel";
import { RsfmriCoregistrationQcPanel } from "../../components/RsfmriCoregistrationQcPanel";
import { RsfmriNormalizationQcPanel } from "../../components/RsfmriNormalizationQcPanel";
import { RsfmriSegmentationTissueQcPanel } from "../../components/RsfmriSegmentationTissueQcPanel";
import { RsfmriSliceTimingPanel } from "../../components/RsfmriSliceTimingPanel";
import { RsfmriSmoothingQcPanel } from "../../components/RsfmriSmoothingQcPanel";
import { RsfmriStRealignMotionChainPanel } from "../../components/RsfmriStRealignMotionChainPanel";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { Badge, Button, Card, EmptyState } from "../../components/ui";
import { createPreprocessingRun } from "../../lib/api/preprocessing";
import type { ProjectDataState, ProjectInventory } from "../../lib/projectWorkflow";
import type { PreprocessingRunCreateResponse } from "../../types";
import { PreprocessingReviewedFlow } from "./PreprocessingReviewedFlow";
import styles from "./PreprocessingWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface PreprocessingWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  dataState?: ProjectDataState;
  inventory: ProjectInventory | null;
  hasPreprocessingRun: boolean;
  preprocessingRunId?: string | null;
  onOpenDataConversion: () => void;
  onOpenToolsDrawer: () => void;
}

export function PreprocessingWorkspace({
  baseUrl,
  projectId,
  dataState,
  inventory,
  hasPreprocessingRun,
  preprocessingRunId,
  onOpenDataConversion,
  onOpenToolsDrawer,
}: PreprocessingWorkspaceProps) {
  const [showTechnicalModules, setShowTechnicalModules] = useState(false);
  const [showDetailedValidation, setShowDetailedValidation] = useState(false);
  const [selectedStageName, setSelectedStageName] = useState(preprocessingStages[0].name);
  const [configMode, setConfigMode] = useState<ConfigMode>("basic");
  const [localRunId, setLocalRunId] = useState<string | null>(null);
  const [createRunResult, setCreateRunResult] = useState<PreprocessingRunCreateResponse | null>(
    null,
  );
  const [createRunError, setCreateRunError] = useState("");
  const [creatingRun, setCreatingRun] = useState(false);
  const resolvedInventory = inventory ?? emptyProjectInventory(dataState);
  const isRawDicom = dataState === "raw_dicom";
  const hasRegisteredConvertedInput =
    resolvedInventory.hasConvertedData &&
    !resolvedInventory.metadataOnlyNiftiInventory &&
    (resolvedInventory.convertedSubjects > 0 || resolvedInventory.niftiFileCount > 0);
  const effectivePreprocessingRunId = localRunId || preprocessingRunId || null;
  const effectiveHasPreprocessingRun = hasPreprocessingRun || Boolean(effectivePreprocessingRunId);

  const handleCreatePreprocessingRun = async () => {
    if (!projectId || !hasRegisteredConvertedInput || creatingRun) return;
    setCreatingRun(true);
    setCreateRunError("");
    try {
      const response = await createPreprocessingRun(baseUrl, projectId, {
        confirm_use_converted_input: true,
        confirm_no_rawdata_modification: true,
        confirm_python_only_execution: true,
        confirm_no_spm_matlab: true,
      });
      setCreateRunResult(response);
      if (response.ok && response.preprocessing_run_id) {
        setLocalRunId(response.preprocessing_run_id);
      } else {
        setCreateRunError(
          response.blocking_issues[0] ||
            response.errors[0] ||
            "Backend did not create a preprocessing run.",
        );
      }
    } catch (error) {
      setCreateRunError(error instanceof Error ? error.message : String(error));
    } finally {
      setCreatingRun(false);
    }
  };

  if (isRawDicom) {
    return (
      <div className={layoutStyles.stack}>
        <WorkspaceHeader
          title="Preprocessing"
          subtitle="Validate the preprocessing pipeline after conversion or BIDS registration."
          status="Blocked"
        />
        <section className={layoutStyles.blockedNotice} aria-label="Preprocessing blocked">
          <div className={layoutStyles.blockedBody}>
            <h3>Preprocessing is blocked</h3>
            <p>
              Raw DICOM has not been converted to registered BIDS/NIfTI data. Complete data
              conversion before preprocessing validation.
            </p>
            <ol className={layoutStyles.dependencyChain} aria-label="Dependency chain">
              <li className={layoutStyles.dependencyDone}>
                <span className={layoutStyles.dependencyLabel}>Data Detection</span>
                <span className={layoutStyles.dependencyStatus}>Done</span>
              </li>
              <li className={layoutStyles.dependencyCurrent}>
                <span className={layoutStyles.dependencyLabel}>Conversion Review</span>
                <span className={layoutStyles.dependencyStatus}>Required</span>
              </li>
              <li>
                <span className={layoutStyles.dependencyLabel}>BIDS Validation</span>
                <span className={layoutStyles.dependencyStatus}>Pending</span>
              </li>
              <li>
                <span className={layoutStyles.dependencyLabel}>Preprocessing</span>
                <span className={layoutStyles.dependencyStatus}>Locked</span>
              </li>
            </ol>
          </div>
          <div className={layoutStyles.blockedActions}>
            <Button variant="primary" onClick={onOpenDataConversion}>
              Return to Data &amp; Conversion
            </Button>
            <span className={layoutStyles.blockedHint}>
              Raw data is mounted read-only. Outputs are written to the project workspace.
            </span>
          </div>
        </section>
      </div>
    );
  }

  const isMissingRegistration =
    dataState === "empty" || dataState === "unknown" || !hasRegisteredConvertedInput;

  if (isMissingRegistration) {
    return (
      <div className={layoutStyles.stack}>
        <WorkspaceHeader
          title="Preprocessing"
          subtitle="Register converted BIDS/NIfTI input before reviewing preprocessing setup."
          status="Input required"
        />
        <section className={styles.inputRequiredGrid} aria-label="Preprocessing input required">
          <Card className={styles.inputRequiredCard} tone="muted">
            <div className={styles.sectionHeader}>
              <div>
                <h3>Register converted outputs before preprocessing</h3>
                <p>
                  Preprocessing setup needs backend-visible BIDS/NIfTI input. Source data remains
                  read-only; derived outputs are managed inside the project workspace.
                </p>
              </div>
              <Badge tone="warning">Input required</Badge>
            </div>
            <ol className={styles.requirementList} aria-label="Preprocessing input requirements">
              <li data-state="complete">
                <span>Project context</span>
                <strong>{projectId ? "Selected" : "Missing"}</strong>
              </li>
              <li data-state={resolvedInventory.hasConvertedData ? "complete" : "blocked"}>
                <span>Converted data evidence</span>
                <strong>
                  {resolvedInventory.hasConvertedData ? "Detected" : "Not registered"}
                </strong>
              </li>
              <li data-state={hasRegisteredConvertedInput ? "complete" : "blocked"}>
                <span>Registered input</span>
                <strong>{hasRegisteredConvertedInput ? "Ready" : "Required"}</strong>
              </li>
            </ol>
            <div className={styles.inputRequiredActions}>
              <Button variant="primary" onClick={onOpenDataConversion}>
                Open Data &amp; Conversion
              </Button>
              <span>Configuration panels stay locked until registered input evidence exists.</span>
            </div>
          </Card>
          <InputReadinessCard inventory={resolvedInventory} />
        </section>
        <PreprocessingTechnicalSections
          baseUrl={baseUrl}
          isMissingRegistration={true}
          preprocessingRunId={null}
          projectId={projectId}
          showDetailedValidation={showDetailedValidation}
          showTechnicalModules={showTechnicalModules}
          onToggleDetailedValidation={() => setShowDetailedValidation((value) => !value)}
          onToggleTechnicalModules={() => setShowTechnicalModules((value) => !value)}
        />
      </div>
    );
  }

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Preprocessing"
        subtitle="Configure, gate, and monitor reviewed preprocessing after BIDS/NIfTI registration."
        status={
          isMissingRegistration
            ? "Input required"
            : effectiveHasPreprocessingRun
              ? "Run available"
              : "Ready to configure"
        }
      />
      {!effectiveHasPreprocessingRun && (
        <EmptyState
          className={styles.setupCallout}
          title="Ready to create preprocessing run"
          description="A reviewed preprocessing run records the converted input registry and opens the execution dashboard. It does not run MATLAB, SPM, DPABI, or mark scientific outputs computed."
          action={
            <div className={styles.createRunActions}>
              <Button
                variant="primary"
                onClick={handleCreatePreprocessingRun}
                disabled={!projectId || !hasRegisteredConvertedInput || creatingRun}
              >
                {creatingRun ? "Creating..." : "Create preprocessing run"}
              </Button>
              <Button variant="secondary" onClick={onOpenToolsDrawer}>
                Open setup context
              </Button>
            </div>
          }
        />
      )}
      {createRunError ? <div className={styles.inlineError}>{createRunError}</div> : null}
      {createRunResult?.ok && effectivePreprocessingRunId ? (
        <Card className={styles.runBridgeCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Reviewed run created</h3>
              <p>Run {effectivePreprocessingRunId} is ready for reviewed execution setup.</p>
            </div>
            <Badge tone="success">Run available</Badge>
          </div>
        </Card>
      ) : null}
      <PreprocessingStageOverview
        configMode={configMode}
        hasPreprocessingRun={effectiveHasPreprocessingRun}
        inventory={resolvedInventory}
        isMissingRegistration={isMissingRegistration}
        onConfigModeChange={setConfigMode}
        onSelectStage={setSelectedStageName}
        selectedStageName={selectedStageName}
      />
      <PreprocessingReviewedFlow
        baseUrl={baseUrl}
        hasPreprocessingRun={effectiveHasPreprocessingRun}
        inventory={resolvedInventory}
        preprocessingRunId={effectivePreprocessingRunId}
        projectId={projectId}
        onOpenDataConversion={onOpenDataConversion}
      />
      <PreprocessingTechnicalSections
        baseUrl={baseUrl}
        isMissingRegistration={false}
        preprocessingRunId={effectivePreprocessingRunId}
        projectId={projectId}
        showDetailedValidation={showDetailedValidation}
        showTechnicalModules={showTechnicalModules}
        onToggleDetailedValidation={() => setShowDetailedValidation((value) => !value)}
        onToggleTechnicalModules={() => setShowTechnicalModules((value) => !value)}
      />
    </div>
  );
}

type StageStatus = "registered" | "configure" | "waiting" | "review" | "locked";
type ConfigMode = "basic" | "advanced";

type ConfigParameter = {
  label: string;
  note: string;
  range?: string;
  unit?: string;
  value: string;
};

type PreprocessingStageDefinition = {
  name: string;
  description: string;
  basic: ConfigParameter[];
  advanced: ConfigParameter[];
};

const preprocessingStages: PreprocessingStageDefinition[] = [
  {
    name: "Data preparation",
    description: "Confirm registered BIDS/NIfTI input, subject scope, and read-only source policy.",
    basic: [
      { label: "Input dataset", value: "Registered BIDS/NIfTI", note: "Required before planning." },
      {
        label: "Subject scope",
        value: "All registered subjects",
        note: "Review exclusions later.",
      },
    ],
    advanced: [
      { label: "BIDS filter", value: "func/*bold", note: "Default functional input pattern." },
      { label: "Derivative root", value: "project derivatives", note: "Must stay under project." },
    ],
  },
  {
    name: "Slice timing",
    description: "Prepare timing metadata before motion-sensitive processing.",
    basic: [
      {
        label: "TR",
        value: "from sidecar",
        unit: "s",
        note: "Loaded from BIDS JSON when present.",
      },
      { label: "Reference slice", value: "middle", note: "Common default for review." },
    ],
    advanced: [
      { label: "Slice order", value: "sidecar timing", note: "Fallback requires manual review." },
      { label: "Acquisition timing", value: "BIDS SliceTiming", note: "No inference in UI." },
    ],
  },
  {
    name: "Motion correction",
    description: "Review realignment settings and motion summary expectations.",
    basic: [
      { label: "Realign", value: "enabled", note: "Dry-run before execution." },
      { label: "FD threshold", value: "0.5", unit: "mm", range: "0.2-1.0", note: "QC flag only." },
    ],
    advanced: [
      { label: "Interpolation", value: "4th degree B-spline", note: "SPM-style parameter." },
      { label: "Quality", value: "0.9", range: "0-1", note: "Registration quality setting." },
    ],
  },
  {
    name: "Coregistration",
    description: "Align functional and anatomical inputs before template normalization.",
    basic: [
      { label: "Alignment", value: "BOLD to T1w", note: "Requires anatomical input." },
      { label: "Preview", value: "QC overlay", note: "Review before downstream use." },
    ],
    advanced: [
      { label: "Cost function", value: "nmi", note: "Normalized mutual information." },
      { label: "Sampling", value: "4", unit: "mm", note: "SPM-style separation." },
    ],
  },
  {
    name: "Segmentation",
    description:
      "Prepare tissue-class references needed by later nuisance and normalization steps.",
    basic: [
      { label: "Tissue classes", value: "GM / WM / CSF", note: "Used by nuisance model." },
      { label: "T1w source", value: "registered anatomical", note: "Required for segmentation." },
    ],
    advanced: [
      { label: "Bias correction", value: "enabled", note: "Review scanner/site assumptions." },
      { label: "Tissue priors", value: "template defaults", note: "Environment-dependent." },
    ],
  },
  {
    name: "Normalization",
    description: "Define standard-space registration and output voxel geometry.",
    basic: [
      { label: "Template", value: "MNI", note: "Standard space target." },
      { label: "Voxel size", value: "3 x 3 x 3", unit: "mm", note: "Typical rs-fMRI output." },
    ],
    advanced: [
      { label: "Warp regularization", value: "default", note: "SPM deformation setting." },
      { label: "Bounding box", value: "template", note: "Review before execution." },
    ],
  },
  {
    name: "Smoothing",
    description: "Set spatial smoothing parameters for downstream rs-fMRI measures.",
    basic: [
      { label: "FWHM", value: "6", unit: "mm", range: "4-8", note: "Common rs-fMRI default." },
      { label: "Apply to", value: "normalized BOLD", note: "After spatial normalization." },
    ],
    advanced: [
      { label: "Kernel shape", value: "Gaussian", note: "SPM-compatible." },
      { label: "Mask policy", value: "preserve brain mask", note: "Avoid silent extrapolation." },
    ],
  },
  {
    name: "Nuisance regression",
    description:
      "Define confound handling without executing external preprocessing from this page.",
    basic: [
      { label: "Motion model", value: "6 motion parameters", note: "Basic confound model." },
      { label: "Physiology", value: "WM + CSF", note: "Requires masks." },
    ],
    advanced: [
      { label: "Scrubbing", value: "FD-based", note: "Threshold reviewed in QC." },
      { label: "Polynomial terms", value: "linear", note: "Avoid overfitting by default." },
    ],
  },
  {
    name: "Temporal filtering",
    description: "Prepare pass-band settings for resting-state analysis.",
    basic: [
      { label: "Band", value: "0.01-0.08", unit: "Hz", note: "Canonical rs-fMRI band." },
      { label: "Detrend", value: "linear", note: "Review with nuisance model." },
    ],
    advanced: [
      { label: "Filter edge", value: "pad and trim", note: "Backend-defined behavior." },
      { label: "Order", value: "automatic", note: "Document final backend choice." },
    ],
  },
  {
    name: "Derived measures",
    description: "Reserve ALFF, ReHo, and connectivity outputs for later validation pages.",
    basic: [
      { label: "Metrics", value: "ALFF / ReHo / FC", note: "Computed in validated kernels only." },
      { label: "Capability", value: "review required", note: "Do not mark validated by UI alone." },
    ],
    advanced: [
      { label: "Atlas", value: "not selected", note: "Required for atlas FC." },
      { label: "Precision", value: "backend default", note: "Record in provenance." },
    ],
  },
];

function emptyProjectInventory(dataState: ProjectDataState | undefined): ProjectInventory {
  const resolvedState = dataState ?? "unknown";
  return {
    projectName: "No project inventory",
    modality: "rs-fMRI",
    dataState: resolvedState,
    dataStateLabel:
      resolvedState === "raw_dicom"
        ? "Raw DICOM"
        : resolvedState === "mixed"
          ? "Mixed"
          : resolvedState === "converted_bids"
            ? "Converted BIDS/NIfTI"
            : "Empty project",
    stateSentence: "Project inventory is not loaded yet.",
    rawDicomCandidates: 0,
    dicomSeriesCount: 0,
    dicomFileCount: 0,
    convertedSubjects: 0,
    niftiFileCount: 0,
    hasRawDicom: resolvedState === "raw_dicom",
    hasConvertedData: false,
    metadataOnlyNiftiInventory: false,
  };
}

function PreprocessingTechnicalSections({
  baseUrl,
  isMissingRegistration,
  onToggleDetailedValidation,
  onToggleTechnicalModules,
  preprocessingRunId,
  projectId,
  showDetailedValidation,
  showTechnicalModules,
}: {
  baseUrl: string;
  isMissingRegistration: boolean;
  onToggleDetailedValidation: () => void;
  onToggleTechnicalModules: () => void;
  preprocessingRunId?: string | null;
  projectId: string | null;
  showDetailedValidation: boolean;
  showTechnicalModules: boolean;
}) {
  return (
    <>
      <TechnicalModuleSection
        actionDisabled={isMissingRegistration}
        ariaLabel="Detailed preprocessing checks"
        description="Metadata-only backend checks stay secondary to staged preprocessing setup."
        disabledReason="Register converted BIDS/NIfTI inputs before preprocessing validation checks."
        evidenceLevel={isMissingRegistration ? "blocked" : "backend_required"}
        hideActionLabel="Hide validation checks"
        isOpen={showDetailedValidation}
        onToggle={onToggleDetailedValidation}
        openLabel="Open validation checks"
        safetyNote="Opening validation checks does not run MATLAB, SPM, DPABI, or write outputs."
        status={
          isMissingRegistration ? "Input required" : showDetailedValidation ? "Open" : "On demand"
        }
        statusTone={isMissingRegistration ? "warning" : "info"}
        title="Detailed validation"
      >
        <AdvancedPreprocessingPipelinePanel
          projectId={projectId}
          preprocessingRunId={preprocessingRunId ?? null}
        />
      </TechnicalModuleSection>

      <TechnicalModuleSection
        actionDisabled={isMissingRegistration}
        ariaLabel="SPM technical modules"
        description="Technical preprocessing panels stay secondary and rely on backend approval, environment, and safe-path gates for any execution."
        disabledReason="Register converted BIDS/NIfTI inputs before technical SPM panels are available."
        evidenceLevel={isMissingRegistration ? "blocked" : "backend_required"}
        hideActionLabel="Hide SPM modules"
        isOpen={showTechnicalModules}
        onToggle={onToggleTechnicalModules}
        openLabel="Open SPM modules"
        safetyNote="Opening this section does not run MATLAB, SPM, or DPABI by itself."
        status={
          isMissingRegistration ? "Input required" : showTechnicalModules ? "Open" : "On demand"
        }
        statusTone={isMissingRegistration ? "warning" : "info"}
        title="SPM technical modules"
      >
        <div className={layoutStyles.panelGrid}>
          <div id="rsfmri-slice-timing-panel">
            <RsfmriSliceTimingPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-st-realign-motion-chain-panel">
            <RsfmriStRealignMotionChainPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-coregistration-qc-panel">
            <RsfmriCoregistrationQcPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-segmentation-tissue-qc-panel">
            <RsfmriSegmentationTissueQcPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-normalization-qc-panel">
            <RsfmriNormalizationQcPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-smoothing-qc-panel">
            <RsfmriSmoothingQcPanel baseUrl={baseUrl} />
          </div>
        </div>
      </TechnicalModuleSection>
    </>
  );
}

function InputReadinessCard({ inventory }: { inventory: ProjectInventory }) {
  return (
    <Card className={styles.readinessCard}>
      <div className={styles.sectionHeader}>
        <div>
          <h3>Input readiness</h3>
          <p>Derived from the current project inventory.</p>
        </div>
      </div>
      <div className={styles.readinessMetrics} aria-label="Preprocessing input readiness">
        <div>
          <span>Data state</span>
          <strong>{inventory.dataStateLabel}</strong>
        </div>
        <div>
          <span>Subjects</span>
          <strong>{inventory.convertedSubjects}</strong>
        </div>
        <div>
          <span>NIfTI files</span>
          <strong>{inventory.niftiFileCount.toLocaleString()}</strong>
        </div>
      </div>
    </Card>
  );
}

function PreprocessingStageOverview({
  configMode,
  hasPreprocessingRun,
  inventory,
  isMissingRegistration,
  onConfigModeChange,
  onSelectStage,
  selectedStageName,
}: {
  configMode: ConfigMode;
  hasPreprocessingRun: boolean;
  inventory: ProjectInventory;
  isMissingRegistration: boolean;
  onConfigModeChange: (mode: ConfigMode) => void;
  onSelectStage: (stageName: string) => void;
  selectedStageName: string;
}) {
  const selectedStage =
    preprocessingStages.find((stage) => stage.name === selectedStageName) ?? preprocessingStages[0];
  const activeParams = configMode === "basic" ? selectedStage.basic : selectedStage.advanced;

  return (
    <section className={styles.overviewGrid} aria-labelledby="preprocessing-stage-title">
      <Card className={styles.flowCard} tone="muted">
        <div className={styles.sectionHeader}>
          <div>
            <h3 id="preprocessing-stage-title">Preprocessing stages</h3>
            <p>
              The page follows the rs-fMRI setup order before any reviewed runtime action is used.
            </p>
          </div>
          <Badge
            tone={isMissingRegistration ? "warning" : hasPreprocessingRun ? "info" : "success"}
          >
            {isMissingRegistration ? "Input required" : hasPreprocessingRun ? "Review" : "Ready"}
          </Badge>
        </div>
        <ol className={styles.stageList} aria-label="Preprocessing stages">
          {preprocessingStages.map((stage, index) => {
            const status = stageStatus(index, isMissingRegistration, hasPreprocessingRun);
            return (
              <li
                className={styles.stageItem}
                data-selected={stage.name === selectedStage.name ? "true" : "false"}
                key={stage.name}
              >
                <button
                  type="button"
                  className={styles.stageSelectButton}
                  onClick={() => onSelectStage(stage.name)}
                  aria-label={`Inspect ${stage.name}`}
                >
                  <span className={styles.stageIndex}>{index + 1}</span>
                </button>
                <div className={styles.stageBody}>
                  <div className={styles.stageTitleRow}>
                    <strong>{stage.name}</strong>
                    <Badge tone={stageStatusTone(status)} size="sm">
                      {stageStatusLabel(status)}
                    </Badge>
                  </div>
                  <p>{stage.description}</p>
                  <dl className={styles.stageConfig}>
                    <div>
                      <dt>Basic</dt>
                      <dd>{summarizeParameters(stage.basic)}</dd>
                    </div>
                    <div>
                      <dt>Advanced</dt>
                      <dd>{summarizeParameters(stage.advanced)}</dd>
                    </div>
                  </dl>
                </div>
              </li>
            );
          })}
        </ol>
      </Card>

      <div className={styles.supportStack}>
        <Card className={styles.configCard} aria-label="Selected preprocessing stage configuration">
          <div className={styles.sectionHeader}>
            <div>
              <h3>{selectedStage.name}</h3>
              <p>{selectedStage.description}</p>
            </div>
          </div>
          <div className={styles.configModeSwitch} aria-label="Configuration mode">
            <button
              type="button"
              aria-pressed={configMode === "basic"}
              onClick={() => onConfigModeChange("basic")}
            >
              Basic
            </button>
            <button
              type="button"
              aria-pressed={configMode === "advanced"}
              onClick={() => onConfigModeChange("advanced")}
            >
              Advanced
            </button>
          </div>
          <dl className={styles.paramList}>
            {activeParams.map((param) => (
              <div key={`${configMode}-${param.label}`}>
                <dt>
                  <span>{param.label}</span>
                  {param.range ? <small>{param.range}</small> : null}
                </dt>
                <dd>
                  <strong>{param.value}</strong>
                  {param.unit ? <span>{param.unit}</span> : null}
                  <p>{param.note}</p>
                </dd>
              </div>
            ))}
          </dl>
        </Card>

        <InputReadinessCard inventory={inventory} />

        <Card className={styles.progressiveCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Progressive configuration</h3>
              <p>Common parameters stay first; technical settings stay reviewable.</p>
            </div>
          </div>
          <div className={styles.modeList} aria-label="Preprocessing configuration modes">
            <div>
              <Badge tone="info" size="sm">
                Basic
              </Badge>
              <p>TR, slice reference, smoothing kernel, nuisance model, and filter band.</p>
            </div>
            <div>
              <Badge tone="neutral" size="sm">
                Advanced
              </Badge>
              <p>SPM/DPABI-specific parameters remain visible without changing execution gates.</p>
            </div>
            <div>
              <Badge tone="warning" size="sm">
                Safety
              </Badge>
              <p>External execution, writes, and approvals remain controlled by backend gates.</p>
            </div>
          </div>
        </Card>
      </div>
    </section>
  );
}

function summarizeParameters(parameters: ConfigParameter[]): string {
  return parameters.map((parameter) => parameter.label).join(", ");
}

function stageStatus(
  index: number,
  isMissingRegistration: boolean,
  hasPreprocessingRun: boolean,
): StageStatus {
  if (isMissingRegistration) {
    return index === 0 ? "configure" : "locked";
  }
  if (hasPreprocessingRun) {
    return index === 0 ? "registered" : "review";
  }
  return index === 0 ? "registered" : "configure";
}

function stageStatusLabel(status: StageStatus): string {
  const labels: Record<StageStatus, string> = {
    registered: "Registered",
    configure: "Configure",
    waiting: "Waiting",
    review: "Review",
    locked: "Locked",
  };
  return labels[status];
}

function stageStatusTone(status: StageStatus): "neutral" | "info" | "success" | "warning" {
  if (status === "registered") return "success";
  if (status === "configure") return "info";
  if (status === "locked") return "warning";
  return "neutral";
}
