import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, getProjectDataReadiness } from "../api";
import type { DataReadinessCheck, DataReadinessResponse } from "../types";

type Props = {
  baseUrl?: string;
  projectId: string | null;
};

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const checkStatusPill: Record<string, React.CSSProperties> = {
  pass: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  fail: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};

const pill: React.CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 24,
  padding: "0 8px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 900,
};

const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

function CheckRow({ check }: { check: DataReadinessCheck }) {
  return (
    <div style={{
      display: "grid", gap: 5, padding: 10,
      border: "1px solid rgba(137, 150, 171, 0.22)", borderRadius: 6, background: "#fff",
    }}>
      <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ ...pill, ...checkStatusPill[check.status] }}>{check.status}</span>
        <strong style={{ fontSize: 13 }}>{check.name}</strong>
      </div>
      <div style={{ fontSize: 12, color: "#344054", lineHeight: 1.5 }}>{check.message}</div>
      {Object.keys(check.details).length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: "2px 8px", fontSize: 11, color: "#667085" }}>
          {Object.entries(check.details).map(([key, value]) => (
            <div key={key}><span>{key}: </span><b>{value === null ? "—" : String(value)}</b></div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function DataReadinessPanel({ baseUrl, projectId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<DataReadinessResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestRef = useRef(0);

  useEffect(() => {
    if (!projectId) {
      setData(null);
      setError("");
      return;
    }
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    setError("");
    getProjectDataReadiness(effectiveBase, projectId)
      .then((res) => {
        if (requestId !== requestRef.current) return;
        setData(res);
      })
      .catch((err) => {
        if (requestId !== requestRef.current) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (requestId === requestRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId]);

  if (!projectId) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="empty">Select a project to assess data readiness.</div>
      </section>
    );
  }

  if (loading) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="empty">Assessing data readiness...</div>
      </section>
    );
  }

  if (error) {
    return (
      <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
        <h3 style={{ margin: "0 0 8px", fontSize: 15 }}>Data Readiness</h3>
        <div className="errorBox">{error}</div>
      </section>
    );
  }

  if (!data) return null;

  return (
    <section style={{ padding: 16, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(255, 255, 255, 0.88)" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <div>
          <h3 style={{ margin: 0, fontSize: 15 }}>Data Readiness</h3>
          <span style={{ color: "#667085", fontSize: 12 }}>Prep-check for pipeline execution readiness.</span>
        </div>
        <span style={{ ...pill, ...statusBadge[data.status] }}>{data.status.toUpperCase()}</span>
      </div>

      {data.errors.length > 0 && (
        <div className="errorBox" style={{ marginBottom: 10 }}>{data.errors.join("\n")}</div>
      )}
      {data.warnings.length > 0 && (
        <div style={{
          marginBottom: 10, padding: 8,
          border: "1px solid rgba(242, 153, 74, 0.24)", borderRadius: 6,
          background: "rgba(255, 251, 242, 0.94)", color: "#9a5a15", fontSize: 12,
        }}>
          {data.warnings.slice(0, 5).map((w, i) => <div key={i}>{w}</div>)}
          {data.warnings.length > 5 && <div>+{data.warnings.length - 5} more</div>}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 8, marginBottom: 12 }}>
        <div style={metricBox}><span>rawdata</span><b style={mono}>{data.rawdata_dir || "—"}</b></div>
        <div style={metricBox}><span>config path</span><b style={mono}>{data.project_config_path || "—"}</b></div>
        <div style={metricBox}><span>dataset index</span><b style={mono}>{data.dataset_index_path || "—"}</b></div>
        <div style={metricBox}><span>imports</span><strong>{data.import_count}</strong></div>
        <div style={metricBox}><span>image sources</span><strong>{data.image_source_count}</strong></div>
        <div style={metricBox}><span>subjects</span><strong>{data.subject_count}</strong></div>
        <div style={metricBox}><span>sequences</span><strong>{data.sequence_count}</strong></div>
        <div style={metricBox}><span>DICOM files</span><strong>{data.dicom_file_count}</strong></div>
        <div style={metricBox}><span>DICOM series</span><strong>{data.dicom_series_count}</strong></div>
      </div>

      <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Checks</h4>
      <div style={{ display: "grid", gap: 8, marginBottom: 12 }}>
        {data.checks.map((check) => (
          <CheckRow key={check.name} check={check} />
        ))}
      </div>

      {data.next_actions.length > 0 && (
        <div>
          <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>Next Actions</h4>
          <div style={{ display: "grid", gap: 5 }}>
            {data.next_actions.map((action, i) => (
              <div key={i} style={{
                padding: "6px 10px",
                border: "1px solid rgba(56, 103, 214, 0.22)", borderRadius: 6,
                background: "rgba(239, 246, 255, 0.82)", color: "#2450a6", fontSize: 12,
              }}>
                {i + 1}. {action}
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

const metricBox: React.CSSProperties = {
  padding: "8px 10px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6, background: "#fff",
  display: "grid", gap: 2,
  color: "#667085", fontSize: 11, fontWeight: 850,
};
