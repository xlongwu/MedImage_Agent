import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getPipelinePreset, instantiatePipelinePreset } from "../api";
import { buildPresetPlanDraft } from "../lib/presetPlanHandoff";
import type { PipelinePreset, PipelinePresetInstantiateResponse, PresetPlanDraft } from "../types";

type Props = {
  baseUrl?: string;
  projectId: string | null;
  onReviewDraft?: (draft: PresetPlanDraft) => void;
};

const pill: React.CSSProperties = { display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900 };

export default function RsfmriPresetPanel({ baseUrl, projectId, onReviewDraft }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [preset, setPreset] = useState<PipelinePreset | null>(null);
  const [result, setResult] = useState<PipelinePresetInstantiateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [instLoading, setInstLoading] = useState(false);
  const [error, setError] = useState("");
  const reqRef = useRef(0);

  useEffect(() => {
    if (!projectId) { setPreset(null); setResult(null); return; }
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    getPipelinePreset(effectiveBase, "rsfmri_preproc_mvp")
      .then((r) => { if (id === reqRef.current) setPreset(r.preset); })
      .catch((e) => { if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e)); })
      .finally(() => { if (id === reqRef.current) setLoading(false); });
  }, [effectiveBase, projectId]);

  async function handleInstantiate() {
    if (!projectId) return;
    setInstLoading(true); setError("");
    try {
      const r = await instantiatePipelinePreset(effectiveBase, projectId, "rsfmri_preproc_mvp");
      setResult(r);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setInstLoading(false); }
  }

  if (!projectId) return <Sec><H3>rs-fMRI Preprocessing Preset</H3><div className="empty">Select a project.</div></Sec>;
  if (loading) return <Sec><H3>rs-fMRI Preprocessing Preset</H3><div className="empty">Loading preset...</div></Sec>;
  if (error) return <Sec><H3>rs-fMRI Preprocessing Preset</H3><div className="errorBox">{error}</div></Sec>;
  if (!preset) return null;

  return (
    <Sec>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><H3>{preset.name}</H3><Sub>{preset.modality} · v{preset.version}</Sub></div>
      </div>
      <div style={{ padding: 8, border: "1px solid rgba(235, 87, 87, 0.18)", borderRadius: 6, background: "rgba(255, 245, 245, 0.92)", fontSize: 11, color: "#b53b3b", marginBottom: 12 }}>
        This preset is a contract MVP for planning only. It does not execute real SPM/DPABI preprocessing. Real MATLAB/SPM execution is not available in this release. Research-use only. Not for clinical diagnosis.
      </div>
      <p style={{ fontSize: 12, color: "#344054", margin: "0 0 12px" }}>{preset.description}</p>

      <h4 style={subH}>Nodes ({preset.nodes.length})</h4>
      <div style={{ display: "grid", gap: 6, marginBottom: 12 }}>
        {preset.nodes.map((n) => (
          <div key={n.id} style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff", display: "grid", gap: 4 }}>
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
              <strong style={{ fontSize: 12 }}>{n.name}</strong>
              <span style={{ ...pill, background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" }}>{n.backend}</span>
              <span style={{ ...pill, background: n.executable ? "#e8f5e9" : "#fff7ed", color: n.executable ? "#176b3b" : "#9a5a15", borderColor: n.executable ? "rgba(33, 150, 83, 0.24)" : "rgba(242, 153, 74, 0.28)" }}>{n.executable ? "executable" : "stub"}</span>
            </div>
            <div style={{ fontSize: 11, color: "#667085" }}>{n.description}</div>
          </div>
        ))}
      </div>

      {preset.readiness_requirements.length > 0 && (
        <div style={{ marginBottom: 12 }}><h4 style={subH}>Readiness Requirements</h4><ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#344054" }}>{preset.readiness_requirements.map((r, i) => <li key={i}>{r}</li>)}</ul></div>
      )}
      {preset.non_goals.length > 0 && (
        <div style={{ marginBottom: 12 }}><h4 style={subH}>Non-Goals</h4><ul style={{ margin: 0, paddingLeft: 18, fontSize: 12, color: "#667085" }}>{preset.non_goals.map((g, i) => <li key={i}>{g}</li>)}</ul></div>
      )}

      <button onClick={handleInstantiate} disabled={instLoading} style={{ marginBottom: 12, padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
        {instLoading ? "Instantiating..." : "Instantiate reviewed plan draft"}
      </button>

      {result && (
        <div style={{ border: `1px solid ${result.ok ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.24)"}`, borderRadius: 6, padding: 12, marginBottom: 12 }}>
          <span style={{ ...pill, background: result.ok ? "#e8f5e9" : "#ffebee", color: result.ok ? "#176b3b" : "#b53b3b", borderColor: result.ok ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)" }}>{result.ok ? "Instantiated" : "Failed"}</span>
          {result.errors.length > 0 && <div className="errorBox" style={{ marginTop: 8 }}>{result.errors.join("\n")}</div>}
          {result.warnings.length > 0 && <div style={{ marginTop: 8, padding: 6, background: "rgba(255, 251, 242, 0.94)", color: "#9a5a15", fontSize: 11 }}>{result.warnings.join("\n")}</div>}
          {result.next_actions.length > 0 && (
            <div style={{ marginTop: 8 }}><strong style={{ fontSize: 12 }}>Next:</strong><ul style={{ margin: "4px 0 0", paddingLeft: 18, fontSize: 12 }}>{result.next_actions.map((a, i) => <li key={i}>{a}</li>)}</ul></div>
          )}
          {result.ok && (
            <>
              <pre style={{ marginTop: 8, padding: 8, background: "#f5f5f5", borderRadius: 4, fontSize: 11, maxHeight: 200, overflow: "auto", whiteSpace: "pre-wrap" }}>{JSON.stringify(result.plan, null, 2)}</pre>
              {onReviewDraft && projectId && (
                <button
                  onClick={() => onReviewDraft(buildPresetPlanDraft(projectId, result))}
                  style={{ marginTop: 8, padding: "8px 18px", background: "#6a1b9a", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}
                >
                  Review this plan in Plan Review Console
                </button>
              )}
            </>
          )}
        </div>
      )}
    </Sec>
  );
}

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 4 }}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>;
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };
