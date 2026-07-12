import { useRef, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { DEFAULT_API_BASE } from "../lib/api/client";
import { generateSpmRealignWrapperSkeleton } from "../lib/api/preprocessing";
import type { SpmRealignWrapperSkeletonResponse } from "../types";

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

export default function SpmRealignWrapperSkeletonPanel({ baseUrl, projectId }: Props) {
  const { t } = useI18n();
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<SpmRealignWrapperSkeletonResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showBatch, setShowBatch] = useState(false);
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    try {
      const r = await generateSpmRealignWrapperSkeleton(effectiveBase, projectId);
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
        <H3>{t("technical.SpmRealignWrapperSkeleton.001")}</H3>
        <div className="empty">{t("technical.BoldReferenceReadiness.002")}</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>{t("technical.SpmRealignWrapperSkeleton.001")}</H3>
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
          <H3>{t("technical.SpmRealignWrapperSkeleton.001")}</H3>
          <Sub>{t("technical.SpmRealignWrapperSkeleton.002")}</Sub>
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
        Preview only. MATLAB/SPM is not executed. This batch template is not executable and must not
        be copied and run as a production command. Research-use only. Not for clinical use.
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
        {loading
          ? t("technical.MotionMetricsDraft.004")
          : t("technical.SpmRealignWrapperSkeleton.003")}
      </button>

      {data && (
        <>
          <div style={{ marginBottom: 8, fontSize: 13, fontWeight: 700 }}>
            Command template: <code style={mono}>{data.command_template_id}</code>
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
                    borderColor: v ? "rgba(33,150,83,0.24)" : "rgba(235,87,87,0.26)",
                  }}
                >
                  {k}: {String(v)}
                </span>
              ))}
            </div>
          )}

          {data.provenance_preview && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 4,
                marginBottom: 12,
                fontSize: 11,
                color: "#667085",
              }}
            >
              <span>
                inputs: <b>{data.provenance_preview.input_count}</b>
              </span>
              <span>
                outputs: <b>{data.provenance_preview.predicted_output_count}</b>
              </span>
              <span>
                exec enabled:{" "}
                <b
                  style={{
                    color: data.provenance_preview.execution_enabled ? "#176b3b" : "#b53b3b",
                  }}
                >
                  {String(data.provenance_preview.execution_enabled)}
                </b>
              </span>
              <span>
                safe allowlist:{" "}
                <b
                  style={{
                    color: data.provenance_preview.safe_allowlist_enabled ? "#176b3b" : "#b53b3b",
                  }}
                >
                  {String(data.provenance_preview.safe_allowlist_enabled)}
                </b>
              </span>
            </div>
          )}

          {data.manifest_summary && Object.keys(data.manifest_summary).length > 0 && (
            <div
              style={{
                marginBottom: 12,
                padding: 10,
                border: "1px solid rgba(137,150,171,0.22)",
                borderRadius: 6,
                background: "rgba(249,249,251,0.9)",
              }}
            >
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 6 }}>
                Output Manifest Preview
              </div>
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "1fr 1fr 1fr",
                  gap: 4,
                  fontSize: 11,
                  color: "#667085",
                  marginBottom: 4,
                }}
              >
                <span>
                  manifests: <b>{String(data.manifest_summary.manifest_count ?? 0)}</b>
                </span>
                <span>
                  items: <b>{String(data.manifest_summary.total_items ?? 0)}</b>
                </span>
                <span>
                  overwrites:{" "}
                  <b
                    style={{
                      color:
                        (data.manifest_summary.would_overwrite_count as number) > 0
                          ? "#b53b3b"
                          : "#667085",
                    }}
                  >
                    {String(data.manifest_summary.would_overwrite_count ?? 0)}
                  </b>
                </span>
                <span>
                  missing req:{" "}
                  <b style={{ color: "#b53b3b" }}>
                    {String(data.manifest_summary.missing_required_count ?? 0)}
                  </b>
                </span>
                <span>
                  verified: <b>{String(data.manifest_summary.verified_count ?? 0)}</b>
                </span>
              </div>
              <div style={{ fontSize: 10, color: "#9a5a15" }}>
                These manifests are preview-only. Missing outputs are expected because MATLAB/SPM
                has not been executed.
              </div>
            </div>
          )}

          {data.matlab_batch_preview && (
            <div style={{ marginBottom: 12 }}>
              <button onClick={() => setShowBatch(!showBatch)} style={{ fontWeight: 600 }}>
                {showBatch ? "Hide" : "Show"} MATLAB Batch Preview
              </button>
              {showBatch && (
                <pre
                  style={{
                    marginTop: 8,
                    padding: 12,
                    border: "1px solid rgba(137,150,171,0.24)",
                    borderRadius: 6,
                    background: "#0f172a",
                    color: "#e5e7eb",
                    fontSize: 11,
                    maxHeight: 360,
                    overflow: "auto",
                    whiteSpace: "pre-wrap",
                    lineHeight: 1.5,
                  }}
                >
                  {data.matlab_batch_preview}
                </pre>
              )}
            </div>
          )}

          {data.warnings.length > 0 && <Warn items={data.warnings} />}
          {data.errors.length > 0 && (
            <div className="errorBox" style={{ marginBottom: 8 }}>
              {data.errors.join("\n")}
            </div>
          )}
          {data.next_actions.length > 0 && (
            <div>
              <h4 style={{ margin: "0 0 6px", fontSize: 13 }}>
                {t("technical.BoldReferenceReadiness.011")}
              </h4>
              <div style={{ display: "grid", gap: 5 }}>
                {data.next_actions.map((a, i) => (
                  <div
                    key={i}
                    style={{
                      padding: "6px 10px",
                      border: "1px solid rgba(56,103,214,0.22)",
                      borderRadius: 6,
                      background: "rgba(239,246,255,0.82)",
                      color: "#2450a6",
                      fontSize: 12,
                    }}
                  >
                    {i + 1}. {a}
                  </div>
                ))}
              </div>
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
        marginTop: 4,
        padding: 6,
        border: "1px solid rgba(242,153,74,0.24)",
        borderRadius: 4,
        background: "rgba(255,251,242,0.94)",
        color: "#9a5a15",
        fontSize: 11,
      }}
    >
      {items.slice(0, 3).map((w, i) => (
        <div key={i}>{w}</div>
      ))}
    </div>
  );
}

const mono: React.CSSProperties = {
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};
const Sec: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <section
    style={{
      padding: 16,
      border: "1px solid rgba(137,150,171,0.28)",
      borderRadius: 8,
      background: "rgba(255,255,255,0.88)",
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
