import { useEffect, useState } from "react";

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
import {
  getLatestQcDashboardReport,
  getProjectBoldReferenceReadiness,
  getProjectMotionQcReadiness,
  getProjectNiftiQcSnapshot,
} from "../../lib/api/legacy";
import { getLatestNativeFullPreprocessingRun } from "../../lib/api/preprocessing";
import { evidenceLabel, type EvidenceLevel } from "../../lib/evidence";
import type {
  BoldReferenceReadinessResponse,
  MotionQcReadinessResponse,
  NativeFullPreprocResponse,
  NiftiQcSnapshotResponse,
  QcDashboardReportResponse,
} from "../../types";
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
        <QcDashboardOverview baseUrl={baseUrl} projectId={projectId!} />
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

function QcDashboardOverview({ baseUrl, projectId }: { baseUrl: string; projectId: string }) {
  const [evidence, setEvidence] = useState<QcOverviewEvidence>(EMPTY_QC_OVERVIEW_EVIDENCE);

  useEffect(() => {
    let cancelled = false;
    let pendingLoads = 5;
    setEvidence({ ...EMPTY_QC_OVERVIEW_EVIDENCE, loading: true });

    const updateEvidence = (partial: Partial<QcOverviewEvidence>) => {
      if (cancelled) return;
      pendingLoads -= 1;
      setEvidence((current) => {
        return {
          ...current,
          ...partial,
          loading: pendingLoads > 0,
        };
      });
    };

    void loadOptional(() => getLatestQcDashboardReport(baseUrl, projectId)).then((qcReport) =>
      updateEvidence({ qcReport }),
    );
    void loadOptional(() => getProjectNiftiQcSnapshot(baseUrl, projectId)).then((niftiSnapshot) =>
      updateEvidence({ niftiSnapshot }),
    );
    void loadOptional(() => getProjectBoldReferenceReadiness(baseUrl, projectId)).then(
      (boldReadiness) => updateEvidence({ boldReadiness }),
    );
    void loadOptional(() => getProjectMotionQcReadiness(baseUrl, projectId)).then(
      (motionReadiness) => updateEvidence({ motionReadiness }),
    );
    void loadOptional(() => getLatestNativeFullPreprocessingRun(baseUrl, projectId)).then(
      (nativeRun) => updateEvidence({ nativeRun }),
    );

    return () => {
      cancelled = true;
    };
  }, [baseUrl, projectId]);

  const model = buildQcOverviewModel(evidence);

  return (
    <section className={styles.dashboardGrid} aria-label="QC dashboard overview">
      <Card className={styles.summaryCard} tone="muted">
        <div className={styles.cardHeader}>
          <div>
            <h3>Evidence-first QC dashboard</h3>
            <p>{model.summaryDescription}</p>
          </div>
          <EvidenceBadge level={model.evidenceLevel} />
        </div>
        <div className={styles.statusStrip} aria-label="QC summary states">
          {model.evidenceStates.map((item) => (
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
            {model.subjectRows.length ? (
              model.subjectRows.map((row) => (
                <tr key={row.subjectId}>
                  <td>{row.subjectId}</td>
                  <td>{row.evidenceSource}</td>
                  <td>{row.coverage}</td>
                  <td>{row.warnings}</td>
                  <td>
                    <Badge tone={row.tone} size="sm">
                      {row.reviewState}
                    </Badge>
                  </td>
                </tr>
              ))
            ) : (
              <TableEmpty colSpan={5}>
                {evidence.loading
                  ? "Loading project-scoped QC evidence from the backend."
                  : "Subject rows appear only after dashboard reports or QC snapshots load reviewed project evidence. No pass, fail, or outlier count is inferred locally."}
              </TableEmpty>
            )}
          </tbody>
        </Table>
      </Card>

      <Card className={styles.outlierCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Outlier focus</h3>
            <p>
              Panels below provide the source data; this overview avoids inferred pass/fail counts.
            </p>
          </div>
        </div>
        <ol className={styles.findingList} aria-label="QC outlier focus areas">
          {model.outlierAreas.map((item) => (
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
            <p>{model.comparison.description}</p>
          </div>
          <Badge tone={model.comparison.tone}>{model.comparison.status}</Badge>
        </div>
        <div className={styles.comparisonGate} aria-label="Image comparison artifact gate">
          <strong>{model.comparison.title}</strong>
          <p>{model.comparison.body}</p>
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
          {model.chartContracts.map((item) => (
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

type QcOverviewEvidence = {
  boldReadiness: BoldReferenceReadinessResponse | null;
  loading: boolean;
  motionReadiness: MotionQcReadinessResponse | null;
  nativeRun: NativeFullPreprocResponse | null;
  niftiSnapshot: NiftiQcSnapshotResponse | null;
  qcReport: QcDashboardReportResponse | null;
};

type QcSubjectRow = {
  coverage: string;
  evidenceSource: string;
  reviewState: string;
  subjectId: string;
  tone: BadgeTone;
  warnings: number;
};

type QcOverviewModel = {
  chartContracts: typeof CHART_CONTRACTS;
  comparison: {
    body: string;
    description: string;
    status: string;
    title: string;
    tone: BadgeTone;
  };
  evidenceLevel: EvidenceLevel;
  evidenceStates: typeof QC_EVIDENCE_STATES;
  outlierAreas: typeof OUTLIER_AREAS;
  subjectRows: QcSubjectRow[];
  summaryDescription: string;
};

const EMPTY_QC_OVERVIEW_EVIDENCE: QcOverviewEvidence = {
  boldReadiness: null,
  loading: false,
  motionReadiness: null,
  nativeRun: null,
  niftiSnapshot: null,
  qcReport: null,
};

async function loadOptional<T>(loader: () => Promise<T>): Promise<T | null> {
  try {
    return await loader();
  } catch {
    return null;
  }
}

function buildQcOverviewModel(evidence: QcOverviewEvidence): QcOverviewModel {
  const sources = collectEvidenceSources(evidence);
  const subjectRows = buildSubjectRows(evidence);
  const nativeComputed = hasNativeComputedEvidence(evidence.nativeRun);
  const hasEvidence = sources.length > 0;
  const warningCount = evidence.nativeRun
    ? evidence.nativeRun.warning_stages.length + subjectReadinessWarningCount(evidence)
    : evidence.qcReport?.warning_count ??
      (evidence.niftiSnapshot?.warning_count ?? 0) +
        (evidence.boldReadiness?.warning_count ?? 0) +
        (evidence.motionReadiness?.warnings.length ?? 0);
  const blockedCount = evidence.nativeRun
    ? evidence.nativeRun.blocked_stages.length + evidence.nativeRun.failed_stages.length
    : evidence.qcReport?.blocked_count ??
      (evidence.boldReadiness?.blocked_count ?? 0) +
        (evidence.motionReadiness?.status === "blocked" ? 1 : 0);
  const evidenceLevel: EvidenceLevel = nativeComputed
    ? "computed"
    : hasEvidence
      ? "created"
      : "backend_required";

  return {
    chartContracts: buildChartContracts(evidence),
    comparison: buildComparisonModel(evidence),
    evidenceLevel,
    evidenceStates: [
      {
        label: "Evidence",
        value: hasEvidence ? "Backend evidence loaded" : evidenceLabel("backend_required"),
        description: hasEvidence ? sources.join(", ") : "Awaiting project-scoped QC reports",
        tone: hasEvidence ? "success" : "neutral",
      },
      {
        label: "Coverage",
        value: subjectRows.length ? `${subjectRows.length} subject(s)` : evidenceLabel("backend_required"),
        description: subjectRows.length
          ? "Subject coverage is derived from backend NIfTI/BOLD/motion evidence"
          : "Subject and run coverage comes from backend evidence",
        tone: subjectRows.length ? "success" : "info",
      },
      {
        label: "Warnings",
        value: String(warningCount),
        description: hasEvidence
          ? `${blockedCount} blocked item(s); warning counts are backend supplied`
          : "Warning counts are not inferred by the UI",
        tone: warningCount > 0 ? "warning" : hasEvidence ? "success" : "warning",
      },
      {
        label: "Decision",
        value: evidence.nativeRun?.status
          ? `Native ${evidence.nativeRun.status}`
          : evidence.qcReport?.status
            ? `Report ${evidence.qcReport.status}`
            : evidenceLabel("backend_required"),
        description: hasEvidence
          ? "Review state is backend-reported; no local pass/fail is inferred"
          : "No pass/fail decision without source evidence",
        tone: blockedCount > 0 ? "warning" : hasEvidence ? "success" : "info",
      },
    ],
    outlierAreas: buildOutlierAreas(evidence),
    subjectRows,
    summaryDescription: hasEvidence
      ? "Summary lanes reflect project-scoped backend evidence already loaded for this project."
      : evidence.loading
        ? "Loading project-scoped backend evidence for QC summary lanes."
        : "Summary lanes stay conservative until project-scoped backend evidence exists.",
  };
}

function collectEvidenceSources(evidence: QcOverviewEvidence): string[] {
  const sources: string[] = [];
  if (evidence.qcReport) sources.push("QC dashboard report");
  if ((evidence.niftiSnapshot?.image_count ?? 0) > 0) sources.push("NIfTI QC snapshot");
  if ((evidence.boldReadiness?.candidate_count ?? 0) > 0) sources.push("BOLD readiness");
  if ((evidence.motionReadiness?.candidate_count ?? 0) > 0) sources.push("Motion readiness");
  if (evidence.nativeRun?.stage_results.length) sources.push("Native preprocessing run");
  return sources;
}

function buildSubjectRows(evidence: QcOverviewEvidence): QcSubjectRow[] {
  const rows = new Map<
    string,
    {
      coverage: Set<string>;
      sources: Set<string>;
      warnings: Set<string>;
    }
  >();
  const ensure = (subjectId?: string | null, path?: string | null) => {
    subjectId = normalizeSubjectId(subjectId, path);
    if (!subjectId) return null;
    if (!rows.has(subjectId)) {
      rows.set(subjectId, { coverage: new Set(), sources: new Set(), warnings: new Set() });
    }
    return rows.get(subjectId)!;
  };

  for (const image of evidence.niftiSnapshot?.images ?? []) {
    const row = ensure(image.subject_id, image.path);
    if (!row) continue;
    row.sources.add("NIfTI");
    row.coverage.add(image.modality === "bold" || image.suffix === "bold" ? "BOLD image" : "NIfTI image");
    image.warnings.forEach((warning) => row.warnings.add(`nifti:${warning}`));
  }
  for (const candidate of evidence.boldReadiness?.candidates ?? []) {
    const row = ensure(candidate.subject_id, candidate.bold_path);
    if (!row) continue;
    row.sources.add("BOLD readiness");
    row.coverage.add(candidate.is_4d ? "4D BOLD" : "BOLD candidate");
    candidate.warnings.forEach((warning) => row.warnings.add(`bold:${warning}`));
  }
  for (const candidate of evidence.motionReadiness?.candidates ?? []) {
    const row = ensure(candidate.subject_id, candidate.bold_path);
    if (!row) continue;
    row.sources.add("Motion readiness");
    row.coverage.add(candidate.has_fd_column ? "FD available" : "motion pending");
    candidate.warnings.forEach((warning) => row.warnings.add(`motion:${warning}`));
  }
  for (const stage of evidence.nativeRun?.stage_results ?? []) {
    const subjectId = nativeStageSubjectId(stage);
    const artifactPath = stage.output_artifacts[0]?.path;
    const row = ensure(subjectId, typeof artifactPath === "string" ? artifactPath : null);
    if (!row) continue;
    row.sources.add("Native preprocessing");
    if (stage.stage_id === "motion_qc" && nativeStageProduced(stage)) row.coverage.add("Motion QC");
    if (stage.stage_id === "normalization" && nativeStageProduced(stage)) row.coverage.add("Normalized BOLD");
    if (stage.stage_id === "functional_connectivity" && nativeStageProduced(stage)) row.coverage.add("FC matrix");
    if (stage.status === "warning" || stage.status === "simplified") {
      row.warnings.add(`native:${stage.stage_id}`);
    }
  }

  return Array.from(rows.entries())
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([subjectId, row]) => ({
      coverage: Array.from(row.coverage).join(", "),
      evidenceSource: Array.from(row.sources).join(", "),
      reviewState: row.warnings.size > 0 ? "review" : "ready",
      subjectId,
      tone: row.warnings.size > 0 ? "warning" : "success",
      warnings: row.warnings.size,
    }));
}

function buildOutlierAreas(evidence: QcOverviewEvidence): typeof OUTLIER_AREAS {
  const nativeMotionSubjects = nativeStageSubjectCount(evidence.nativeRun, ["motion_qc"]);
  const readinessMotionSubjects = uniqueReadinessSubjectCount(evidence.motionReadiness, true);
  const motionSubjectCount = nativeMotionSubjects || readinessMotionSubjects;
  const motionReady = motionSubjectCount > 0;
  const nativeSpatialArtifacts = spatialNativeArtifactCount(evidence.nativeRun);
  const spatialReady =
    nativeSpatialArtifacts > 0 ||
    ((evidence.boldReadiness?.ready_count ?? 0) > 0 && (evidence.niftiSnapshot?.four_d_count ?? 0) > 0);
  const reportCreated = Boolean(evidence.qcReport || evidence.nativeRun?.final_report_path);

  return [
    {
      label: "Motion outliers",
      description: "FD, DVARS, and scrubbing candidates come from motion readiness and draft panels.",
      source: motionReady ? "Motion readiness evidence" : "Motion QC evidence",
      status: motionReady ? `${motionSubjectCount} subject(s) FD ready` : "Awaiting metrics",
      tone: motionReady ? "success" : "neutral",
      unit: "mm / signal scale",
    },
    {
      label: "Spatial alignment",
      description: "BOLD reference and NIfTI snapshots provide the reviewed alignment inputs.",
      source:
        nativeSpatialArtifacts > 0
          ? "Native spatial artifacts"
          : spatialReady
            ? "BOLD + NIfTI snapshot artifacts"
            : "Snapshot artifacts",
      status: nativeSpatialArtifacts > 0 ? "Partial artifact" : spatialReady ? "Ready inputs" : "Artifact gated",
      tone: spatialReady ? "success" : "warning",
      unit: "voxel / transform",
    },
    {
      label: "Report completeness",
      description: "Planning reports identify missing modules before export or validation.",
      source: reportCreated ? "Native/QC report artifact" : "QC planning report",
      status: reportCreated ? "Created" : "Review",
      tone: reportCreated ? "success" : "info",
      unit: "checklist",
    },
  ];
}

function buildComparisonModel(evidence: QcOverviewEvidence): QcOverviewModel["comparison"] {
  const comparisonSubjects = nativeComparisonSubjectCount(evidence.nativeRun);
  if (comparisonSubjects > 0) {
    return {
      body: `${comparisonSubjects} subject(s) have paired mean-functional, normalized-BOLD, and transform or mask evidence.`,
      description: "Subject-linked reference and processed-image evidence is registered for spatial review.",
      status: "Ready artifact",
      title: "Paired spatial comparison evidence is available",
      tone: "success",
    };
  }
  const artifactCount = spatialNativeArtifactCount(evidence.nativeRun);
  if (artifactCount > 0) {
    return {
      body: `${artifactCount} native spatial artifact(s) are registered. Overlay review still waits for paired reference and processed-image evidence before rendering synchronized controls.`,
      description: "Registration, atlas, and reference evidence is present but overlay review remains artifact-gated.",
      status: "Partial artifact",
      title: "Spatial artifacts are available for backend review",
      tone: "warning",
    };
  }
  return {
    body: "The QC page does not render medical imagery, overlay canvases, or synchronized controls until reference and processed artifacts are both supplied by backend evidence.",
    description: "Registration, segmentation, and normalization review is artifact-gated.",
    status: "No artifact",
    title: "No comparison artifact is available",
    tone: "warning",
  };
}

function buildChartContracts(evidence: QcOverviewEvidence): typeof CHART_CONTRACTS {
  const fcStages = findNativeStages(evidence.nativeRun, "functional_connectivity");
  const motionStages = findNativeStages(evidence.nativeRun, "motion_qc");
  const fcComputed = fcStages.some(nativeStageProduced);
  const motionSubjectCount =
    nativeStageSubjectCount(evidence.nativeRun, ["motion_qc"]) ||
    uniqueReadinessSubjectCount(evidence.motionReadiness, true);
  const motionReady = motionSubjectCount > 0;
  const nativeSpatialArtifacts = spatialNativeArtifactCount(evidence.nativeRun);
  const spatialReady =
    nativeSpatialArtifacts > 0 ||
    ((evidence.boldReadiness?.ready_count ?? 0) > 0 && (evidence.niftiSnapshot?.four_d_count ?? 0) > 0);

  return [
    {
      label: "FD / DVARS",
      range: motionReady ? `${motionSubjectCount} subject(s)` : "Pending subjects and runs",
      source: motionStages.length ? "Native motion QC artifact" : "Motion metrics artifact",
      status: motionReady || motionStages.length ? evidenceLabel("created") : evidenceLabel("backend_required"),
      threshold: motionReady ? "FD column backend supplied" : "Pending metadata",
      tone: motionReady || motionStages.length ? "success" : "warning",
      unit: "mm / signal scale",
    },
    {
      label: "Spatial alignment",
      range:
        nativeSpatialArtifacts > 0
          ? `${nativeSpatialArtifacts} spatial artifact(s)`
          : spatialReady
            ? `${evidence.boldReadiness!.ready_count} BOLD candidate(s)`
            : "Pending snapshots",
      source: nativeSpatialArtifacts > 0 ? "Native spatial artifacts" : "BOLD/T1 readiness artifacts",
      status: spatialReady ? evidenceLabel("created") : evidenceLabel("backend_required"),
      threshold: "Backend supplied",
      tone: spatialReady ? "success" : "info",
      unit: "voxel / transform",
    },
    {
      label: "ALFF / fALFF",
      range: nativeStageRange(evidence.nativeRun, ["alff", "falff"]),
      source: "Derived metric modules",
      status: nativeAnyProduced(evidence.nativeRun, ["alff", "falff"])
        ? nativeAnyWarning(evidence.nativeRun, ["alff", "falff"])
          ? "Computed with warnings"
          : evidenceLabel("computed")
        : evidenceLabel("unavailable"),
      threshold: nativeAnyProduced(evidence.nativeRun, ["alff", "falff"])
        ? "Backend QC warnings disclosed"
        : "Not applicable until computed",
      tone: nativeAnyWarning(evidence.nativeRun, ["alff", "falff"])
        ? "warning"
        : nativeAnyProduced(evidence.nativeRun, ["alff", "falff"])
          ? "success"
          : "neutral",
      unit: "backend-defined",
    },
    {
      label: "ReHo / FC",
      range: fcComputed
        ? `${nativeStageSubjectCount(evidence.nativeRun, ["functional_connectivity"])} subject(s), ${fcStages.reduce((total, stage) => total + stage.output_artifacts.length, 0)} FC artifact(s)`
        : nativeStageRange(evidence.nativeRun, ["reho", "functional_connectivity"]),
      source: "Derived metric modules",
      status: fcComputed ? "FC computed" : evidenceLabel("unavailable"),
      threshold: fcComputed ? "Atlas and ROI evidence supplied" : "Not applicable until computed",
      tone: fcComputed ? "success" : "neutral",
      unit: "backend-defined",
    },
  ];
}

function hasNativeComputedEvidence(nativeRun: NativeFullPreprocResponse | null): boolean {
  return Boolean(
    nativeRun?.stage_results.some(
      (stage) =>
        (stage.status === "succeeded" || stage.status === "simplified") &&
        (stage.capability_level === "computed" || stage.output_artifacts.length > 0),
    ),
  );
}

function normalizeSubjectId(subjectId?: string | null, path?: string | null): string | null {
  for (const value of [subjectId, path]) {
    const match = value?.match(/(?:^|[/\\])?(sub-[A-Za-z0-9]+)(?=[_/\\.]|$)/);
    if (match) return match[1];
  }
  return null;
}

function spatialNativeArtifactCount(nativeRun: NativeFullPreprocResponse | null): number {
  const spatialTokens = [
    "align",
    "atlas",
    "coreg",
    "mean_functional",
    "normalization",
    "realign",
    "reference",
    "registration",
    "spatial",
    "transform",
  ];
  return (nativeRun?.stage_results ?? []).reduce((total, stage) => {
    const stageText = `${stage.stage_id} ${stage.display_name ?? ""}`.toLowerCase();
    if (!spatialTokens.some((token) => stageText.includes(token))) return total;
    return total + stage.output_artifacts.length;
  }, 0);
}

function findNativeStages(nativeRun: NativeFullPreprocResponse | null, stageId: string) {
  return nativeRun?.stage_results.filter((stage) => stage.stage_id === stageId) ?? [];
}

function nativeStageProduced(stage: NativeFullPreprocResponse["stage_results"][number]): boolean {
  return ["succeeded", "simplified", "warning"].includes(stage.status) && stage.output_artifacts.length > 0;
}

function nativeAnyProduced(nativeRun: NativeFullPreprocResponse | null, stageIds: string[]): boolean {
  return stageIds.some((stageId) => findNativeStages(nativeRun, stageId).some(nativeStageProduced));
}

function nativeAnyWarning(nativeRun: NativeFullPreprocResponse | null, stageIds: string[]): boolean {
  return stageIds.some((stageId) =>
    findNativeStages(nativeRun, stageId).some((stage) => stage.status === "warning"),
  );
}

function nativeStageRange(
  nativeRun: NativeFullPreprocResponse | null,
  stageIds: string[],
): string {
  const stages = stageIds
    .flatMap((stageId) => findNativeStages(nativeRun, stageId));
  if (!stages.length) return "Pending computed artifacts";
  const produced = stages.filter(nativeStageProduced);
  const skipped = stages.filter((stage) => stage.status === "skipped").length;
  if (produced.length) {
    const subjects = new Set(produced.map(nativeStageSubjectId).filter(Boolean)).size;
    const artifacts = produced.reduce((total, stage) => total + stage.output_artifacts.length, 0);
    return subjects ? `${subjects} subject(s), ${artifacts} artifact(s)` : `${artifacts} computed artifact(s)`;
  }
  if (skipped) return `${skipped} skipped stage(s)`;
  return "Pending computed artifacts";
}

function nativeStageSubjectId(
  stage: NativeFullPreprocResponse["stage_results"][number],
): string | null {
  const resultSubject = stage.result?.subject_id;
  const artifactPath = stage.output_artifacts[0]?.path;
  return normalizeSubjectId(
    typeof resultSubject === "string" ? resultSubject : null,
    typeof artifactPath === "string" ? artifactPath : null,
  );
}

function nativeStageSubjectCount(
  nativeRun: NativeFullPreprocResponse | null,
  stageIds: string[],
): number {
  return new Set(
    stageIds
      .flatMap((stageId) => findNativeStages(nativeRun, stageId))
      .filter(nativeStageProduced)
      .map(nativeStageSubjectId)
      .filter((subjectId): subjectId is string => Boolean(subjectId)),
  ).size;
}

function nativeComparisonSubjectCount(nativeRun: NativeFullPreprocResponse | null): number {
  const references = new Set(
    findNativeStages(nativeRun, "realignment")
      .filter(nativeStageProduced)
      .map(nativeStageSubjectId)
      .filter((subjectId): subjectId is string => Boolean(subjectId)),
  );
  const processed = new Set(
    findNativeStages(nativeRun, "normalization")
      .filter(nativeStageProduced)
      .map(nativeStageSubjectId)
      .filter((subjectId): subjectId is string => Boolean(subjectId)),
  );
  return Array.from(references).filter((subjectId) => processed.has(subjectId)).length;
}

function uniqueReadinessSubjectCount(
  readiness: MotionQcReadinessResponse | null,
  requireFd: boolean,
): number {
  return new Set(
    (readiness?.candidates ?? [])
      .filter((candidate) => !requireFd || candidate.has_fd_column)
      .map((candidate) => normalizeSubjectId(candidate.subject_id, candidate.bold_path))
      .filter((subjectId): subjectId is string => Boolean(subjectId)),
  ).size;
}

function subjectReadinessWarningCount(evidence: QcOverviewEvidence): number {
  const warnings = new Set<string>();
  for (const candidate of evidence.boldReadiness?.candidates ?? []) {
    const subjectId = normalizeSubjectId(candidate.subject_id, candidate.bold_path);
    candidate.warnings.forEach((warning) => warnings.add(`${subjectId ?? "unknown"}:bold:${warning}`));
  }
  for (const candidate of evidence.motionReadiness?.candidates ?? []) {
    const subjectId = normalizeSubjectId(candidate.subject_id, candidate.bold_path);
    candidate.warnings.forEach((warning) => warnings.add(`${subjectId ?? "unknown"}:motion:${warning}`));
  }
  return warnings.size;
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
