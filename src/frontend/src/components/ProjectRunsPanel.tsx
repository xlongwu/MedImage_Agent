import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import {
  getProjectRun,
  getProjectRunArtifact,
  listProjectRunArtifacts,
  listProjectRuns,
} from "../api";
import type {
  RunArtifactPreviewResponse,
  RunArtifactRecord,
  RunLinkRecord,
  RunSummaryPreview,
} from "../types";
import { JsonBlock } from "./JsonBlock";
import {
  ARTIFACT_CATEGORIES,
  artifactPath,
  buildArtifactProvenanceRows,
  canOpenExternalPath,
  classifyArtifact,
  extractFailedNodeHighlights,
  extractQcHighlights,
  extractRunPaths,
  filterArtifacts,
  formatArtifactSize,
  getArtifactWarnings,
  getKeyArtifactReason,
  getKeyArtifacts,
  getRunStatusToneKey,
  getRunWarnings,
  groupArtifacts,
  isFailedNodeArtifact,
  isPreviewableArtifact,
  markdownPreviewBlocks,
  mergeSummaryWarnings,
  missingSummaryWarning,
  normalizeCsvPreview,
  normalizeJsonPreviewSummary,
  normalizeRunSummaryPreview,
  sortArtifacts,
  summarizeRunHealth,
} from "./projectRunsPanelModel";
import type { RunArtifactCategoryFilter, RunArtifactStateFilter } from "./projectRunsPanelModel";

type Props = {
  baseUrl: string;
  projectId: string | null;
  projectDir?: string | null;
};

type PathActionProps = {
  label: string;
  path?: string | null;
  onNotice: (message: string) => void;
};

function formatDate(value: string | null | undefined): string {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function shortId(value: string | null | undefined): string {
  if (!value) return "-";
  return value.length > 28 ? `${value.slice(0, 14)}...${value.slice(-8)}` : value;
}

function statusTone(status: string): CSSProperties {
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

function PathActions({ label, path, onNotice }: PathActionProps) {
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
    if (!canOpenExternalPath(window)) {
      onNotice(`Open path is available only in the desktop app. ${label}: ${path}`);
      return;
    }
    const opened = await window.medimage.openExternalPath(path);
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

const actionButtonStyle: CSSProperties = {
  minHeight: 28,
  padding: "4px 9px",
  fontSize: 11,
  fontWeight: 850,
};

function WarningList({ warnings }: { warnings?: string[] }) {
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

function SummaryMetric({
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

function SummaryPreviewCard({
  preview,
  summaryPath,
  warnings,
  error,
  loading,
}: {
  preview: RunSummaryPreview | null;
  summaryPath?: string | null;
  warnings: string[];
  error: string;
  loading: boolean;
}) {
  if (loading) {
    return <div className="empty">Loading summary preview...</div>;
  }

  if (error) {
    return <div className="errorBox">{error}</div>;
  }

  if (!preview) {
    return (
      <div>
        <div className="empty">{warnings[0] || missingSummaryWarning(summaryPath)}</div>
        <WarningList warnings={warnings.slice(1)} />
      </div>
    );
  }

  const failedNodes = preview.failed_nodes ?? [];
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <div style={{ minWidth: 0 }}>
          <div style={{ color: "#667085", fontSize: 11, fontWeight: 900 }}>summary_path</div>
          <div style={{ ...monoPathStyle, marginTop: 4 }}>{summaryPath || "-"}</div>
        </div>
        {preview.status ? (
          <span style={{ ...statusPillStyle, ...statusTone(preview.status) }}>
            {preview.status}
          </span>
        ) : null}
      </div>

      <div style={summaryMetricsStyle}>
        <SummaryMetric label="nodes total" value={preview.nodes_total} />
        <SummaryMetric label="succeeded" value={preview.nodes_succeeded} />
        <SummaryMetric label="failed" value={preview.nodes_failed} />
        <SummaryMetric label="skipped" value={preview.nodes_skipped} />
      </div>

      <div style={detailGridStyle}>
        <div><span>started</span><strong>{formatDate(preview.started_at)}</strong></div>
        <div><span>finished</span><strong>{formatDate(preview.finished_at)}</strong></div>
        <div><span>summary run_id</span><strong>{preview.run_id || "-"}</strong></div>
        <div><span>raw preview</span><strong>{preview.raw_truncated ? "truncated" : "bounded"}</strong></div>
      </div>

      <WarningList warnings={mergeSummaryWarnings(preview, warnings)} />

      {failedNodes.length ? (
        <details open>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Failed nodes</summary>
          <div style={{ marginTop: 8 }}>
            <JsonBlock value={failedNodes} emptyText="No failed nodes recorded" />
          </div>
        </details>
      ) : null}

      {preview.outputs && Object.keys(preview.outputs).length ? (
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Output paths</summary>
          <div style={{ marginTop: 8 }}>
            <JsonBlock value={preview.outputs} emptyText="No outputs recorded" />
          </div>
        </details>
      ) : null}
    </div>
  );
}

function ArtifactPreview({
  preview,
  onNotice,
}: {
  preview: RunArtifactPreviewResponse | null;
  onNotice: (message: string) => void;
}) {
  if (!preview) {
    return <div className="empty">Select an artifact to inspect.</div>;
  }

  const warnings = mergeSummaryWarnings(preview);
  const csvPreview = normalizeCsvPreview(preview.csv);
  const jsonSummary = normalizeJsonPreviewSummary(preview);
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, flexWrap: "wrap" }}>
        <strong style={{ fontSize: 13 }}>{preview.artifact.name}</strong>
        <span style={{ ...statusPillStyle, ...artifactTone(preview.ok ? "ok" : "error") }}>
          {preview.preview_type}
        </span>
      </div>
      {preview.errors.length ? <div className="errorBox">{preview.errors.join("\n")}</div> : null}
      <WarningList warnings={warnings} />
      {preview.preview_type === "json" && preview.json !== null ? (
        <JsonArtifactSummary summary={jsonSummary} raw={preview.json} />
      ) : preview.preview_type === "csv" && csvPreview ? (
        <CsvArtifactTable table={csvPreview} rawContent={preview.content} />
      ) : preview.preview_type === "markdown" && preview.content !== null ? (
        <MarkdownArtifactPreview content={preview.content} />
      ) : (preview.preview_type === "text" || preview.preview_type === "log") && preview.content !== null ? (
        <pre style={artifactPreviewTextStyle}>{preview.content}</pre>
      ) : (
        <ArtifactMetadata preview={preview} onNotice={onNotice} />
      )}
      {preview.truncated ? (
        <div className="empty" style={{ padding: 8 }}>
          Preview truncated.
        </div>
      ) : null}
    </div>
  );
}

function JsonArtifactSummary({
  summary,
  raw,
}: {
  summary: ReturnType<typeof normalizeJsonPreviewSummary>;
  raw: unknown;
}) {
  if (!summary) {
    return <JsonBlock value={raw} emptyText="No JSON preview" />;
  }
  const fieldRows = summary.field_summaries.slice(0, 18);
  return (
    <div style={{ display: "grid", gap: 10 }}>
      <div style={jsonSummaryGridStyle}>
        <div><span>type</span><strong>{summary.type}</strong></div>
        <div><span>size</span><strong>{summary.size ?? "-"}</strong></div>
        <div><span>status</span><strong>{summary.status === null || summary.status === undefined ? "-" : String(summary.status)}</strong></div>
        <div><span>warnings</span><strong>{summary.warnings.count}</strong></div>
        <div><span>errors</span><strong>{summary.errors.count}</strong></div>
      </div>

      {summary.top_level_keys.length ? (
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {summary.top_level_keys.slice(0, 24).map((key) => (
            <span key={key} style={jsonKeyChipStyle}>{key}</span>
          ))}
        </div>
      ) : null}

      {summary.warnings.sample.length || summary.errors.sample.length ? (
        <div style={{ display: "grid", gap: 6 }}>
          {summary.warnings.sample.map((item, index) => (
            <div key={`warning-${index}`} style={jsonMessageStyle}>warning: {item}</div>
          ))}
          {summary.errors.sample.map((item, index) => (
            <div key={`error-${index}`} style={{ ...jsonMessageStyle, color: "#b53b3b" }}>error: {item}</div>
          ))}
        </div>
      ) : null}

      {fieldRows.length ? (
        <div style={tableScrollStyle}>
          <table style={artifactTableStyle}>
            <thead>
              <tr>
                <th style={tableHeaderCellStyle}>key</th>
                <th style={tableHeaderCellStyle}>type</th>
                <th style={tableHeaderCellStyle}>size</th>
                <th style={tableHeaderCellStyle}>shape</th>
              </tr>
            </thead>
            <tbody>
              {fieldRows.map((field) => (
                <tr key={field.key}>
                  <td style={tableCellStyle}>{field.key}</td>
                  <td style={tableCellStyle}>{field.type}</td>
                  <td style={tableCellStyle}>{field.size ?? "-"}</td>
                  <td style={tableCellStyle}>{field.keys?.join(", ") || field.sample_types?.join(", ") || "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <details>
        <summary style={{ cursor: "pointer", fontWeight: 900 }}>Raw JSON preview</summary>
        <div style={{ marginTop: 8 }}>
          <JsonBlock value={raw} emptyText="No JSON preview" />
        </div>
      </details>
    </div>
  );
}

function CsvArtifactTable({
  table,
  rawContent,
}: {
  table: NonNullable<ReturnType<typeof normalizeCsvPreview>>;
  rawContent: string | null;
}) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      {table.columns.length ? (
        <div style={tableScrollStyle}>
          <table style={artifactTableStyle}>
            <thead>
              <tr>
                {table.columns.map((column, index) => (
                  <th key={`${column}-${index}`} style={tableHeaderCellStyle}>{column}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {table.rows.map((row, rowIndex) => (
                <tr key={`row-${rowIndex}`}>
                  {table.columns.map((_, columnIndex) => (
                    <td key={`cell-${rowIndex}-${columnIndex}`} style={tableCellStyle}>{row[columnIndex] ?? ""}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="empty">CSV preview is empty.</div>
      )}
      <div className="empty" style={{ padding: 8 }}>
        Showing {table.displayed_rows} row(s).{table.columns_truncated ? " Columns truncated." : ""}
      </div>
      {rawContent ? (
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Raw CSV preview</summary>
          <pre style={{ ...artifactPreviewTextStyle, marginTop: 8 }}>{rawContent}</pre>
        </details>
      ) : null}
    </div>
  );
}

function MarkdownArtifactPreview({ content }: { content: string }) {
  const blocks = markdownPreviewBlocks(content);
  if (!blocks.length) {
    return <div className="empty">Markdown preview is empty.</div>;
  }
  return (
    <div style={markdownPreviewStyle}>
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          const fontSize = block.level === 1 ? 18 : block.level === 2 ? 15 : 13;
          return (
            <div key={index} style={{ fontSize, fontWeight: 900, color: "#111827", marginTop: index ? 6 : 0 }}>
              {block.text}
            </div>
          );
        }
        if (block.type === "list_item") {
          return (
            <div key={index} style={{ display: "grid", gridTemplateColumns: "14px minmax(0, 1fr)", gap: 6 }}>
              <span>-</span>
              <span>{block.text}</span>
            </div>
          );
        }
        if (block.type === "code") {
          return <pre key={index} style={markdownCodeStyle}>{block.text}</pre>;
        }
        if (block.type === "rule") {
          return <div key={index} style={{ borderTop: "1px solid rgba(137, 150, 171, 0.28)" }} />;
        }
        return <p key={index} style={{ margin: 0 }}>{block.text}</p>;
      })}
    </div>
  );
}

function ArtifactMetadata({
  preview,
  onNotice,
}: {
  preview: RunArtifactPreviewResponse;
  onNotice: (message: string) => void;
}) {
  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div style={artifactMetaGridStyle}>
        <span>kind</span>
        <b>{preview.kind}</b>
        <span>size</span>
        <b>{formatArtifactSize(preview.artifact.size_bytes)}</b>
        <span>exists</span>
        <b>{preview.exists ? "yes" : "no"}</b>
        <span>modified</span>
        <b>{formatDate(preview.artifact.modified_at)}</b>
      </div>
      <PathActions label="Artifact" path={artifactPath(preview.artifact)} onNotice={onNotice} />
      <div className="empty" style={{ padding: 8 }}>
        Content preview is not available for this artifact type.
      </div>
    </div>
  );
}

function ArtifactBadgeRow({
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

function KeyArtifactsPanel({
  artifacts,
  runSummary,
  loading,
  previewLoading,
  selectedArtifactId,
  onPreview,
}: {
  artifacts: RunArtifactRecord[];
  runSummary: RunSummaryPreview | null;
  loading: boolean;
  previewLoading: boolean;
  selectedArtifactId: string | null;
  onPreview: (artifact: RunArtifactRecord) => void;
}) {
  const keyArtifacts = useMemo(
    () => getKeyArtifacts(artifacts, runSummary),
    [artifacts, runSummary]
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Key Artifacts</h4>
          <span style={subtitleStyle}>Summary, pipeline, reports, QC, failed logs, and tables.</span>
        </div>
        <span style={{ ...statusPillStyle, ...artifactTone(keyArtifacts.length ? "ok" : "neutral") }}>
          {keyArtifacts.length}
        </span>
      </div>

      {keyArtifacts.length ? (
        <div style={keyArtifactGridStyle}>
          {keyArtifacts.map((artifact) => {
            const selected = artifact.artifact_id === selectedArtifactId;
            const reason = getKeyArtifactReason(artifact, runSummary);
            return (
              <button
                key={artifact.artifact_id}
                type="button"
                onClick={() => onPreview(artifact)}
                disabled={previewLoading}
                style={{
                  ...keyArtifactButtonStyle,
                  ...(selected ? selectedArtifactCardStyle : artifactAttentionStyle(artifact, runSummary)),
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", gap: 8, alignItems: "flex-start" }}>
                  <strong style={{ fontSize: 12, overflowWrap: "anywhere" }}>{artifact.name}</strong>
                  <span style={{ color: "#667085", fontSize: 11, fontWeight: 900, whiteSpace: "nowrap" }}>
                    {reason}
                  </span>
                </div>
                <ArtifactBadgeRow artifact={artifact} runSummary={runSummary} />
                <div style={keyArtifactPathStyle}>{artifact.relative_path || artifact.path}</div>
              </button>
            );
          })}
        </div>
      ) : (
        <div className="empty">
          {loading ? "Loading key artifacts..." : "No key artifacts were discovered for this run."}
        </div>
      )}
    </div>
  );
}

function RunQcErrorSummaryCard({
  run,
  runSummary,
  artifacts,
  loading,
  previewLoading,
  selectedArtifactId,
  onPreview,
}: {
  run: RunLinkRecord;
  runSummary: RunSummaryPreview | null;
  artifacts: RunArtifactRecord[];
  loading: boolean;
  previewLoading: boolean;
  selectedArtifactId: string | null;
  onPreview: (artifact: RunArtifactRecord) => void;
}) {
  const health = useMemo(
    () => summarizeRunHealth(run, runSummary, artifacts),
    [artifacts, run, runSummary]
  );
  const qcHighlights = useMemo(() => extractQcHighlights(artifacts), [artifacts]);
  const failedNodes = useMemo(
    () => extractFailedNodeHighlights(runSummary, artifacts),
    [artifacts, runSummary]
  );
  const provenanceRows = useMemo(
    () => buildArtifactProvenanceRows(artifacts).slice(0, 8),
    [artifacts]
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>QC / Error Summary</h4>
          <span style={subtitleStyle}>Run health, QC highlights, failed logs, and artifact provenance.</span>
        </div>
        <span style={{ ...statusPillStyle, ...statusTone(health.status) }}>{health.status}</span>
      </div>

      <div style={summaryMetricsStyle}>
        <SummaryMetric label="nodes total" value={health.nodesTotal} />
        <SummaryMetric label="succeeded" value={health.nodesSucceeded} />
        <SummaryMetric label="failed" value={health.nodesFailed} />
        <SummaryMetric label="skipped" value={health.nodesSkipped} />
        <SummaryMetric label="warnings" value={health.warningsCount} />
        <SummaryMetric label="errors" value={health.errorsCount} />
        <SummaryMetric label="missing" value={health.missingArtifactCount} />
        <SummaryMetric label="failed logs" value={health.failedLogCount} />
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        <span style={{ ...artifactChipStyle, ...artifactTone(health.hasMissingArtifacts ? "missing" : "ok") }}>
          {health.hasMissingArtifacts ? "missing artifacts" : "artifacts present"}
        </span>
        <span style={{ ...artifactChipStyle, ...artifactTone(health.hasFailedNodeLogs ? "error" : "ok") }}>
          {health.hasFailedNodeLogs ? "failed-node logs" : "no failed-node logs"}
        </span>
        {loading ? (
          <span style={{ ...artifactChipStyle, ...artifactTone("neutral") }}>loading artifacts</span>
        ) : null}
      </div>

      {failedNodes.length ? (
        <div style={{ display: "grid", gap: 7 }}>
          <strong style={summarySectionLabelStyle}>Failed nodes</strong>
          {failedNodes.map((node) => {
            const selected = node.artifactId === selectedArtifactId;
            return (
              <div
                key={`${node.nodeId}-${node.artifactId || "summary"}`}
                style={{
                  ...summaryRowStyle,
                  ...(selected ? selectedArtifactCardStyle : {}),
                }}
              >
                <div style={{ minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 12 }}>{node.nodeName || node.nodeId}</strong>
                    <span style={{ ...artifactChipStyle, ...artifactTone("error") }}>{node.status}</span>
                    {node.artifactName ? <span style={artifactMiniTextStyle}>{node.artifactName}</span> : null}
                  </div>
                  {node.errorExcerpt ? (
                    <pre style={summaryExcerptStyle}>{node.errorExcerpt}</pre>
                  ) : (
                    <div style={artifactMiniTextStyle}>No bounded error excerpt recorded.</div>
                  )}
                </div>
                {node.artifact ? (
                  <button
                    type="button"
                    onClick={() => onPreview(node.artifact!)}
                    disabled={previewLoading}
                    style={smallButtonStyle}
                  >
                    Preview log
                  </button>
                ) : null}
              </div>
            );
          })}
        </div>
      ) : null}

      {qcHighlights.length ? (
        <div style={{ display: "grid", gap: 7 }}>
          <strong style={summarySectionLabelStyle}>QC highlights</strong>
          {qcHighlights.map((highlight) => {
            const selected = highlight.artifactId === selectedArtifactId;
            const tone = highlight.failed ? "error" : highlight.passed ? "ok" : "neutral";
            return (
              <div
                key={highlight.artifactId}
                style={{
                  ...summaryRowStyle,
                  ...(selected ? selectedArtifactCardStyle : {}),
                }}
              >
                <div style={{ display: "grid", gap: 6, minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 12, overflowWrap: "anywhere" }}>{highlight.artifactName}</strong>
                    <span style={{ ...artifactChipStyle, ...artifactTone(tone) }}>
                      {highlight.status ?? highlight.category}
                    </span>
                    {highlight.subjectId ? <span style={artifactMiniTextStyle}>subject {highlight.subjectId}</span> : null}
                    {highlight.nodeId ? <span style={artifactMiniTextStyle}>node {highlight.nodeId}</span> : null}
                  </div>
                  {highlight.metrics.length ? (
                    <div style={metricChipGridStyle}>
                      {highlight.metrics.map((metric) => (
                        <span key={`${highlight.artifactId}-${metric.label}`} style={metricChipStyle}>
                          {metric.label}: <b>{metric.value}</b>
                        </span>
                      ))}
                    </div>
                  ) : highlight.topLevelKeys.length ? (
                    <div style={artifactMiniTextStyle}>
                      keys: {highlight.topLevelKeys.join(", ")}
                    </div>
                  ) : null}
                  <WarningList warnings={highlight.warnings.slice(0, 3)} />
                  {highlight.errorMessage ? (
                    <div style={{ ...jsonMessageStyle, color: "#b53b3b" }}>{highlight.errorMessage}</div>
                  ) : null}
                  <div style={artifactMiniTextStyle}>{highlight.reference}</div>
                </div>
                <button
                  type="button"
                  onClick={() => onPreview(highlight.artifact)}
                  disabled={previewLoading}
                  style={smallButtonStyle}
                >
                  Preview
                </button>
              </div>
            );
          })}
        </div>
      ) : (
        <div className="empty" style={{ padding: 8 }}>
          {loading ? "Loading QC artifacts..." : "No QC JSON or QC report artifacts were discovered."}
        </div>
      )}

      {provenanceRows.length ? (
        <details>
          <summary style={{ cursor: "pointer", fontWeight: 900 }}>Artifact provenance</summary>
          <div style={{ ...tableScrollStyle, marginTop: 8, maxHeight: 220 }}>
            <table style={artifactTableStyle}>
              <thead>
                <tr>
                  <th style={tableHeaderCellStyle}>source</th>
                  <th style={tableHeaderCellStyle}>node</th>
                  <th style={tableHeaderCellStyle}>kind</th>
                  <th style={tableHeaderCellStyle}>artifact</th>
                  <th style={tableHeaderCellStyle}>state</th>
                </tr>
              </thead>
              <tbody>
                {provenanceRows.map((row) => (
                  <tr key={row.artifactId}>
                    <td style={tableCellStyle}>{row.source}</td>
                    <td style={tableCellStyle}>{row.nodeId || "-"}</td>
                    <td style={tableCellStyle}>{row.kind}</td>
                    <td style={tableCellStyle}>{row.artifactName}</td>
                    <td style={tableCellStyle}>{row.state}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      ) : null}
    </div>
  );
}

function RunArtifactsPanel({
  artifacts,
  runSummary,
  selectedArtifactId,
  preview,
  loading,
  previewLoading,
  error,
  warnings,
  onRefresh,
  onPreview,
  onNotice,
}: {
  artifacts: RunArtifactRecord[];
  runSummary: RunSummaryPreview | null;
  selectedArtifactId: string | null;
  preview: RunArtifactPreviewResponse | null;
  loading: boolean;
  previewLoading: boolean;
  error: string;
  warnings: string[];
  onRefresh: () => void;
  onPreview: (artifact: RunArtifactRecord) => void;
  onNotice: (message: string) => void;
}) {
  const [categoryFilter, setCategoryFilter] = useState<RunArtifactCategoryFilter>("all");
  const [stateFilter, setStateFilter] = useState<RunArtifactStateFilter>("all");
  const [kindFilter, setKindFilter] = useState("all");
  const [sourceFilter, setSourceFilter] = useState("all");
  const sortedArtifacts = useMemo(
    () => sortArtifacts(artifacts, runSummary),
    [artifacts, runSummary]
  );
  const kindOptions = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.kind).filter(Boolean))).sort(),
    [artifacts]
  );
  const sourceOptions = useMemo(
    () => Array.from(new Set(artifacts.map((artifact) => artifact.source || "").filter(Boolean))).sort(),
    [artifacts]
  );
  const filteredArtifacts = useMemo(
    () =>
      filterArtifacts(sortedArtifacts, {
        category: categoryFilter,
        kind: kindFilter,
        state: stateFilter,
        source: sourceFilter,
      }),
    [categoryFilter, kindFilter, sortedArtifacts, sourceFilter, stateFilter]
  );
  const groupedArtifacts = useMemo(
    () => groupArtifacts(filteredArtifacts, runSummary),
    [filteredArtifacts, runSummary]
  );

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Artifacts</h4>
          <span style={subtitleStyle}>Run-scoped reports, QC files, and logs.</span>
        </div>
        <button type="button" onClick={onRefresh} disabled={loading} style={smallButtonStyle}>
          {loading ? "Loading..." : "Refresh"}
        </button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      <WarningList warnings={warnings} />

      {artifacts.length ? (
        <>
          <div style={filterGridStyle}>
            <label style={filterLabelStyle}>
              Category
              <select
                value={categoryFilter}
                onChange={(event) => setCategoryFilter(event.target.value as RunArtifactCategoryFilter)}
                style={selectStyle}
              >
                <option value="all">All categories</option>
                {ARTIFACT_CATEGORIES.map((category) => (
                  <option key={category.key} value={category.key}>{category.label}</option>
                ))}
              </select>
            </label>
            <label style={filterLabelStyle}>
              State
              <select
                value={stateFilter}
                onChange={(event) => setStateFilter(event.target.value as RunArtifactStateFilter)}
                style={selectStyle}
              >
                <option value="all">All states</option>
                <option value="exists">Exists</option>
                <option value="missing">Missing</option>
                <option value="warnings">Warnings</option>
                <option value="previewable">Previewable</option>
              </select>
            </label>
            <label style={filterLabelStyle}>
              Kind
              <select
                value={kindFilter}
                onChange={(event) => setKindFilter(event.target.value)}
                style={selectStyle}
              >
                <option value="all">All kinds</option>
                {kindOptions.map((kind) => (
                  <option key={kind} value={kind}>{kind}</option>
                ))}
              </select>
            </label>
            <label style={filterLabelStyle}>
              Source
              <select
                value={sourceFilter}
                onChange={(event) => setSourceFilter(event.target.value)}
                style={selectStyle}
              >
                <option value="all">All sources</option>
                {sourceOptions.map((source) => (
                  <option key={source} value={source}>{source}</option>
                ))}
              </select>
            </label>
          </div>
          <div style={{ color: "#667085", fontSize: 11, fontWeight: 850, marginBottom: 8 }}>
            Showing {filteredArtifacts.length} of {artifacts.length} artifact(s).
          </div>

          {groupedArtifacts.length ? (
            <div style={{ display: "grid", gap: 12 }}>
              {groupedArtifacts.map((group) => (
                <div key={group.category} style={{ display: "grid", gap: 8 }}>
                  <div style={artifactGroupHeaderStyle}>
                    <span>{group.label}</span>
                    <b>{group.artifacts.length}</b>
                  </div>
                  {group.artifacts.map((artifact) => {
                    const artifactWarnings = getArtifactWarnings(artifact);
                    const previewable = isPreviewableArtifact(artifact);
                    const selected = artifact.artifact_id === selectedArtifactId;
                    return (
                      <div
                        key={artifact.artifact_id}
                        style={{
                          ...artifactCardStyle,
                          ...(selected ? selectedArtifactCardStyle : artifactAttentionStyle(artifact, runSummary)),
                        }}
                      >
                        <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                          <strong style={{ fontSize: 13, overflowWrap: "anywhere" }}>{artifact.name}</strong>
                          <ArtifactBadgeRow artifact={artifact} runSummary={runSummary} />
                        </div>
                        <div style={artifactMetaGridStyle}>
                          <span>size</span>
                          <b>{formatArtifactSize(artifact.size_bytes)}</b>
                          <span>exists</span>
                          <b>{artifact.exists ? "yes" : "no"}</b>
                          <span>modified</span>
                          <b>{formatDate(artifact.modified_at)}</b>
                          <span>source</span>
                          <b>{artifact.source || "-"}</b>
                        </div>
                        <div style={monoPathStyle}>{artifact.relative_path || artifact.path}</div>
                        <WarningList warnings={artifactWarnings} />
                        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
                          <button
                            type="button"
                            onClick={() => onPreview(artifact)}
                            disabled={previewLoading}
                            style={smallButtonStyle}
                          >
                            {previewable ? "Preview" : "Details"}
                          </button>
                          <PathActions label="Artifact" path={artifactPath(artifact)} onNotice={onNotice} />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ))}
            </div>
          ) : (
            <div className="empty">No artifacts match the current filters.</div>
          )}
        </>
      ) : (
        <div className="empty">
          {loading ? "Loading artifacts..." : "No artifacts were discovered for this run."}
        </div>
      )}

      <div style={{ marginTop: 12, paddingTop: 12, borderTop: "1px solid rgba(137, 150, 171, 0.24)" }}>
        {previewLoading ? <div className="empty">Loading artifact preview...</div> : <ArtifactPreview preview={preview} onNotice={onNotice} />}
      </div>
    </div>
  );
}

export default function ProjectRunsPanel({ baseUrl, projectId, projectDir }: Props) {
  const [runs, setRuns] = useState<RunLinkRecord[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [selectedRun, setSelectedRun] = useState<RunLinkRecord | null>(null);
  const [summaryPreview, setSummaryPreview] = useState<RunSummaryPreview | null>(null);
  const [summaryWarnings, setSummaryWarnings] = useState<string[]>([]);
  const [summaryError, setSummaryError] = useState("");
  const [artifacts, setArtifacts] = useState<RunArtifactRecord[]>([]);
  const [artifactWarnings, setArtifactWarnings] = useState<string[]>([]);
  const [artifactError, setArtifactError] = useState("");
  const [artifactsLoading, setArtifactsLoading] = useState(false);
  const [artifactPreviewLoading, setArtifactPreviewLoading] = useState(false);
  const [selectedArtifactId, setSelectedArtifactId] = useState<string | null>(null);
  const [artifactPreview, setArtifactPreview] = useState<RunArtifactPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const selectedFromList = useMemo(
    () => runs.find((run) => run.run_id === selectedRunId) ?? null,
    [runs, selectedRunId]
  );
  const detail = selectedRun ?? selectedFromList;

  useEffect(() => {
    setRuns([]);
    setSelectedRunId(null);
    setSelectedRun(null);
    setSummaryPreview(null);
    setSummaryWarnings([]);
    setSummaryError("");
    resetArtifacts();
    setError("");
    setNotice("");
    if (projectId) {
      void refreshRuns(projectId);
    }
  }, [projectId]);

  async function refreshRuns(nextProjectId = projectId) {
    if (!nextProjectId) {
      setRuns([]);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const payload = await listProjectRuns(baseUrl, nextProjectId);
      const nextRuns = payload.runs ?? [];
      setRuns(nextRuns);
      if (selectedRunId && !nextRuns.some((run) => run.run_id === selectedRunId)) {
        setSelectedRunId(null);
        setSelectedRun(null);
        setSummaryPreview(null);
        setSummaryWarnings([]);
        setSummaryError("");
        resetArtifacts();
      }
      setNotice(nextRuns.length ? `Loaded ${nextRuns.length} project run(s).` : "");
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  async function loadRunDetail(runId: string) {
    if (!projectId) return;
    setSelectedRunId(runId);
    setSelectedRun(null);
    setSummaryPreview(null);
    setSummaryWarnings([]);
    setSummaryError("");
    resetArtifacts();
    setDetailLoading(true);
    setError("");
    try {
      const payload = await getProjectRun(baseUrl, projectId, runId);
      setSelectedRun(payload.run_link);
      setSummaryPreview(normalizeRunSummaryPreview(payload.summary_preview, payload.run_link));
      setSummaryWarnings(mergeSummaryWarnings(payload, payload.summary_preview));
      setSummaryError(payload.summary_preview_error || "");
      setNotice(`Loaded run detail for ${runId}.`);
      void loadArtifacts(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setDetailLoading(false);
    }
  }

  function resetArtifacts() {
    setArtifacts([]);
    setArtifactWarnings([]);
    setArtifactError("");
    setArtifactsLoading(false);
    setArtifactPreviewLoading(false);
    setSelectedArtifactId(null);
    setArtifactPreview(null);
  }

  async function loadArtifacts(runId = selectedRunId) {
    if (!projectId || !runId) return;
    setArtifactsLoading(true);
    setArtifactError("");
    setArtifactPreview(null);
    setSelectedArtifactId(null);
    try {
      const payload = await listProjectRunArtifacts(baseUrl, projectId, runId);
      setArtifacts(payload.artifacts ?? []);
      setArtifactWarnings(payload.warnings ?? []);
    } catch (err) {
      setArtifactError(err instanceof Error ? err.message : String(err));
    } finally {
      setArtifactsLoading(false);
    }
  }

  async function loadArtifactPreview(artifact: RunArtifactRecord) {
    if (!projectId || !selectedRunId) return;
    setSelectedArtifactId(artifact.artifact_id);
    setArtifactPreview(null);
    setArtifactPreviewLoading(true);
    setArtifactError("");
    try {
      const payload = await getProjectRunArtifact(
        baseUrl,
        projectId,
        selectedRunId,
        artifact.artifact_id,
      );
      setArtifactPreview(payload);
    } catch (err) {
      setArtifactError(err instanceof Error ? err.message : String(err));
    } finally {
      setArtifactPreviewLoading(false);
    }
  }

  if (!projectId) {
    return (
      <section style={panelStyle}>
        <div style={headerStyle}>
          <div>
            <h2 style={titleStyle}>Project Runs</h2>
            <span style={subtitleStyle}>Select a project to view reviewed execution history.</span>
          </div>
        </div>
        <div className="empty">No project selected.</div>
      </section>
    );
  }

  return (
    <section style={panelStyle}>
      <div style={headerStyle}>
        <div>
          <h2 style={titleStyle}>Project Runs</h2>
          <span style={subtitleStyle}>Reviewed execute history and artifact entry points.</span>
        </div>
        <button type="button" onClick={() => void refreshRuns()} disabled={loading} style={{ minHeight: 34, padding: "6px 12px", fontWeight: 850 }}>
          {loading ? "Refreshing..." : "Refresh"}
        </button>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      {notice ? (
        <div className="empty" style={{ marginBottom: 12, padding: 10 }}>
          {notice}
        </div>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: 14, alignItems: "start" }}>
        <div style={{ minWidth: 0 }}>
          {runs.length ? (
            <div style={{ display: "grid", gap: 8 }}>
              {runs.map((run) => {
                const selected = run.run_id === selectedRunId;
                const warnings = getRunWarnings(run);
                return (
                  <button
                    key={run.run_link_id}
                    type="button"
                    onClick={() => void loadRunDetail(run.run_id)}
                    style={{
                      display: "grid",
                      gap: 7,
                      width: "100%",
                      padding: 12,
                      border: selected
                        ? "1px solid rgba(56, 103, 214, 0.42)"
                        : "1px solid rgba(137, 150, 171, 0.28)",
                      borderRadius: 8,
                      background: selected ? "rgba(239, 246, 255, 0.9)" : "rgba(255, 255, 255, 0.86)",
                      textAlign: "left",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "center" }}>
                      <strong style={{ fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 12 }}>
                        {shortId(run.run_id)}
                      </strong>
                      <span style={{ ...statusPillStyle, ...statusTone(run.status) }}>{run.status}</span>
                    </div>
                    <div style={miniGridStyle}>
                      <span>run_link_id</span>
                      <b>{shortId(run.run_link_id)}</b>
                      <span>reviewed_plan_id</span>
                      <b>{shortId(run.reviewed_plan_id)}</b>
                      <span>created</span>
                      <b>{formatDate(run.created_at)}</b>
                      <span>updated</span>
                      <b>{formatDate(run.updated_at)}</b>
                    </div>
                    <div style={pathPreviewStyle}>
                      <span>pipeline</span>
                      <b>{run.pipeline_path || "-"}</b>
                      <span>summary</span>
                      <b>{run.summary_path || "-"}</b>
                    </div>
                    {warnings.length ? (
                      <div style={{ color: "#9a5a15", fontSize: 12, fontWeight: 800 }}>
                        {warnings.length} warning(s)
                      </div>
                    ) : null}
                  </button>
                );
              })}
            </div>
          ) : (
            <div className="empty">
              {loading
                ? "Loading project runs..."
                : "No reviewed execution runs have been recorded for this project yet."}
            </div>
          )}
        </div>

        <div style={{ minWidth: 0, border: "1px solid rgba(137, 150, 171, 0.28)", borderRadius: 8, background: "rgba(247, 249, 253, 0.9)", padding: 12 }}>
          <div style={{ ...headerStyle, marginBottom: 10 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 15 }}>Run Detail</h3>
              <span style={subtitleStyle}>
                {detailLoading ? "Loading detail..." : detail ? detail.run_id : "Select a run"}
              </span>
            </div>
            {detail ? <span style={{ ...statusPillStyle, ...statusTone(detail.status) }}>{detail.status}</span> : null}
          </div>

          {detail ? (
            <div style={{ display: "grid", gap: 12 }}>
              <div style={detailGridStyle}>
                <div><span>run_id</span><strong>{detail.run_id}</strong></div>
                <div><span>run_link_id</span><strong>{detail.run_link_id}</strong></div>
                <div><span>reviewed_plan_id</span><strong>{detail.reviewed_plan_id}</strong></div>
                <div><span>audit_id</span><strong>{detail.audit_id || "-"}</strong></div>
                <div><span>created_at</span><strong>{formatDate(detail.created_at)}</strong></div>
                <div><span>updated_at</span><strong>{formatDate(detail.updated_at)}</strong></div>
              </div>

              <div style={{ display: "grid", gap: 10 }}>
                {extractRunPaths(detail, projectDir).map((entry) => (
                  <PathActions
                    key={entry.label}
                    label={entry.label}
                    path={entry.path}
                    onNotice={setNotice}
                  />
                ))}
              </div>

              <WarningList warnings={detail.warnings} />

              <RunQcErrorSummaryCard
                run={detail}
                runSummary={summaryPreview}
                artifacts={artifacts}
                loading={artifactsLoading}
                previewLoading={artifactPreviewLoading}
                selectedArtifactId={selectedArtifactId}
                onPreview={(artifact) => void loadArtifactPreview(artifact)}
              />

              <KeyArtifactsPanel
                artifacts={artifacts}
                runSummary={summaryPreview}
                loading={artifactsLoading}
                previewLoading={artifactPreviewLoading}
                selectedArtifactId={selectedArtifactId}
                onPreview={(artifact) => void loadArtifactPreview(artifact)}
              />

              <div style={summaryPanelStyle}>
                <div style={{ ...headerStyle, marginBottom: 10 }}>
                  <div>
                    <h4 style={{ margin: 0, fontSize: 14 }}>Summary Preview</h4>
                    <span style={subtitleStyle}>Pipeline summary JSON key fields.</span>
                  </div>
                </div>
                <SummaryPreviewCard
                  preview={summaryPreview}
                  summaryPath={detail.summary_path}
                  warnings={summaryWarnings}
                  error={summaryError}
                  loading={detailLoading}
                />
              </div>

              <RunArtifactsPanel
                artifacts={artifacts}
                runSummary={summaryPreview}
                selectedArtifactId={selectedArtifactId}
                preview={artifactPreview}
                loading={artifactsLoading}
                previewLoading={artifactPreviewLoading}
                error={artifactError}
                warnings={artifactWarnings}
                onRefresh={() => void loadArtifacts(detail.run_id)}
                onPreview={(artifact) => void loadArtifactPreview(artifact)}
                onNotice={setNotice}
              />

              <details>
                <summary style={{ cursor: "pointer", fontWeight: 900 }}>Run link payload</summary>
                <div style={{ marginTop: 8 }}>
                  <JsonBlock value={detail.payload} emptyText="No run payload recorded" />
                </div>
              </details>
            </div>
          ) : (
            <div className="empty">Select a run to inspect paths, warnings, and payload.</div>
          )}
        </div>
      </div>
    </section>
  );
}

const panelStyle: CSSProperties = {
  marginTop: 16,
  padding: 16,
  border: "1px solid rgba(137, 150, 171, 0.28)",
  borderRadius: 8,
  background: "rgba(255, 255, 255, 0.88)",
  boxShadow: "0 12px 36px rgba(15, 23, 42, 0.08)",
};

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
};

const titleStyle: CSSProperties = {
  margin: 0,
  fontSize: 18,
};

const subtitleStyle: CSSProperties = {
  color: "#667085",
  fontSize: 12,
  fontWeight: 750,
};

const statusPillStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 24,
  padding: "0 8px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 11,
  fontWeight: 900,
};

const miniGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "120px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

const pathPreviewStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "70px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

const monoPathStyle: CSSProperties = {
  padding: "7px 9px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#111827",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

const summaryMetricsStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
  gap: 8,
};

const summaryPanelStyle: CSSProperties = {
  padding: 12,
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 8,
  background: "rgba(255, 255, 255, 0.72)",
};

const summarySectionLabelStyle: CSSProperties = {
  color: "#344054",
  fontSize: 12,
  fontWeight: 900,
};

const summaryRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "minmax(0, 1fr) auto",
  gap: 10,
  alignItems: "start",
  padding: 10,
  border: "1px solid rgba(137, 150, 171, 0.22)",
  borderRadius: 6,
  background: "#fff",
};

const summaryExcerptStyle: CSSProperties = {
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

const artifactMiniTextStyle: CSSProperties = {
  color: "#667085",
  fontSize: 11,
  fontWeight: 800,
  overflowWrap: "anywhere",
};

const metricChipGridStyle: CSSProperties = {
  display: "flex",
  gap: 6,
  flexWrap: "wrap",
};

const metricChipStyle: CSSProperties = {
  padding: "4px 7px",
  border: "1px solid rgba(137, 150, 171, 0.22)",
  borderRadius: 6,
  background: "rgba(248, 250, 252, 0.95)",
  color: "#344054",
  fontSize: 11,
  fontWeight: 800,
};

const detailGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(170px, 1fr))",
  gap: 8,
};

const smallButtonStyle: CSSProperties = {
  minHeight: 28,
  padding: "4px 9px",
  fontSize: 11,
  fontWeight: 850,
};

const artifactMetaGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "72px minmax(0, 1fr)",
  gap: "3px 8px",
  color: "#667085",
  fontSize: 11,
};

const keyArtifactGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
  gap: 8,
};

const keyArtifactButtonStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  width: "100%",
  minHeight: 106,
  padding: 10,
  borderRadius: 8,
  textAlign: "left",
};

const keyArtifactPathStyle: CSSProperties = {
  color: "#667085",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  overflowWrap: "anywhere",
};

const filterGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(130px, 1fr))",
  gap: 8,
  marginBottom: 8,
};

const filterLabelStyle: CSSProperties = {
  display: "grid",
  gap: 4,
  color: "#667085",
  fontSize: 11,
  fontWeight: 900,
};

const selectStyle: CSSProperties = {
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

const artifactGroupHeaderStyle: CSSProperties = {
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

const artifactCardStyle: CSSProperties = {
  display: "grid",
  gap: 7,
  padding: 10,
  borderRadius: 8,
};

const selectedArtifactCardStyle: CSSProperties = {
  border: "1px solid rgba(56, 103, 214, 0.42)",
  background: "rgba(239, 246, 255, 0.86)",
};

const artifactChipStyle: CSSProperties = {
  display: "inline-flex",
  alignItems: "center",
  minHeight: 22,
  padding: "0 7px",
  border: "1px solid",
  borderRadius: 999,
  fontSize: 10,
  fontWeight: 900,
};

const artifactPreviewTextStyle: CSSProperties = {
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

const jsonSummaryGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))",
  gap: 8,
};

const jsonKeyChipStyle: CSSProperties = {
  padding: "4px 7px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#344054",
  fontFamily: '"Cascadia Mono", "Consolas", monospace',
  fontSize: 11,
  fontWeight: 800,
};

const jsonMessageStyle: CSSProperties = {
  padding: "7px 9px",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
  color: "#9a5a15",
  fontSize: 12,
  overflowWrap: "anywhere",
};

const tableScrollStyle: CSSProperties = {
  maxHeight: 320,
  overflow: "auto",
  border: "1px solid rgba(137, 150, 171, 0.24)",
  borderRadius: 6,
  background: "#fff",
};

const artifactTableStyle: CSSProperties = {
  width: "100%",
  borderCollapse: "collapse",
  fontSize: 12,
};

const tableHeaderCellStyle: CSSProperties = {
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

const tableCellStyle: CSSProperties = {
  padding: "7px 8px",
  borderBottom: "1px solid rgba(137, 150, 171, 0.16)",
  color: "#111827",
  verticalAlign: "top",
  overflowWrap: "anywhere",
};

const markdownPreviewStyle: CSSProperties = {
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

const markdownCodeStyle: CSSProperties = {
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

function artifactAttentionStyle(
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

function artifactTone(value: string): CSSProperties {
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
