import { useState } from "react";
import type { DicomConversionReleaseReadinessReport } from "../types";

type Props = {
  readiness: DicomConversionReleaseReadinessReport | null;
  loading: boolean;
  error: string;
  onRefresh: () => void;
};

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
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };

const statusColors: Record<string, React.CSSProperties> = {
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  ready_internal: {
    background: "#e8f5e9",
    color: "#176b3b",
    borderColor: "rgba(33, 150, 83, 0.24)",
  },
  ready_for_human_release_review: {
    background: "#e3f2fd",
    color: "#0d47a1",
    borderColor: "rgba(25, 118, 210, 0.28)",
  },
};

export default function DicomConversionReleaseReadinessPanel({
  readiness,
  loading,
  error,
  onRefresh,
}: Props) {
  return (
    <section
      style={{
        padding: 16,
        border: "1px solid rgba(137, 150, 171, 0.28)",
        borderRadius: 8,
        background: "rgba(255, 255, 255, 0.88)",
        marginTop: 12,
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 10,
          marginBottom: 12,
        }}
      >
        <div>
          <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>Release Readiness</h3>
          <span style={{ color: "#667085", fontSize: 12 }}>
            Read-only evaluation — does not run conversion.
          </span>
        </div>
        {readiness && (
          <span
            style={{
              ...pill,
              ...(statusColors[readiness.status] || {
                background: "#eef1f6",
                color: "#667085",
                borderColor: "rgba(137, 150, 171, 0.28)",
              }),
            }}
          >
            {readiness.status.replace(/_/g, " ").toUpperCase()}
          </span>
        )}
      </div>

      {/* Safety callout */}
      <div
        style={{
          padding: 10,
          border: "1px solid rgba(242, 153, 74, 0.28)",
          borderRadius: 6,
          background: "rgba(255, 251, 242, 0.94)",
          fontSize: 11,
          color: "#9a5a15",
          marginBottom: 12,
          lineHeight: 1.5,
        }}
      >
        <strong>This panel is read-only. It does not run conversion.</strong> Public DICOM
        conversion remains disabled until final human release approval.
      </div>

      {loading && (
        <div className="empty" style={{ marginBottom: 12 }}>
          Checking release readiness...
        </div>
      )}
      {error && (
        <div className="errorBox" style={{ marginBottom: 10, fontSize: 11 }}>
          {error}
        </div>
      )}

      {!readiness && !loading && !error && (
        <div className="empty" style={{ marginBottom: 12 }}>
          Loading release readiness data...
        </div>
      )}

      {readiness && (
        <>
          {/* A. Release readiness summary */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>Summary</h4>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap: 8,
              }}
            >
              <M label="gates" value={`${readiness.gates_met}/${readiness.gates_total}`} />
              <M label="gate status" value={readiness.gate_status} />
              <M
                label="human approval required"
                value={String(readiness.human_release_approval_required)}
              />
              <M
                label="public endpoint"
                value={readiness.public_endpoint_enabled ? "ENABLED ⚠" : "disabled"}
              />
              <M
                label="frontend execute"
                value={readiness.frontend_execute_enabled ? "ENABLED ⚠" : "disabled"}
              />
              <M
                label="full preprocessing"
                value={readiness.full_preprocessing_enabled ? "ENABLED ⚠" : "disabled"}
              />
            </div>
          </div>

          {/* B. Disk-space check */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>Disk Space</h4>
            <div style={{ fontSize: 11, color: "#667085", marginBottom: 4 }}>
              output root:{" "}
              <span style={{ fontFamily: "monospace" }}>
                {readiness.disk_space.output_root || "(not set)"}
              </span>
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
                gap: 8,
              }}
            >
              <M label="free" value={_fmtBytes(readiness.disk_space.free_bytes)} />
              <M
                label="estimated required"
                value={_fmtBytes(readiness.disk_space.estimated_required_bytes)}
              />
              <M label="multiplier" value={`×${readiness.disk_space.required_multiplier}`} />
              <M label="ok" value={String(readiness.disk_space.ok)} />
            </div>
            {readiness.disk_space.warnings.map((w, i) => (
              <div key={i} style={{ fontSize: 10, color: "#9a5a15" }}>
                {w}
              </div>
            ))}
            {readiness.disk_space.errors.map((e, i) => (
              <div key={i} style={{ fontSize: 10, color: "#b53b3b" }}>
                {e}
              </div>
            ))}
          </div>

          {/* C. Runtime policy */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>Runtime Policy</h4>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(120px, 1fr))",
                gap: 8,
              }}
            >
              <M
                label="timeout (per subj)"
                value={`${readiness.runtime_policy.timeout_seconds}s`}
              />
              <M
                label="cancellation"
                value={
                  readiness.runtime_policy.cancellation_supported ? "supported" : "unsupported"
                }
              />
              <M
                label="resume"
                value={readiness.runtime_policy.resume_supported ? "supported" : "unsupported"}
              />
              <M
                label="retry"
                value={readiness.runtime_policy.retry_supported ? "supported" : "unsupported"}
              />
              <M label="max subjects" value={readiness.runtime_policy.max_subjects_per_run} />
            </div>
            {readiness.runtime_policy.warnings.map((w, i) => (
              <div key={i} style={{ fontSize: 10, color: "#9a5a15" }}>
                {w}
              </div>
            ))}
          </div>

          {/* D. Safety invariants */}
          <div style={{ marginBottom: 12 }}>
            <h4 style={subH}>Safety Invariants</h4>
            <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
              <Badge label="public endpoint absent" ok={!readiness.public_endpoint_enabled} />
              <Badge label="frontend execute absent" ok={!readiness.frontend_execute_enabled} />
              <Badge label="SPM/DPABI/MATLAB disabled" ok={!readiness.spm_dpabi_matlab_enabled} />
              <Badge
                label="full preprocessing disabled"
                ok={!readiness.full_preprocessing_enabled}
              />
              <Badge label="rollback ready" ok={readiness.rollback_ready} />
              <Badge label="approval/audit ready" ok={readiness.approval_audit_ready} />
              <Badge label="rawdata read-only" ok={true} />
              <Badge
                label="human approval required"
                ok={readiness.human_release_approval_required}
              />
            </div>
          </div>

          {/* E. Release blockers/warnings */}
          {(readiness.blocking_issues.length > 0 || readiness.warnings.length > 0) && (
            <div style={{ marginBottom: 12 }}>
              {readiness.blocking_issues.length > 0 && (
                <>
                  <h4 style={{ ...subH, color: "#b53b3b" }}>
                    Blockers ({readiness.blocking_issues.length})
                  </h4>
                  {readiness.blocking_issues.map((b, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "4px 8px",
                        border: "1px solid rgba(235, 87, 87, 0.22)",
                        borderRadius: 4,
                        background: "#fff",
                        fontSize: 11,
                        color: "#b53b3b",
                        marginBottom: 3,
                      }}
                    >
                      {b}
                    </div>
                  ))}
                </>
              )}
              {readiness.warnings.length > 0 && (
                <>
                  <h4 style={{ ...subH, color: "#9a5a15", marginTop: 8 }}>
                    Warnings ({readiness.warnings.length})
                  </h4>
                  {readiness.warnings.map((w, i) => (
                    <div
                      key={i}
                      style={{
                        padding: "4px 8px",
                        border: "1px solid rgba(242, 153, 74, 0.18)",
                        borderRadius: 4,
                        background: "#fff",
                        fontSize: 11,
                        color: "#9a5a15",
                        marginBottom: 3,
                      }}
                    >
                      {w}
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </>
      )}

      {/* Refresh button */}
      <div style={{ marginTop: 8 }}>
        <button
          onClick={onRefresh}
          disabled={loading}
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
          {loading ? "Checking..." : "Check release readiness"}
        </button>
      </div>
    </section>
  );
}

function M({ label, value }: { label: string; value: number | string }) {
  return (
    <div
      style={{
        padding: "8px 10px",
        border: "1px solid rgba(137, 150, 171, 0.24)",
        borderRadius: 6,
        background: "#fff",
        display: "grid",
        gap: 2,
        color: "#667085",
        fontSize: 11,
        fontWeight: 850,
      }}
    >
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function Badge({ label, ok }: { label: string; ok: boolean }) {
  return (
    <span
      style={{
        ...pill,
        background: ok ? "#e8f5e9" : "#ffebee",
        color: ok ? "#176b3b" : "#b53b3b",
        borderColor: ok ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
      }}
    >
      {label}: {ok ? "✓" : "✗"}
    </span>
  );
}

function _fmtBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(1)} GB`;
  if (bytes >= 1_048_576) return `${(bytes / 1_048_576).toFixed(1)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}
