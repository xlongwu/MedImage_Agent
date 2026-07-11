import { useEffect, useRef, useState } from "react";
import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import BidsValidationPanel from "../../components/BidsValidationPanel";
import DataReadinessPanel from "../../components/DataReadinessPanel";
import ConversionDryRunPanel from "../../components/ConversionDryRunPanel";
import DicomConversionReviewPanel from "../../components/DicomConversionReviewPanel";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { DataSeriesSelection } from "../../lib/workspaceSelection";
import { getLatestConversionDryRun, runConversionDryRun } from "../../lib/api/dicom";
import type { ConversionDryRunResponse } from "../../types";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import { Badge, Card, EmptyState, Table } from "../../components/ui";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { ConversionStepper } from "./ConversionStepper";
import { DicomSeriesTable } from "./DicomSeriesTable";
import styles from "./DataConversionWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

type DryRunRestoreState = "idle" | "loading" | "restored" | "refresh_required" | "error";

export interface DataConversionWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  inventory: ProjectInventory;
  onSelectedDataSeriesChange?: (selection: DataSeriesSelection | null) => void;
}

export function DataConversionWorkspace({
  baseUrl,
  projectId,
  inventory,
  onSelectedDataSeriesChange,
}: DataConversionWorkspaceProps) {
  const [dryRun, setDryRun] = useState<ConversionDryRunResponse | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunError, setDryRunError] = useState("");
  const [dryRunRestoreState, setDryRunRestoreState] = useState<DryRunRestoreState>("idle");
  const [dryRunRestoreMessage, setDryRunRestoreMessage] = useState("");
  const [detailedChecksOpen, setDetailedChecksOpen] = useState(false);
  const dryRunRequestRef = useRef(0);
  const hasRegisteredConvertedInput =
    inventory.hasConvertedData &&
    !inventory.metadataOnlyNiftiInventory &&
    (inventory.convertedSubjects > 0 || inventory.niftiFileCount > 0);
  const isConverted = inventory.dataState === "converted_bids" || hasRegisteredConvertedInput;
  const isRawConversionState = inventory.dataState === "raw_dicom";

  useEffect(() => {
    if (!projectId || !isRawConversionState) {
      setDryRun(null);
      setDryRunRestoreState("idle");
      setDryRunRestoreMessage("");
      return;
    }

    const requestId = dryRunRequestRef.current + 1;
    dryRunRequestRef.current = requestId;
    setDryRun(null);
    setDryRunError("");
    setDryRunRestoreState("loading");
    setDryRunRestoreMessage("Checking persisted dry-run review package...");

    getLatestConversionDryRun(baseUrl, projectId)
      .then((response) => {
        if (dryRunRequestRef.current !== requestId) return;
        if (response.ok && response.mapping_preview.length > 0) {
          setDryRun(response);
          setDryRunRestoreState("restored");
          setDryRunRestoreMessage("Restored mappings from the latest persisted review package.");
          return;
        }
        setDryRun(null);
        setDryRunRestoreState("refresh_required");
        setDryRunRestoreMessage(
          response.blocking_issues[0]
            ? `Dry-run preview not loaded; refresh required. ${response.blocking_issues[0]}`
            : "Dry-run preview not loaded; refresh required for the active project.",
        );
      })
      .catch((error) => {
        if (dryRunRequestRef.current !== requestId) return;
        setDryRun(null);
        setDryRunRestoreState("error");
        setDryRunRestoreMessage(
          `Dry-run mappings were not restored: ${
            error instanceof Error ? error.message : String(error)
          }. Refresh is required.`,
        );
      });
  }, [baseUrl, isRawConversionState, projectId]);

  const handleGenerateDryRun = async () => {
    if (!projectId || dryRunLoading || dryRunRestoreState === "loading") return;
    const requestId = dryRunRequestRef.current + 1;
    dryRunRequestRef.current = requestId;
    setDryRunLoading(true);
    setDryRunError("");
    setDryRunRestoreState("idle");
    setDryRunRestoreMessage("");
    try {
      const response = await runConversionDryRun(baseUrl, projectId);
      if (dryRunRequestRef.current === requestId) {
        setDryRun(response);
      }
    } catch (error) {
      if (dryRunRequestRef.current === requestId) {
        setDryRunError(error instanceof Error ? error.message : String(error));
      }
    } finally {
      if (dryRunRequestRef.current === requestId) {
        setDryRunLoading(false);
      }
    }
  };

  if (isConverted) {
    return (
      <div className={layoutStyles.stack}>
        <WorkspaceHeader
          title="Data & Conversion"
          subtitle={
            inventory.dataState === "mixed"
              ? "Converted BIDS/NIfTI outputs are registered while source DICOM remains available for audit."
              : "Converted BIDS/NIfTI project overview."
          }
          status="Ready"
        />
        <div className={layoutStyles.modeNote}>
          {inventory.dataState === "mixed"
            ? "DICOM conversion has completed and registered preprocessing input. Raw DICOM evidence remains visible in detailed checks for audit and review."
            : "This project is already in converted BIDS/NIfTI mode. DICOM conversion is not the primary workflow."}
        </div>
        <ConvertedInventorySummary inventory={inventory} />
        <div className={layoutStyles.summaryRow}>
          <div>
            <span>Primary action</span>
            <strong>Validate converted inventory</strong>
          </div>
          <div>
            <span>Next workspace</span>
            <strong>Preprocessing or QC</strong>
          </div>
        </div>
        <div className={layoutStyles.panelGrid}>
          <div id="bids-validation-panel">
            <BidsValidationPanel
              baseUrl={baseUrl}
              projectId={projectId}
              projectState={inventory.dataState}
            />
          </div>
        </div>
        <DetailedDataChecks
          baseUrl={baseUrl}
          includeBidsValidation={false}
          includeConversionReview={inventory.dataState === "mixed"}
          inventory={inventory}
          isOpen={detailedChecksOpen}
          onToggle={() => setDetailedChecksOpen((open) => !open)}
          projectId={projectId}
        />
      </div>
    );
  }

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Data & Conversion"
        subtitle="Review raw input state, BIDS/NIfTI readiness, and conversion safety without writing files."
        status={
          inventory.hasRawDicom
            ? "Expected before conversion"
            : inventory.hasConvertedData
              ? "Ready"
              : "Not started"
        }
      />
      {inventory.dataState === "mixed" && (
        <div className={`${layoutStyles.modeNote} ${layoutStyles.modeNoteSpaced}`}>
          <strong>Notice:</strong> Converted BIDS/NIfTI outputs are already present in this project,
          but raw DICOM files have also been detected. Review the conversion state before
          preprocessing.
        </div>
      )}
      {isRawConversionState ? (
        <div className={styles.rawWorkspace}>
          <div className={styles.rawMain}>
            <DicomSeriesTable
              dryRun={dryRun}
              error={dryRunError}
              inventory={inventory}
              loading={dryRunLoading || dryRunRestoreState === "loading"}
              onGenerateDryRun={handleGenerateDryRun}
              onReviewSelectionChange={onSelectedDataSeriesChange}
              projectId={projectId}
              restoreMessage={dryRunRestoreMessage}
              restoreState={dryRunRestoreState}
            />
          </div>
          <aside className={styles.rawAside} aria-label="Conversion readiness">
            <ConversionStepper dryRun={dryRun} error={dryRunError} inventory={inventory} />
          </aside>
        </div>
      ) : (
        <EmptyDataState />
      )}
      <DetailedDataChecks
        baseUrl={baseUrl}
        includeBidsValidation={true}
        includeConversionReview={isRawConversionState}
        inventory={inventory}
        isOpen={detailedChecksOpen}
        onToggle={() => setDetailedChecksOpen((open) => !open)}
        projectId={projectId}
      />
    </div>
  );
}

function DetailedDataChecks({
  baseUrl,
  includeBidsValidation,
  includeConversionReview,
  inventory,
  isOpen,
  onToggle,
  projectId,
}: {
  baseUrl: string;
  includeBidsValidation: boolean;
  includeConversionReview: boolean;
  inventory: ProjectInventory;
  isOpen: boolean;
  onToggle: () => void;
  projectId: string | null;
}) {
  const isEmpty = inventory.dataState === "empty" || inventory.dataState === "unknown";
  const status = isOpen ? "Open for review" : "Collapsed";
  const helperText = isEmpty
    ? "Only inventory/readiness checks are available until data is referenced."
    : includeConversionReview
      ? "Dry-run and review panels stay read-only until backend approval gates allow more."
      : "Converted projects keep validation checks separate from conversion workflow.";

  return (
    <TechnicalModuleSection
      ariaLabel="Detailed data checks"
      bodyClassName={layoutStyles.panelGrid}
      description="Secondary backend checks for readiness, validation, dry-run review, and diagnostics. These panels do not execute conversion or mark artifacts computed."
      evidenceLevel={isEmpty ? "backend_required" : "metadata_only"}
      helperText={helperText}
      hideActionLabel="Hide detailed checks"
      isOpen={isOpen}
      onToggle={onToggle}
      openLabel="Open detailed checks"
      safetyNote="Backend gates remain authoritative. Opening these checks performs no conversion, no preprocessing, no source-data writes, and no scientific validation claim."
      status={status}
      statusTone={isOpen ? "info" : "neutral"}
      title="Detailed data checks"
    >
      <div id="data-readiness-panel">
        <DataReadinessPanel
          baseUrl={baseUrl}
          projectId={projectId}
          projectState={inventory.dataState}
        />
      </div>
      {includeBidsValidation ? (
        <div id="bids-validation-panel">
          <BidsValidationPanel
            baseUrl={baseUrl}
            projectId={projectId}
            projectState={inventory.dataState}
          />
        </div>
      ) : null}
      {includeConversionReview ? (
        <>
          <div id="conversion-dry-run-panel">
            <ConversionDryRunPanel baseUrl={baseUrl} projectId={projectId} />
          </div>
          <div id="dicom-conversion-review-panel">
            <DicomConversionReviewPanel baseUrl={baseUrl} projectId={projectId} />
          </div>
        </>
      ) : null}
    </TechnicalModuleSection>
  );
}

function ConvertedInventorySummary({ inventory }: { inventory: ProjectInventory }) {
  return (
    <Card className={styles.summaryCard} tone="muted">
      <div className={styles.cardHeader}>
        <div>
          <h3>Converted imaging inventory</h3>
          <p>Data & Conversion is now focused on validation because BIDS/NIfTI outputs exist.</p>
        </div>
        <Badge tone="success">{inventory.dataStateLabel}</Badge>
      </div>
      <Table caption="Converted data readiness summary">
        <thead>
          <tr>
            <th>Scope</th>
            <th>Evidence</th>
            <th>Status</th>
            <th>Next action</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Converted subjects</td>
            <td>{inventory.convertedSubjects}</td>
            <td>
              <Badge tone="success" size="sm">
                Registered
              </Badge>
            </td>
            <td>Check preprocessing validation</td>
          </tr>
          <tr>
            <td>NIfTI files</td>
            <td>{inventory.niftiFileCount.toLocaleString()}</td>
            <td>
              <EvidenceBadge
                level={inventory.metadataOnlyNiftiInventory ? "metadata_only" : "created"}
                size="sm"
              />
            </td>
            <td>Review BIDS validation and QC summary</td>
          </tr>
        </tbody>
      </Table>
    </Card>
  );
}

function EmptyDataState() {
  return (
    <EmptyState
      title="No imaging inventory yet"
      description="Import a BIDS/NIfTI dataset or raw DICOM directory before conversion, QC, or preprocessing actions become available."
    />
  );
}
