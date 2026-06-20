import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, runConversionDryRun } from "../lib/api/legacy";
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

const statusBadge: Record<string, React.CSSProperties> = {
  ready: { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" },
  warning: { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" },
  blocked: { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" },
  unknown: { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" },
};
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
        <H3>Conversion Dry-Run</H3>
        <div className="empty">Select a project.</div>
      </Sect>
    );
  if (error)
    return (
      <Sect>
        <H3>Conversion Dry-Run</H3>
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
          <H3>Conversion Dry-Run</H3>
          <Sub>Plan DICOM / loose NIfTI → BIDS conversion without writing files.</Sub>
        </div>
        {data && <StatusPill status={data.status} />}
      </div>

      <SafetyBanner tone="info">
        Dry-run only. No files are written. No rawdata is modified. No external tools are executed.
      </SafetyBanner>

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
        {loading ? "Generating..." : "Generate conversion dry-run"}
      </button>

      {loading && (
        <div className="empty" style={{ marginBottom: 12 }}>
          Generating conversion plan...
        </div>
      )}
      {!data && !loading && (
        <div className="empty" style={{ marginBottom: 12 }}>
          Click the button above to generate a conversion dry-run plan.
        </div>
      )}

      {data && (
        <>
          {data.safety_flags && (
            <CollapsibleDetails title="Conversion safety details" summary="Read-only dry-run gates">
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
            <MetricTile label="Sources" value={data.source_summaries.length} />
            <MetricTile
              label="Mappings"
              value={data.mapping_preview.length}
              tone={data.mapping_preview.length > 0 ? "blue" : "neutral"}
            />
            <MetricTile
              label="Output root"
              value={data.output_root_preview || data.output_root_name}
              mono
            />
          </div>

          {data.source_summaries.length > 0 && (
            <CollapsibleDetails
              title="DICOM and loose NIfTI sources"
              summary={`${data.source_summaries.length} source(s)`}
            >
              <div style={{ display: "grid", gap: 6 }}>
                {data.source_summaries.map((s) => (
                  <SourceRow key={s.source_id} source={s} />
                ))}
              </div>
            </CollapsibleDetails>
          )}

          {data.mapping_preview.length > 0 && (
            <CollapsibleDetails
              title="DICOM mapping preview"
              summary={`${data.mapping_preview.length} mapping(s)`}
            >
              <div style={{ display: "grid", gap: 6 }}>
                {data.mapping_preview.slice(0, 30).map((m, i) => (
                  <MappingRow key={i} mapping={m} />
                ))}
              </div>
            </CollapsibleDetails>
          )}

          {data.next_actions.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <h4 style={subH}>Next Actions</h4>
              <ActionList actions={data.next_actions} rawDicom />
            </div>
          )}
        </>
      )}
    </Sect>
  );
}

function SourceRow({ source }: { source: ConversionSourceSummary }) {
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
          {source.exists ? "exists" : "missing"}
        </span>
      </div>
      <div style={mono}>{source.root}</div>
      <div style={{ fontSize: 11, color: "#667085" }}>
        {source.file_count} file(s), {source.series_count} series,{" "}
        {source.subject_candidates.length} subject candidate(s)
      </div>
      {source.warnings.length > 0 && <Warn items={source.warnings} />}
    </div>
  );
}

function MappingRow({ mapping }: { mapping: ConversionMappingPreview }) {
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
        <div style={{ ...mono, color: "#98a2b3" }}>source: {mapping.source_path}</div>
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
