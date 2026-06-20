import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import AdvancedPreprocessingPipelinePanel from "../../components/AdvancedPreprocessingPipelinePanel";
import type { ProjectDataState } from "../../lib/projectWorkflow";

export interface PreprocessingWorkspaceProps {
  projectId: string | null;
  dataState?: ProjectDataState;
  inventory: import("../../lib/projectWorkflow").ProjectInventory;
  hasPreprocessingRun: boolean;
  onOpenDataConversion: () => void;
  onOpenToolsDrawer: () => void;
}

export function PreprocessingWorkspace({
  projectId,
  dataState,
  inventory,
  hasPreprocessingRun,
  onOpenDataConversion,
  onOpenToolsDrawer,
}: PreprocessingWorkspaceProps) {
  const isRawDicom = dataState === "raw_dicom";

  if (isRawDicom) {
    return (
      <div className="workspace-stack preprocessing-workspace">
        <WorkspaceHeader
          title="Preprocessing"
          subtitle="Validate the preprocessing pipeline after conversion or BIDS registration. No full preprocessing action is exposed here."
          status="Blocked"
        />
        <section className="workflow-empty-note">
          <h3>Preprocessing validation</h3>
          <p>Convert DICOM to BIDS/NIfTI before preprocessing validation.</p>
          <button type="button" onClick={onOpenDataConversion}>Open Data & Conversion</button>
        </section>
      </div>
    );
  }

  const isMissingRegistration =
    dataState === "empty" ||
    (dataState === "converted_bids" && inventory.convertedSubjects === 0);
  const ctaTitle = isMissingRegistration
    ? "Register converted outputs before preprocessing"
    : "Create preprocessing run";
  const ctaDescription = isMissingRegistration
    ? "Configure your BIDS dataset directory or import converted NIfTI outputs before setting up preprocessing."
    : "Set up and run the preprocessing pipeline using the local workstation tool stack.";
  const ctaButtonText = isMissingRegistration
    ? "Open Data & Conversion"
    : "Configure Preprocessing Run";
  const handleCtaClick = isMissingRegistration
    ? onOpenDataConversion
    : onOpenToolsDrawer;

  return (
    <div className="workspace-stack preprocessing-workspace">
      <WorkspaceHeader
        title="Preprocessing"
        subtitle="Validate the preprocessing pipeline after conversion or BIDS registration. No full preprocessing action is exposed here."
        status={hasPreprocessingRun ? "Ready" : "Not started"}
      />
      {!hasPreprocessingRun && (
        <section className="workflow-empty-note">
          <h3>{ctaTitle}</h3>
          <p>{ctaDescription}</p>
          <button type="button" onClick={handleCtaClick}>{ctaButtonText}</button>
        </section>
      )}
      <AdvancedPreprocessingPipelinePanel projectId={projectId} preprocessingRunId={null} />
    </div>
  );
}
