import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ProjectDetail } from "../../lib/types/project";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { WorkspaceSelectionContext } from "../../lib/workspaceSelection";
import type { EvidenceLevel } from "../../lib/evidence";
import { Badge, Button, Card } from "../../components/ui";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import styles from "./ContextInspector.module.css";

export interface ContextInspectorProps {
  activePageLabel: string;
  inventory: ProjectInventory | null;
  isOpen: boolean;
  onToggle: () => void;
  project: ProjectDetail;
  model: ModelStatus | null;
  dataset: DatasetSummary | null;
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  externalSmokeApprovedBy: string;
  onConfigure: () => void;
  selectionContext: WorkspaceSelectionContext;
}

export function ContextInspector({
  activePageLabel,
  inventory,
  isOpen,
  onToggle,
  project,
  model,
  dataset,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  onConfigure,
  selectionContext,
}: ContextInspectorProps) {
  if (!isOpen) {
    return null;
  }

  const projectRows = [
    ["Project", project?.name ?? "No project selected"],
    ["Data state", inventory?.dataStateLabel ?? "Loading"],
    ["Modality", inventory?.modality ?? project?.modality ?? "rs-fMRI"],
    ["Subjects", formatCount(dataset?.subjects ?? project?.subjects_count)],
    ["Scans", formatCount(dataset?.scans ?? project?.scans_count)],
    ["Dataset health", dataset?.health_status ?? "Not loaded"],
  ];
  const executionRows = [
    ["Workspace", activePageLabel],
    ["Execution mode", formatExecutionMode(executionMode)],
    ["Selected run", formatRunSelection(selectionContext)],
    ["Model", model ? `${model.model_name} ${model.version}` : "Not loaded"],
    ["External smoke", externalSmokeApprovedRun ? "Approved elsewhere" : "Not approved here"],
    ["Approved by", externalSmokeApprovedRun ? externalSmokeApprovedBy || "Missing name" : "N/A"],
  ];
  const selectedObjectRows = [
    ["Data table", formatDataSeries(selectionContext)],
    ["Subject", selectionContext.image.subjectId || "No subject selected"],
    ["Series", selectionContext.image.series || "No series selected"],
    ["Plane", formatPlane(selectionContext.image.plane)],
    ["Image source", selectionContext.image.source || "No source selected"],
    ["Plan node", formatPlanNode(selectionContext)],
    ["Artifact", formatArtifact(selectionContext)],
  ];
  const evidenceGroups = buildEvidenceGroups(inventory, selectionContext);

  return (
    <aside className={styles.inspector} aria-label="Context inspector">
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>Inspector</h3>
          <p>Read-only project, workspace, run, and execution context</p>
        </div>
        <button
          type="button"
          className={styles.closeButton}
          onClick={onToggle}
          aria-label="Close inspector"
          title="Close"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path
              fill="none"
              stroke="currentColor"
              strokeLinecap="round"
              strokeWidth="1.6"
              d="M4 4l8 8M12 4l-8 8"
            />
          </svg>
        </button>
      </header>

      <div className={styles.body}>
        <Card className={styles.summaryCard} tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h4>Project context</h4>
              <p>Evidence and dataset facts stay read-only in the Inspector.</p>
            </div>
            <Badge tone="info">Summary</Badge>
          </div>
          <dl className={styles.summaryList}>
            {projectRows.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className={styles.summaryCard}>
          <div className={styles.cardHeader}>
            <div>
              <h4>Workspace context</h4>
              <p>Execution settings are surfaced here as status, not editable controls.</p>
            </div>
            <Badge tone="warning">Backend owned</Badge>
          </div>
          <dl className={styles.summaryList}>
            {executionRows.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className={styles.summaryCard} tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h4>Selected objects</h4>
              <p>Current data table, image, node, run, and artifact summaries.</p>
            </div>
            <Badge tone="neutral">Read only</Badge>
          </div>
          <dl className={styles.summaryList}>
            {selectedObjectRows.map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <Card className={styles.summaryCard}>
          <div className={styles.cardHeader}>
            <div>
              <h4>Evidence drilldown</h4>
              <p>Truth levels are read from shared evidence definitions, not color alone.</p>
            </div>
            <Badge tone="info">Read only</Badge>
          </div>
          <div className={styles.evidenceGrid}>
            {evidenceGroups.map((group) => (
              <section className={styles.evidenceGroup} key={group.title}>
                <div className={styles.evidenceGroupHeader}>
                  <div>
                    <h5>{group.title}</h5>
                    <p>{group.summary}</p>
                  </div>
                  <EvidenceBadge level={group.level} size="sm" />
                </div>
                <dl className={styles.evidenceList}>
                  {group.rows.map(([label, value]) => (
                    <div key={label}>
                      <dt>{label}</dt>
                      <dd>{value}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            ))}
          </div>
        </Card>

        <Card className={styles.boundaryCard}>
          <div>
            <h4>Configuration boundary</h4>
            <p>
              Change execution mode, environment readiness, external smoke approval, and other
              setup controls in Settings / Environment. The Inspector does not run, approve,
              export, or alter safety policy.
            </p>
          </div>
          <Button variant="secondary" onClick={onConfigure}>
            Open Settings
          </Button>
        </Card>
      </div>
    </aside>
  );
}

function formatCount(value: number | null | undefined): string {
  return Number.isFinite(Number(value)) ? String(value) : "Not loaded";
}

function formatExecutionMode(mode: ExecutionMode): string {
  if (mode === "external_smoke") return "External smoke";
  if (mode === "rsfmri_python") return "rs-fMRI Python";
  return "Simulated";
}

function formatPlane(plane: WorkspaceSelectionContext["image"]["plane"]): string {
  if (plane === "sagittal") return "Sagittal";
  if (plane === "coronal") return "Coronal";
  return "Axial";
}

function formatPlanNode(selection: WorkspaceSelectionContext): string {
  const node = selection.planNode;
  if (!node) return "No plan node selected";
  return `${node.name} (${node.risk})`;
}

function formatDataSeries(selection: WorkspaceSelectionContext): string {
  const dataSeries = selection.dataSeries;
  if (!dataSeries) return "No data table row selected";
  return `${dataSeries.subject} / ${dataSeries.series}`;
}

function formatArtifact(selection: WorkspaceSelectionContext): string {
  const artifact = selection.artifact;
  if (!artifact) return "No artifact selected";
  return `${artifact.name} - ${artifact.stage}`;
}

function formatRunSelection(selection: WorkspaceSelectionContext): string {
  if (!selection.run.id) return "No run selected";
  if (!selection.run.name) return selection.run.id;
  return `${selection.run.name} (${selection.run.status ?? "status unknown"})`;
}

type EvidenceGroup = {
  level: EvidenceLevel;
  rows: Array<[string, string]>;
  summary: string;
  title: string;
};

function buildEvidenceGroups(
  inventory: ProjectInventory | null,
  selection: WorkspaceSelectionContext,
): EvidenceGroup[] {
  const dataSeries = selection.dataSeries;
  const artifact = selection.artifact;
  const planNode = selection.planNode;
  const run = selection.run;
  const imageEvidence: EvidenceLevel = selection.image.source ? "preview_only" : "backend_required";

  return [
    {
      title: "Project",
      summary: inventory?.dataStateLabel ?? "Project inventory is still loading.",
      level: projectEvidenceLevel(inventory),
      rows: [
        ["Data state", inventory?.dataStateLabel ?? "Not loaded"],
        ["Modality", inventory?.modality ?? "Not loaded"],
      ],
    },
    {
      title: "Subject",
      summary: dataSeries?.subject ?? selection.image.subjectId ?? "No subject selected.",
      level: dataSeries?.evidenceLevel ?? imageEvidence,
      rows: [
        ["Data table subject", dataSeries?.subject ?? "No data table row selected"],
        ["Image subject", selection.image.subjectId ?? "No image subject selected"],
      ],
    },
    {
      title: "Series",
      summary: dataSeries?.series ?? selection.image.series ?? "No series selected.",
      level: dataSeries?.evidenceLevel ?? imageEvidence,
      rows: [
        ["Data table series", dataSeries?.series ?? "No data table row selected"],
        ["Status", dataSeries?.status ?? "No table status selected"],
        ["Image series", selection.image.series ?? "No image series selected"],
      ],
    },
    {
      title: "Plan node",
      summary: planNode ? planNode.name : "No plan node selected.",
      level: planNode ? "planned" : "backend_required",
      rows: [
        ["Node ID", planNode?.id ?? "Not selected"],
        ["Risk", planNode?.risk ?? "Not selected"],
        ["Backend", planNode?.backend ?? "Not selected"],
      ],
    },
    {
      title: "Run",
      summary: run.id ? formatRunSelection(selection) : "No run selected.",
      level: run.id ? "created" : "backend_required",
      rows: [
        ["Run ID", run.id ?? "Not selected"],
        ["Status", run.status ?? "No status selected"],
        ["Pipeline", run.pipeline ?? "No pipeline selected"],
      ],
    },
    {
      title: "Artifact",
      summary: artifact ? artifact.name : "No artifact selected.",
      level: artifact?.evidenceLevel ?? "backend_required",
      rows: [
        ["Path", artifact?.path ?? "No artifact path selected"],
        ["Stage", artifact?.stage ?? "Not selected"],
        ["Run", artifact?.runId ?? "No producing run selected"],
      ],
    },
  ];
}

function projectEvidenceLevel(inventory: ProjectInventory | null): EvidenceLevel {
  if (!inventory) return "backend_required";
  if (inventory.dataState === "converted_bids") {
    return inventory.metadataOnlyNiftiInventory ? "metadata_only" : "created";
  }
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") {
    return "metadata_only";
  }
  return "backend_required";
}
