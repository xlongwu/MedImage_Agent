import { useState } from "react";

import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import QcDashboardSummaryPanel from "../../components/QcDashboardSummaryPanel";
import NiftiQcSnapshotPanel from "../../components/NiftiQcSnapshotPanel";
import BoldReferenceReadinessPanel from "../../components/BoldReferenceReadinessPanel";
import MotionQcReadinessPanel from "../../components/MotionQcReadinessPanel";
import MotionMetricsDraftPanel from "../../components/MotionMetricsDraftPanel";
import RsfmriQcPlanningReportPanel from "../../components/RsfmriQcPlanningReportPanel";
import { RsfmriAlffFalffPanel } from "../../components/RsfmriAlffFalffPanel";
import { RsfmriFunctionalConnectivityPanel } from "../../components/RsfmriFunctionalConnectivityPanel";
import { RsfmriMotionQcPanel } from "../../components/RsfmriMotionQcPanel";
import { RsfmriNuisanceRegressionPanel } from "../../components/RsfmriNuisanceRegressionPanel";
import { RsfmriRehoPanel } from "../../components/RsfmriRehoPanel";
import { RsfmriTemporalFilteringPanel } from "../../components/RsfmriTemporalFilteringPanel";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import { Badge, Card, EmptyState, Table, TableEmpty } from "../../components/ui";
import { evidenceLabel } from "../../lib/evidence";
import styles from "./QCReportsWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface QCReportsWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
}

export function QCReportsWorkspace({ baseUrl, projectId }: QCReportsWorkspaceProps) {
  const hasProject = Boolean(projectId);
  const [showDerivedModules, setShowDerivedModules] = useState(false);

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="QC"
        subtitle="Review quality gates, subject-level evidence, and research artifacts without hiding backend validation state."
        status={hasProject ? "Review" : "Select project"}
      />

      {!hasProject ? (
        <EmptyState
          title="Select a project before QC review"
          description="QC evidence is project-scoped. Choose a project so dashboard reports, snapshots, motion checks, and planning artifacts stay tied to the correct audit trail."
        />
      ) : (
        <QcDashboardOverview />
      )}

      <TechnicalModuleSection
        ariaLabel="Detailed QC modules"
        bodyVisible={hasProject}
        description="These panels keep the existing backend calls for dashboard generation, NIfTI snapshots, reference readiness, motion metrics, and planning reports."
        evidenceLevel={hasProject ? "backend_required" : "blocked"}
        fallback={
          <Card tone="muted">
            <EmptyState
              title="QC modules are waiting for project context"
              description="Detailed panels are hidden until a project is selected to avoid running checks against an undefined project."
            />
          </Card>
        }
        helperText={
          hasProject
            ? "Detailed panels load project-scoped backend evidence."
            : "Select a project before loading detailed QC modules."
        }
        safetyNote="Detailed QC panels expose existing backend evidence; the UI does not infer pass, fail, or computed states."
        status={hasProject ? "Project scoped" : "Select project"}
        statusTone={hasProject ? "info" : "warning"}
        title="Detailed QC modules"
      >
        {hasProject ? (
          <div className={layoutStyles.panelGrid}>
            <div id="qc-dashboard-summary-panel">
              <QcDashboardSummaryPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
            <div id="nifti-qc-snapshot-panel">
              <NiftiQcSnapshotPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
            <div id="bold-reference-readiness-panel">
              <BoldReferenceReadinessPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
            <div id="motion-qc-readiness-panel">
              <MotionQcReadinessPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
            <div id="motion-metrics-draft-panel">
              <MotionMetricsDraftPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
            <div id="rsfmri-qc-planning-report-panel">
              <RsfmriQcPlanningReportPanel baseUrl={baseUrl} projectId={projectId} />
            </div>
          </div>
        ) : null}
      </TechnicalModuleSection>

      <TechnicalModuleSection
        actionDisabled={!hasProject}
        ariaLabel="Derived metric modules"
        description="Derived metric panels stay secondary to the QC dashboard and do not imply ALFF, ReHo, FC, filtering, or motion artifacts have been computed."
        disabledReason="Select a project before loading metric-specific QC modules."
        evidenceLevel={hasProject ? "unavailable" : "blocked"}
        hideActionLabel="Hide derived modules"
        isOpen={showDerivedModules}
        onToggle={() => setShowDerivedModules((value) => !value)}
        openLabel="Open derived modules"
        safetyNote="Opening this section loads existing reviewed panels; backend gates remain authoritative for ALFF, ReHo, FC, filtering, and motion artifact state."
        status={hasProject ? (showDerivedModules ? "Open" : "On demand") : "Select project"}
        statusTone={hasProject ? "info" : "warning"}
        title="Derived metric modules"
      >
        <div className={layoutStyles.panelGrid}>
          <div id="rsfmri-nuisance-regression-panel">
            <RsfmriNuisanceRegressionPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-temporal-filtering-panel">
            <RsfmriTemporalFilteringPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-motion-qc-panel">
            <RsfmriMotionQcPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-alff-falff-panel">
            <RsfmriAlffFalffPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-reho-panel">
            <RsfmriRehoPanel baseUrl={baseUrl} />
          </div>
          <div id="rsfmri-functional-connectivity-panel">
            <RsfmriFunctionalConnectivityPanel baseUrl={baseUrl} />
          </div>
        </div>
      </TechnicalModuleSection>
    </div>
  );
}

function QcDashboardOverview() {
  return (
    <section className={styles.dashboardGrid} aria-label="QC dashboard overview">
      <Card className={styles.summaryCard} tone="muted">
        <div className={styles.cardHeader}>
          <div>
            <h3>Evidence-first QC dashboard</h3>
            <p>
              Summary lanes stay conservative until project-scoped backend evidence exists.
            </p>
          </div>
          <EvidenceBadge level="backend_required" />
        </div>
        <div className={styles.statusStrip} aria-label="QC summary states">
          {QC_EVIDENCE_STATES.map((item) => (
            <div data-tone={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.description}</small>
            </div>
          ))}
        </div>
        <Table caption="Subject-level QC status">
          <thead>
            <tr>
              <th>Subject</th>
              <th>Evidence source</th>
              <th>Coverage</th>
              <th>Warnings</th>
              <th>Review state</th>
            </tr>
          </thead>
          <tbody>
            <TableEmpty colSpan={5}>
              Subject rows appear only after dashboard reports or QC snapshots load reviewed
              project evidence. No pass, fail, or outlier count is inferred locally.
            </TableEmpty>
          </tbody>
        </Table>
      </Card>

      <Card className={styles.outlierCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Outlier focus</h3>
            <p>Panels below provide the source data; this overview avoids inferred pass/fail counts.</p>
          </div>
        </div>
        <ol className={styles.findingList} aria-label="QC outlier focus areas">
          {OUTLIER_AREAS.map((item) => (
            <li key={item.label}>
              <div>
                <strong>{item.label}</strong>
                <p>{item.description}</p>
                <dl className={styles.evidenceMeta}>
                  <div>
                    <dt>Source</dt>
                    <dd>{item.source}</dd>
                  </div>
                  <div>
                    <dt>Unit</dt>
                    <dd>{item.unit}</dd>
                  </div>
                </dl>
              </div>
              <Badge tone={item.tone} size="sm">
                {item.status}
              </Badge>
            </li>
          ))}
        </ol>
        <details className={styles.drilldownShell}>
          <summary>Outlier drill-down contract</summary>
          <Table caption="Outlier drill-down evidence">
            <thead>
              <tr>
                <th>Subject / run</th>
                <th>Metric</th>
                <th>Threshold</th>
                <th>Evidence</th>
              </tr>
            </thead>
            <tbody>
              <TableEmpty colSpan={4}>
                Drill-down rows stay empty until backend evidence provides subject, run, unit,
                threshold, and source metadata.
              </TableEmpty>
            </tbody>
          </Table>
        </details>
      </Card>

      <Card className={styles.comparisonCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Image comparison</h3>
            <p>Registration, segmentation, and normalization review is artifact-gated.</p>
          </div>
          <Badge tone="warning">No artifact</Badge>
        </div>
        <div className={styles.comparisonGate} aria-label="Image comparison artifact gate">
          <strong>No comparison artifact is available</strong>
          <p>
            The QC page does not render medical imagery, overlay canvases, or synchronized controls
            until reference and processed artifacts are both supplied by backend evidence.
          </p>
          <ul>
            {COMPARISON_REQUIREMENTS.map((item) => (
              <li key={item}>{item}</li>
            ))}
          </ul>
        </div>
        <div className={styles.comparisonStates} aria-label="Image comparison artifact states">
          {COMPARISON_STATES.map((item) => (
            <div key={item.label} data-state={item.state}>
              <span>{item.label}</span>
              <strong>{item.status}</strong>
              <small>{item.description}</small>
            </div>
          ))}
        </div>
        <p className={styles.helperText}>
          Sync slices, opacity, and before/after controls appear only in the ready artifact state.
        </p>
      </Card>

      <Card className={styles.metricsCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>QC chart contract</h3>
            <p>Chart shells disclose metadata before any source-backed marks are rendered.</p>
          </div>
        </div>
        <dl className={styles.chartContractList}>
          {CHART_CONTRACTS.map((item) => (
            <div key={item.label}>
              <dt>
                {item.label}
                <Badge tone={item.tone} size="sm">
                  {item.status}
                </Badge>
              </dt>
              <dd>
                <span>Unit: {item.unit}</span>
                <span>Threshold: {item.threshold}</span>
                <span>Range: {item.range}</span>
                <span>Source: {item.source}</span>
              </dd>
            </div>
          ))}
        </dl>
      </Card>

      <Card className={styles.visualSpecCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Visualization contract</h3>
            <p>QC charts stay summary-first and must disclose the evidence behind each mark.</p>
          </div>
          <Badge tone="info">Required</Badge>
        </div>
        <dl className={styles.visualSpecList} aria-label="QC visualization requirements">
          {VISUALIZATION_REQUIREMENTS.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.description}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </section>
  );
}

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const QC_EVIDENCE_STATES: Array<{
  description: string;
  label: string;
  tone: BadgeTone;
  value: string;
}> = [
  {
    label: "Evidence",
    value: evidenceLabel("backend_required"),
    description: "Awaiting project-scoped QC reports",
    tone: "neutral",
  },
  {
    label: "Coverage",
    value: evidenceLabel("backend_required"),
    description: "Subject and run coverage comes from backend evidence",
    tone: "info",
  },
  {
    label: "Warnings",
    value: evidenceLabel("backend_required"),
    description: "Warning counts are not inferred by the UI",
    tone: "warning",
  },
  {
    label: "Decision",
    value: evidenceLabel("backend_required"),
    description: "No pass/fail decision without source evidence",
    tone: "info",
  },
];

const OUTLIER_AREAS: Array<{
  description: string;
  label: string;
  source: string;
  status: string;
  tone: BadgeTone;
  unit: string;
}> = [
  {
    label: "Motion outliers",
    description: "FD, DVARS, and scrubbing candidates come from motion readiness and draft panels.",
    source: "Motion QC evidence",
    status: "Awaiting metrics",
    tone: "neutral",
    unit: "mm / signal scale",
  },
  {
    label: "Spatial alignment",
    description: "BOLD reference and NIfTI snapshots provide the reviewed alignment inputs.",
    source: "Snapshot artifacts",
    status: "Artifact gated",
    tone: "warning",
    unit: "voxel / transform",
  },
  {
    label: "Report completeness",
    description: "Planning reports identify missing modules before export or validation.",
    source: "QC planning report",
    status: "Review",
    tone: "info",
    unit: "checklist",
  },
];

const COMPARISON_REQUIREMENTS = [
  "Reference image artifact",
  "Processed image artifact",
  "Transform or mask evidence",
  "Comparable subject and run metadata",
];

const COMPARISON_STATES: Array<{
  description: string;
  label: string;
  state: "blocked" | "partial" | "ready";
  status: string;
}> = [
  {
    label: "No artifact",
    state: "blocked",
    status: evidenceLabel("backend_required"),
    description: "No reference or processed artifact is present.",
  },
  {
    label: "Partial artifact",
    state: "partial",
    status: evidenceLabel("metadata_only"),
    description: "Show the missing reference, processed image, transform, or mask.",
  },
  {
    label: "Ready artifact",
    state: "ready",
    status: evidenceLabel("created"),
    description: "Enable synchronized review without claiming QC passed.",
  },
];

const CHART_CONTRACTS: Array<{
  label: string;
  range: string;
  source: string;
  status: string;
  threshold: string;
  tone: BadgeTone;
  unit: string;
}> = [
  {
    label: "FD / DVARS",
    range: "Pending subjects and runs",
    source: "Motion metrics artifact",
    status: evidenceLabel("backend_required"),
    threshold: "Pending metadata",
    tone: "warning",
    unit: "mm / signal scale",
  },
  {
    label: "Spatial alignment",
    range: "Pending snapshots",
    source: "BOLD/T1 readiness artifacts",
    status: evidenceLabel("backend_required"),
    threshold: "Backend supplied",
    tone: "info",
    unit: "voxel / transform",
  },
  {
    label: "ALFF / fALFF",
    range: "Pending computed artifacts",
    source: "Derived metric modules",
    status: evidenceLabel("unavailable"),
    threshold: "Not applicable until computed",
    tone: "neutral",
    unit: "backend-defined",
  },
  {
    label: "ReHo / FC",
    range: "Pending computed artifacts",
    source: "Derived metric modules",
    status: evidenceLabel("unavailable"),
    threshold: "Not applicable until computed",
    tone: "neutral",
    unit: "backend-defined",
  },
];

const VISUALIZATION_REQUIREMENTS = [
  {
    label: "Unit",
    description: "Every plotted metric names the unit or source scale before values are shown.",
  },
  {
    label: "Threshold",
    description: "Warning and failure bands must come from backend QC configuration or reports.",
  },
  {
    label: "Data range",
    description: "Charts disclose the covered subjects, volumes, runs, or artifact subset.",
  },
  {
    label: "Drill-down",
    description: "Detailed statistics stay collapsed until reviewed source data is available.",
  },
];
