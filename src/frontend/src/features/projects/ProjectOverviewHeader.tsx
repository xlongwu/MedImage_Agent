import type { ProjectInventory } from "../../lib/projectWorkflow";
import { Badge, Button } from "../../components/ui";

import styles from "./ProjectOverviewHeader.module.css";

export type ProjectOverviewHeaderProps = {
  hasPreprocessingRun: boolean;
  inventory: ProjectInventory | null;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
};

type OverviewAction = {
  explanation: string;
  primary: string;
  secondary: string;
};

export function ProjectOverviewHeader({
  hasPreprocessingRun,
  inventory,
  onPrimaryAction,
  onSecondaryAction,
}: ProjectOverviewHeaderProps) {
  const action = getOverviewAction(inventory, hasPreprocessingRun);
  const statusTone = getStatusTone(inventory);
  const projectName = inventory?.projectName ?? "Project workspace";
  const modality = inventory?.modality ?? "rs-fMRI";
  const stateLabel = inventory?.dataStateLabel ?? "Loading";
  const stateSentence = inventory?.stateSentence ?? "Project inventory is loading.";

  return (
    <section className={styles.header} aria-label="Project overview">
      <div className={styles.summary}>
        <div className={styles.metaRow}>
          <Badge tone={statusTone}>{stateLabel}</Badge>
          <span>{modality}</span>
        </div>
        <h1>{projectName}</h1>
        <p>{stateSentence}</p>
        <InlineMetrics inventory={inventory} />
      </div>
      <aside className={styles.nextAction} aria-label="Recommended next step">
        <span className={styles.kicker}>Recommended next step</span>
        <h2>{action.primary}</h2>
        <p>{action.explanation}</p>
        <div className={styles.actionRow}>
          <Button onClick={onPrimaryAction} variant="primary">
            {action.primary}
          </Button>
          {action.secondary ? (
            <Button onClick={onSecondaryAction} variant="ghost">
              {action.secondary}
            </Button>
          ) : null}
        </div>
      </aside>
    </section>
  );
}

function InlineMetrics({ inventory }: { inventory: ProjectInventory | null }) {
  const metrics = inventory
    ? [
        {
          label: "Raw DICOM",
          value: inventory.rawDicomCandidates,
          detail: `${inventory.dicomSeriesCount} series`,
        },
        {
          label: "DICOM files",
          value: inventory.dicomFileCount.toLocaleString(),
          detail: inventory.hasRawDicom ? "conversion input" : "none detected",
        },
        {
          label: "Converted subjects",
          value: inventory.convertedSubjects,
          detail: inventory.hasConvertedData ? "registered" : "not registered",
        },
        {
          label: "NIfTI files",
          value: inventory.niftiFileCount.toLocaleString(),
          detail: inventory.metadataOnlyNiftiInventory ? "metadata only" : "inventory",
        },
      ]
    : [
        { label: "Raw DICOM", value: "-", detail: "loading" },
        { label: "DICOM files", value: "-", detail: "loading" },
        { label: "Converted subjects", value: "-", detail: "loading" },
        { label: "NIfTI files", value: "-", detail: "loading" },
      ];

  return (
    <dl className={styles.metrics} aria-label="Project inventory metrics">
      {metrics.map((metric) => (
        <div key={metric.label}>
          <dt>{metric.label}</dt>
          <dd>
            <strong>{metric.value}</strong>
            <span>{metric.detail}</span>
          </dd>
        </div>
      ))}
    </dl>
  );
}

function getOverviewAction(
  inventory: ProjectInventory | null,
  hasPreprocessingRun: boolean,
): OverviewAction {
  if (!inventory) {
    return {
      primary: "Review workspace",
      secondary: "",
      explanation: "Inventory is loading. Review workspace state when ready.",
    };
  }

  if (inventory.dataState === "mixed") {
    return {
      primary: "Review conversion state",
      secondary: "Inspect raw DICOM evidence",
      explanation:
        "Raw DICOM and converted outputs coexist. Verify conversion evidence before treating preprocessing as ready.",
    };
  }

  if (inventory.dataState === "raw_dicom") {
    return {
      primary: "Generate conversion dry-run",
      secondary: "Review conversion readiness",
      explanation:
        "Create a read-only conversion plan before NIfTI QC or preprocessing. No conversion writes are requested from this action.",
    };
  }

  if (inventory.dataState === "converted_bids") {
    return {
      primary: hasPreprocessingRun ? "Check preprocessing validation" : "Create preprocessing run",
      secondary: "Review QC report status",
      explanation: "Inspect preprocessing readiness before creating or reviewing a run.",
    };
  }

  return {
    primary: "Import dataset",
    secondary: "",
    explanation:
      "Reference a local BIDS/NIfTI dataset or raw DICOM directory before conversion, QC, or preprocessing workflows are available.",
  };
}

function getStatusTone(
  inventory: ProjectInventory | null,
): "neutral" | "info" | "success" | "warning" {
  if (!inventory) return "neutral";
  if (inventory.dataState === "converted_bids") return "success";
  if (inventory.dataState === "raw_dicom" || inventory.dataState === "mixed") return "warning";
  return "neutral";
}
