import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ProjectDetail } from "../../lib/types/project";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { WorkspaceSelectionContext } from "../../lib/workspaceSelection";
import type { EvidenceLevel } from "../../lib/evidence";
import { Badge, Button, Card } from "../../components/ui";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import { useI18n } from "../../i18n/useI18n";
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
  const { t } = useI18n();
  if (!isOpen) {
    return null;
  }

  const projectRows = [
    [t("inspector.project"), project?.name ?? t("inspector.noProject")],
    [t("inspector.dataState"), inventory?.dataStateLabel ?? t("inspector.loading")],
    [t("inspector.modality"), inventory?.modality ?? project?.modality ?? "rs-fMRI"],
    [t("inspector.subjects"), formatCount(dataset?.subjects ?? project?.subjects_count, t)],
    [t("inspector.scans"), formatCount(dataset?.scans ?? project?.scans_count, t)],
    [t("inspector.datasetHealth"), dataset?.health_status ?? t("inspector.notLoaded")],
  ];
  const executionRows = [
    [t("inspector.workspace"), activePageLabel],
    [t("inspector.executionMode"), formatExecutionMode(executionMode, t)],
    [t("inspector.selectedRun"), formatRunSelection(selectionContext, t)],
    [
      t("inspector.model"),
      model ? `${model.model_name} ${model.version}` : t("inspector.notLoaded"),
    ],
    [
      t("inspector.externalSmoke"),
      externalSmokeApprovedRun ? t("inspector.approvedElsewhere") : t("inspector.notApprovedHere"),
    ],
    [
      t("inspector.approvedBy"),
      externalSmokeApprovedRun
        ? externalSmokeApprovedBy || t("inspector.missingName")
        : t("inspector.na"),
    ],
  ];
  const selectedObjectRows = [
    [t("inspector.dataTable"), formatDataSeries(selectionContext, t)],
    [t("inspector.subject"), selectionContext.image.subjectId || t("inspector.noSubject")],
    [t("inspector.series"), selectionContext.image.series || t("inspector.noSeries")],
    [t("inspector.plane"), formatPlane(selectionContext.image.plane, t)],
    [t("inspector.imageSource"), selectionContext.image.source || t("inspector.noSource")],
    [t("inspector.planNode"), formatPlanNode(selectionContext, t)],
    [t("inspector.artifact"), formatArtifact(selectionContext, t)],
  ];
  const evidenceGroups = buildEvidenceGroups(inventory, selectionContext, t);

  return (
    <aside className={styles.inspector} aria-label={t("inspector.aria")}>
      <header className={styles.header}>
        <div>
          <h3 className={styles.title}>{t("inspector.title")}</h3>
          <p>{t("inspector.description")}</p>
        </div>
        <button
          type="button"
          className={styles.closeButton}
          onClick={onToggle}
          aria-label={t("inspector.close")}
          title={t("common.close")}
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
              <h4>{t("inspector.projectContext")}</h4>
              <p>{t("inspector.projectDescription")}</p>
            </div>
            <Badge tone="info">{t("inspector.summary")}</Badge>
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
              <h4>{t("inspector.workspaceContext")}</h4>
              <p>{t("inspector.workspaceDescription")}</p>
            </div>
            <Badge tone="warning">{t("inspector.backendOwned")}</Badge>
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
              <h4>{t("inspector.selectedObjects")}</h4>
              <p>{t("inspector.selectedDescription")}</p>
            </div>
            <Badge tone="neutral">{t("inspector.readOnly")}</Badge>
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
              <h4>{t("inspector.evidenceDrilldown")}</h4>
              <p>{t("inspector.evidenceDescription")}</p>
            </div>
            <Badge tone="info">{t("inspector.readOnly")}</Badge>
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
            <h4>{t("inspector.configurationBoundary")}</h4>
            <p>{t("inspector.configurationDescription")}</p>
          </div>
          <Button variant="secondary" onClick={onConfigure}>
            {t("inspector.openSettings")}
          </Button>
        </Card>
      </div>
    </aside>
  );
}

type Translate = ReturnType<typeof useI18n>["t"];

function formatCount(value: number | null | undefined, t: Translate): string {
  return Number.isFinite(Number(value)) ? String(value) : t("inspector.notLoaded");
}

function formatExecutionMode(mode: ExecutionMode, t: Translate): string {
  if (mode === "external_smoke") return t("inspector.mode.externalSmoke");
  if (mode === "rsfmri_python") return t("inspector.mode.python");
  return t("inspector.mode.simulated");
}

function formatPlane(plane: WorkspaceSelectionContext["image"]["plane"], t: Translate): string {
  if (plane === "sagittal") return t("viewer.plane.sagittal");
  if (plane === "coronal") return t("viewer.plane.coronal");
  return t("viewer.plane.axial");
}

function formatPlanNode(selection: WorkspaceSelectionContext, t: Translate): string {
  const node = selection.planNode;
  if (!node) return t("inspector.noPlanNode");
  return `${node.name} (${node.risk})`;
}

function formatDataSeries(selection: WorkspaceSelectionContext, t: Translate): string {
  const dataSeries = selection.dataSeries;
  if (!dataSeries) return t("inspector.noDataRow");
  return `${dataSeries.subject} / ${dataSeries.series}`;
}

function formatArtifact(selection: WorkspaceSelectionContext, t: Translate): string {
  const artifact = selection.artifact;
  if (!artifact) return t("inspector.noArtifact");
  return `${artifact.name} - ${artifact.stage}`;
}

function formatRunSelection(selection: WorkspaceSelectionContext, t: Translate): string {
  if (!selection.run.id) return t("inspector.noRun");
  if (!selection.run.name) return selection.run.id;
  return `${selection.run.name} (${selection.run.status ?? t("inspector.statusUnknown")})`;
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
  t: Translate,
): EvidenceGroup[] {
  const dataSeries = selection.dataSeries;
  const artifact = selection.artifact;
  const planNode = selection.planNode;
  const run = selection.run;
  const imageEvidence: EvidenceLevel = selection.image.source ? "preview_only" : "backend_required";

  return [
    {
      title: t("inspector.project"),
      summary: inventory?.dataStateLabel ?? t("inspector.projectInventoryLoading"),
      level: projectEvidenceLevel(inventory),
      rows: [
        [t("inspector.dataState"), inventory?.dataStateLabel ?? t("inspector.notLoaded")],
        [t("inspector.modality"), inventory?.modality ?? t("inspector.notLoaded")],
      ],
    },
    {
      title: t("inspector.subject"),
      summary: dataSeries?.subject ?? selection.image.subjectId ?? t("inspector.noSubject"),
      level: dataSeries?.evidenceLevel ?? imageEvidence,
      rows: [
        [t("inspector.dataTableSubject"), dataSeries?.subject ?? t("inspector.noDataRow")],
        [t("inspector.imageSubject"), selection.image.subjectId ?? t("inspector.noImageSubject")],
      ],
    },
    {
      title: t("inspector.series"),
      summary: dataSeries?.series ?? selection.image.series ?? t("inspector.noSeries"),
      level: dataSeries?.evidenceLevel ?? imageEvidence,
      rows: [
        [t("inspector.dataTableSeries"), dataSeries?.series ?? t("inspector.noDataRow")],
        [t("inspector.status"), dataSeries?.status ?? t("inspector.noTableStatus")],
        [t("inspector.imageSeries"), selection.image.series ?? t("inspector.noSeries")],
      ],
    },
    {
      title: t("inspector.planNode"),
      summary: planNode ? planNode.name : t("inspector.noPlanNode"),
      level: planNode ? "planned" : "backend_required",
      rows: [
        [t("inspector.nodeId"), planNode?.id ?? t("inspector.notSelected")],
        [t("inspector.risk"), planNode?.risk ?? t("inspector.notSelected")],
        [t("inspector.backend"), planNode?.backend ?? t("inspector.notSelected")],
      ],
    },
    {
      title: t("inspector.run"),
      summary: run.id ? formatRunSelection(selection, t) : t("inspector.noRun"),
      level: run.id ? "created" : "backend_required",
      rows: [
        [t("inspector.runId"), run.id ?? t("inspector.notSelected")],
        [t("inspector.status"), run.status ?? t("inspector.noStatus")],
        [t("inspector.pipeline"), run.pipeline ?? t("inspector.noPipeline")],
      ],
    },
    {
      title: t("inspector.artifact"),
      summary: artifact ? artifact.name : t("inspector.noArtifact"),
      level: artifact?.evidenceLevel ?? "backend_required",
      rows: [
        [t("inspector.path"), artifact?.path ?? t("inspector.noArtifactPath")],
        [t("inspector.stage"), artifact?.stage ?? t("inspector.notSelected")],
        [t("inspector.run"), artifact?.runId ?? t("inspector.noProducingRun")],
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
