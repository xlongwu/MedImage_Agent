import type { RunArtifactPreviewResponse } from "../../types";
import { JsonBlock } from "../JsonBlock";
import {
  artifactPath,
  formatArtifactSize,
  markdownPreviewBlocks,
  mergeSummaryWarnings,
  normalizeCsvPreview,
  normalizeJsonPreviewSummary,
} from "../projectRunsPanelModel";
import {
  artifactMetaGridStyle,
  artifactPreviewTextStyle,
  artifactTableStyle,
  artifactTone,
  formatDate,
  jsonKeyChipStyle,
  jsonMessageStyle,
  jsonSummaryGridStyle,
  markdownCodeStyle,
  markdownPreviewStyle,
  PathActions,
  statusPillStyle,
  tableCellStyle,
  tableHeaderCellStyle,
  tableScrollStyle,
  WarningList,
} from "./pathActions";

export function ArtifactPreviewPane({
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
