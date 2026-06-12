import { useState } from "react";
import { runProjectDicomConversionExecute } from "../api";
import type {
  DicomConversionExecutionUiState,
  DicomConversionPublicExecutionResponse,
  DicomConversionPublicExecutionSafetyFlags,
  DicomConversionReleaseReadinessReport,
} from "../types";

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
  { key: "confirm_spm_disabled", label: "I understand SPM/DPABI/MATLAB preprocessing is not part of this action." },
  { key: "confirm_dicom_only", label: "I understand this only runs DICOM-to-NIfTI conversion." },
];

const pill: React.CSSProperties = {
  display: "inline-flex", alignItems: "center", minHeight: 22,
  padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900,
};
const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 11, overflowWrap: "anywhere",
};

export default function DicomConversionExecutePanel({ baseUrl, projectId, conversionRunId, readiness }: Props) {
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
    setConfirmChecks(prev => ({ ...prev, [key]: !prev[key] }));
  }

  const allConfirmed = CONFIRMATIONS.every(c => confirmChecks[c.key] === true);

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
        baseUrl, projectId, body,
      )) as DicomConversionPublicExecutionResponse;

      setResponse(resp);
      if (resp.ok && resp.status === "succeeded") {
        setUiState("succeeded");
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
  if (uiState === "disabled_info" || (!canShowConfirm && uiState !== "submitting" && uiState !== "succeeded" && uiState !== "failed" && uiState !== "blocked")) {
    const missing: string[] = [];
    if (!featureEnabled) missing.push("Frontend feature flag VITE_ENABLE_DICOM_EXECUTE_UI is not set.");
    if (!readinessReady) missing.push("Release readiness is not ready_for_human_release_review.");
    if (!gatesFull) missing.push(`Safety gates: ${readiness?.gates_met ?? 0}/${readiness?.gates_total ?? 32}.`);

    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 12 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>DICOM Conversion Execution</h3>
        <div style={{ padding: 10, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 12, lineHeight: 1.5 }}>
          <strong>DICOM conversion execution UI is disabled in this build.</strong>{" "}
          Conversion execution requires maintainer release approval, runtime flags, release readiness, and operator confirmations.
        </div>
        {missing.length > 0 && (
          <div style={{ marginBottom: 12 }}>
            <h4 style={{ margin: "0 0 6px", fontSize: 13, color: "#b53b3b" }}>Blocking conditions</h4>
            {missing.map((m, i) => (
              <div key={i} style={{ padding: "4px 8px", border: "1px solid rgba(235, 87, 87, 0.22)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#b53b3b", marginBottom: 3 }}>{m}</div>
            ))}
          </div>
        )}
        {canShowConfirm && (
          <button
            onClick={() => setUiState("confirming")}
            style={{ padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 13 }}
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
      <section style={{ padding: 16, border: "1px solid rgba(235, 87, 87, 0.26)", borderRadius: 8, background: "rgba(255, 245, 245, 0.88)", marginTop: 12 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15, color: "#b53b3b" }}>Conversion blocked</h3>
        <div style={{ fontSize: 11, color: "#b53b3b", marginBottom: 10 }}>
          The backend blocked this conversion request. Review the blocking issues below.
        </div>
        {(response?.blocking_issues ?? []).map((b, i) => (
          <div key={i} style={{ padding: "4px 8px", border: "1px solid rgba(235, 87, 87, 0.22)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#b53b3b", marginBottom: 3 }}>{b}</div>
        ))}
        {safety && (
          <div style={{ marginTop: 10, display: "flex", gap: 4, flexWrap: "wrap" }}>
            {Object.entries(safety).map(([k, v]) => (
              <span key={k} style={{ ...pill, background: v ? "#e8f5e9" : "#ffebee", color: v ? "#176b3b" : "#b53b3b", borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)" }}>
                {k.replace(/_/g, " ")}: {String(v)}
              </span>
            ))}
          </div>
        )}
        <button onClick={() => { setUiState("disabled_info"); setResponse(null); setConfirmChecks({}); }} style={{ marginTop: 12, padding: "6px 14px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
          Back to readiness
        </button>
      </section>
    );
  }

  // ── Failed response ──
  if (uiState === "failed") {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(235, 87, 87, 0.26)", borderRadius: 8, background: "rgba(255, 245, 245, 0.88)", marginTop: 12 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15, color: "#b53b3b" }}>Conversion failed</h3>
        {error && <div style={{ padding: 8, border: "1px solid rgba(235, 87, 87, 0.22)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#b53b3b", marginBottom: 8 }}>{error}</div>}
        {(response?.errors ?? []).map((e, i) => (
          <div key={i} style={{ padding: "4px 8px", border: "1px solid rgba(235, 87, 87, 0.22)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#b53b3b", marginBottom: 3 }}>{e}</div>
        ))}
        {response?.warnings && response.warnings.length > 0 && (
          <div style={{ marginTop: 8 }}>
            {response.warnings.map((w, i) => (
              <div key={i} style={{ padding: "4px 8px", border: "1px solid rgba(242, 153, 74, 0.18)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#9a5a15", marginBottom: 3 }}>{w}</div>
            ))}
          </div>
        )}
        {response?.rollback_result_path && (
          <div style={{ marginTop: 8, fontSize: 11 }}>
            <strong style={{ color: "#667085" }}>Rollback result:</strong>{" "}
            <span style={mono}>{response.rollback_result_path}</span>
          </div>
        )}
        <div style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.18)", borderRadius: 4, background: "#f9f9fb", fontSize: 11, color: "#667085", marginTop: 8 }}>
          Rawdata remains unchanged. Review the rollback evidence above before retrying.
        </div>
        <button onClick={() => { setUiState("disabled_info"); setResponse(null); setConfirmChecks({}); }} style={{ marginTop: 12, padding: "6px 14px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
          Back to readiness
        </button>
      </section>
    );
  }

  // ── Submitting / progress ──
  if (uiState === "submitting") {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(56, 103, 214, 0.22)", borderRadius: 8, background: "rgba(239, 246, 255, 0.88)", marginTop: 12 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15, color: "#2450a6" }}>Converting DICOM to NIfTI...</h3>
        <div style={{ fontSize: 12, color: "#667085" }}>
          The backend is executing dcm2niix. This may take several minutes for large datasets.
          Do not close this page.
        </div>
        <div style={{ marginTop: 10 }}>
          <div style={{ height: 4, background: "#e3e8f0", borderRadius: 2, overflow: "hidden" }}>
            <div style={{ height: "100%", width: "60%", background: "#1976d2", borderRadius: 2, animation: "pulse 1.5s infinite" }} />
          </div>
        </div>
        <div style={{ marginTop: 8, fontSize: 11, color: "#667085" }}>
          Status: {response?.status ?? "requesting execution..."}
        </div>
      </section>
    );
  }

  // ── Succeeded response ──
  if (uiState === "succeeded" && response) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(33, 150, 83, 0.24)", borderRadius: 8, background: "rgba(245, 255, 248, 0.88)", marginTop: 12 }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15, color: "#176b3b" }}>Conversion complete</h3>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))", gap: 8, marginBottom: 12 }}>
          <KV label="status" value={response.status} />
          <KV label="execution ID" value={response.execution_id} />
          <KV label="started" value={response.started_at ?? ""} />
          <KV label="finished" value={response.finished_at ?? ""} />
          <KV label="checksum verified" value={String(response.checksum_verified)} />
          <KV label="output root" value={response.output_root} />
        </div>

        {response.output_manifest_path && <PathRow label="Output manifest" path={response.output_manifest_path} />}
        {response.execution_provenance_path && <PathRow label="Execution provenance" path={response.execution_provenance_path} />}
        {response.audit_execution_start_path && <PathRow label="Audit start" path={response.audit_execution_start_path} />}
        {response.audit_execution_final_path && <PathRow label="Audit final" path={response.audit_execution_final_path} />}
        {response.checksum_comparison_path && <PathRow label="Checksum comparison" path={response.checksum_comparison_path} />}
        {response.rollback_plan_path && <PathRow label="Rollback plan" path={response.rollback_plan_path} />}

        <div style={{ padding: 8, border: "1px solid rgba(33, 150, 83, 0.18)", borderRadius: 4, background: "#fff", fontSize: 11, color: "#176b3b", marginTop: 10 }}>
          Rawdata checksum verified — rawdata is unchanged. SPM/DPABI/MATLAB were not executed.
        </div>
        <button onClick={() => { setUiState("disabled_info"); setResponse(null); setConfirmChecks({}); }} style={{ marginTop: 12, padding: "6px 14px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
          Back to readiness
        </button>
      </section>
    );
  }

  // ── Confirmation dialog ──
  return (
    <section style={{ padding: 16, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 8, background: "rgba(255, 251, 242, 0.94)", marginTop: 12 }}>
      <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>
        <span role="img" aria-label="warning" style={{ marginRight: 6 }}>&#9888;</span>
        Approve &amp; Execute DICOM Conversion
      </h3>
      <div style={{ fontSize: 11, color: "#9a5a15", marginBottom: 12, lineHeight: 1.5 }}>
        You are about to execute DICOM-to-NIfTI conversion using dcm2niix.
        This is a one-way operation. Confirm each statement below before proceeding.
      </div>

      {CONFIRMATIONS.map(c => (
        <label key={c.key} style={{ display: "flex", gap: 8, alignItems: "center", padding: "6px 8px", marginBottom: 4, border: "1px solid rgba(137, 150, 171, 0.18)", borderRadius: 4, background: "#fff", cursor: "pointer", fontSize: 12 }}>
          <input
            type="checkbox"
            checked={confirmChecks[c.key] ?? false}
            onChange={() => toggleConfirm(c.key)}
          />
          {c.label}
        </label>
      ))}

      <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
        <button
          onClick={() => { setUiState("disabled_info"); setConfirmChecks({}); }}
          style={{ padding: "8px 18px", background: "#667085", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 12 }}
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
            border: "none", borderRadius: 4,
            cursor: allConfirmed ? "pointer" : "not-allowed",
            fontWeight: 600, fontSize: 12,
          }}
        >
          {submitting ? "Submitting..." : "Approve and request conversion"}
        </button>
      </div>

      <div style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.18)", borderRadius: 4, background: "#f9f9fb", fontSize: 10, color: "#667085", marginTop: 12, lineHeight: 1.4 }}>
        MedImage Agent is for research use only. It is not for clinical use or medical decision-making.
        Rawdata remains read-only. SPM/DPABI/MATLAB are not executed. Full preprocessing is not triggered.
      </div>
    </section>
  );
}

function KV({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ padding: "6px 8px", border: "1px solid rgba(137, 150, 171, 0.2)", borderRadius: 4, background: "#fff", fontSize: 11 }}>
      <div style={{ color: "#667085", fontWeight: 700 }}>{label}</div>
      <div style={{ fontFamily: "monospace", overflowWrap: "anywhere" }}>{value || "—"}</div>
    </div>
  );
}

function PathRow({ label, path }: { label: string; path: string }) {
  return (
    <div style={{ padding: "4px 8px", border: "1px solid rgba(137, 150, 171, 0.14)", borderRadius: 4, background: "#fff", fontSize: 11, marginBottom: 3 }}>
      <span style={{ color: "#667085", fontWeight: 600 }}>{label}:</span>{" "}
      <span style={{ fontFamily: "monospace", fontSize: 10, color: "#888" }}>{path}</span>
    </div>
  );
}
