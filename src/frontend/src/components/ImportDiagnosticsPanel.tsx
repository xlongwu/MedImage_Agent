import { useEffect, useMemo, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import {
  createImportDiagnosticsPackage,
  getDatasetImportHistory,
  getLatestImportDiagnosticsPackage,
  verifyImportDiagnosticsPackage,
} from "../lib/api/diagnostic";
import { getDicomPreflight } from "../lib/api/dicom";
import { getImageManifestReport, getImageValidationReport } from "../lib/api/qc";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
  projectId?: string | null;
  rawdataDir?: string | null;
};

type ValidationIssue = {
  severity?: string;
  code?: string;
  message?: string;
  subject_id?: string;
  session_id?: string;
  sequence?: string;
  file_path?: string;
  details?: Record<string, unknown>;
};

type ImportRecord = {
  dataset_id?: string;
  project_id?: string;
  path?: string;
  dataset_type?: string;
  created_at?: string;
  exists?: boolean;
};

type DicomSeries = {
  series_instance_uid?: string;
  study_instance_uid?: string;
  subject_id?: string;
  modality?: string;
  series_description?: string;
  protocol_name?: string;
  sequence_name?: string;
  manufacturer?: string;
  magnetic_field_strength?: number;
  repetition_time?: number;
  echo_time?: number;
  flip_angle?: number;
  rows?: number;
  columns?: number;
  instances?: number;
  sample_file?: string;
  warnings?: string[];
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function asIssueList(value: unknown): ValidationIssue[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .map((item) => item as ValidationIssue);
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => String(item));
}

function asImportRecords(value: unknown): ImportRecord[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .map((item) => item as ImportRecord);
}

function asDicomSeries(value: unknown): DicomSeries[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => asRecord(item))
    .filter((item): item is Record<string, unknown> => Boolean(item))
    .map((item) => item as DicomSeries);
}

function severityTone(severity: string | undefined) {
  if (severity === "error") {
    return "#dc2626";
  }
  if (severity === "warning") {
    return "#d97706";
  }
  return "#2563eb";
}

export default function ImportDiagnosticsPanel({
  baseUrl,
  projectId: activeProjectId,
  rawdataDir,
}: Props) {
  const { t } = useI18n();
  const [projectId, setProjectId] = useState(activeProjectId ?? "");
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null);
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null);
  const [importHistory, setImportHistory] = useState<Record<string, unknown> | null>(null);
  const [handoffPackage, setHandoffPackage] = useState<Record<string, unknown> | null>(null);
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null);
  const [dicomPreflight, setDicomPreflight] = useState<Record<string, unknown> | null>(null);
  const [dicomPath, setDicomPath] = useState(rawdataDir ?? "");
  const [dicomMaxFiles, setDicomMaxFiles] = useState(2000);
  const [busy, setBusy] = useState(false);
  const [packaging, setPackaging] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [dicomBusy, setDicomBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    if (projectId.trim()) {
      void refresh();
    }
    // Refresh only when the API origin changes; project context is synchronized separately below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baseUrl]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Clear stale form context when the active project changes.
    setProjectId(activeProjectId ?? "");
    setDicomPath(rawdataDir ?? "");
    if (activeProjectId || rawdataDir) {
      setNotice("Active project context loaded. Run diagnostics when ready.");
      setError("");
    }
  }, [activeProjectId, rawdataDir]);

  function useActiveProjectContext() {
    setProjectId(activeProjectId ?? "");
    setDicomPath(rawdataDir ?? "");
    setNotice(
      activeProjectId
        ? "Active project context applied. Run diagnostics when ready."
        : "No active project context is available.",
    );
    setError("");
  }

  function getRequestedProjectId(action: string) {
    const trimmedProjectId = projectId.trim();
    if (!trimmedProjectId) {
      setError(`Enter a project ID before ${action}.`);
      setNotice("");
      return null;
    }
    return trimmedProjectId;
  }

  async function refresh() {
    const trimmedProjectId = getRequestedProjectId("loading import diagnostics");
    if (!trimmedProjectId) return;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const [validationPayload, manifestPayload, importHistoryPayload, latestPackagePayload] =
        await Promise.all([
          getImageValidationReport(baseUrl, trimmedProjectId),
          getImageManifestReport(baseUrl, trimmedProjectId),
          getDatasetImportHistory(baseUrl, trimmedProjectId),
          getLatestImportDiagnosticsPackage(baseUrl, trimmedProjectId),
        ]);
      setValidation(validationPayload);
      setManifest(manifestPayload);
      setImportHistory(importHistoryPayload);
      const latestPackage = asRecord(latestPackagePayload.latest);
      if (latestPackage) {
        setHandoffPackage(latestPackage);
      }
      try {
        setDicomPreflight(
          await getDicomPreflight(baseUrl, trimmedProjectId, dicomPath, dicomMaxFiles),
        );
      } catch (dicomErr) {
        setDicomPreflight(null);
        setNotice(
          `DICOM preflight unavailable: ${dicomErr instanceof Error ? dicomErr.message : String(dicomErr)}`,
        );
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openArtifact(targetPath: string, label: string) {
    if (!targetPath) {
      setNotice(`${label} has not been generated yet.`);
      return;
    }
    if (!window.medimage?.openExternalPath) {
      setNotice(`${label}: ${targetPath}`);
      return;
    }
    const opened = await window.medimage.openExternalPath(targetPath);
    setNotice(opened ? `Opened ${label}: ${targetPath}` : `${label}: ${targetPath}`);
  }

  async function generatePackage() {
    const trimmedProjectId = getRequestedProjectId("generating an import diagnostics package");
    if (!trimmedProjectId) return;
    setPackaging(true);
    setError("");
    setNotice("");
    try {
      const payload = await createImportDiagnosticsPackage(baseUrl, trimmedProjectId);
      setHandoffPackage(payload);
      await refresh();
      setNotice(`Import diagnostics package generated: ${String(payload.report_path || "")}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setPackaging(false);
    }
  }

  async function verifyPackage() {
    const trimmedProjectId = getRequestedProjectId("verifying an import diagnostics package");
    if (!trimmedProjectId) return;
    setVerifying(true);
    setError("");
    setNotice("");
    try {
      const payload = await verifyImportDiagnosticsPackage(baseUrl, trimmedProjectId);
      setVerifyResult(payload);
      setNotice(
        payload.ok
          ? "Handoff package verification passed."
          : "Handoff package verification needs review.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setVerifying(false);
    }
  }

  async function runDicomMetadataPreflight() {
    const trimmedProjectId = getRequestedProjectId("running DICOM metadata preflight");
    if (!trimmedProjectId) return;
    setDicomBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = await getDicomPreflight(baseUrl, trimmedProjectId, dicomPath, dicomMaxFiles);
      setDicomPreflight(payload);
      setNotice(
        payload.ok
          ? `DICOM metadata preflight complete: ${String(payload.report_path || "")}`
          : "DICOM metadata preflight needs review.",
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDicomBusy(false);
    }
  }

  const issues = useMemo(() => asIssueList(validation?.issues), [validation]);
  const imports = useMemo(() => asImportRecords(importHistory?.imports), [importHistory]);
  const dicomSeries = useMemo(() => asDicomSeries(dicomPreflight?.series), [dicomPreflight]);
  const manifestWarnings = useMemo(() => stringList(manifest?.warnings), [manifest]);
  const sourceCount = Number(manifest?.source_count ?? manifest?.count ?? 0);
  const issueCount = Number(validation?.issue_count ?? issues.length);
  const reportPath = String(validation?.report_path || "");
  const jsonPath = String(validation?.json_path || validation?.report_json_path || "");
  const manifestPath = String(manifest?.manifest_path || "");
  const reportText = String(validation?.report_text || "");
  const packageReportPath = String(handoffPackage?.report_path || "");
  const packageJsonPath = String(handoffPackage?.json_path || "");
  const packageZipPath = String(handoffPackage?.zip_path || "");
  const packageDir = String(handoffPackage?.package_dir || "");
  const checksumPath = String(handoffPackage?.checksum_path || "");
  const checksumCount = asRecord(handoffPackage?.checksums)
    ? Object.keys(asRecord(handoffPackage?.checksums) || {}).length
    : 0;
  const safetyFlags = asRecord(handoffPackage?.safety_flags);
  const dicomSafetyFlags = asRecord(dicomPreflight?.safety_flags);
  const dicomReportPath = String(dicomPreflight?.report_path || "");
  const dicomJsonPath = String(dicomPreflight?.json_path || "");
  const dicomReportText = String(dicomPreflight?.report_text || "");
  const dicomWarnings = stringList(dicomPreflight?.warnings);
  const dicomErrors = stringList(dicomPreflight?.errors);
  const hasProjectId = Boolean(projectId.trim());
  const dicomInputConfigured = Boolean(dicomPath.trim());

  return (
    <div>
      {error ? <div className="errorBox">{error}</div> : null}
      {notice ? (
        <div className="empty" style={{ marginBottom: 12 }}>
          {notice}
        </div>
      ) : null}
      <div className="formGrid">
        <label>
          {t("technical.ImportDiagnostics.001")}
          <input
            placeholder={t("technical.ImportDiagnostics.002")}
            value={projectId}
            onChange={(event) => setProjectId(event.target.value)}
          />
        </label>
        <label>
          {t("technical.ImportDiagnostics.003")}
          <input
            readOnly
            value={
              activeProjectId
                ? `${activeProjectId}${rawdataDir ? ` | ${rawdataDir}` : ""}`
                : t("technical.ImportDiagnostics.004")
            }
          />
        </label>
        <label>
          {t("technical.ImportDiagnostics.005")}
          <input readOnly value={reportPath || t("technical.ImportDiagnostics.006")} />
        </label>
        <label>
          {t("technical.ImportDiagnostics.007")}
          <input readOnly value={jsonPath || t("technical.ImportDiagnostics.006")} />
        </label>
        <label>
          {t("technical.ImportDiagnostics.008")}
          <input readOnly value={manifestPath || t("technical.ImportDiagnostics.006")} />
        </label>
      </div>

      <div className="row">
        <button onClick={useActiveProjectContext} disabled={!activeProjectId && !rawdataDir}>
          {t("technical.ImportDiagnostics.009")}
        </button>
        <button onClick={refresh} disabled={busy || !hasProjectId}>
          {busy ? t("technical.ImportDiagnostics.010") : t("technical.ImportDiagnostics.011")}
        </button>
        <button
          onClick={() => void openArtifact(reportPath, "validation report")}
          disabled={!reportPath}
        >
          {t("technical.ImportDiagnostics.012")}
        </button>
        <button onClick={() => void openArtifact(jsonPath, "validation JSON")} disabled={!jsonPath}>
          {t("technical.ImportDiagnostics.013")}
        </button>
        <button
          onClick={() => void openArtifact(manifestPath, "image manifest")}
          disabled={!manifestPath}
        >
          {t("technical.ImportDiagnostics.014")}
        </button>
        <button onClick={generatePackage} disabled={packaging || !hasProjectId}>
          {packaging ? t("technical.ImportDiagnostics.015") : t("technical.ImportDiagnostics.016")}
        </button>
        <button
          onClick={() => void openArtifact(packageReportPath, "handoff report")}
          disabled={!packageReportPath}
        >
          {t("technical.ImportDiagnostics.017")}
        </button>
        <button
          onClick={() => void openArtifact(packageZipPath, "handoff ZIP")}
          disabled={!packageZipPath}
        >
          {t("technical.ImportDiagnostics.018")}
        </button>
        <button
          onClick={() => void openArtifact(packageDir, "handoff folder")}
          disabled={!packageDir}
        >
          {t("technical.ImportDiagnostics.019")}
        </button>
        <button
          onClick={() => void openArtifact(checksumPath, "handoff checksums")}
          disabled={!checksumPath}
        >
          {t("technical.ImportDiagnostics.020")}
        </button>
        <button onClick={verifyPackage} disabled={verifying || !packageZipPath}>
          {verifying ? t("technical.ImportDiagnostics.021") : t("technical.ImportDiagnostics.022")}
        </button>
        <span className="status-pill">
          {issueCount === 0
            ? t("technical.ImportDiagnostics.023")
            : t("technical.ImportDiagnostics.024", { value0: issueCount })}
        </span>
        <span className="status-pill">
          {sourceCount} {t("technical.ImportDiagnostics.025")}
        </span>
        {checksumCount ? (
          <span className="status-pill">
            {checksumCount} {t("technical.ImportDiagnostics.026")}
          </span>
        ) : null}
      </div>

      <div className="metricGrid" style={{ marginTop: 12 }}>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.027")}</div>
          <strong>
            {String(validation?.ok ?? false) === "true"
              ? t("technical.ImportDiagnostics.028")
              : t("technical.ImportDiagnostics.029")}
          </strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.030")}</div>
          <strong>{issueCount}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.031")}</div>
          <strong>{sourceCount}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.DicomConversionReleaseReadiness.012")}</div>
          <strong>{manifestWarnings.length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.032")}</div>
          <strong>{imports.length}</strong>
        </div>
      </div>

      <h3>{t("technical.ImportDiagnostics.033")}</h3>
      <div className="formGrid">
        <label>
          {t("technical.ImportDiagnostics.034")}
          <input
            placeholder={t("technical.ImportDiagnostics.035")}
            value={dicomPath}
            onChange={(event) => setDicomPath(event.target.value)}
          />
        </label>
        <label>
          {t("technical.ImportDiagnostics.036")}
          <input
            type="number"
            min={1}
            max={10000}
            value={dicomMaxFiles}
            onChange={(event) => setDicomMaxFiles(Math.max(1, Number(event.target.value) || 1))}
          />
        </label>
        <label>
          {t("technical.ImportDiagnostics.037")}
          <input readOnly value={dicomReportPath || t("technical.ImportDiagnostics.006")} />
        </label>
        <label>
          {t("technical.ImportDiagnostics.038")}
          <input readOnly value={dicomJsonPath || t("technical.ImportDiagnostics.006")} />
        </label>
      </div>
      {!dicomInputConfigured ? (
        <div className="empty" style={{ marginTop: 8 }}>
          DICOM diagnostics input is not configured. A 0 sources / 0 DICOM files preflight in this
          module means no diagnostics root has been supplied here; it does not mean the active
          project has no raw DICOM data.
        </div>
      ) : null}
      <div className="row">
        <button onClick={runDicomMetadataPreflight} disabled={dicomBusy || !hasProjectId}>
          {dicomBusy ? t("technical.ImportDiagnostics.039") : t("technical.ImportDiagnostics.040")}
        </button>
        <button
          onClick={() => void openArtifact(dicomReportPath, "DICOM preflight report")}
          disabled={!dicomReportPath}
        >
          {t("technical.ImportDiagnostics.041")}
        </button>
        <button
          onClick={() => void openArtifact(dicomJsonPath, "DICOM preflight JSON")}
          disabled={!dicomJsonPath}
        >
          {t("technical.ImportDiagnostics.042")}
        </button>
        <span className="status-pill">
          {Number(dicomPreflight?.dicom_file_count || 0)} DICOM files
        </span>
        <span className="status-pill">{Number(dicomPreflight?.series_count || 0)} series</span>
        <span className="status-pill">
          {Number(dicomPreflight?.sampled_file_count || 0)} sampled
        </span>
      </div>
      <div className="metricGrid" style={{ marginTop: 12 }}>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.043")}</div>
          <strong>
            {dicomPreflight?.ok
              ? t("technical.ImportDiagnostics.028")
              : t("technical.ImportDiagnostics.029")}
          </strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.044")}</div>
          <strong>{stringList(dicomPreflight?.subjects).length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.045")}</div>
          <strong>{stringList(dicomPreflight?.modalities).join(", ") || "-"}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.DicomConversionReleaseReadiness.012")}</div>
          <strong>{dicomWarnings.length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">{t("technical.ImportDiagnostics.046")}</div>
          <strong>{dicomErrors.length}</strong>
        </div>
      </div>
      {dicomSafetyFlags ? (
        <div className="metricGrid" style={{ marginTop: 8 }}>
          {Object.entries(dicomSafetyFlags).map(([key, value]) => (
            <div className="metricCard" key={key}>
              <div className="muted">{key}</div>
              <strong>
                {value
                  ? t("technical.ImportDiagnostics.047")
                  : t("technical.ImportDiagnostics.048")}
              </strong>
            </div>
          ))}
        </div>
      ) : null}
      {dicomSeries.length ? (
        <div style={{ display: "grid", gap: 8, marginTop: 12 }}>
          {dicomSeries.slice(0, 6).map((series, index) => (
            <div
              key={series.series_instance_uid || `${series.subject_id}-${index}`}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 12,
                background: "#fff",
              }}
            >
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <strong>
                  {series.series_description || series.sequence_name || "DICOM series"}
                </strong>
                <span className="status-pill">{series.subject_id || "subject unknown"}</span>
                <span className="status-pill">{series.modality || "modality unknown"}</span>
                <span className="status-pill">{series.instances || 0} instances</span>
              </div>
              <div className="muted" style={{ marginTop: 6 }}>
                {[
                  series.manufacturer,
                  series.magnetic_field_strength ? `${series.magnetic_field_strength}T` : "",
                  series.repetition_time ? `TR ${series.repetition_time}` : "",
                  series.echo_time ? `TE ${series.echo_time}` : "",
                ]
                  .filter(Boolean)
                  .join(" · ") || "Header metadata available"}
              </div>
              <div className="muted" style={{ marginTop: 6, wordBreak: "break-all" }}>
                {series.sample_file || ""}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          {dicomInputConfigured
            ? t("technical.ImportDiagnostics.049")
            : t("technical.ImportDiagnostics.050")}
        </div>
      )}
      {dicomWarnings.length || dicomErrors.length ? (
        <div style={{ display: "grid", gap: 6, marginTop: 12 }}>
          {[...dicomErrors, ...dicomWarnings].map((message, index) => (
            <div
              key={`${message}-${index}`}
              className={dicomErrors.includes(message) ? "errorBox" : "empty"}
            >
              {message}
            </div>
          ))}
        </div>
      ) : null}
      <h3>{t("technical.ImportDiagnostics.051")}</h3>
      <TextViewer
        text={dicomReportText || t("technical.ImportDiagnostics.052")}
        maxHeight="260px"
      />
      <h3>{t("technical.ImportDiagnostics.053")}</h3>
      <JsonBlock value={dicomPreflight} emptyText={t("technical.ImportDiagnostics.054")} />

      <h3>{t("technical.ImportDiagnostics.055")}</h3>
      {imports.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {imports.map((item) => (
            <div
              key={item.dataset_id || item.path}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 12,
                background: "#fff",
              }}
            >
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <strong>{item.dataset_id || "dataset"}</strong>
                <span className="status-pill">{item.dataset_type || "unknown"}</span>
                <span className="status-pill">{item.exists ? "path exists" : "path missing"}</span>
                <span className="muted">{item.created_at || ""}</span>
              </div>
              <div className="muted" style={{ marginTop: 6, wordBreak: "break-all" }}>
                {item.path || ""}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">{t("technical.ImportDiagnostics.056")}</div>
      )}

      <h3>{t("technical.ImportDiagnostics.057")}</h3>
      {issues.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {issues.map((issue, index) => (
            <div
              key={`${issue.code || "issue"}-${index}`}
              style={{
                border: "1px solid #e5e7eb",
                borderRadius: 8,
                padding: 12,
                background: "#fff",
              }}
            >
              <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
                <span
                  style={{
                    color: severityTone(issue.severity),
                    fontWeight: 700,
                    textTransform: "uppercase",
                    fontSize: 11,
                  }}
                >
                  {issue.severity || "info"}
                </span>
                <strong>{issue.code || "diagnostic"}</strong>
                <span className="muted">
                  {[issue.subject_id, issue.session_id, issue.sequence].filter(Boolean).join(" / ")}
                </span>
              </div>
              <div style={{ marginTop: 6 }}>{issue.message || "No message"}</div>
              {issue.file_path ? (
                <div className="muted" style={{ marginTop: 6, wordBreak: "break-all" }}>
                  {issue.file_path}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">{t("technical.ImportDiagnostics.058")}</div>
      )}

      {manifestWarnings.length ? (
        <>
          <h3>{t("technical.ImportDiagnostics.059")}</h3>
          <div style={{ display: "grid", gap: 6 }}>
            {manifestWarnings.map((warning, index) => (
              <div key={`${warning}-${index}`} className="errorBox">
                {warning}
              </div>
            ))}
          </div>
        </>
      ) : null}

      <h3>{t("technical.ImportDiagnostics.005")}</h3>
      <TextViewer text={reportText || "No validation report text loaded"} maxHeight="300px" />
      <h3>{t("technical.ImportDiagnostics.060")}</h3>
      <JsonBlock value={validation} emptyText="No validation report loaded" />
      <h3>{t("technical.ImportDiagnostics.061")}</h3>
      <JsonBlock value={manifest} emptyText="No manifest loaded" />
      <h3>{t("technical.ImportDiagnostics.062")}</h3>
      <JsonBlock value={importHistory} emptyText="No import history loaded" />
      <h3>{t("technical.ImportDiagnostics.063")}</h3>
      {safetyFlags ? (
        <div className="metricGrid" style={{ marginTop: 8 }}>
          {Object.entries(safetyFlags).map(([key, value]) => (
            <div className="metricCard" key={key}>
              <div className="muted">{key}</div>
              <strong>
                {value
                  ? t("technical.ImportDiagnostics.047")
                  : t("technical.ImportDiagnostics.048")}
              </strong>
            </div>
          ))}
        </div>
      ) : null}
      <div className="row">
        <button
          onClick={() => void openArtifact(packageJsonPath, "handoff JSON")}
          disabled={!packageJsonPath}
        >
          {t("technical.ImportDiagnostics.064")}
        </button>
      </div>
      <JsonBlock value={handoffPackage} emptyText="No handoff package generated in this session" />
      <h3>{t("technical.ImportDiagnostics.065")}</h3>
      <JsonBlock value={verifyResult} emptyText="No package verification run in this session" />
    </div>
  );
}
