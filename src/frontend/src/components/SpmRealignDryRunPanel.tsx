import { useRef, useState } from "react";
import { DEFAULT_API_BASE, runSpmRealignDryRun } from "../api";
import type { SpmRealignDryRunResponse } from "../types";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};
const pill: React.CSSProperties = { display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900 };
const mono: React.CSSProperties = { fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 10, overflowWrap: "anywhere" };

export default function SpmRealignDryRunPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<SpmRealignDryRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    try {
      const r = await runSpmRealignDryRun(effectiveBase, projectId);
      if (id === reqRef.current) setData(r);
    } catch (e) { if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (id === reqRef.current) setLoading(false); }
  }

  if (!projectId) return <Sec><H3>SPM Realign Dry-Run</H3><div className="empty">Select a project.</div></Sec>;
  if (error) return <Sec><H3>SPM Realign Dry-Run</H3><div className="errorBox">{error}</div></Sec>;

  return (
    <Sec>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><H3>SPM Realign Dry-Run</H3><Sub>Predict output paths and manifest without MATLAB execution.</Sub></div>
        {data && <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>}
      </div>
      <div style={{ padding: 8, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 12 }}>
        Dry-run only. MATLAB/SPM is not executed. No files or directories are created. Predicted output paths are previews, not real outputs. Research-use only. Not for clinical use.
      </div>

      <button onClick={handleGenerate} disabled={loading} style={{ marginBottom: 12, padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
        {loading ? "Generating..." : "Generate Dry-Run Manifest"}
      </button>

      {data && (
        <>
          <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
            <span style={{ ...pill, background: data.execution_enabled ? "#e8f5e9" : "#ffebee", color: data.execution_enabled ? "#176b3b" : "#b53b3b", borderColor: data.execution_enabled ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)" }}>exec: {String(data.execution_enabled)}</span>
            <span style={{ ...pill, background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242,153,74,0.28)" }}>approval: {String(data.approval_required)}</span>
            <span style={{ ...pill, background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242,153,74,0.28)" }}>audit: {String(data.audit_required)}</span>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(90px, 1fr))", gap: 8, marginBottom: 12 }}>
            <M label="inputs" value={data.input_count} />
            <M label="ready" value={data.ready_input_count} />
            <M label="env" value={data.environment_status ?? "?"} />
          </div>

          {data.output_root_preview && <div style={{ ...mono, marginBottom: 8 }}>output: {data.output_root_preview}</div>}
          {data.blocking_issues.length > 0 && <div className="errorBox" style={{ marginBottom: 8 }}>{data.blocking_issues.join("\n")}</div>}
          {data.param_errors.length > 0 && <div className="errorBox" style={{ marginBottom: 8 }}>{data.param_errors.join("\n")}</div>}

          {data.inputs.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>BOLD Inputs</h4>
              <div style={{ display: "grid", gap: 6 }}>
                {data.inputs.map((inp, i) => {
                  const key = inp.subject_id ?? `inp-${i}`;
                  return (
                    <div key={key} style={{ padding: 8, border: "1px solid rgba(137,150,171,0.22)", borderRadius: 6, background: "#fff", display: "grid", gap: 4 }}>
                      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", fontSize: 11 }}>
                        {inp.subject_id && <strong>{inp.subject_id}</strong>}
                        <span style={{ ...pill, background: inp.valid_for_realign ? "#e8f5e9" : "#ffebee", color: inp.valid_for_realign ? "#176b3b" : "#b53b3b", borderColor: inp.valid_for_realign ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)" }}>{inp.valid_for_realign ? "valid" : "invalid"}</span>
                        <span>{inp.volume_count ?? "?"} vols</span>
                        <span>{inp.predicted_outputs.length} outputs</span>
                      </div>
                      <div style={mono}>{inp.bold_path}</div>
                      <button onClick={() => setExpanded((p) => { const n = new Set(p); n.has(key) ? n.delete(key) : n.add(key); return n; })} style={{ fontSize: 11, fontWeight: 600 }}>{expanded.has(key) ? "Hide" : "Show"} outputs</button>
                      {expanded.has(key) && (
                        <div style={{ display: "grid", gap: 3, marginTop: 4 }}>
                          {inp.predicted_outputs.map((o, j) => (
                            <div key={j} style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 10 }}>
                              <span style={{ ...pill, background: o.exists ? "#fff7ed" : "#eef1f6", color: o.exists ? "#9a5a15" : "#667085", borderColor: "rgba(137,150,171,0.28)" }}>{o.kind}</span>
                              {o.would_overwrite && <span style={{ color: "#b53b3b" }}>⚠</span>}
                              <span style={mono}>{o.path}</span>
                            </div>
                          ))}
                        </div>
                      )}
                      {inp.warnings.length > 0 && <Warn items={inp.warnings} />}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {data.warnings.length > 0 && <Warn items={data.warnings} />}
          {data.next_actions.length > 0 && (
            <div>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Next Actions</h4>
              <div style={{ display: "grid", gap: 5 }}>{data.next_actions.map((a, i) => <div key={i} style={{ padding: "6px 10px", border: "1px solid rgba(56,103,214,0.22)", borderRadius: 6, background: "rgba(239,246,255,0.82)", color: "#2450a6", fontSize: 12 }}>{i + 1}. {a}</div>)}</div>
            </div>
          )}
        </>
      )}
    </Sec>
  );
}

function Warn({ items }: { items: string[] }) { return <div style={{ marginTop: 4, padding: 6, border: "1px solid rgba(242,153,74,0.24)", borderRadius: 4, background: "rgba(255,251,242,0.94)", color: "#9a5a15", fontSize: 11 }}>{items.slice(0, 3).map((w,i)=><div key={i}>{w}</div>)}</div>; }
function M({ label, value }: { label: string; value: number | string }) { return <div style={{ padding: "8px 10px", border: "1px solid rgba(137,150,171,0.24)", borderRadius: 6, background: "#fff", display: "grid", gap: 2, color: "#667085", fontSize: 11, fontWeight: 850 }}><span>{label}</span><strong>{value}</strong></div>; }

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => <section style={{ padding: 16, border: "1px solid rgba(137,150,171,0.28)", borderRadius: 8, background: "rgba(255,255,255,0.88)", marginTop: 4 }}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>;
