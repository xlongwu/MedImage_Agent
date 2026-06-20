import { useEffect, useMemo, useState } from "react";
import {
  createImportDiagnosticsPackage,
  getDatasetImportHistory,
  getDicomPreflight,
  getImageManifestReport,
  getImageValidationReport,
  getLatestImportDiagnosticsPackage,
  verifyImportDiagnosticsPackage,
} from "../lib/api/legacy";
import { JsonBlock } from "./JsonBlock";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
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

export default function ImportDiagnosticsPanel({ baseUrl }: Props) {
  const [projectId, setProjectId] = useState("brain-tumor-study");
  const [validation, setValidation] = useState<Record<string, unknown> | null>(null);
  const [manifest, setManifest] = useState<Record<string, unknown> | null>(null);
  const [importHistory, setImportHistory] = useState<Record<string, unknown> | null>(null);
  const [handoffPackage, setHandoffPackage] = useState<Record<string, unknown> | null>(null);
  const [verifyResult, setVerifyResult] = useState<Record<string, unknown> | null>(null);
  const [dicomPreflight, setDicomPreflight] = useState<Record<string, unknown> | null>(null);
  const [dicomPath, setDicomPath] = useState("data/DemoData");
  const [dicomMaxFiles, setDicomMaxFiles] = useState(2000);
  const [busy, setBusy] = useState(false);
  const [packaging, setPackaging] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [dicomBusy, setDicomBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    void refresh();
  }, [baseUrl]);

  async function refresh() {
    const trimmedProjectId = projectId.trim() || "brain-tumor-study";
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
    const trimmedProjectId = projectId.trim() || "brain-tumor-study";
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
    const trimmedProjectId = projectId.trim() || "brain-tumor-study";
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
    const trimmedProjectId = projectId.trim() || "brain-tumor-study";
    setDicomBusy(true);
    setError("");
    setNotice("");
    try {
      const payload = await getDicomPreflight(baseUrl, trimmedProjectId, dicomPath, dicomMaxFiles);
      setDicomPreflight(payload);
      setNotice(
        Boolean(payload.ok)
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
          Project ID
          <input value={projectId} onChange={(event) => setProjectId(event.target.value)} />
        </label>
        <label>
          Validation report
          <input readOnly value={reportPath || "Not generated yet"} />
        </label>
        <label>
          Validation JSON
          <input readOnly value={jsonPath || "Not generated yet"} />
        </label>
        <label>
          Manifest path
          <input readOnly value={manifestPath || "Not generated yet"} />
        </label>
      </div>

      <div className="row">
        <button onClick={refresh} disabled={busy}>
          {busy ? "Refreshing..." : "Revalidate imports"}
        </button>
        <button
          onClick={() => void openArtifact(reportPath, "validation report")}
          disabled={!reportPath}
        >
          Open report
        </button>
        <button onClick={() => void openArtifact(jsonPath, "validation JSON")} disabled={!jsonPath}>
          Open JSON
        </button>
        <button
          onClick={() => void openArtifact(manifestPath, "image manifest")}
          disabled={!manifestPath}
        >
          Open manifest
        </button>
        <button onClick={generatePackage} disabled={packaging}>
          {packaging ? "Packaging..." : "Generate handoff package"}
        </button>
        <button
          onClick={() => void openArtifact(packageReportPath, "handoff report")}
          disabled={!packageReportPath}
        >
          Open handoff
        </button>
        <button
          onClick={() => void openArtifact(packageZipPath, "handoff ZIP")}
          disabled={!packageZipPath}
        >
          Open ZIP
        </button>
        <button
          onClick={() => void openArtifact(packageDir, "handoff folder")}
          disabled={!packageDir}
        >
          Open folder
        </button>
        <button
          onClick={() => void openArtifact(checksumPath, "handoff checksums")}
          disabled={!checksumPath}
        >
          Open checksums
        </button>
        <button onClick={verifyPackage} disabled={verifying || !packageZipPath}>
          {verifying ? "Verifying..." : "Verify package"}
        </button>
        <span className="status-pill">
          {issueCount === 0 ? "No blocking issues" : `${issueCount} validation issues`}
        </span>
        <span className="status-pill">{sourceCount} image sources</span>
        {checksumCount ? <span className="status-pill">{checksumCount} checksums</span> : null}
      </div>

      <div className="metricGrid" style={{ marginTop: 12 }}>
        <div className="metricCard">
          <div className="muted">Validation</div>
          <strong>{String(validation?.ok ?? false) === "true" ? "Pass" : "Needs review"}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Issues</div>
          <strong>{issueCount}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Sources</div>
          <strong>{sourceCount}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Warnings</div>
          <strong>{manifestWarnings.length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Imports</div>
          <strong>{imports.length}</strong>
        </div>
      </div>

      <h3>DICOM metadata preflight</h3>
      <div className="formGrid">
        <label>
          DICOM root
          <input value={dicomPath} onChange={(event) => setDicomPath(event.target.value)} />
        </label>
        <label>
          Max files sampled
          <input
            type="number"
            min={1}
            max={10000}
            value={dicomMaxFiles}
            onChange={(event) => setDicomMaxFiles(Math.max(1, Number(event.target.value) || 1))}
          />
        </label>
        <label>
          DICOM report
          <input readOnly value={dicomReportPath || "Not generated yet"} />
        </label>
        <label>
          DICOM JSON
          <input readOnly value={dicomJsonPath || "Not generated yet"} />
        </label>
      </div>
      <div className="row">
        <button onClick={runDicomMetadataPreflight} disabled={dicomBusy}>
          {dicomBusy ? "Checking DICOM..." : "Run DICOM preflight"}
        </button>
        <button
          onClick={() => void openArtifact(dicomReportPath, "DICOM preflight report")}
          disabled={!dicomReportPath}
        >
          Open DICOM report
        </button>
        <button
          onClick={() => void openArtifact(dicomJsonPath, "DICOM preflight JSON")}
          disabled={!dicomJsonPath}
        >
          Open DICOM JSON
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
          <div className="muted">Preflight</div>
          <strong>{Boolean(dicomPreflight?.ok) ? "Pass" : "Needs review"}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Subjects</div>
          <strong>{stringList(dicomPreflight?.subjects).length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Modalities</div>
          <strong>{stringList(dicomPreflight?.modalities).join(", ") || "-"}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Warnings</div>
          <strong>{dicomWarnings.length}</strong>
        </div>
        <div className="metricCard">
          <div className="muted">Errors</div>
          <strong>{dicomErrors.length}</strong>
        </div>
      </div>
      {dicomSafetyFlags ? (
        <div className="metricGrid" style={{ marginTop: 8 }}>
          {Object.entries(dicomSafetyFlags).map(([key, value]) => (
            <div className="metricCard" key={key}>
              <div className="muted">{key}</div>
              <strong>{Boolean(value) ? "Yes" : "No"}</strong>
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
        <div className="empty">No DICOM series metadata loaded yet</div>
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
      <h3>DICOM preflight report</h3>
      <TextViewer text={dicomReportText || "No DICOM preflight report loaded"} maxHeight="260px" />
      <h3>DICOM preflight payload</h3>
      <JsonBlock value={dicomPreflight} emptyText="No DICOM preflight loaded" />

      <h3>Imported paths</h3>
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
        <div className="empty">No imported paths recorded for this project</div>
      )}

      <h3>Validation issues</h3>
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
        <div className="empty">No validation issues found</div>
      )}

      {manifestWarnings.length ? (
        <>
          <h3>Manifest warnings</h3>
          <div style={{ display: "grid", gap: 6 }}>
            {manifestWarnings.map((warning, index) => (
              <div key={`${warning}-${index}`} className="errorBox">
                {warning}
              </div>
            ))}
          </div>
        </>
      ) : null}

      <h3>Validation report</h3>
      <TextViewer text={reportText || "No validation report text loaded"} maxHeight="300px" />
      <h3>Validation payload</h3>
      <JsonBlock value={validation} emptyText="No validation report loaded" />
      <h3>Manifest payload</h3>
      <JsonBlock value={manifest} emptyText="No manifest loaded" />
      <h3>Import history payload</h3>
      <JsonBlock value={importHistory} emptyText="No import history loaded" />
      <h3>Handoff package payload</h3>
      {safetyFlags ? (
        <div className="metricGrid" style={{ marginTop: 8 }}>
          {Object.entries(safetyFlags).map(([key, value]) => (
            <div className="metricCard" key={key}>
              <div className="muted">{key}</div>
              <strong>{value ? "Yes" : "No"}</strong>
            </div>
          ))}
        </div>
      ) : null}
      <div className="row">
        <button
          onClick={() => void openArtifact(packageJsonPath, "handoff JSON")}
          disabled={!packageJsonPath}
        >
          Open handoff JSON
        </button>
      </div>
      <JsonBlock value={handoffPackage} emptyText="No handoff package generated in this session" />
      <h3>Verify result</h3>
      <JsonBlock value={verifyResult} emptyText="No package verification run in this session" />
    </div>
  );
}
