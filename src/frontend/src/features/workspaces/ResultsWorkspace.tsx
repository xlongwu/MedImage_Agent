import { useState } from "react";

import { ArtifactBrowser } from "../../components/ArtifactBrowser";
import { ReportViewer } from "../../components/ReportViewer";
import { RsfmriGroupSummaryPanel } from "../../components/RsfmriGroupSummaryPanel";
import { RsfmriReportExporterPanel } from "../../components/RsfmriReportExporterPanel";
import { RsfmriReportValidatorPanel } from "../../components/RsfmriReportValidatorPanel";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { EvidenceBadge } from "../../components/domain/EvidenceBadge";
import { Badge, Button, Card, EmptyState, Table, TableEmpty } from "../../components/ui";
import { evidenceLabel } from "../../lib/evidence";
import type { ArtifactSelection } from "../../lib/workspaceSelection";
import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import styles from "./ResultsWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface ResultsWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  onSelectedArtifactChange?: (artifact: ArtifactSelection | null) => void;
}

export function ResultsWorkspace({
  baseUrl,
  projectId,
  onSelectedArtifactChange,
}: ResultsWorkspaceProps) {
  const hasProject = Boolean(projectId);
  const [showMigratedReports, setShowMigratedReports] = useState(false);

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Results"
        subtitle="Collect generated reports, exports, validation records, and previewable artifacts."
        status={hasProject ? "Artifacts" : "Select project"}
      />

      {!hasProject ? (
        <EmptyState
          title="Select a project before reviewing results"
          description="Artifact browsing and report export stay project-scoped in the workflow, even when the underlying artifact index is loaded on demand."
        />
      ) : (
        <ResultsOverview />
      )}

      <TechnicalModuleSection
        ariaLabel="Artifact and report modules"
        bodyVisible={hasProject}
        description="Existing modules remain the source of truth for artifact indexing, report export, and package validation."
        evidenceLevel={hasProject ? "backend_required" : "blocked"}
        fallback={
          <Card tone="muted">
            <EmptyState
              title="Result modules are waiting for project context"
              description="Select a project before loading artifact indexes, export packages, or validation records."
            />
          </Card>
        }
        helperText={
          hasProject
            ? "Artifact, export, and validation modules use backend-owned state."
            : "Select a project before loading result modules."
        }
        safetyNote="Opening result modules does not create exports or validate packages; backend modules remain the source of truth."
        status={hasProject ? "Project scoped" : "Select project"}
        statusTone={hasProject ? "info" : "warning"}
        title="Artifact and report modules"
      >
        {hasProject ? (
          <div className={layoutStyles.panelGrid}>
            <div id="artifact-browser-panel">
              <ArtifactBrowser
                baseUrl={baseUrl}
                onSelectedArtifactChange={onSelectedArtifactChange}
              />
            </div>
            <div id="rsfmri-report-exporter-panel">
              <RsfmriReportExporterPanel baseUrl={baseUrl} />
            </div>
            <div id="rsfmri-report-validator-panel">
              <RsfmriReportValidatorPanel baseUrl={baseUrl} />
            </div>
          </div>
        ) : null}
      </TechnicalModuleSection>

      <TechnicalModuleSection
        actionDisabled={!hasProject}
        actionSize="sm"
        actionVariant="secondary"
        ariaLabel="Migrated report modules"
        description="Report viewer and group summary tools stay secondary to artifact indexing and do not imply fresh metrics were computed."
        disabledReason="Select a project before loading report-specific modules."
        evidenceLevel={hasProject ? "backend_required" : "blocked"}
        hideActionLabel="Hide report modules"
        isOpen={showMigratedReports}
        onToggle={() => setShowMigratedReports((value) => !value)}
        openLabel="Open report modules"
        safetyNote="Opening this section loads existing report viewers; export and validation remain backend-owned."
        status={hasProject ? (showMigratedReports ? "Open" : "On demand") : "Select project"}
        statusTone={hasProject ? "info" : "warning"}
        title="Migrated report modules"
      >
        <div className={layoutStyles.panelGrid}>
          <div id="rsfmri-group-summary-panel">
            <RsfmriGroupSummaryPanel baseUrl={baseUrl} />
          </div>
          <div id="dataset-report-viewer-panel">
            <ReportViewer baseUrl={baseUrl} />
          </div>
        </div>
      </TechnicalModuleSection>
    </div>
  );
}

function ResultsOverview() {
  return (
    <section className={styles.resultsGrid} aria-label="Results workspace overview">
      <Card className={styles.packageCard} tone="muted">
        <div className={styles.cardHeader}>
          <div>
            <h3>Artifact evidence boundary</h3>
            <p>
              Page-level handoff for generated artifacts. Created, previewable, exported, and
              validated states stay separate until backend modules load persisted evidence.
            </p>
          </div>
          <EvidenceBadge level="backend_required" />
        </div>
        <div className={styles.statusStrip} aria-label="Artifact evidence states">
          {ARTIFACT_STATE_BOUNDARIES.map((item) => (
            <div data-tone={item.tone} key={item.label}>
              <span>{item.label}</span>
              <strong>{item.value}</strong>
              <small>{item.description}</small>
            </div>
          ))}
        </div>
        <Table caption="Artifact handoff index">
          <thead>
            <tr>
              <th>Artifact</th>
              <th>Run or subject</th>
              <th>Type</th>
              <th>Stage</th>
              <th>Preview</th>
            </tr>
          </thead>
          <tbody>
            <TableEmpty colSpan={5}>
              Artifact rows appear only after the Artifact Browser loads the backend index. Planned
              outputs, preview-only records, and missing provenance stay labeled as such.
            </TableEmpty>
          </tbody>
        </Table>
        <Table caption="Artifact state boundaries">
          <thead>
            <tr>
              <th>State</th>
              <th>Required evidence</th>
              <th>UI behavior</th>
            </tr>
          </thead>
          <tbody>
            {ARTIFACT_BOUNDARY_ROWS.map((item) => (
              <tr key={item.state}>
                <td>{item.state}</td>
                <td>{item.evidence}</td>
                <td>{item.behavior}</td>
              </tr>
            ))}
          </tbody>
        </Table>
      </Card>

      <Card className={styles.flowCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Artifact workflow</h3>
            <p>Browsing, preview, provenance, export, and validation stay separate.</p>
          </div>
        </div>
        <ol className={styles.flowList} aria-label="Results artifact workflow">
          {ARTIFACT_WORKFLOW.map((item, index) => (
            <li key={item.label}>
              <span>{index + 1}</span>
              <div>
                <strong>{item.label}</strong>
                <p>{item.description}</p>
              </div>
              <Badge tone={item.tone} size="sm">
                {item.status}
              </Badge>
            </li>
          ))}
        </ol>
      </Card>

      <Card className={styles.provenanceCard}>
        <div className={styles.cardHeader}>
          <div>
            <h3>Provenance checks</h3>
            <p>Validation records should prove package integrity before handoff.</p>
          </div>
        </div>
        <dl className={styles.checkList}>
          {PROVENANCE_CHECKS.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.description}</dd>
            </div>
          ))}
        </dl>
        <nav className={styles.moduleRail} aria-label="Results module shortcuts">
          {RESULT_MODULES.map((item) => (
            <a href={item.href} key={item.label}>
              <strong>{item.label}</strong>
              <span>{item.status}</span>
              <small>{item.description}</small>
            </a>
          ))}
        </nav>
      </Card>
    </section>
  );
}

type BadgeTone = "neutral" | "info" | "success" | "warning" | "danger";

const ARTIFACT_STATE_BOUNDARIES: Array<{
  description: string;
  label: string;
  tone: BadgeTone;
  value: string;
}> = [
  {
    label: "Planned",
    value: evidenceLabel("planned"),
    description: "Expected output without a persisted artifact path",
    tone: "neutral",
  },
  {
    label: "Created",
    value: evidenceLabel("created"),
    description: "Created only when a persisted artifact record exists",
    tone: "success",
  },
  {
    label: "Preview",
    value: evidenceLabel("preview_only"),
    description: "Preview appears only for supported artifact evidence",
    tone: "info",
  },
  {
    label: "Provenance",
    value: evidenceLabel("backend_required"),
    description: "Missing run, node, input, parameter, or checksum stays visible",
    tone: "warning",
  },
  {
    label: "Validation",
    value: evidenceLabel("backend_required"),
    description: "Validation failed and not generated are distinct states",
    tone: "warning",
  },
];

const ARTIFACT_BOUNDARY_ROWS = [
  {
    state: "Planned output",
    evidence: "Workflow plan or expected path only",
    behavior: "List as planned; do not count as created",
  },
  {
    state: "Created artifact",
    evidence: "Persisted path, type, run or subject, and artifact index record",
    behavior: "Show in artifact table with provenance availability",
  },
  {
    state: "Preview-only",
    evidence: "Supported preview evidence without export or validation package",
    behavior: "Allow preview; do not imply export or validation",
  },
  {
    state: "Missing provenance",
    evidence:
      "Artifact exists but run, node, input, parameter, checksum, or warning data is absent",
    behavior: "Flag provenance gap before handoff",
  },
  {
    state: "Validation failed",
    evidence: "Backend validation record reports mismatch, missing file, or safety violation",
    behavior: "Keep failure visible; do not offer success copy",
  },
];

const ARTIFACT_WORKFLOW: Array<{
  description: string;
  label: string;
  status: string;
  tone: BadgeTone;
}> = [
  {
    label: "Browse artifacts",
    description: "Load or refresh the artifact index before showing generated files.",
    status: evidenceLabel("backend_required"),
    tone: "info",
  },
  {
    label: "Preview supported artifact",
    description: "Open only artifact types the backend preview endpoint marks as supported.",
    status: evidenceLabel("preview_only"),
    tone: "info",
  },
  {
    label: "Check provenance",
    description: "Review run, node, input, and parameter records before treating output as final.",
    status: "Review",
    tone: "warning",
  },
  {
    label: "Export package",
    description: "Request reviewed report packages through the existing backend exporter module.",
    status: evidenceLabel("backend_required"),
    tone: "warning",
  },
  {
    label: "Validate package",
    description: "Check manifest, checksums, missing files, and safety violations after export.",
    status: evidenceLabel("backend_required"),
    tone: "neutral",
  },
];

const PROVENANCE_CHECKS = [
  {
    label: "Run and node",
    description: "Producing run, node, and workflow context must come from persisted records.",
  },
  {
    label: "Inputs and parameters",
    description: "Artifact sidecars supplement numerical files; they do not replace them.",
  },
  {
    label: "Checksum and warnings",
    description:
      "Checksums and warnings should be visible when available and explicitly pending when absent.",
  },
  {
    label: "Package integrity",
    description: "The validation module reports mismatches instead of the UI inferring success.",
  },
];

const RESULT_MODULES = [
  {
    description: "Load counts, filters, supported previews, and artifact rows.",
    href: "#artifact-browser-panel",
    label: "Artifact Browser",
    status: "Index + preview",
  },
  {
    description: "Request backend-owned rs-fMRI report packages when evidence is ready.",
    href: "#rsfmri-report-exporter-panel",
    label: "Report Export",
    status: "Backend gated",
  },
  {
    description: "Review manifests, checksums, missing files, and safety violations.",
    href: "#rsfmri-report-validator-panel",
    label: "Package Validation",
    status: "Integrity checks",
  },
];
