import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import QcDashboardSummaryPanel from "../../components/QcDashboardSummaryPanel";
import NiftiQcSnapshotPanel from "../../components/NiftiQcSnapshotPanel";
import BoldReferenceReadinessPanel from "../../components/BoldReferenceReadinessPanel";
import MotionQcReadinessPanel from "../../components/MotionQcReadinessPanel";
import MotionMetricsDraftPanel from "../../components/MotionMetricsDraftPanel";
import RsfmriQcPlanningReportPanel from "../../components/RsfmriQcPlanningReportPanel";

export interface QCReportsWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
}

export function QCReportsWorkspace({ baseUrl, projectId }: QCReportsWorkspaceProps) {
  return (
    <div className="workspace-stack qc-reports-workspace">
      <WorkspaceHeader
        title="QC & Reports"
        subtitle="Compact report status, latest artifacts, warnings, and export actions."
        status="Review"
      />
      <div className="workspace-panel-grid">
        <div><QcDashboardSummaryPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><NiftiQcSnapshotPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><BoldReferenceReadinessPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><MotionQcReadinessPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><MotionMetricsDraftPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><RsfmriQcPlanningReportPanel baseUrl={baseUrl} projectId={projectId} /></div>
      </div>
    </div>
  );
}
