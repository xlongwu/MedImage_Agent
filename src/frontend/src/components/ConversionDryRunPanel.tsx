import { useRef, useState } from "react";
import { useI18n } from "../i18n/useI18n";
import { DEFAULT_API_BASE } from "../lib/api/client";
import { runConversionDryRun } from "../lib/api/dicom";
import type {
  ConversionDryRunResponse,
  ConversionMappingPreview,
  ConversionSourceSummary,
} from "../types";
import {
  ActionList,
  CollapsibleDetails,
  MetricTile,
  SafetyBanner,
  StatusPill,
} from "./dashboardUi";

type Props = { baseUrl?: string; projectId: string | null };

const confidenceColor: Record<string, string> = {
  high: "#176b3b",
  medium: "#9a5a15",
  low: "#b53b3b",
  manual_required: "#667085",
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

export default function ConversionDryRunPanel({ baseUrl, projectId }: Props) {
  const { t } = useI18n();
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [data, setData] = useState<ConversionDryRunResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const reqRef = useRef(0);

  async function handleGenerate() {
    if (!projectId) return;
    const id = reqRef.current + 1;
    reqRef.current = id;
    setLoading(true);
    setError("");
    try {
      const res = await runConversionDryRun(effectiveBase, projectId);
      if (id === reqRef.current) setData(res);
    } catch (e) {
      if (id === reqRef.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (id === reqRef.current) setLoading(false);
    }
  }

  if (!projectId)
    return (
      <Sect>
        <H3>{t("data.dryRun.title")}</H3>
        <div className="empty">{t("data.bids.selectProject")}</div>
      </Sect>
    );
  if (error)
    return (
      <Sect>
        <H3>{t("data.dryRun.title")}</H3>
        <div className="errorBox">{error}</div>
      </Sect>
    );

  return (
    <Sect>
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
          <H3>{t("data.dryRun.title")}</H3>
          <Sub>{t("data.dryRun.description")}</Sub>
        </div>
        {data && <StatusPill status={data.status} />}
      </div>

      <SafetyBanner tone="info">{t("data.dryRun.safety")}</SafetyBanner>

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
        {loading ? t("data.dryRun.generating") : t("data.dryRun.generate")}
      </button>

      {loading && (
        <div className="empty" style={{ marginBottom: 12 }}>
          {t("data.dryRun.generatingPlan")}
        </div>
      )}
      {!data && !loading && (
        <div className="empty" style={{ marginBottom: 12 }}>
          {t("data.dryRun.empty")}
        </div>
      )}

      {data && (
        <>
          {data.safety_flags && (
            <CollapsibleDetails
              title={t("data.dryRun.safetyDetails")}
              summary={t("data.dryRun.safetySummary")}
            >
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
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
            </CollapsibleDetails>
          )}

          {data.blocking_issues.length > 0 && (
            <div className="errorBox" style={{ marginBottom: 10 }}>
              {data.blocking_issues.join("\n")}
            </div>
          )}
          {data.warnings.length > 0 && <Warn items={data.warnings} />}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
              gap: 8,
              marginBottom: 12,
            }}
          >
            <MetricTile label={t("data.dryRun.sources")} value={data.source_summaries.length} />
            <MetricTile
              label={t("data.dryRun.mappings")}
              value={data.mapping_preview.length}
              tone={data.mapping_preview.length > 0 ? "blue" : "neutral"}
            />
            <MetricTile
              label={t("data.dryRun.outputRoot")}
              value={data.output_root_preview || data.output_root_name}
              mono
            />
          </div>

          {data.source_summaries.length > 0 && (
            <CollapsibleDetails
              title={t("data.dryRun.sourceTitle")}
              summary={t("data.dryRun.sourceCount", { count: data.source_summaries.length })}
            >
              <div style={{ display: "grid", gap: 6 }}>
                {data.source_summaries.map((s) => (
                  <SourceRow key={s.source_id} source={s} t={t} />
                ))}
              </div>
            </CollapsibleDetails>
          )}

          {data.mapping_preview.length > 0 && (
            <CollapsibleDetails
              title={t("data.dryRun.mappingTitle")}
              summary={t("data.dryRun.mappingCount", { count: data.mapping_preview.length })}
            >
              <div style={{ display: "grid", gap: 6 }}>
                {data.mapping_preview.slice(0, 30).map((m, i) => (
                  <MappingRow key={i} mapping={m} t={t} />
                ))}
              </div>
            </CollapsibleDetails>
          )}

          {data.next_actions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4 style={subH}>{t("data.bids.nextActions")}</h4>
              <ActionList actions={data.next_actions} rawDicom />
            </div>
          )}
        </>
      )}
    </Sect>
  );
}

type Translate = ReturnType<typeof useI18n>["t"];

function SourceRow({ source, t }: { source: ConversionSourceSummary; t: Translate }) {
  return (
    <div
      style={{
        display: "grid",
        gap: 4,
        padding: 8,
        border: "1px solid rgba(137, 150, 171, 0.22)",
        borderRadius: 6,
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span
          style={{
            ...pill,
            background: "#eef1f6",
            color: "#667085",
            borderColor: "rgba(137, 150, 171, 0.28)",
          }}
        >
          {source.source_type}
        </span>
        <strong style={{ fontSize: 12 }}>{source.source_id}</strong>
        <span style={{ fontSize: 11, color: source.exists ? "#176b3b" : "#b53b3b" }}>
          {source.exists ? t("data.dryRun.exists") : t("data.dryRun.missing")}
        </span>
      </div>
      <div style={mono}>{source.root}</div>
      <div style={{ fontSize: 11, color: "#667085" }}>
        {t("data.dryRun.sourceStats", {
          files: source.file_count,
          series: source.series_count,
          subjects: source.subject_candidates.length,
        })}
      </div>
      {source.warnings.length > 0 && <Warn items={source.warnings} />}
    </div>
  );
}

function MappingRow({ mapping, t }: { mapping: ConversionMappingPreview; t: Translate }) {
  return (
    <div
      style={{
        display: "grid",
        gap: 4,
        padding: 8,
        border: "1px solid rgba(137, 150, 171, 0.22)",
        borderRadius: 6,
        background: "#fff",
      }}
    >
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
        <span
          style={{
            ...pill,
            background: "#eff6ff",
            color: "#2450a6",
            borderColor: "rgba(56, 103, 214, 0.24)",
          }}
        >
          {mapping.source_type}
        </span>
        <span style={{ fontSize: 12, fontWeight: 700, color: confidenceColor[mapping.confidence] }}>
          {mapping.confidence}
        </span>
        {mapping.subject_id && (
          <span style={{ fontSize: 11, color: "#667085" }}>{mapping.subject_id}</span>
        )}
        {mapping.modality && (
          <span
            style={{
              ...pill,
              background: "#eef1f6",
              color: "#667085",
              borderColor: "rgba(137, 150, 171, 0.28)",
            }}
          >
            {mapping.modality}
          </span>
        )}
        {mapping.suffix && (
          <span style={{ ...pill, ...suffixPill(mapping.suffix) }}>{mapping.suffix}</span>
        )}
      </div>
      {mapping.suggested_relative_path && <div style={mono}>{mapping.suggested_relative_path}</div>}
      {mapping.source_path && (
        <div style={{ ...mono, color: "#98a2b3" }}>
          {t("data.dryRun.source")}: {mapping.source_path}
        </div>
      )}
      {mapping.warnings.length > 0 && <Warn items={mapping.warnings} />}
    </div>
  );
}

function suffixPill(suffix: string): React.CSSProperties {
  if (suffix === "bold")
    return { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" };
  if (suffix === "T1w" || suffix === "T2w" || suffix === "FLAIR")
    return { background: "#eff6ff", color: "#2450a6", borderColor: "rgba(56, 103, 214, 0.24)" };
  return { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" };
}

function Warn({ items }: { items: string[] }) {
  return (
    <div
      style={{
        padding: 6,
        border: "1px solid rgba(242, 153, 74, 0.24)",
        borderRadius: 4,
        background: "rgba(255, 251, 242, 0.94)",
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
const Sect: React.FC<{ children: React.ReactNode }> = ({ children }) => (
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
const subH: React.CSSProperties = { margin: "0 0 6px", fontSize: 13 };
