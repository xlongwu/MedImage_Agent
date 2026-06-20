import { useState } from "react";
import { runProjectDicomConversionExecute } from "../lib/api/legacy";
import type {
  DicomConversionExecutionUiState,
  DicomConversionPublicExecutionResponse,
  DicomConversionPublicExecutionSafetyFlags,
  DicomConversionReleaseReadinessReport,
} from "../types";
import styles from "./DicomConversionExecutePanel.module.css";

type Props = {
  baseUrl: string;
  projectId: string;
  conversionRunId: string;
  readiness: DicomConversionReleaseReadinessReport | null;
};

const CONFIRMATIONS: { key: string; label: string }[] = [
  { key: "confirm_research_use_only", label: "I understand this is for research use only." },
  { key: "confirm_no_clinical_use", label: "I understand this is not for clinical use." },
  { key: "confirm_rawdata_readonly", label: "I confirm rawdata must remain read-only." },
  { key: "confirm_rollback_available", label: "I confirm rollback is available." },
  { key: "confirm_disk_space_checked", label: "I confirm disk space was checked." },
  { key: "confirm_public_execution_risk", label: "I confirm public DICOM conversion risks." },
  {
    key: "confirm_spm_disabled",
    label: "I understand SPM/DPABI/MATLAB preprocessing is not part of this action.",
  },
  { key: "confirm_dicom_only", label: "I understand this only runs DICOM-to-NIfTI conversion." },
];

const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};
const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

export default function DicomConversionExecutePanel({
  baseUrl,
  projectId,
  conversionRunId,
  readiness,
}: Props) {
  const featureEnabled = import.meta.env.VITE_ENABLE_DICOM_EXECUTE_UI === "1";

  const [uiState, setUiState] = useState<DicomConversionExecutionUiState>(
    featureEnabled ? "disabled_info" : "hidden",
  );
  const [confirmChecks, setConfirmChecks] = useState<Record<string, boolean>>({});
  const [response, setResponse] = useState<DicomConversionPublicExecutionResponse | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Determine if readiness allows execution
  const readinessReady = readiness?.status === "ready_for_human_release_review";
  const gatesFull = readiness != null && readiness.gates_met >= readiness.gates_total;

  // Show the confirm button only when readiness passes
  const canShowConfirm = featureEnabled && readinessReady && gatesFull;

  function toggleConfirm(key: string) {
    setConfirmChecks((prev) => ({ ...prev, [key]: !prev[key] }));
  }

  const allConfirmed = CONFIRMATIONS.every((c) => confirmChecks[c.key] === true);

  async function handleExecute() {
    if (!allConfirmed || submitting) return;
    setSubmitting(true);
    setUiState("submitting");
    setError("");
    setResponse(null);

    try {
      const body: Record<string, unknown> = {
        conversion_run_id: conversionRunId,
        release_approval_id: `frontend-${Date.now()}`,
        confirm_user_data_conversion: confirmChecks.confirm_dicom_only ?? false,
        confirm_rawdata_readonly: confirmChecks.confirm_rawdata_readonly ?? false,
        confirm_research_use_only: confirmChecks.confirm_research_use_only ?? false,
        confirm_no_clinical_use: confirmChecks.confirm_no_clinical_use ?? false,
        confirm_rollback_available: confirmChecks.confirm_rollback_available ?? false,
        confirm_disk_space_checked: confirmChecks.confirm_disk_space_checked ?? false,
        confirm_public_execution_risk: confirmChecks.confirm_public_execution_risk ?? false,
        requested_by: "operator",
        reason: "Research DICOM-to-NIfTI conversion via frontend execute UI",
        dry_run_first: true,
        rollback_mode_on_failure: "quarantine",
      };

      const resp = (await runProjectDicomConversionExecute(
        baseUrl,
        projectId,
        body,
      )) as DicomConversionPublicExecutionResponse;

      setResponse(resp);
      if (resp.ok && resp.status === "succeeded") {
        setUiState("succeeded");
      } else if (resp.status === "partial") {
        setUiState("partial");
      } else if (resp.status === "blocked" || resp.status === "disabled") {
        setUiState("blocked");
      } else {
        setUiState("failed");
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setUiState("failed");
    } finally {
      setSubmitting(false);
    }
  }

  // ── Hidden state ──
  if (uiState === "hidden") {
    return null;
  }

  // ── Disabled info state ──
  if (
    uiState === "disabled_info" ||
    (!canShowConfirm &&
      uiState !== "submitting" &&
      uiState !== "succeeded" &&
      uiState !== "partial" &&
      uiState !== "failed" &&
      uiState !== "blocked")
  ) {
    const missing: string[] = [];
    if (!featureEnabled)
      missing.push("Frontend feature flag VITE_ENABLE_DICOM_EXECUTE_UI is not set.");
    if (!readinessReady) missing.push("Release readiness is not ready_for_human_release_review.");
    if (!gatesFull)
      missing.push(`Safety gates: ${readiness?.gates_met ?? 0}/${readiness?.gates_total ?? 32}.`);

    return (
      <section className={styles.style001}>
        <h3 className={styles.style002}>DICOM Conversion Execution</h3>
        <div className={styles.style003}>
          <strong>DICOM conversion execution UI is disabled in this build.</strong> Conversion
          execution requires maintainer release approval, runtime flags, release readiness, and
          operator confirmations.
        </div>
        {missing.length > 0 && (
          <div className={styles.style004}>
            <h4 className={styles.style005}>Blocking conditions</h4>
            {missing.map((m, i) => (
              <div key={i} className={styles.style006}>
                {m}
              </div>
            ))}
          </div>
        )}
        {canShowConfirm && (
          <button
            onClick={() => setUiState("confirming")}
            style={{
              padding: "8px 18px",
              background: "#1976d2",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 13,
            }}
          >
            Approve and request conversion
          </button>
        )}
      </section>
    );
  }

  // ── Blocked response ──
  if (uiState === "blocked") {
    const safety = response?.safety_flags as DicomConversionPublicExecutionSafetyFlags | undefined;
    return (
      <section className={styles.style007}>
        <h3 className={styles.style008}>Conversion blocked</h3>
        <div className={styles.style009}>
          The backend blocked this conversion request. Review the blocking issues below.
        </div>
        {(response?.blocking_issues ?? []).map((b, i) => (
          <div key={i} className={styles.style010}>
            {b}
          </div>
        ))}
        {safety && (
          <div className={styles.style011}>
            {Object.entries(safety).map(([k, v]) => (
              <span
                key={k}
                style={{
                  ...pill,
                  background: v ? "#e8f5e9" : "#ffebee",
                  color: v ? "#176b3b" : "#b53b3b",
                  borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
                }}
              >
                {k.replace(/_/g, " ")}: {String(v)}
              </span>
            ))}
          </div>
        )}
        <button
          onClick={() => {
            setUiState("disabled_info");
            setResponse(null);
            setConfirmChecks({});
          }}
          style={{
            marginTop: 12,
            padding: "6px 14px",
            background: "#1976d2",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          Back to readiness
        </button>
      </section>
    );
  }

  // ── Failed response ──
  if (uiState === "failed") {
    return (
      <section className={styles.style012}>
        <h3 className={styles.style013}>Conversion failed</h3>
        {error && <div className={styles.style014}>{error}</div>}
        {(response?.errors ?? []).map((e, i) => (
          <div key={i} className={styles.style015}>
            {e}
          </div>
        ))}
        {response?.warnings && response.warnings.length > 0 && (
          <div className={styles.style016}>
            {response.warnings.map((w, i) => (
              <div key={i} className={styles.style017}>
                {w}
              </div>
            ))}
          </div>
        )}
        {response?.rollback_result_path && (
          <div className={styles.style018}>
            <strong className={styles.style019}>Rollback result:</strong>{" "}
            <span style={mono}>{response.rollback_result_path}</span>
          </div>
        )}
        <div className={styles.style020}>
          Rawdata remains unchanged. Review the rollback evidence above before retrying.
        </div>
        <button
          onClick={() => {
            setUiState("disabled_info");
            setResponse(null);
            setConfirmChecks({});
          }}
          style={{
            marginTop: 12,
            padding: "6px 14px",
            background: "#1976d2",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 11,
          }}
        >
          Back to readiness
        </button>
      </section>
    );
  }

  // ── Submitting / progress ──
  if (uiState === "submitting") {
    return (
      <section className={styles.style021}>
        <h3 className={styles.style022}>Converting DICOM to NIfTI...</h3>
        <div className={styles.style023}>
          The backend is executing dcm2niix. This may take several minutes for large datasets. Do
          not close this page.
        </div>
        <div className={styles.style024}>
          <div className={styles.style025}>
            <div className={styles.style026} />
          </div>
        </div>
        <div className={styles.style027}>
          Status: {response?.status ?? "requesting execution..."}
        </div>
      </section>
    );
  }

  // ── Succeeded / Partial response ──
  if ((uiState === "succeeded" || uiState === "partial") && response) {
    return (
      <section className={styles.style028}>
        <h3 className={styles.style029}>
          {uiState === "partial" ? "Conversion partially completed" : "Conversion complete"}
        </h3>
        <div className={styles.style030}>
          <KV label="status" value={response.status} />
          {response.execution_id && <KV label="execution ID" value={response.execution_id} />}
          {response.started_at && <KV label="started" value={response.started_at} />}
          {response.finished_at && <KV label="finished" value={response.finished_at} />}
          {response.checksum_verified !== undefined && (
            <KV label="checksum verified" value={String(response.checksum_verified)} />
          )}
          {response.output_root && <KV label="output root" value={response.output_root} />}
        </div>

        {uiState === "partial" && (
          <div className={styles.style031} style={{ background: "#fff3e0", color: "#8d6300" }}>
            Some mappings completed successfully while others failed. Rawdata remains unchanged.
            Review errors below and retry failed mappings.
          </div>
        )}

        {(response as any).mapping_results && (response as any).mapping_results.length > 0 && (
          <div className={styles.style004}>
            <h4 className={styles.style005}>Mapping Results</h4>
            {(response as any).mapping_results.map((mr: any, i: number) => (
              <div
                key={i}
                className={styles.style006}
                style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}
              >
                <span>
                  <strong>
                    {mr.subject_id}/{mr.modality}
                  </strong>
                  : {mr.status}
                </span>
                {mr.error && <span style={{ color: "#b53b3b", fontSize: 11 }}>{mr.error}</span>}
                {mr.output_file && (
                  <span style={{ ...mono, fontSize: 10, color: "#555" }}>{mr.output_file}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {response.output_manifest_path && (
          <PathRow label="Output manifest" path={response.output_manifest_path} />
        )}
        {response.execution_provenance_path && (
          <PathRow label="Execution provenance" path={response.execution_provenance_path} />
        )}
        {response.audit_execution_start_path && (
          <PathRow label="Audit start" path={response.audit_execution_start_path} />
        )}
        {response.audit_execution_final_path && (
          <PathRow label="Audit final" path={response.audit_execution_final_path} />
        )}
        {response.checksum_comparison_path && (
          <PathRow label="Checksum comparison" path={response.checksum_comparison_path} />
        )}
        {response.rollback_plan_path && (
          <PathRow label="Rollback plan" path={response.rollback_plan_path} />
        )}
        {response.manifest_path && (
          <PathRow label="Conversion manifest" path={response.manifest_path} />
        )}
        {response.provenance_path && <PathRow label="Provenance" path={response.provenance_path} />}

        <div className={styles.style031}>
          Rawdata checksum verified — rawdata is unchanged. SPM/DPABI/MATLAB were not executed.
        </div>
        <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
          <button
            onClick={() => {
              setUiState("disabled_info");
              setResponse(null);
              setConfirmChecks({});
            }}
            style={{
              padding: "6px 14px",
              background: "#1976d2",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 11,
            }}
          >
            Back to readiness
          </button>
        </div>
      </section>
    );
  }

  // ── Confirmation dialog ──
  return (
    <section className={styles.style032}>
      <h3 className={styles.style033}>
        <span role="img" aria-label="warning" className={styles.style034}>
          &#9888;
        </span>
        Approve &amp; Execute DICOM Conversion
      </h3>
      <div className={styles.style035}>
        You are about to execute DICOM-to-NIfTI conversion using dcm2niix. This is a one-way
        operation. Confirm each statement below before proceeding.
      </div>

      {CONFIRMATIONS.map((c) => (
        <label key={c.key} className={styles.style036}>
          <input
            type="checkbox"
            checked={confirmChecks[c.key] ?? false}
            onChange={() => toggleConfirm(c.key)}
          />
          {c.label}
        </label>
      ))}

      <div className={styles.style037}>
        <button
          onClick={() => {
            setUiState("disabled_info");
            setConfirmChecks({});
          }}
          style={{
            padding: "8px 18px",
            background: "#667085",
            color: "#fff",
            border: "none",
            borderRadius: 4,
            cursor: "pointer",
            fontWeight: 600,
            fontSize: 12,
          }}
        >
          Cancel
        </button>
        <button
          onClick={handleExecute}
          disabled={!allConfirmed || submitting}
          style={{
            padding: "8px 18px",
            background: allConfirmed ? "#4caf50" : "#ccc",
            color: allConfirmed ? "#fff" : "#98a2b3",
            border: "none",
            borderRadius: 4,
            cursor: allConfirmed ? "pointer" : "not-allowed",
            fontWeight: 600,
            fontSize: 12,
          }}
        >
          {submitting ? "Submitting..." : "Approve and request conversion"}
        </button>
      </div>

      <div className={styles.style038}>
        MedImage Agent is for research use only. It is not for clinical use or medical
        decision-making. Rawdata remains read-only. SPM/DPABI/MATLAB are not executed. Full
        preprocessing is not triggered.
      </div>
    </section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div className={styles.style039}>
      <div className={styles.style040}>{label}</div>
      <div className={styles.style041}>{value || "—"}</div>
    </div>
  );
}

function PathRow({ label, path }: { label: string; path: string }) {
  return (
    <div className={styles.style042}>
      <span className={styles.style043}>{label}:</span>{" "}
      <span className={styles.style044}>{path}</span>
    </div>
  );
}
