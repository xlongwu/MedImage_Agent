import { useRef, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { DEFAULT_API_BASE } from "../lib/api/client";
import { generateRsfmriQcPlanningReport } from "../lib/api/rsfmri";
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
  const { t } = useI18n();
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
        <H3>{t("qc.planning.title")}</H3>
        <div className="empty">{t("settings.preset.selectProject")}</div>
      </Sec>
    );
  if (error)
    return (
      <Sec>
        <H3>{t("qc.planning.title")}</H3>
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
          <H3>{t("qc.planning.fullTitle")}</H3>
          <Sub>{t("qc.planning.description")}</Sub>
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
        {t("qc.planning.boundary")}
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
        {loading ? t("qc.planning.generating") : t("qc.planning.generate")}
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
            <M label={t("qc.planning.boldRef")} value={data.bold_reference_status} />
            <M label={t("qc.planning.motionQc")} value={data.motion_qc_status} />
            <M label={t("qc.planning.boldCandidates")} value={data.bold_candidate_count} />
            <M label={t("qc.planning.motionCandidates")} value={data.motion_candidate_count} />
            <M label={t("qc.planning.ready")} value={data.ready_candidate_count} />
            <M label={t("qc.planning.warnings")} value={data.warning_count} />
            <M label={t("qc.planning.blocked")} value={data.blocked_count} />
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
            <div style={mono}>
              {t("qc.planning.json")}: {data.json_path}
            </div>
            <div style={mono}>
              {t("qc.planning.markdown")}: {data.markdown_path}
            </div>
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
                  {a.kind}: {a.exists ? `${a.size_bytes ?? 0} B` : t("qc.planning.missing")}
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
                {showMd ? t("qc.planning.hidePreview") : t("qc.planning.showPreview")}
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
