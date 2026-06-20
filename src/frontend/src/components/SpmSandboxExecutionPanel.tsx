import { useState } from "react";
import type { SpmSandboxExecutionResponse, StageOutputRegistrationResponse } from "../types";
type RegResponse = StageOutputRegistrationResponse;

type Props = {
  projectId: string;
  preprocessingRunId: string;
  dryRunId: string;
};

const pill = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
} as const;

export default function SpmSandboxExecutionPanel({
  projectId,
  preprocessingRunId,
  dryRunId,
}: Props) {
  const enabled = import.meta.env.VITE_ENABLE_SPM_SANDBOX_EXECUTION_UI === "1";
  const [result, setResult] = useState<SpmSandboxExecutionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [checks, setChecks] = useState<boolean[]>([
    false,
    false,
    false,
    false,
    false,
    false,
    false,
  ]);
  const [regResult, setRegResult] = useState<RegResponse | null>(null);
  const [regLoading, setRegLoading] = useState(false);

  if (!enabled) return null;

  const allChecked = checks.every(Boolean);

  async function handleExecute() {
    if (!allChecked) return;
    setLoading(true);
    setError("");
    setResult(null);
    try {
      const { executeSpmSandboxSliceTimingRealign } = await import("../lib/api/legacy");
      const res = await executeSpmSandboxSliceTimingRealign("", projectId, preprocessingRunId, {
        dry_run_id: dryRunId,
        confirm_sandbox_copy: true,
        confirm_no_rawdata_modification: true,
        confirm_slice_timing_realign_only: true,
        confirm_no_full_preprocessing: true,
        confirm_research_use_only: true,
      });
      setResult(res as SpmSandboxExecutionResponse);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleRegister() {
    if (!result?.execution_id) return;
    setRegLoading(true);
    setRegResult(null);
    try {
      const { registerSandboxSpmOutputs } = await import("../lib/api/legacy");
      const res = await registerSandboxSpmOutputs("", projectId, preprocessingRunId, {
        execution_id: result.execution_id,
        confirm_sandbox_outputs: true,
        confirm_rawdata_readonly: true,
        confirm_converted_input_readonly: true,
        confirm_no_additional_execution: true,
        confirm_use_as_next_stage_input: true,
      });
      setRegResult(res as RegResponse);
    } catch (e) {
      /* ignore */
    } finally {
      setRegLoading(false);
    }
  }

  const confirmLabels = [
    "I understand execution uses copied sandbox inputs only.",
    "I confirm rawdata will not be modified.",
    "I confirm original converted_bids inputs will not be modified.",
    "I understand this runs Slice Timing + Realign only.",
    "I understand this is not full preprocessing.",
    "I understand this is for research use only.",
    "I understand this is not for clinical use.",
  ];

  return (
    <section
      style={{
        padding: 16,
        border: "1px solid rgba(137,150,171,0.28)",
        borderRadius: 8,
        background: "rgba(255,255,255,0.88)",
        marginTop: 12,
      }}
    >
      <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>Sandbox Slice Timing + Realign</h3>
      <span style={{ color: "#667085", fontSize: 12 }}>
        Run: {preprocessingRunId} · Dry-run: {dryRunId} · Sandbox only · Full preprocessing disabled
        · DPABI disabled
      </span>

      <div
        style={{
          padding: 8,
          border: "1px solid rgba(242,153,74,0.22)",
          borderRadius: 4,
          background: "rgba(255,251,242,0.94)",
          fontSize: 11,
          color: "#9a5a15",
          margin: "8px 0",
        }}
      >
        This action runs Slice Timing + Realign only on copied sandbox inputs. Rawdata and original
        converted_bids inputs are not modified.
      </div>

      {/* Confirmations */}
      <div style={{ display: "grid", gap: 3, marginBottom: 8 }}>
        {confirmLabels.map((label, i) => (
          <label
            key={i}
            style={{
              display: "flex",
              gap: 6,
              alignItems: "center",
              fontSize: 11,
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              checked={checks[i]}
              onChange={() => {
                const c = [...checks];
                c[i] = !c[i];
                setChecks(c);
              }}
            />
            {label}
          </label>
        ))}
      </div>

      <button
        onClick={handleExecute}
        disabled={!allChecked || loading}
        style={{
          padding: "6px 14px",
          background: allChecked ? "#1976d2" : "#ccc",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: allChecked ? "pointer" : "not-allowed",
          fontWeight: 600,
          fontSize: 11,
        }}
      >
        {loading ? "Executing..." : "Run Slice Timing + Realign in sandbox"}
      </button>

      {error && (
        <div className="errorBox" style={{ fontSize: 11, marginTop: 6 }}>
          {error}
        </div>
      )}

      {result && (
        <div
          style={{
            marginTop: 8,
            padding: 8,
            border: `1px solid ${result.ok ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)"}`,
            borderRadius: 4,
            background: result.ok ? "rgba(232,245,233,0.88)" : "rgba(255,235,238,0.88)",
            fontSize: 11,
          }}
        >
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Status: {result.status}</div>
          <div style={{ display: "grid", gap: 1 }}>
            <div>exec: {result.execution_id}</div>
            <div>dir: {result.execution_dir}</div>
            <div>sandbox input: {result.sandbox_input_dir}</div>
            <div>sandbox output: {result.sandbox_output_dir}</div>
            <div>
              subjects: {result.subjects_succeeded}/{result.subjects_total}
            </div>
            <div>stdout: {result.stdout_log_path}</div>
            <div>stderr: {result.stderr_log_path}</div>
          </div>
          {result.blocking_issues?.map((b: string, i: number) => (
            <div key={i} style={{ color: "#b53b3b" }}>
              {b}
            </div>
          ))}
          {result.warnings?.map((w: string, i: number) => (
            <div key={i} style={{ color: "#9a5a15" }}>
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Register sandbox outputs button */}
      {result?.ok && (
        <div style={{ marginTop: 8 }}>
          <button
            onClick={handleRegister}
            disabled={regLoading}
            style={{
              padding: "6px 14px",
              background: "#4caf50",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 600,
              fontSize: 11,
            }}
          >
            {regLoading ? "Registering..." : "Register sandbox outputs for next stage"}
          </button>
          {regResult && (
            <div
              style={{
                marginTop: 6,
                padding: 8,
                border: "1px solid rgba(33,150,83,0.24)",
                borderRadius: 4,
                background: "rgba(232,245,233,0.88)",
                fontSize: 11,
              }}
            >
              <div style={{ fontWeight: 700 }}>
                Registered: {regResult.registered_stage_output_id}
              </div>
              <div>next-stage input: {regResult.next_stage_input_dir}</div>
              <div>
                subjects: {regResult.subject_count} | BOLD outputs:{" "}
                {regResult.registered_bold_outputs?.length || 0}
              </div>
              {regResult.warnings?.map((w: string, i: number) => (
                <div key={i} style={{ color: "#9a5a15" }}>
                  {w}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}
