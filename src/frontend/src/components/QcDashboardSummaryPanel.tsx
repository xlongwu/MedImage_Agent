import { useRef, useState } from "react";
import { DEFAULT_API_BASE, generateQcDashboardReport, getLatestQcDashboardReport, getQcDashboardFingerprint } from "../lib/api/legacy";
import type { QcDashboardFingerprintResponse } from "../types";
import type { QcDashboardReportResponse } from "../types";
import { ActionList, CollapsibleDetails, MetricTile, SafetyBanner, StatusPill } from "./dashboardUi";
import styles from "./QcDashboardSummaryPanel.module.css";

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
      <div className={styles.style001}>
        <div><H3>QC Dashboard Report</H3><Sub>Aggregate summary of all QC checks. No preprocessing is executed.</Sub></div>
        {data && <StatusPill status={data.status} />}
      </div>
      <SafetyBanner tone="warning">
        Dashboard report only. No preprocessing is executed. Rawdata is not modified.
      </SafetyBanner>

      <div className={styles.style002}>
        <button onClick={handleGenerate} disabled={loading} className={styles.style003}>
          {loading ? "Generating..." : "Generate Dashboard Report"}
        </button>
        <button onClick={handleLoadLatest} disabled={loading} className={styles.style004}>
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
            <div className={styles.style005}>
              <div style={{ color: "#667085", marginBottom: data.cache.module_records?.length ? 4 : 0 }}>
                Cache: <b>{data.cache.mode}</b>
                {data.cache.mode !== "off" && ` · modules: ${Object.values(data.cache.module_hits ?? {}).filter(Boolean).length}/${Object.keys(data.cache.module_hits ?? {}).length || Object.keys(data.cache.module_records ?? []).length || 1}`}
              </div>
              {/* Module-level cache records */}
              {data.cache.module_records?.length ? (
                <div className={styles.style006}>
                  {data.cache.module_records.map((r, i) => {
                    const statusColors: Record<string, string> = {
                      hit: "#176b3b", miss: "#667085", stale: "#9a5a15",
                      disabled: "#999", error: "#b53b3b",
                    };
                    return (
                      <div key={i} className={styles.style007}>
                        <span className={styles.style008}>{r.module_id}</span>
                        <span style={{ ...pill, background: r.status === "hit" ? "#e8f5e9" : r.status === "stale" ? "#fff7ed" : r.status === "error" ? "#ffebee" : "#eef1f6", color: statusColors[r.status] || "#667085", borderColor: "rgba(137,150,171,0.28)" }}>{r.status}</span>
                        {r.hit && <span className={styles.style009}>✓ hit</span>}
                        {r.stale && <span className={styles.style010}>⚠ stale</span>}
                        {r.module_version && <span className={styles.style011}>v{r.module_version}</span>}
                        {r.warnings.length > 0 && <span className={styles.style012}>⚠{r.warnings.length}</span>}
                        {r.errors.length > 0 && <span className={styles.style013}>✗{r.errors.length}</span>}
                      </div>
                    );
                  })}
                </div>
              ) : null}
              {data.cache.mode !== "off" && (
                <div className={styles.style014}>
                  Module cache currently applies only to NIfTI QC Snapshot. Other modules run normally.
                </div>
              )}
              {(data.cache.cache_warnings?.length ?? 0) > 0 && (
                <div className={styles.style015}>⚠ {data.cache.cache_warnings![0].slice(0, 80)}</div>
              )}
            </div>
          )}

          {fpData && (
            <div className={styles.style016}>
              <div className={styles.style017}>Rawdata Fingerprint</div>
              <div className={styles.style018}>
                <span><b>hash:</b> {fpData.fingerprint.fingerprint?.slice(0, 12) ?? "—"}</span>
                <span><b>files:</b> {fpData.fingerprint.file_count}</span>
                <span><b>size:</b> {fpData.fingerprint.total_size_bytes}</span>
                <span><b>mtime:</b> {fpData.fingerprint.newest_mtime_iso ?? "—"}</span>
                <span><b>trunc:</b> {String(fpData.fingerprint.truncated)}</span>
              </div>
              <div className={styles.style019}>
                Fingerprint is metadata-only and used for future cache invalidation. No cache is created in this release.
              </div>
            </div>
          )}

          {/* Counts */}
          <div className={styles.style020}>
            <MetricTile label="Ready" value={data.ready_count} tone="green" />
            <MetricTile label="Warning" value={data.warning_count} tone={data.warning_count > 0 ? "amber" : "neutral"} />
            <MetricTile label="Blocked" value={data.blocked_count} tone={data.blocked_count > 0 ? "red" : "neutral"} />
            <MetricTile label="Unknown" value={data.unknown_count} />
          </div>

          {/* Module cards */}
          {data.modules.length > 0 && (
            <CollapsibleDetails title="QC module details" summary={`${data.modules.length} module(s)`}>
              <div className={styles.style021}>
                {data.modules.map((m) => (
                  <div key={m.module_id} className={styles.style022}>
                    <div className={styles.style023}>
                      <strong>{m.name}</strong>
                      <span style={{ ...pill, ...statusBadge[m.status] }}>{m.status}</span>
                      <span className={styles.style024}>{m.summary?.slice(0, 80)}</span>
                    </div>
                    {Object.keys(m.key_metrics).length > 0 && (
                      <div className={styles.style025}>
                        {Object.entries(m.key_metrics).slice(0, 6).map(([k, v]) => (
                          <span key={k}>{k}: <b>{v == null ? "—" : String(v)}</b></span>
                        ))}
                      </div>
                    )}
                    <div className={styles.style026}>
                      {m.warnings.length > 0 && <span className={styles.style027}>⚠{m.warnings.length}</span>}
                      {m.errors.length > 0 && <span className={styles.style028}>✗{m.errors.length}</span>}
                      {m.next_actions.length > 0 && <span className={styles.style029}>→ {m.next_actions[0].slice(0, 60)}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </CollapsibleDetails>
          )}

          {/* Artifacts */}
          {data.artifacts.length > 0 && (
            <CollapsibleDetails title="Report artifacts" summary={`${data.artifacts.length} artifact(s)`}>
            <div className={styles.style030}>
              {data.artifacts.map((a, i) => (
                <div key={i} style={mono}>
                  [{a.kind}] {a.path} {a.size_bytes != null ? `(${a.size_bytes} B)` : ""}
                </div>
              ))}
            </div>
            </CollapsibleDetails>
          )}

          {/* Markdown preview */}
          {data.report_markdown && (
            <div className={styles.style031}>
              <button onClick={() => setShowMd(!showMd)} style={{ fontWeight: 600 }}>{showMd ? "Hide" : "Show"} Markdown Preview</button>
              {showMd && <pre className={styles.style032}>{data.report_markdown}</pre>}
            </div>
          )}

          {data.overall_warnings.length > 0 && <Warn items={data.overall_warnings} />}
          {data.overall_errors.length > 0 && <div className={`errorBox ${styles.style039}`}>{data.overall_errors.join("\n")}</div>}
          {data.next_actions.length > 0 && (
            <div>
              <h4 className={styles.style033}>Next Actions</h4>
              <ActionList actions={data.next_actions} />
            </div>
          )}
        </>
      )}
    </Sec>
  );
}

function Warn({ items }: { items: string[] }) { return <div className={styles.style034}>{items.slice(0, 3).map((w,i)=><div key={i}>{w}</div>)}</div>; }
function M({ label, value, color }: { label: string; value: number; color: string }) { return <div className={styles.style035}><span>{label}</span><strong style={{ color }}>{value}</strong></div>; }

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => <section className={styles.style036}>{children}</section>;
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => <h3 className={styles.style037}>{children}</h3>;
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => <span className={styles.style038}>{children}</span>;
