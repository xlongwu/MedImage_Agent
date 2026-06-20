import { useState } from "react";
import type { ProjectCreateResponse } from "../../types";
import { ActionList, cleanupNextActions } from "../../components/dashboardUi";

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
              ? "Creating project..."
              : error
                ? "Project creation failed"
                : `Project created: ${result?.project_name}`}
          </div>
          <span>
            {loading ? "Inspecting the selected BIDS/rawdata directory" : `Status: ${status}`}
          </span>
        </div>
        <div className="detail-actions">
          {!loading ? <button onClick={onDismiss}>Dismiss</button> : null}
        </div>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {result ? (
        <>
          <div className="detail-grid">
            <div>
              <span>Status</span>
              <strong>{status}</strong>
            </div>
            <div>
              <span>Converted subjects</span>
              <strong>{diagnosticNumber(diagnostics, "image_subject_count")}</strong>
            </div>
            <div>
              <span>Raw DICOM candidates</span>
              <strong>{rawDicomCandidates}</strong>
            </div>
            <div>
              <span>DICOM files</span>
              <strong>{dicomFileCount.toLocaleString()}</strong>
            </div>
            <div>
              <span>Complete</span>
              <strong>{diagnosticNumber(diagnostics, "subjects_complete")}</strong>
            </div>
            <div>
              <span>Warning</span>
              <strong>{diagnosticNumber(diagnostics, "subjects_warning")}</strong>
            </div>
            <div>
              <span>Incomplete</span>
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
              Show technical details
            </label>
          </div>

          {showTechDetails && (
            <>
              <div className="event-list">
                <div className="event-row">
                  <span>Project directory</span>
                  <p>{result.project_dir}</p>
                </div>
                <div className="event-row">
                  <span>Rawdata directory</span>
                  <p>{result.rawdata_dir}</p>
                </div>
                <div className="event-row">
                  <span>Dataset index</span>
                  <p>{result.dataset_index_path || "Not generated"}</p>
                </div>
              </div>

              <div className="tool-result-list">
                <div className="panel-kicker">Next actions</div>
                <ActionList actions={nextActions} rawDicom={hasRawDicom} />
              </div>
            </>
          )}

          {result.warnings.length ? (
            <div className="diagnostic-list">
              {result.warnings.map((warning, index) => (
                <div className="diagnostic-item warning" key={`${warning}-${index}`}>
                  <span>Warning</span>
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
