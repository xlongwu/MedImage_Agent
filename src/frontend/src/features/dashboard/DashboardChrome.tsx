import { memo, useCallback, type KeyboardEvent } from "react";
import { MetricTile, StatusPill as DashboardStatusPill } from "../../components/dashboardUi";
import type { ProjectInventory, WorkflowTab } from "../../lib/projectWorkflow";
import type { ProjectSummary } from "../../lib/types/project";

type StatusTone = "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown";

const workflowTabItems: Array<{ id: WorkflowTab; label: string; description: string }> = [
  { id: "data", label: "Data & Conversion", description: "DICOM, BIDS, dry-run" },
  { id: "preprocessing", label: "Preprocessing", description: "Validation and reports" },
  { id: "reports", label: "QC & Reports", description: "Artifacts and warnings" },
  { id: "environment", label: "Settings / Environment", description: "Planning tools" },
];

export const WorkspaceSuspenseFallback = memo(function WorkspaceSuspenseFallback({
  label,
}: {
  label: string;
}) {
  return (
    <div className="workspace-suspense-fallback" role="status" aria-live="polite">
      <span className="loading-dot" />
      <span>{label}</span>
    </div>
  );
});

export const TopBar = memo(function TopBar({
  health,
  apiError,
  onRetry,
  onToggleMode,
  modeLabel,
}: {
  health: boolean | null;
  apiError: string;
  onRetry: () => void;
  onToggleMode: () => void;
  modeLabel: string;
}) {
  return (
    <>
      <header className="topbar">
        <div className="window-caption">
          <span className="app-spark">M</span>
          <strong>MedImage Agent</strong>
        </div>
        <label className="search-box" htmlFor="global-search">
          <span>Search</span>
          <input
            id="global-search"
            type="search"
            aria-label="Search projects, datasets, and studies"
            placeholder="projects, datasets, studies..."
          />
          <kbd>Ctrl K</kbd>
        </label>
        <div className="top-actions">
          <span className={`backend-chip ${health ? "online" : health === false ? "offline" : ""}`}>
            {health === null ? "Checking" : health ? "Backend Connected" : "Backend Offline"}
          </span>
          {!health ? <button onClick={onRetry}>Retry</button> : null}
          <button onClick={onToggleMode}>{modeLabel}</button>
          <div className="profile-chip">
            <span>AM</span>
            <div>
              <strong>Dr. Alex Morgan</strong>
              <small>Local lab desktop</small>
            </div>
          </div>
        </div>
      </header>
      {apiError ? <div className="api-banner">{apiError}</div> : null}
    </>
  );
});

export const ProjectList = memo(function ProjectList({
  projects,
  selectedProjectId,
  loading,
  error,
  deletingProjectId,
  onSelect,
  onDelete,
}: {
  projects: ProjectSummary[];
  selectedProjectId: string;
  loading: boolean;
  error: string;
  deletingProjectId: string | null;
  onSelect: (id: string) => void;
  onDelete: (id: string, name: string) => void;
}) {
  return (
    <div className="project-stack">
      <div className="panel-kicker">
        Recent projects {loading ? "(loading)" : error ? "(fallback)" : ""}
      </div>
      {projects.map((item) => (
        <div key={item.id} className="project-pill-row">
          <button
            className={`project-pill ${item.id === selectedProjectId ? "selected" : ""}`}
            onClick={() => onSelect(item.id)}
            title={item.name}
          >
            <span className="project-pill-name">{item.name}</span>
            {item.id === selectedProjectId ? <span className="project-pill-dot" /> : null}
          </button>
          <button
            type="button"
            className="project-delete-button"
            title={`Remove ${item.name}`}
            aria-label={`Remove ${item.name} from Recent projects`}
            disabled={deletingProjectId === item.id}
            onClick={() => onDelete(item.id, item.name)}
          >
            {deletingProjectId === item.id ? "..." : "x"}
          </button>
        </div>
      ))}
    </div>
  );
});

export const ProjectHeroPanel = memo(function ProjectHeroPanel({
  inventory,
}: {
  inventory: ProjectInventory;
}) {
  return (
    <section className="project-hero-panel" aria-label="Project summary">
      <div className="summary-meta-row">
        <DashboardStatusPill
          status={
            inventory.dataState === "converted_bids"
              ? "ready"
              : inventory.dataState === "empty"
                ? "not_started"
                : "warning"
          }
        >
          {inventory.dataStateLabel}
        </DashboardStatusPill>
        <span className="panel-kicker">{inventory.modality}</span>
      </div>
      <h1>{inventory.projectName}</h1>
      <p className="project-state-sentence">{inventory.stateSentence}</p>

      <ProjectInventorySummary inventory={inventory} />
      {inventory.metadataOnlyNiftiInventory ? (
        <div className="panel-kicker panel-kicker-spaced">NIfTI inventory: metadata only</div>
      ) : null}
    </section>
  );
});

const ProjectInventorySummary = memo(function ProjectInventorySummary({
  inventory,
}: {
  inventory: ProjectInventory;
}) {
  return (
    <div className="hero-metrics-grid">
      <MetricTile
        label="Raw DICOM candidates"
        value={inventory.rawDicomCandidates}
        tone={inventory.hasRawDicom ? "blue" : "neutral"}
      />
      <MetricTile label="DICOM series" value={inventory.dicomSeriesCount} />
      <MetricTile label="DICOM files" value={inventory.dicomFileCount.toLocaleString()} />
      <MetricTile
        label="Converted subjects"
        value={inventory.convertedSubjects}
        tone={inventory.convertedSubjects > 0 ? "green" : "neutral"}
      />
      <MetricTile
        label="NIfTI files"
        value={inventory.niftiFileCount.toLocaleString()}
        tone={inventory.niftiFileCount > 0 ? "green" : "neutral"}
      />
    </div>
  );
});

export const RecommendedNextStepCard = memo(function RecommendedNextStepCard({
  inventory,
  hasPreprocessingRun,
  onPrimaryAction,
  onSecondaryAction,
}: {
  inventory: ProjectInventory;
  hasPreprocessingRun: boolean;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
}) {
  const primary =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Generate conversion dry-run"
      : inventory.dataState === "converted_bids"
        ? hasPreprocessingRun
          ? "Check preprocessing validation"
          : "Create preprocessing run"
        : "Import dataset";
  const explanation =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Create a read-only conversion plan before NIfTI QC or preprocessing."
      : inventory.dataState === "converted_bids"
        ? "Inspect preprocessing readiness before creating or reviewing a run."
        : "Import a BIDS/NIfTI dataset or raw DICOM directory to begin.";
  const secondary =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Review conversion readiness"
      : inventory.dataState === "converted_bids"
        ? "Review QC report status"
        : "";
  const steps =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? ["Generate conversion dry-run", "Review conversion readiness", "Persist review package"]
      : inventory.dataState === "converted_bids"
        ? [
            hasPreprocessingRun ? "Check preprocessing validation" : "Create preprocessing run",
            "Review QC report status",
            "Open Plan Review when ready",
          ]
        : ["Import dataset", "Review data readiness", "Check environment health"];

  return (
    <aside className="recommended-card" aria-label="Recommended next step">
      <div>
        <h2>Recommended Next Step</h2>
        <p>{explanation}</p>
      </div>
      <ol className="recommended-steps">
        {steps.slice(0, 3).map((step, index) => (
          <li key={step}>
            <span>{index + 1}</span>
            {step}
          </li>
        ))}
      </ol>
      <div className="recommended-actions">
        <button type="button" className="primary-scroll-button" onClick={onPrimaryAction}>
          {primary}
        </button>
        {secondary ? (
          <button type="button" className="secondary-scroll-button" onClick={onSecondaryAction}>
            {secondary}
          </button>
        ) : null}
      </div>
    </aside>
  );
});

export const ReadinessStatusStrip = memo(function ReadinessStatusStrip({
  inventory,
  health,
  hasPreprocessingRun,
}: {
  inventory: ProjectInventory;
  health: boolean | null;
  hasPreprocessingRun: boolean;
}) {
  const isConverted = inventory.dataState === "converted_bids";
  const isRawDicom = inventory.dataState === "raw_dicom";
  const isMixed = inventory.dataState === "mixed";
  const isEmpty = inventory.dataState === "empty";

  let dataStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" =
    "unknown";
  if (isConverted) {
    dataStatus = "ready";
  } else if (isRawDicom || isMixed) {
    dataStatus = inventory.rawDicomCandidates > 0 ? "ready" : "warning";
  } else if (isEmpty) {
    dataStatus = "not_started";
  }

  const dicomStatus = inventory.dicomFileCount > 0 ? "ready" : "not_applicable";

  let bidsStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" =
    "unknown";
  if (isConverted) {
    bidsStatus = "ready";
  } else if (isRawDicom) {
    bidsStatus = "warning";
  } else if (isMixed) {
    bidsStatus = "ready";
  } else if (isEmpty) {
    bidsStatus = "not_started";
  }

  let safetyStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" =
    "unknown";
  if (isConverted) {
    safetyStatus = "not_applicable";
  } else if (isRawDicom || isMixed) {
    safetyStatus = "warning";
  } else {
    safetyStatus = "not_applicable";
  }

  let prepStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" =
    "unknown";
  if (isConverted || isMixed) {
    prepStatus = hasPreprocessingRun ? "ready" : "not_started";
  } else if (isRawDicom) {
    prepStatus = "not_applicable";
  } else {
    prepStatus = "not_started";
  }

  const envStatus = health === false ? "blocked" : health ? "ready" : "unknown";

  return (
    <section className="readiness-status-strip" aria-label="Readiness status strip">
      <StatusStripItem label="Data" status={dataStatus} />
      <StatusStripItem label="DICOM" status={dicomStatus} />
      <StatusStripItem label="BIDS/NIfTI" status={bidsStatus} projectState={inventory.dataState} />
      <StatusStripItem
        label="Conversion Safety"
        status={safetyStatus}
        projectState={inventory.dataState}
      />
      <StatusStripItem label="Preprocessing" status={prepStatus} />
      <StatusStripItem label="Environment" status={envStatus} />
    </section>
  );
});

const StatusStripItem = memo(function StatusStripItem({
  label,
  status,
  projectState,
}: {
  label: string;
  status: StatusTone;
  projectState?: string;
}) {
  let copy: string | undefined = undefined;
  if (label === "BIDS/NIfTI" && status === "warning" && projectState === "raw_dicom") {
    copy = "Expected before conversion";
  } else if (
    label === "Conversion Safety" &&
    status === "warning" &&
    projectState === "raw_dicom"
  ) {
    copy = "Review required";
  }
  return (
    <div className="status-strip-item">
      <small>{label}</small>
      <DashboardStatusPill status={status}>{copy}</DashboardStatusPill>
    </div>
  );
});

export const WorkflowTabs = memo(function WorkflowTabs({
  activeTab,
  onChange,
}: {
  activeTab: WorkflowTab;
  onChange: (tab: WorkflowTab) => void;
}) {
  const handleKeyDown = useCallback(
    (event: KeyboardEvent<HTMLButtonElement>, tabId: WorkflowTab) => {
      const currentIndex = workflowTabItems.findIndex((tab) => tab.id === tabId);
      const lastIndex = workflowTabItems.length - 1;
      let nextIndex: number | null = null;
      if (event.key === "ArrowRight" || event.key === "ArrowDown") {
        nextIndex = currentIndex === lastIndex ? 0 : currentIndex + 1;
      } else if (event.key === "ArrowLeft" || event.key === "ArrowUp") {
        nextIndex = currentIndex === 0 ? lastIndex : currentIndex - 1;
      } else if (event.key === "Home") {
        nextIndex = 0;
      } else if (event.key === "End") {
        nextIndex = lastIndex;
      }
      if (nextIndex === null) {
        return;
      }
      event.preventDefault();
      const nextTab = workflowTabItems[nextIndex];
      onChange(nextTab.id);
      window.requestAnimationFrame(() => {
        document.getElementById(`workflow-tab-${nextTab.id}`)?.focus();
      });
    },
    [onChange],
  );

  return (
    <nav className="workflow-tabs" role="tablist" aria-label="Workflow stages">
      {workflowTabItems.map((tab) => (
        <button
          key={tab.id}
          id={`workflow-tab-${tab.id}`}
          type="button"
          role="tab"
          className={activeTab === tab.id ? "active" : ""}
          aria-selected={activeTab === tab.id}
          aria-controls="workflow-workspace"
          tabIndex={activeTab === tab.id ? 0 : -1}
          onClick={() => onChange(tab.id)}
          onKeyDown={(event) => handleKeyDown(event, tab.id)}
        >
          <span>{tab.label}</span>
          <small>{tab.description}</small>
        </button>
      ))}
    </nav>
  );
});

export const WorkspaceHeader = memo(function WorkspaceHeader({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle: string;
  status?: string;
}) {
  return (
    <div className="workspace-header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {status ? <DashboardStatusPill status={status}>{status}</DashboardStatusPill> : null}
    </div>
  );
});
