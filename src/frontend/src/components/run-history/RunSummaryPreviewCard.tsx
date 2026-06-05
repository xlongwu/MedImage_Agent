import type { RunSummaryPreview } from "../../types";
import { JsonBlock } from "../JsonBlock";
import {
  mergeSummaryWarnings,
  missingSummaryWarning,
} from "../projectRunsPanelModel";
import {
  detailGridStyle,
  formatDate,
  monoPathStyle,
  statusPillStyle,
  statusTone,
  SummaryMetric,
  summaryMetricsStyle,
  WarningList,
} from "./pathActions";

export function RunSummaryPreviewCard({
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
