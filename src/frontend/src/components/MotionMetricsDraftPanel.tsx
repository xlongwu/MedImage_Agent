import { useRef, useState } from "react";
import { DEFAULT_API_BASE, generateMotionMetricsDraft } from "../api";
import type { MotionMetricsDraftResponse } from "../types";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};
const pill: React.CSSProperties = { display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900 };

export default function MotionMetricsDraftPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<MotionMetricsDraftResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMd, setShowMd] = useState(false);
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    try {
      const r = await generateMotionMetricsDraft(effectiveBase, projectId);
      if (id === reqRef.current) setData(r);
    } catch (e) { if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (id === reqRef.current) setLoading(false); }
  }

  if (!projectId) return <Sec><H3>Motion Metrics Draft</H3><div className="empty">Select a project.</div></Sec>;
  if (error) return <Sec><H3>Motion Metrics Draft</H3><div className="errorBox">{error}</div></Sec>;

  return (
    <Sec>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><H3>Motion Metrics Draft</H3><Sub>QC summary from motion parameters / confounds.</Sub></div>
        {data && <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>}
      </div>
      <div style={{ padding: 8, border: "1px solid rgba(242, 153, 74, 0.28)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 12 }}>
        QC summary only. No realignment is executed.
      </div>

      <button onClick={handleGenerate} disabled={loading} style={{ marginBottom: 12, padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
        {loading ? "Generating..." : "Generate Motion Metrics Draft"}
      </button>

      {data && (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(80px, 1fr))", gap: 8, marginBottom: 12 }}>
            <M label="candidates" value={data.candidate_count} />
            <M label="parsed" value={data.parsed_count} />
            <M label="FD avail" value={data.fd_available_count} />
          </div>
          {data.summaries.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Summaries</h4>
              <div style={{ display: "grid", gap: 6 }}>
                {data.summaries.slice(0, 10).map((s, i) => (
                  <div key={i} style={{ padding: 8, border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff", display: "grid", gap: 4 }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center", fontSize: 11 }}>
                      {s.subject_id && <strong>{s.subject_id}</strong>}
                      <span style={{ ...pill, background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" }}>{s.source_type}</span>
                      <span>{s.row_count} rows</span>
                      <span style={{ ...pill, background: s.has_fd ? "#e8f5e9" : "#fff7ed", color: s.has_fd ? "#176b3b" : "#9a5a15", borderColor: s.has_fd ? "rgba(33, 150, 83, 0.24)" : "rgba(242, 153, 74, 0.28)" }}>FD: {String(s.has_fd)}</span>
                      {s.fd_mean != null && <span>FD mean: {s.fd_mean.toFixed(3)}</span>}
                      {s.fd_max != null && <span>max: {s.fd_max.toFixed(3)}</span>}
                      {s.max_abs_translation_mm != null && <span>max trans: {s.max_abs_translation_mm.toFixed(2)}mm</span>}
                    </div>
                    {s.qc_flags.length > 0 && <div style={{ color: "#b53b3b", fontSize: 11 }}>{s.qc_flags.join("; ")}</div>}
                  </div>
                ))}
              </div>
            </div>
          )}
          {data.warnings.length > 0 && <Warn items={data.warnings} />}
          {data.report_markdown && (
            <div>
              <button onClick={() => setShowMd(!showMd)} style={{ marginBottom: 8, fontWeight: 600 }}>{showMd ? "Hide" : "Show"} Markdown Preview</button>
              {showMd && <pre style={{ padding: 12, border: "1px solid rgba(137, 150, 171, 0.24)", borderRadius: 6, background: "#fff", fontSize: 11, maxHeight: 360, overflow: "auto", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{data.report_markdown}</pre>}
            </div>
          )}
        </>
      )}
    </Sec>
  );
}

function Warn({ items }: { items: string[] }) { return <div style={{ marginBottom: 10, padding: 8, border: "1px solid rgba(242, 153, 74, 0.24)", borderRadius: 6, background: "rgba(255, 251, 242, 0.94)", color: "#9a5a15", fontSize: 12 }}>{items.slice(0, 5).map((w,i)=><div key={i}>{w}</div>)}</div>; }
function M({ label, value }: { label: string; value: number }) { return <div style={{ padding: "8px 10px", border: "1px solid rgba(137, 150, 171, 0.24)", borderRadius: 6, background: "#fff", display: "grid", gap: 2, color: "#667085", fontSize: 11, fontWeight: 850 }}><span>{label}</span><strong>{value}</strong></div>; }

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)", marginTop: 4 }}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>;
