import { useRef, useState } from "react";
import { DEFAULT_API_BASE, generateRsfmriQcPlanningReport } from "../lib/api/legacy";
import type { RsfmriQcPlanningReportResponse } from "../types";

type Props = { baseUrl?: string; projectId: string | null };

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
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
const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

export default function RsfmriQcPlanningReportPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<RsfmriQcPlanningReportResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showMd, setShowMd] = useState(false);
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    try {
      const r = await generateRsfmriQcPlanningReport(effectiveBase, projectId);
      if (id === reqRef.current) setData(r);
    } catch (e) {
      if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (id === reqRef.current) setLoading(false);
    }
  }

  if (!projectId)
    return (
      <Sec>
        <H3>QC Planning Report</H3>
        <div className="empty">Select a project.</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>QC Planning Report</H3>
        <div className="errorBox">{error}</div>
      </Sec>
    );

  return (
    <Sec>
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
          <H3>rs-fMRI QC Planning Report</H3>
          <Sub>Generate a combined BOLD reference + motion QC planning artifact.</Sub>
        </div>
        {data && (
          <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>
        )}
      </div>
      <div
        style={{
          padding: 8,
          border: "1px solid rgba(242, 153, 74, 0.28)",
          borderRadius: 6,
          background: "rgba(255, 251, 242, 0.94)",
          fontSize: 11,
          color: "#9a5a15",
          marginBottom: 12,
        }}
      >
        Planning report only. No preprocessing is executed.
      </div>

      <button
        onClick={handleGenerate}
        disabled={loading}
        style={{
          marginBottom: 12,
          padding: "8px 18px",
          background: "#1976d2",
          color: "#fff",
          border: "none",
          borderRadius: 4,
          cursor: "pointer",
          fontWeight: 600,
        }}
      >
        {loading ? "Generating..." : "Generate QC Planning Report"}
      </button>

      {data && (
        <>
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
              gap: 8,
              marginBottom: 12,
            }}
          >
            <M label="BOLD ref" value={data.bold_reference_status} />
            <M label="Motion QC" value={data.motion_qc_status} />
            <M label="BOLD cand." value={data.bold_candidate_count} />
            <M label="Motion cand." value={data.motion_candidate_count} />
            <M label="Ready" value={data.ready_candidate_count} />
            <M label="Warnings" value={data.warning_count} />
            <M label="Blocked" value={data.blocked_count} />
          </div>

          {data.safety_flags && (
            <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: 12 }}>
              {Object.entries(data.safety_flags).map(([k, v]) => (
                <span
                  key={k}
                  style={{
                    ...pill,
                    background: v ? "#e8f5e9" : "#ffebee",
                    color: v ? "#176b3b" : "#b53b3b",
                    borderColor: v ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
                  }}
                >
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          )}

          <div style={{ display: "grid", gap: 4, marginBottom: 12, fontSize: 11 }}>
            <div style={mono}>JSON: {data.json_path}</div>
            <div style={mono}>Markdown: {data.markdown_path}</div>
          </div>

          {data.artifacts.length > 0 && (
            <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
              {data.artifacts.map((a, i) => (
                <span
                  key={i}
                  style={{
                    ...pill,
                    background: a.exists ? "#e8f5e9" : "#ffebee",
                    color: a.exists ? "#176b3b" : "#b53b3b",
                    borderColor: a.exists ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
                  }}
                >
                  {a.kind}: {a.exists ? `${a.size_bytes ?? 0} B` : "missing"}
                </span>
              ))}
            </div>
          )}

          {data.warnings.length > 0 && <Warn items={data.warnings} />}
          {data.errors.length > 0 && (
            <div className="errorBox" style={{ marginBottom: 10 }}>
              {data.errors.join("\n")}
            </div>
          )}

          {data.report_markdown && (
            <div>
              <button
                onClick={() => setShowMd(!showMd)}
                style={{ marginBottom: 8, fontWeight: 600 }}
              >
                {showMd ? "Hide" : "Show"} Markdown Preview
              </button>
              {showMd && (
                <pre
                  style={{
                    padding: 12,
                    border: "1px solid rgba(137, 150, 171, 0.24)",
                    borderRadius: 6,
                    background: "#fff",
                    fontSize: 11,
                    maxHeight: 360,
                    overflow: "auto",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.5,
                  }}
                >
                  {data.report_markdown}
                </pre>
              )}
            </div>
          )}
        </>
      )}
    </Sec>
  );
}

function Warn({ items }: { items: string[] }) {
  return (
    <div
      style={{
        marginBottom: 10,
        padding: 8,
        border: "1px solid rgba(242, 153, 74, 0.24)",
        borderRadius: 6,
        background: "rgba(255, 251, 242, 0.94)",
        color: "#9a5a15",
        fontSize: 12,
      }}
    >
      {items.slice(0, 5).map((w, i) => (
        <div key={i}>{w}</div>
      ))}
    </div>
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

const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section
    style={{
      padding: 16,
      border: "1px solid rgba(137, 150, 171, 0.28)",
      borderRadius: 8,
      background: "rgba(255, 255, 255, 0.88)",
      marginTop: 4,
    }}
  >
    {children}
  </section>
);
const H3: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h3 style={{ margin: "0 0 4px", fontSize: 15 }}>{children}</h3>
);
const Sub: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span style={{ color: "#667085", fontSize: 12 }}>{children}</span>
);
