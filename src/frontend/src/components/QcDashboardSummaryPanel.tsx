import { useRef, useState } from "react";
import { DEFAULT_API_BASE, generateQcDashboardReport, getLatestQcDashboardReport, getQcDashboardFingerprint } from "../api";
import type { QcDashboardFingerprintResponse } from "../types";
import type { QcDashboardReportResponse } from "../types";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33,150,83,0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242,153,74,0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235,87,87,0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137,150,171,0.28)" },
  not_run: { background: "#f5f5f5", color: "#999", borderColor: "rgba(137,150,171,0.28)" },
};
const pill: React.CSSProperties = { display: "inline-flex", alignItems: "center", minHeight: 22, padding: "0 7px", border: "1px solid", borderRadius: 999, fontSize: 10, fontWeight: 900 };
const mono: React.CSSProperties = { fontFamily: '"Cascadia Mono","Consolas",monospace', fontSize: 10, overflowWrap: "anywhere" };

export default function QcDashboardSummaryPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<QcDashboardReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMd, setShowMd] = useState(false);
  const [cacheMode, setCacheMode] = useState<"off" | "prefer" | "refresh">("off");
  const [fpData, setFpData] = useState<QcDashboardFingerprintResponse | null>(null);
  const [fpLoading, setFpLoading] = useState(false);
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    try {
      const d = await generateQcDashboardReport(effectiveBase, projectId, { cacheMode });
      if (id === reqRef.current) setData(d);
    } catch (e) { if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e)); }
    finally { if (id === reqRef.current) setLoading(false); }
  }

  async function handleLoadLatest() {
    if (!projectId) return;
    const id = reqRef.current + 1; reqRef.current = id;
    setLoading(true); setError("");
    try {
      const d = await getLatestQcDashboardReport(effectiveBase, projectId);
      if (id === reqRef.current) setData(d);
    } catch (e) {
      if (id === reqRef.current) {
        const msg = e instanceof Error ? e.message : String(e);
        if (msg.includes("404") || msg.includes("not been generated")) {
          setError("No saved QC Dashboard report exists yet. Generate one first.");
        } else {
          setError(msg);
        }
      }
    }
    finally { if (id === reqRef.current) setLoading(false); }
  }

  if (!projectId) return <Sec><H3>QC Dashboard Report</H3><div className="empty">Select a project.</div></Sec>;
  if (error) return <Sec><H3>QC Dashboard Report</H3><div className="errorBox">{error}</div></Sec>;

  return (
    <Sec>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div><H3>QC Dashboard Report</H3><Sub>Aggregate summary of all QC checks. No preprocessing is executed.</Sub></div>
        {data && <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>}
      </div>
      <div style={{ padding: 8, border: "1px solid rgba(242,153,74,0.28)", borderRadius: 6, background: "rgba(255,251,242,0.94)", fontSize: 11, color: "#9a5a15", marginBottom: 12 }}>
        Dashboard report only. No preprocessing is executed. Rawdata is not modified.
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={handleGenerate} disabled={loading} style={{ padding: "8px 18px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
          {loading ? "Generating..." : "Generate Dashboard Report"}
        </button>
        <button onClick={handleLoadLatest} disabled={loading} style={{ padding: "8px 18px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer", fontWeight: 600 }}>
          Load Latest
        </button>
        <select value={cacheMode} onChange={(e) => setCacheMode(e.target.value as "off" | "prefer" | "refresh")}
          style={{ padding: "6px 10px", borderRadius: 3, border: "1px solid #ccc", fontSize: 12 }}>
          <option value="off">off</option>
          <option value="prefer">prefer</option>
          <option value="refresh">refresh</option>
        </select>
        <button onClick={async () => {
          if (!projectId) return;
          setFpLoading(true);
          try { setFpData(await getQcDashboardFingerprint(effectiveBase, projectId)); }
          catch { setFpData(null); }
          finally { setFpLoading(false); }
        }} disabled={fpLoading}
          style={{ padding: "6px 12px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer", fontWeight: 600, fontSize: 12 }}>
          {fpLoading ? "..." : "Inspect Fingerprint"}
        </button>
      </div>

      {data && (
        <>
          {/* Cache indicator */}
          {data.cache && (
            <div style={{ marginBottom: 8, padding: 8, border: "1px solid rgba(137,150,171,0.18)", borderRadius: 6, background: "rgba(249,249,251,0.9)", fontSize: 11 }}>
              <div style={{ color: "#667085", marginBottom: data.cache.module_records?.length ? 4 : 0 }}>
                Cache: <b>{data.cache.mode}</b>
                {data.cache.mode !== "off" && ` · modules: ${Object.values(data.cache.module_hits ?? {}).filter(Boolean).length}/${Object.keys(data.cache.module_hits ?? {}).length || Object.keys(data.cache.module_records ?? []).length || 1}`}
              </div>
              {/* Module-level cache records */}
              {data.cache.module_records?.length ? (
                <div style={{ display: "grid", gap: 3 }}>
                  {data.cache.module_records.map((r, i) => {
                    const statusColors: Record<string, string> = {
                      hit: "#176b3b", miss: "#667085", stale: "#9a5a15",
                      disabled: "#999", error: "#b53b3b",
                    };
                    return (
                      <div key={i} style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                        <span style={{ fontWeight: 600 }}>{r.module_id}</span>
                        <span style={{ ...pill, background: r.status === "hit" ? "#e8f5e9" : r.status === "stale" ? "#fff7ed" : r.status === "error" ? "#ffebee" : "#eef1f6", color: statusColors[r.status] || "#667085", borderColor: "rgba(137,150,171,0.28)" }}>{r.status}</span>
                        {r.hit && <span style={{ color: "#176b3b" }}>✓ hit</span>}
                        {r.stale && <span style={{ color: "#9a5a15" }}>⚠ stale</span>}
                        {r.module_version && <span style={{ color: "#999", fontSize: 9 }}>v{r.module_version}</span>}
                        {r.warnings.length > 0 && <span style={{ color: "#9a5a15", fontSize: 10 }}>⚠{r.warnings.length}</span>}
                        {r.errors.length > 0 && <span style={{ color: "#b53b3b", fontSize: 10 }}>✗{r.errors.length}</span>}
                      </div>
                    );
                  })}
                </div>
              ) : null}
              {data.cache.mode !== "off" && (
                <div style={{ fontSize: 9, color: "#999", marginTop: 4 }}>
                  Module cache currently applies only to NIfTI QC Snapshot. Other modules run normally.
                </div>
              )}
              {(data.cache.cache_warnings?.length ?? 0) > 0 && (
                <div style={{ color: "#9a5a15", marginTop: 2 }}>⚠ {data.cache.cache_warnings![0].slice(0, 80)}</div>
              )}
            </div>
          )}

          {fpData && (
            <div style={{ marginBottom: 12, padding: 8, border: "1px solid rgba(137,150,171,0.22)", borderRadius: 6, background: "rgba(249,249,251,0.9)", fontSize: 11 }}>
              <div style={{ fontWeight: 700, marginBottom: 4 }}>Rawdata Fingerprint</div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 3, color: "#667085" }}>
                <span><b>hash:</b> {fpData.fingerprint.fingerprint?.slice(0, 12) ?? "—"}</span>
                <span><b>files:</b> {fpData.fingerprint.file_count}</span>
                <span><b>size:</b> {fpData.fingerprint.total_size_bytes}</span>
                <span><b>mtime:</b> {fpData.fingerprint.newest_mtime_iso ?? "—"}</span>
                <span><b>trunc:</b> {String(fpData.fingerprint.truncated)}</span>
              </div>
              <div style={{ fontSize: 10, color: "#9a5a15", marginTop: 4 }}>
                Fingerprint is metadata-only and used for future cache invalidation. No cache is created in this release.
              </div>
            </div>
          )}

          {/* Counts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(70px, 1fr))", gap: 8, marginBottom: 12 }}>
            <M label="ready" value={data.ready_count} color="#176b3b" />
            <M label="warning" value={data.warning_count} color="#9a5a15" />
            <M label="blocked" value={data.blocked_count} color="#b53b3b" />
            <M label="unknown" value={data.unknown_count} color="#667085" />
          </div>

          {/* Module cards */}
          {data.modules.length > 0 && (
            <div style={{ marginBottom: 12 }}>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Modules ({data.modules.length})</h4>
              <div style={{ display: "grid", gap: 6, maxHeight: 360, overflow: "auto" }}>
                {data.modules.map((m) => (
                  <div key={m.module_id} style={{ padding: "8px 10px", border: "1px solid rgba(137,150,171,0.22)", borderRadius: 6, background: "#fff", display: "grid", gap: 4, fontSize: 11 }}>
                    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                      <strong>{m.name}</strong>
                      <span style={{ ...pill, ...statusBadge[m.status] }}>{m.status}</span>
                      <span style={{ color: "#667085" }}>{m.summary?.slice(0, 80)}</span>
                    </div>
                    {Object.keys(m.key_metrics).length > 0 && (
                      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", color: "#667085", fontSize: 10 }}>
                        {Object.entries(m.key_metrics).slice(0, 6).map(([k, v]) => (
                          <span key={k}>{k}: <b>{v == null ? "—" : String(v)}</b></span>
                        ))}
                      </div>
                    )}
                    <div style={{ display: "flex", gap: 8 }}>
                      {m.warnings.length > 0 && <span style={{ color: "#9a5a15" }}>⚠{m.warnings.length}</span>}
                      {m.errors.length > 0 && <span style={{ color: "#b53b3b" }}>✗{m.errors.length}</span>}
                      {m.next_actions.length > 0 && <span style={{ color: "#2450a6" }}>→ {m.next_actions[0].slice(0, 60)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Artifacts */}
          {data.artifacts.length > 0 && (
            <div style={{ marginBottom: 12, fontSize: 11 }}>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Report Artifacts</h4>
              {data.artifacts.map((a, i) => (
                <div key={i} style={mono}>
                  [{a.kind}] {a.path} {a.size_bytes != null ? `(${a.size_bytes} B)` : ""}
                </div>
              ))}
            </div>
          )}

          {/* Markdown preview */}
          {data.report_markdown && (
            <div style={{ marginBottom: 12 }}>
              <button onClick={() => setShowMd(!showMd)} style={{ fontWeight: 600 }}>{showMd ? "Hide" : "Show"} Markdown Preview</button>
              {showMd && <pre style={{ marginTop: 8, padding: 12, border: "1px solid rgba(137,150,171,0.24)", borderRadius: 6, background: "#0f172a", color: "#e5e7eb", fontSize: 11, maxHeight: 360, overflow: "auto", whiteSpace: "pre-wrap", lineHeight: 1.5 }}>{data.report_markdown}</pre>}
            </div>
          )}

          {data.overall_warnings.length > 0 && <Warn items={data.overall_warnings} />}
          {data.overall_errors.length > 0 && <div className="errorBox" style={{ marginBottom: 8 }}>{data.overall_errors.join("\n")}</div>}
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
function M({ label, value, color }: { label: string; value: number; color: string }) { return <div style={{ padding: "8px 10px", border: "1px solid rgba(137,150,171,0.24)", borderRadius: 6, background: "#fff", display: "grid", gap: 2, color: "#667085", fontSize: 11, fontWeight: 850 }}><span>{label}</span><strong style={{ color }}>{value}</strong></div>; }

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => <section style={{ padding: 16, border: "1px solid rgba(137,150,171,0.28)", borderRadius: 8, background: "rgba(255,255,255,0.88)", marginTop: 4 }}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>;
