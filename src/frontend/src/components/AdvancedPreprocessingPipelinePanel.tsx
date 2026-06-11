import { useState } from "react";
import { DEFAULT_API_BASE } from "../api";

type Props = { projectId: string; preprocessingRunId: string };

type StageInfo = { stage_id: string; name: string; dry_run: boolean; executed: boolean; registered: boolean; metadata_only: boolean; status: string };
type PipelineValidation = { ok: boolean; status: string; project_id: string; preprocessing_run_id: string; stage_summary: StageInfo[]; completed_stages: string[]; dry_run_only_stages: string[]; sandbox_executed_stages: string[]; registered_outputs: string[]; metadata_only_stages: string[]; blocked_stages: string[]; warnings: string[]; errors: string[]; next_actions: string[]; safety_flags: Record<string, boolean> };
type PipelineReport = { ok: boolean; status: string; report_id: string; report_path: string; summary: string; stage_statuses: Record<string,unknown>[]; registered_outputs: Record<string,unknown>[]; warnings: string[]; safety_flags: Record<string, boolean> };

const stageNames: Record<string, string> = {
  slice_timing_realign: "Slice Timing + Realign",
  coreg_norm: "Coregistration + Normalization",
  smoothing: "Smoothing",
  nuisance_regression: "Nuisance Regression",
  temporal_filtering: "Temporal Filtering",
  alff_reho: "ALFF/ReHo",
  functional_connectivity: "Functional Connectivity",
};

const badge = (s: string) => {
  const colors: Record<string, string> = { ready_for_review: "#176b3b", warning: "#9a5a15", blocked: "#b53b3b", not_started: "#667085", loading: "#1976d2" };
  return { background: colors[s] || "#667085", color: "#fff", padding: "2px 8px", borderRadius: 999, fontSize: 10, fontWeight: 700, display: "inline-block" };
};

const flagChip = (k: string, v: boolean) => (
  <span key={k} style={{ display: "inline-block", padding: "2px 8px", borderRadius: 999, fontSize: 10, marginRight: 4, marginBottom: 2, background: v ? "#e8f5e9" : "#ffebee", color: v ? "#176b3b" : "#b53b3b", border: `1px solid ${v ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)"}` }}>
    {k.replace(/_/g, " ")}: {String(v)}
  </span>
);

export default function AdvancedPreprocessingPipelinePanel({ projectId, preprocessingRunId }: Props) {
  const [valResult, setValResult] = useState<PipelineValidation | null>(null);
  const [valLoading, setValLoading] = useState(false);
  const [valError, setValError] = useState("");
  const [repResult, setRepResult] = useState<PipelineReport | null>(null);
  const [repLoading, setRepLoading] = useState(false);

  async function handleValidation() {
    setValLoading(true); setValError(""); setValResult(null);
    try {
      const { getPreprocessingPipelineValidation } = await import("../api");
      const res = await getPreprocessingPipelineValidation(DEFAULT_API_BASE, projectId, preprocessingRunId);
      setValResult(res as PipelineValidation);
    } catch (e: any) { setValError(e?.message || String(e)); }
    finally { setValLoading(false); }
  }

  async function handleReport() {
    setRepLoading(true); setRepResult(null);
    try {
      const { getPreprocessingPipelineReport } = await import("../api");
      const res = await getPreprocessingPipelineReport(DEFAULT_API_BASE, projectId, preprocessingRunId);
      setRepResult(res as PipelineReport);
    } catch (e) { /* ignore */ }
    finally { setRepLoading(false); }
  }

  return (
    <section style={{ padding: 16, border: "1px solid rgba(137,150,171,0.28)", borderRadius: 8, background: "rgba(255,255,255,0.88)", marginTop: 12 }}>
      <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>Preprocessing Pipeline Validation</h3>
      <span style={{ color: "#667085", fontSize: 12 }}>Check pipeline status, inspect stage summaries, and export reports.</span>

      <div style={{ padding: 8, border: "1px solid rgba(242,153,74,0.22)", borderRadius: 4, background: "rgba(255,251,242,0.94)", fontSize: 11, color: "#9a5a15", margin: "8px 0" }}>
        This is a metadata-only dashboard. No preprocessing is executed. Rawdata, converted_bids, and sandbox outputs remain unchanged.
      </div>

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <button onClick={handleValidation} disabled={valLoading}
          style={{ padding: "6px 14px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
          {valLoading ? "Checking..." : "Check pipeline validation"}
        </button>
        {valResult?.status === "ready_for_review" && (
          <button onClick={handleReport} disabled={repLoading}
            style={{ padding: "6px 14px", background: "#4caf50", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 11 }}>
            {repLoading ? "Exporting..." : "Export preprocessing pipeline report"}
          </button>
        )}
      </div>

      {valError && <div className="errorBox" style={{ fontSize: 11, marginBottom: 6 }}>{valError}</div>}

      {valResult && (
        <div style={{ marginBottom: 10, padding: 8, border: "1px solid rgba(137,150,171,0.18)", borderRadius: 4, background: "#f9f9fb", fontSize: 11 }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>
            Status: <span style={badge(valResult.status)}>{valResult.status}</span>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(60px, 1fr))", gap: 4, marginBottom: 4 }}>
            <M label="Stages" value={valResult.stage_summary.length} />
            <M label="Dry-run only" value={valResult.dry_run_only_stages.length} />
            <M label="Sandbox exec" value={valResult.sandbox_executed_stages.length} />
            <M label="Registered" value={valResult.registered_outputs.length} />
            <M label="Metadata-only" value={valResult.metadata_only_stages.length} />
          </div>

          {valResult.stage_summary.length > 0 && (
            <div style={{ display: "grid", gap: 2, marginBottom: 4, maxHeight: 180, overflow: "auto" }}>
              {valResult.stage_summary.map((s, i) => (
                <div key={i} style={{ display: "flex", gap: 4, alignItems: "center", padding: "2px 6px", border: "1px solid rgba(137,150,171,0.14)", borderRadius: 3, background: "#fff" }}>
                  <span style={{ flex: 1, fontWeight: 600 }}>{s.name}</span>
                  <span style={{ fontSize: 9, color: s.executed ? "#176b3b" : s.dry_run ? "#1976d2" : "#667085" }}>{s.dry_run ? "DR" : ""}{s.executed ? (s.metadata_only ? " EX(mo)" : " EX") : ""}{s.registered ? " REG" : ""}</span>
                </div>
              ))}
            </div>
          )}

          {valResult.warnings.length > 0 && (
            <div style={{ marginBottom: 4, maxHeight: 60, overflow: "auto" }}>
              {valResult.warnings.map((w: string, i: number) => <div key={i} style={{ color: "#9a5a15" }}>{w}</div>)}
            </div>
          )}

          <div style={{ display: "flex", flexWrap: "wrap", gap: 2, marginTop: 4 }}>
            {Object.entries(valResult.safety_flags).map(([k, v]) => flagChip(k, v as boolean))}
          </div>
        </div>
      )}

      {repResult && (
        <div style={{ padding: 8, border: "1px solid rgba(33,150,83,0.24)", borderRadius: 4, background: "rgba(232,245,233,0.88)", fontSize: 11 }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>Report: {repResult.report_id}</div>
          <div>path: {repResult.report_path}</div>
          <div style={{ color: "#667085", marginTop: 4 }}>{repResult.summary}</div>
          {repResult.warnings?.map((w: string, i: number) => <div key={i} style={{ color: "#9a5a15" }}>{w}</div>)}
        </div>
      )}
    </section>
  );
}

function M({ label, value }: { label: string; value: number }) {
  return <div style={{ padding: "4px 6px", border: "1px solid rgba(137,150,171,0.20)", borderRadius: 3, background: "#fff", fontSize: 10, fontWeight: 800, color: "#667085" }}><span>{label}</span><strong style={{ color: "#333" }}>{value}</strong></div>;
}
