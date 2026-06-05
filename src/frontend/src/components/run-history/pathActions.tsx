import type { CSSProperties } from "react";
import type { RunArtifactRecord, RunSummaryPreview } from "../../types";
import {
  canOpenExternalPath,
  classifyArtifact,
  getArtifactWarnings,
  getRunStatusToneKey,
  getRunWarnings,
  isFailedNodeArtifact,
  isPreviewableArtifact,
} from "../projectRunsPanelModel";

type PathActionProps = {
  label: string;
  path?: string | null;
  onNotice: (message: string) => void;
};

type ExternalPathWindow = Window & {
  medimage?: {
    openExternalPath?: (path: string) => Promise<boolean> | boolean;
  };
};

export function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

export function shortId(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 28 ? `${value.slice(0, 14)}...${value.slice(-8)}` : value;
}

export function statusTone(status: string): CSSProperties {
  switch (getRunStatusToneKey(status)) {
    case "success":
      return { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" };
    case "danger":
      return { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" };
    case "active":
      return { background: "#eff6ff", color: "#2450a6", borderColor: "rgba(56, 103, 214, 0.24)" };
    default:
      return { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" };
  }
}

async function copyText(value: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(value);
    return true;
  } catch {
    return false;
  }
}

export function PathActions({ label, path, onNotice }: PathActionProps) {
  const available = Boolean(path);

  async function handleCopy() {
    if (!path) {
      onNotice(`${label} path is not available.`);
      return;
    }
    const copied = await copyText(path);
    onNotice(copied ? `Copied ${label} path.` : `${label}: ${path}`);
  }

  async function handleOpen() {
    if (!path) {
      onNotice(`${label} path is not available.`);
      return;
    }
    const externalPathWindow = window as ExternalPathWindow;
    const openExternalPath = externalPathWindow.medimage?.openExternalPath;
    if (!canOpenExternalPath(externalPathWindow) || typeof openExternalPath !== "function") {
      onNotice(`Open path is available only in the desktop app. ${label}: ${path}`);
      return;
    }
    const opened = await openExternalPath(path);
    onNotice(opened ? `Opened ${label}.` : `${label}: ${path}`);
  }

  return (
    <div style={{ display: "grid", gap: 6, minWidth: 0 }}>
      <div style={{ color: "#667085", fontSize: 11, fontWeight: 900 }}>{label}</div>
      <div
        title={path || "Not available"}
        style={{
          minHeight: 34,
          padding: "7px 9px",
          border: "1px solid rgba(137, 150, 171, 0.28)",
          borderRadius: 6,
          background: "#fff",
          color: path ? "#111827" : "#98a2b3",
          fontFamily: '"Cascadia Mono", "Consolas", monospace',
          fontSize: 11,
          overflowWrap: "anywhere",
        }}
      >
        {path || "Not available"}
      </div>
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <button type="button" onClick={handleCopy} disabled={!available} style={actionButtonStyle}>
          Copy
        </button>
        <button type="button" onClick={handleOpen} disabled={!available} style={actionButtonStyle}>
          Open
        </button>
      </div>
    </div>
  );
}

export function WarningList({ warnings }: { warnings?: string[] }) {
  const visibleWarnings = getRunWarnings({ warnings });
  if (!visibleWarnings.length) return null;
  return (
    <div style={{ display: "grid", gap: 5, marginTop: 8 }}>
      {visibleWarnings.map((warning, index) => (
        <div
          key={`${warning}-${index}`}
          style={{
            padding: "7px 9px",
            border: "1px solid rgba(242, 153, 74, 0.24)",
            borderRadius: 6,
            background: "rgba(255, 248, 236, 0.82)",
            color: "#9a5a15",
            fontSize: 12,
            overflowWrap: "anywhere",
          }}
        >
          {warning}
        </div>
      ))}
    </div>
  );
}

export function SummaryMetric({
  label,
  value,
}: {
  label: string;
  value?: number | null;
}) {
  return (
    <div
      style={{
        padding: "8px 10px",
        border: "1px solid rgba(137, 150, 171, 0.24)",
        borderRadius: 6,
        background: "#fff",
      }}
    >
      <span style={{ color: "#667085", fontSize: 11, fontWeight: 850 }}>{label}</span>
      <strong style={{ display: "block", marginTop: 3, fontSize: 18 }}>
        {value ?? "-"}
      </strong>
    </div>
  );
}

export function ArtifactBadgeRow({
  artifact,
  runSummary,
}: {
  artifact: RunArtifactRecord;
  runSummary?: RunSummaryPreview | null;
}) {
  const classification = classifyArtifact(artifact);
  const warnings = getArtifactWarnings(artifact);
  const failedNode = isFailedNodeArtifact(artifact, runSummary);
  return (
    <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
      <span style={{ ...artifactChipStyle, ...artifactTone(classification.category) }}>
        {classification.label}
      </span>
      <span style={{ ...artifactChipStyle, ...artifactTone(artifact.exists ? artifact.kind : "missing") }}>
        {artifact.kind}
      </span>
      {!artifact.exists ? (
        <span style={{ ...artifactChipStyle, ...artifactTone("missing") }}>missing</span>
      ) : null}
      {warnings.length ? (
        <span style={{ ...artifactChipStyle, background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" }}>
          warnings
        </span>
      ) : null}
      {failedNode ? (
        <span style={{ ...artifactChipStyle, background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" }}>
          failed node
        </span>
      ) : null}
      <span style={{ ...artifactChipStyle, background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" }}>
        {isPreviewableArtifact(artifact) ? "previewable" : "metadata-only"}
      </span>
    </div>
  );
}

export const panelStyle: CSSProperties = {
  marginTop: 16,
  padding: 16,
  border: "1px solid rgba(137, 150, 171, 0.28)",
  borderRadius: 8,
  background: "rgba(255, 255, 255, 0.88)",
  boxShadow: "0 12px 36px rgba(15, 23, 42, 0.08)",
};

export const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

export const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 18,
};

export const subtitleStyle: CSSProperties = {
  color: "#667085",
  fontSize: 12,
  fontWeight: 750,
};

export const statusPillStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 24,
  padding: "0 8px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 900,
};

export const miniGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "120px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

export const pathPreviewStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "70px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

export const monoPathStyle: CSSProperties = {
  padding: "7px 9px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#111827",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

export const summaryMetricsStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
  gap: 8,
};

export const summaryPanelStyle: CSSProperties = {
  padding: 12,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 8,
  background: "rgba(255, 255, 255, 0.72)",
};

export const summarySectionLabelStyle: CSSProperties = {
  color: "#344054",
  fontSize: 12,
  fontWeight: 900,
};

export const summaryRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) auto",
  gap: 10,
  alignItems: "start",
  padding: 10,
  border: "1px solid rgba(137, 150, 171, 0.22)",
  borderRadius: 6,
  background: "#fff",
};

export const summaryExcerptStyle: CSSProperties = {
  margin: "6px 0 0",
  maxHeight: 150,
  overflow: "auto",
  padding: 8,
  border: "1px solid rgba(235, 87, 87, 0.18)",
  borderRadius: 6,
  background: "#fff8f6",
  color: "#7a271a",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  lineHeight: 1.5,
  whiteSpace: "pre-wrap",
  overflowWrap: "anywhere",
};

export const artifactMiniTextStyle: CSSProperties = {
  color: "#667085",
  fontSize: 11,
  fontWeight: 800,
  overflowWrap: "anywhere",
};

export const metricChipGridStyle: CSSProperties = {
  display: "flex",
  gap: 6,
  flexWrap: "wrap",
};

export const metricChipStyle: CSSProperties = {
  padding: "4px 7px",
  border: "1px solid rgba(137, 150, 171, 0.22)",
  borderRadius: 6,
  background: "rgba(248, 250, 252, 0.95)",
  color: "#344054",
  fontSize: 11,
  fontWeight: 800,
};

export const detailGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: 8,
};

export const smallButtonStyle: CSSProperties = {
  minHeight: 28,
  padding: "4px 9px",
  fontSize: 11,
  fontWeight: 850,
};

export const artifactMetaGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "72px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

export const keyArtifactGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
  gap: 8,
};

export const keyArtifactButtonStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  width: "100%",
  minHeight: 106,
  padding: 10,
  borderRadius: 8,
  textAlign: "left",
};

export const keyArtifactPathStyle: CSSProperties = {
  color: "#667085",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

export const filterGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
  gap: 8,
  marginBottom: 8,
};

export const filterLabelStyle: CSSProperties = {
  display: "grid",
  gap: 4,
  color: "#667085",
  fontSize: 11,
  fontWeight: 900,
};

export const selectStyle: CSSProperties = {
  minHeight: 30,
  width: "100%",
  padding: "4px 8px",
  border: "1px solid rgba(137, 150, 171, 0.28)",
  borderRadius: 6,
  background: "#fff",
  color: "#111827",
  fontSize: 12,
  fontWeight: 750,
};

export const artifactGroupHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  gap: 8,
  padding: "6px 8px",
  border: "1px solid rgba(137, 150, 171, 0.2)",
  borderRadius: 6,
  background: "rgba(248, 250, 252, 0.92)",
  color: "#344054",
  fontSize: 12,
  fontWeight: 900,
};

export const artifactCardStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  padding: 10,
  borderRadius: 8,
};

export const selectedArtifactCardStyle: CSSProperties = {
  border: "1px solid rgba(56, 103, 214, 0.42)",
  background: "rgba(239, 246, 255, 0.86)",
};

export const artifactChipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};

export const artifactPreviewTextStyle: CSSProperties = {
  maxHeight: 320,
  overflow: "auto",
  padding: 10,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#0f172a",
  color: "#e5e7eb",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  lineHeight: 1.55,
  whiteSpace: "pre-wrap",
  overflowWrap: "anywhere",
};

export const jsonSummaryGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
  gap: 8,
};

export const jsonKeyChipStyle: CSSProperties = {
  padding: "4px 7px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#344054",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  fontWeight: 800,
};

export const jsonMessageStyle: CSSProperties = {
  padding: "7px 9px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#9a5a15",
  fontSize: 12,
  overflowWrap: "anywhere",
};

export const tableScrollStyle: CSSProperties = {
  maxHeight: 320,
  overflow: "auto",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
};

export const artifactTableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 12,
};

export const tableHeaderCellStyle: CSSProperties = {
  position: "sticky",
  top: 0,
  padding: "7px 8px",
  borderBottom: "1px solid rgba(137, 150, 171, 0.24)",
  background: "#f8fafc",
  color: "#344054",
  fontSize: 11,
  fontWeight: 900,
  textAlign: "left",
  whiteSpace: "nowrap",
};

export const tableCellStyle: CSSProperties = {
  padding: "7px 8px",
  borderBottom: "1px solid rgba(137, 150, 171, 0.16)",
  color: "#111827",
  verticalAlign: "top",
  overflowWrap: "anywhere",
};

export const markdownPreviewStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  maxHeight: 360,
  overflow: "auto",
  padding: 12,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#344054",
  fontSize: 13,
  lineHeight: 1.55,
  overflowWrap: "anywhere",
};

export const markdownCodeStyle: CSSProperties = {
  margin: 0,
  padding: 9,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#0f172a",
  color: "#e5e7eb",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  whiteSpace: "pre-wrap",
  overflowWrap: "anywhere",
};

export function artifactAttentionStyle(
  artifact: RunArtifactRecord,
  runSummary?: RunSummaryPreview | null
): CSSProperties {
  if (!artifact.exists) {
    return {
      border: "1px solid rgba(235, 87, 87, 0.30)",
      background: "rgba(255, 245, 245, 0.92)",
    };
  }
  if (isFailedNodeArtifact(artifact, runSummary)) {
    return {
      border: "1px solid rgba(235, 87, 87, 0.24)",
      background: "rgba(255, 248, 246, 0.94)",
    };
  }
  if (getArtifactWarnings(artifact).length) {
    return {
      border: "1px solid rgba(242, 153, 74, 0.26)",
      background: "rgba(255, 251, 242, 0.94)",
    };
  }
  return {
    border: "1px solid rgba(137, 150, 171, 0.24)",
    background: "#fff",
  };
}

export function artifactTone(value: string): CSSProperties {
  const normalized = value.toLowerCase();
  if (normalized === "missing" || normalized === "error") {
    return { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" };
  }
  if (
    normalized === "ok" ||
    normalized === "summary" ||
    normalized === "reports" ||
    normalized === "qc" ||
    normalized === "json" ||
    normalized === "text" ||
    normalized === "markdown"
  ) {
    return { background: "#e8f5e9", color: "#176b3b", borderColor: "rgba(33, 150, 83, 0.24)" };
  }
  if (
    normalized === "pipeline" ||
    normalized === "logs" ||
    normalized === "tables" ||
    normalized === "image" ||
    normalized === "images" ||
    normalized === "nifti" ||
    normalized === "binary" ||
    normalized === "matlab" ||
    normalized === "other_binary"
  ) {
    return { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" };
  }
  return { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" };
}

const actionButtonStyle: CSSProperties = {
  minHeight: 28,
  padding: "4px 9px",
  fontSize: 11,
  fontWeight: 850,
};
