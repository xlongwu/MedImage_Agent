import { useState } from "react";
import type { ProjectCreateResponse } from "../../types";
import { ActionList } from "../../components/dashboardUi";
import { cleanupNextActions } from "../../components/dashboardUiModel";
import { formatNumber } from "../../i18n/format";
import { useI18n } from "../../i18n/useI18n";

export interface ProjectCreateResultPanelProps {
  result: ProjectCreateResponse | null;
  loading: boolean;
  error: string;
  onDismiss: () => void;
}

export function ProjectCreateResultPanel({
  result,
  loading,
  error,
  onDismiss,
}: ProjectCreateResultPanelProps) {
  const { locale, t } = useI18n();
  const [showTechDetails, setShowTechDetails] = useState(false);

  if (!result && !loading && !error) {
    return null;
  }

  const diagnostics = result?.diagnostics ?? {};
  const status = String(diagnostics.status ?? "UNKNOWN");
  const dicomFileCount = diagnosticNumber(diagnostics, "dicom_file_count");
  const hasRawDicom =
    dicomFileCount > 0 && diagnosticNumber(diagnostics, "image_source_count") === 0;
  const rawDicomCandidates = firstDiagnosticNumber(
    diagnostics,
    ["raw_dicom_candidate_subjects", "dicom_candidate_subjects", "dicom_subject_count"],
    diagnosticArrayLength(diagnostics, "subject_candidates") ||
      diagnosticNumber(diagnostics, "subjects_total"),
  );
  const nextActions = cleanupNextActions(result?.next_actions ?? [], { rawDicom: hasRawDicom });
  return (
    <section className="task-detail-panel">
      <div className="card-row">
        <div>
          <div className="card-title">
            {loading
              ? t("projects.createResult.creating")
              : error
                ? t("projects.createResult.failed")
                : t("projects.createResult.created", { name: result?.project_name ?? "" })}
          </div>
          <span>
            {loading
              ? t("projects.createResult.inspecting")
              : t("projects.createResult.statusValue", { status })}
          </span>
        </div>
        <div className="detail-actions">
          {!loading ? (
            <button onClick={onDismiss}>{t("projects.createResult.dismiss")}</button>
          ) : null}
        </div>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {result ? (
        <>
          <div className="detail-grid">
            <div>
              <span>{t("projects.createResult.status")}</span>
              <strong>{status}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.convertedSubjects")}</span>
              <strong>{diagnosticNumber(diagnostics, "image_subject_count")}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.rawCandidates")}</span>
              <strong>{rawDicomCandidates}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.dicomFiles")}</span>
              <strong>{formatNumber(locale, dicomFileCount)}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.complete")}</span>
              <strong>{diagnosticNumber(diagnostics, "subjects_complete")}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.warning")}</span>
              <strong>{diagnosticNumber(diagnostics, "subjects_warning")}</strong>
            </div>
            <div>
              <span>{t("projects.createResult.incomplete")}</span>
              <strong>{diagnosticNumber(diagnostics, "subjects_incomplete")}</strong>
            </div>
          </div>

          <div className="section-spacer">
            <label className="tech-details-toggle">
              <input
                type="checkbox"
                checked={showTechDetails}
                onChange={(e) => setShowTechDetails(e.target.checked)}
              />
              {t("projects.createResult.showTechnical")}
            </label>
          </div>

          {showTechDetails && (
            <>
              <div className="event-list">
                <div className="event-row">
                  <span>{t("projects.createResult.projectDirectory")}</span>
                  <p>{result.project_dir}</p>
                </div>
                <div className="event-row">
                  <span>{t("projects.createResult.rawdataDirectory")}</span>
                  <p>{result.rawdata_dir}</p>
                </div>
                <div className="event-row">
                  <span>{t("projects.createResult.datasetIndex")}</span>
                  <p>{result.dataset_index_path || t("projects.createResult.notGenerated")}</p>
                </div>
              </div>

              <div className="tool-result-list">
                <div className="panel-kicker">{t("projects.createResult.nextActions")}</div>
                <ActionList actions={nextActions} rawDicom={hasRawDicom} />
              </div>
            </>
          )}

          {result.warnings.length ? (
            <div className="diagnostic-list">
              {result.warnings.map((warning, index) => (
                <div className="diagnostic-item warning" key={`${warning}-${index}`}>
                  <span>{t("projects.createResult.warning")}</span>
                  <p>{warning}</p>
                </div>
              ))}
            </div>
          ) : null}
        </>
      ) : null}
    </section>
  );
}

function diagnosticNumber(diagnostics: Record<string, unknown>, key: string): number {
  const value = diagnostics[key];
  return typeof value === "number" ? value : 0;
}

function diagnosticArrayLength(diagnostics: Record<string, unknown>, key: string): number {
  const value = diagnostics[key];
  return Array.isArray(value) ? value.length : 0;
}

function firstDiagnosticNumber(
  diagnostics: Record<string, unknown>,
  keys: string[],
  fallback: number,
): number {
  for (const key of keys) {
    const value = diagnostics[key];
    if (typeof value === "number") {
      return value;
    }
  }
  return fallback;
}
