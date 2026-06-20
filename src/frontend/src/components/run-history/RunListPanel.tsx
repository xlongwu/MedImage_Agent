import type { RunLinkRecord } from "../../types";
import { getRunWarnings } from "../projectRunsPanelModel";
import {
  formatDate,
  miniGridStyle,
  pathPreviewStyle,
  shortId,
  statusPillStyle,
  statusTone,
} from "./pathActions";

export function RunListPanel({
  runs,
  loading,
  error,
  selectedRunId,
  onSelect,
}: {
  runs: RunLinkRecord[];
  loading: boolean;
  error?: string;
  selectedRunId: string | null;
  onSelect: (runId: string) => void;
}) {
  if (error) {
    return <div className="errorBox">{error}</div>;
  }

  if (loading && !runs.length) {
    return <div className="empty">Loading project runs...</div>;
  }

  if (!runs.length) {
    return (
      <div className="empty">
        No reviewed execution runs have been recorded for this project yet.
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gap: 8 }}>
      {runs.map((run) => {
        const selected = run.run_id === selectedRunId;
        const warnings = getRunWarnings(run);
        return (
          <button
            key={run.run_link_id}
            type="button"
            onClick={() => onSelect(run.run_id)}
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
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 10,
                alignItems: "center",
              }}
            >
              <strong
                style={{ fontFamily: '"Cascadia Mono", "Consolas", monospace', fontSize: 12 }}
              >
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
  );
}
