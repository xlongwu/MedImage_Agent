import { useState, type ReactNode } from "react";

import { ArtifactBrowser } from "../../components/ArtifactBrowser";
import { ReportViewer } from "../../components/ReportViewer";
import { RsfmriGroupSummaryPanel } from "../../components/RsfmriGroupSummaryPanel";
import { RsfmriReportExporterPanel } from "../../components/RsfmriReportExporterPanel";
import { RsfmriReportValidatorPanel } from "../../components/RsfmriReportValidatorPanel";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { Card, EmptyState } from "../../components/ui";
import type { ArtifactSelection } from "../../lib/workspaceSelection";
import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import styles from "./ResultsWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";
import { useI18n } from "../../i18n/useI18n";

export interface ResultsWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  onSelectedArtifactChange?: (artifact: ArtifactSelection | null) => void;
  viewer?: ReactNode;
}

export function ResultsWorkspace({
  baseUrl,
  projectId,
  onSelectedArtifactChange,
  viewer,
}: ResultsWorkspaceProps) {
  const { t } = useI18n();
  const hasProject = Boolean(projectId);
  const [showMigratedReports, setShowMigratedReports] = useState(false);

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title={t("results.title")}
        subtitle={t("results.subtitle")}
        status={hasProject ? t("results.artifacts") : t("results.selectProject")}
      />

      {!hasProject ? (
        <EmptyState title={t("results.selectTitle")} description={t("results.selectDescription")} />
      ) : (
        <section className={styles.artifactViewerGrid} aria-label={t("results.browserViewer")}>
          <Card className={styles.artifactListCard}>
            <ArtifactBrowser
              baseUrl={baseUrl}
              projectId={projectId}
              onSelectedArtifactChange={onSelectedArtifactChange}
            />
          </Card>
          <Card className={styles.viewerCard}>
            {viewer ?? (
              <EmptyState
                title={t("results.noPreview")}
                description={t("results.noPreviewDescription")}
              />
            )}
          </Card>
        </section>
      )}

      <TechnicalModuleSection
        ariaLabel={t("results.artifactModules")}
        bodyVisible={false}
        description={t("results.artifactModulesDescription")}
        evidenceLevel={hasProject ? "unavailable" : "blocked"}
        fallback={
          <Card tone="muted">
            <EmptyState
              title={hasProject ? t("common.unavailable") : t("results.modulesWaiting")}
              description={
                hasProject ? t("results.legacyUnavailable") : t("results.modulesWaitingDescription")
              }
            />
          </Card>
        }
        helperText={hasProject ? t("results.legacyUnavailable") : t("results.modulesSelectHelp")}
        safetyNote={t("results.modulesSafety")}
        status={hasProject ? t("common.unavailable") : t("results.selectProject")}
        statusTone={hasProject ? "info" : "warning"}
        title={t("results.artifactModules")}
      >
        {hasProject ? (
          <div className={layoutStyles.panelGrid}>
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
        actionDisabled
        actionSize="sm"
        actionVariant="secondary"
        ariaLabel={t("results.migratedModules")}
        description={t("results.migratedDescription")}
        disabledReason={t("results.migratedDisabled")}
        evidenceLevel={hasProject ? "unavailable" : "blocked"}
        hideActionLabel={t("results.hideReports")}
        isOpen={showMigratedReports}
        onToggle={() => setShowMigratedReports((value) => !value)}
        openLabel={t("results.openReports")}
        safetyNote={t("results.migratedSafety")}
        status={hasProject ? t("common.unavailable") : t("results.selectProject")}
        statusTone={hasProject ? "info" : "warning"}
        title={t("results.migratedModules")}
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
