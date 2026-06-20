import { Suspense } from "react";
import { WorkspaceHeader, WorkspaceSuspenseFallback } from "../dashboard/DashboardChrome";
import BidsValidationPanel from "../../components/BidsValidationPanel";
import AdvancedPreprocessingPipelinePanel from "../../components/AdvancedPreprocessingPipelinePanel";
import QcDashboardSummaryPanel from "../../components/QcDashboardSummaryPanel";
import DataReadinessPanel from "../../components/DataReadinessPanel";
import ConversionDryRunPanel from "../../components/ConversionDryRunPanel";
import DicomConversionReviewPanel from "../../components/DicomConversionReviewPanel";
import type { ProjectInventory } from "../../lib/projectWorkflow";

export interface DataConversionWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  inventory: ProjectInventory;
}

export function DataConversionWorkspace({
  baseUrl,
  projectId,
  inventory,
}: DataConversionWorkspaceProps) {
  const isConverted = inventory.dataState === "converted_bids";

  if (isConverted) {
    return (
      <div className="workspace-stack data-conversion-workspace">
        <WorkspaceHeader
          title="Data & Conversion"
          subtitle="Converted BIDS/NIfTI project overview."
          status="Ready"
        />
        <div className="workspace-mode-note">
          This project is already in converted BIDS/NIfTI mode. DICOM conversion is not the primary
          workflow.
        </div>
        <div className="workspace-summary-row">
          <div>
            <span>Primary action</span>
            <strong>Check preprocessing validation</strong>
          </div>
          <div>
            <span>Key blocker</span>
            <strong>None</strong>
          </div>
        </div>
        <div className="workspace-panel-grid">
          <div id="bids-validation-panel">
            <BidsValidationPanel
              baseUrl={baseUrl}
              projectId={projectId}
              projectState={inventory.dataState}
            />
          </div>
          <div id="preprocessing-validation-card">
            <AdvancedPreprocessingPipelinePanel projectId={projectId} preprocessingRunId={null} />
          </div>
          <div id="qc-dashboard-summary-panel">
            <QcDashboardSummaryPanel baseUrl={baseUrl} projectId={projectId} />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-stack data-conversion-workspace">
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
        <div className="workspace-mode-note workspace-mode-note-spaced">
          <strong>Notice:</strong> Converted BIDS/NIfTI outputs are already present in this project,
          but raw DICOM files have also been detected. Review the conversion state before
          preprocessing.
        </div>
      )}
      <div className="workspace-summary-row">
        <div>
          <span>Primary action</span>
          <strong>
            {inventory.hasRawDicom
              ? "Generate conversion dry-run"
              : inventory.hasConvertedData
                ? "Review BIDS/NIfTI validation"
                : "Import dataset"}
          </strong>
        </div>
        <div>
          <span>Key blocker</span>
          <strong>
            {inventory.hasRawDicom
              ? "NIfTI QC waits for conversion"
              : inventory.hasConvertedData
                ? "Preprocessing run required"
                : "No imaging inventory"}
          </strong>
        </div>
      </div>
      <div className="workspace-panel-grid">
        <div id="data-readiness-panel">
          <DataReadinessPanel
            baseUrl={baseUrl}
            projectId={projectId}
            projectState={inventory.dataState}
          />
        </div>
        <div id="bids-validation-panel">
          <BidsValidationPanel
            baseUrl={baseUrl}
            projectId={projectId}
            projectState={inventory.dataState}
          />
        </div>
        <div id="conversion-dry-run-panel">
          <ConversionDryRunPanel baseUrl={baseUrl} projectId={projectId} />
        </div>
        <div id="dicom-conversion-review-panel">
          <DicomConversionReviewPanel baseUrl={baseUrl} projectId={projectId} />
        </div>
      </div>
    </div>
  );
}
