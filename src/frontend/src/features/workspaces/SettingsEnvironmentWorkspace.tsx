import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import EnvironmentHealthPanel from "../../components/EnvironmentHealthPanel";
import SpmRealignDryRunPanel from "../../components/SpmRealignDryRunPanel";
import SpmRealignWrapperSkeletonPanel from "../../components/SpmRealignWrapperSkeletonPanel";
import RsfmriPresetPanel from "../../components/RsfmriPresetPanel";
import type { PresetPlanDraft } from "../../types";

export interface SettingsEnvironmentWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  onReviewDraft: (draft: PresetPlanDraft) => void;
}

export function SettingsEnvironmentWorkspace({
  baseUrl,
  projectId,
  onReviewDraft,
}: SettingsEnvironmentWorkspaceProps) {
  return (
    <div className="workspace-stack settings-environment-workspace">
      <WorkspaceHeader
        title="Settings / Environment"
        subtitle="Planning-only checks for environment health, SPM wrappers, and preset review."
        status="Planning only"
      />
      <div className="planning-note">
        These tools produce readiness previews and review packages. They do not enable MATLAB/SPM
        execution or DPABI execution.
      </div>
      <div className="workspace-panel-grid">
        <div>
          <EnvironmentHealthPanel baseUrl={baseUrl} />
        </div>
        <div>
          <SpmRealignDryRunPanel baseUrl={baseUrl} projectId={projectId} />
        </div>
        <div>
          <SpmRealignWrapperSkeletonPanel baseUrl={baseUrl} projectId={projectId} />
        </div>
        <div>
          <RsfmriPresetPanel
            baseUrl={baseUrl}
            projectId={projectId}
            onReviewDraft={onReviewDraft}
          />
        </div>
      </div>
    </div>
  );
}
