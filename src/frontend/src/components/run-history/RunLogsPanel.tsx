import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, listProjectRunLogs } from "../../api";
import type { ProjectRunLogRecord } from "../../types";
import {
  formatDate,
  headerStyle,
  monoPathStyle,
  smallButtonStyle,
  statusPillStyle,
  subtitleStyle,
  summaryPanelStyle,
  WarningList,
} from "./pathActions";

type Props = {
  baseUrl?: string;
  projectId: string | null;
  runId: string | null;
  maxBytes?: number;
};

function formatSize(bytes: number | null | undefined): string {
  if (bytes == null) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function RunLogsPanel({ baseUrl, projectId, runId, maxBytes }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [logs, setLogs] = useState<ProjectRunLogRecord[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedContent, setExpandedContent] = useState<Set<string>>(new Set());
  const requestRef = useRef(0);

  useEffect(() => {
    if (!projectId || !runId) {
      setLogs([]);
      setWarnings([]);
      setError("");
      return;
    }
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    setError("");
    listProjectRunLogs(effectiveBase, projectId, runId, {
      maxBytes: maxBytes ?? 20000,
      includeContent: true,
    })
      .then((res) => {
        if (requestId !== requestRef.current) return;
        setLogs(res.logs ?? []);
        setWarnings(res.warnings ?? []);
      })
      .catch((err) => {
        if (requestId !== requestRef.current) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (requestId === requestRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId, runId, maxBytes]);

  function toggleContent(logId: string) {
    setExpandedContent((prev) => {
      const next = new Set(prev);
      if (next.has(logId)) next.delete(logId);
      else next.add(logId);
      return next;
    });
  }

  const toggleAll = () => {
    if (expandedContent.size > 0) {
      setExpandedContent(new Set());
    } else {
      setExpandedContent(new Set(logs.filter((l) => l.content).map((l) => l.log_id)));
    }
  };

  if (!projectId || !runId) {
    return (
      <div style={summaryPanelStyle}>
        <div style={headerStyle}>
          <h4 style={{ margin: 0, fontSize: 14 }}>Run Logs</h4>
        </div>
        <div className="empty">Select a run to view logs.</div>
      </div>
    );
  }

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Run Logs</h4>
          <span style={subtitleStyle}>
            {loading ? "Loading..." : `${logs.length} log(s)`}
          </span>
        </div>
        {logs.length > 0 && (
          <button type="button" onClick={toggleAll} style={smallButtonStyle}>
            {expandedContent.size > 0 ? "Collapse all" : "Expand all"}
          </button>
        )}
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      <WarningList warnings={warnings} />

      {logs.length ? (
        <div style={{ display: "grid", gap: 8 }}>
          {logs.map((log) => (
            <div
              key={log.log_id}
              style={{
                display: "grid",
                gap: 7,
                padding: 10,
                border: "1px solid rgba(137, 150, 171, 0.24)",
                borderRadius: 6,
                background: "#fff",
              }}
            >
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                <strong style={{ fontSize: 13, overflowWrap: "anywhere" }}>{log.name}</strong>
                <span style={{
                  ...statusPillStyle,
                  background: log.exists ? "#e8f5e9" : "#ffebee",
                  color: log.exists ? "#176b3b" : "#b53b3b",
                  borderColor: log.exists ? "rgba(33, 150, 83, 0.24)" : "rgba(235, 87, 87, 0.26)",
                }}>
                  {log.exists ? "exists" : "missing"}
                </span>
                {log.truncated ? (
                  <span style={{
                    ...statusPillStyle,
                    background: "#fff7ed",
                    color: "#9a5a15",
                    borderColor: "rgba(242, 153, 74, 0.28)",
                  }}>
                    truncated
                  </span>
                ) : null}
                <span style={{ fontSize: 11, color: "#667085", marginLeft: "auto" }}>
                  {formatSize(log.size_bytes)}
                </span>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "60px minmax(0, 1fr)", gap: "2px 8px", fontSize: 11, color: "#667085" }}>
                <span>path</span>
                <b style={{ fontFamily: '"Cascadia Mono", "Consolas", monospace', overflowWrap: "anywhere" }}>
                  {log.relative_path || log.path}
                </b>
                <span>modified</span>
                <b>{formatDate(log.modified_at)}</b>
              </div>

              <WarningList warnings={log.warnings} />

              {log.exists && log.content != null ? (
                <div>
                  <button
                    type="button"
                    onClick={() => toggleContent(log.log_id)}
                    style={smallButtonStyle}
                  >
                    {expandedContent.has(log.log_id) ? "Hide content" : "Show content"}
                  </button>
                  {expandedContent.has(log.log_id) && (
                    <pre
                      style={{
                        marginTop: 8,
                        maxHeight: 260,
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
                      }}
                    >
                      {log.content || "(empty)"}
                    </pre>
                  )}
                </div>
              ) : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          {loading ? "Loading logs..." : "No run logs were discovered for this run."}
        </div>
      )}
    </div>
  );
}
