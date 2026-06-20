import { useEffect, useRef, useState } from "react";
import { DEFAULT_API_BASE, listProjectRunEvents } from "../../lib/api/legacy";
import type { ProjectRunEventRecord } from "../../types";
import {
  formatDate,
  headerStyle,
  monoPathStyle,
  statusPillStyle,
  subtitleStyle,
  summaryPanelStyle,
  WarningList,
} from "./pathActions";

type Props = {
  baseUrl?: string;
  projectId: string | null;
  runId: string | null;
};

const levelTone = (level: string): React.CSSProperties => {
  switch (level) {
    case "error":
      return { background: "#ffebee", color: "#b53b3b", borderColor: "rgba(235, 87, 87, 0.26)" };
    case "warning":
      return { background: "#fff7ed", color: "#9a5a15", borderColor: "rgba(242, 153, 74, 0.28)" };
    default:
      return { background: "#eef1f6", color: "#667085", borderColor: "rgba(137, 150, 171, 0.28)" };
  }
};

export function RunEventsPanel({ baseUrl, projectId, runId }: Props) {
  const effectiveBase = baseUrl ?? DEFAULT_API_BASE;
  const [events, setEvents] = useState<ProjectRunEventRecord[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const requestRef = useRef(0);

  useEffect(() => {
    if (!projectId || !runId) {
      setEvents([]);
      setWarnings([]);
      setError("");
      return;
    }
    const requestId = requestRef.current + 1;
    requestRef.current = requestId;
    setLoading(true);
    setError("");
    listProjectRunEvents(effectiveBase, projectId, runId)
      .then((res) => {
        if (requestId !== requestRef.current) return;
        setEvents(res.events ?? []);
        setWarnings(res.warnings ?? []);
      })
      .catch((err) => {
        if (requestId !== requestRef.current) return;
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => {
        if (requestId === requestRef.current) setLoading(false);
      });
  }, [effectiveBase, projectId, runId]);

  if (!projectId || !runId) {
    return (
      <div style={summaryPanelStyle}>
        <div style={headerStyle}>
          <h4 style={{ margin: 0, fontSize: 14 }}>Run Events</h4>
        </div>
        <div className="empty">Select a run to view events.</div>
      </div>
    );
  }

  return (
    <div style={summaryPanelStyle}>
      <div style={{ ...headerStyle, marginBottom: 10 }}>
        <div>
          <h4 style={{ margin: 0, fontSize: 14 }}>Run Events</h4>
          <span style={subtitleStyle}>{loading ? "Loading..." : `${events.length} event(s)`}</span>
        </div>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}
      <WarningList warnings={warnings} />

      {events.length ? (
        <div style={{ display: "grid", gap: 6 }}>
          {events.map((event, idx) => (
            <div
              key={`${event.timestamp}-${idx}`}
              style={{
                display: "grid",
                gap: 5,
                padding: 10,
                border: "1px solid rgba(137, 150, 171, 0.22)",
                borderRadius: 6,
                background: "#fff",
              }}
            >
              <div style={{ display: "flex", gap: 6, flexWrap: "wrap", alignItems: "center" }}>
                <span style={{ ...statusPillStyle, ...levelTone(event.level) }}>{event.level}</span>
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    minHeight: 22,
                    padding: "0 7px",
                    borderRadius: 999,
                    fontSize: 10,
                    fontWeight: 900,
                    background: "#eef1f6",
                    color: "#667085",
                    border: "1px solid rgba(137, 150, 171, 0.28)",
                  }}
                >
                  {event.source}
                </span>
                {event.node_id ? (
                  <span style={{ fontSize: 11, color: "#667085" }}>node: {event.node_id}</span>
                ) : null}
                {event.subject_id ? (
                  <span style={{ fontSize: 11, color: "#667085" }}>
                    subject: {event.subject_id}
                  </span>
                ) : null}
                <span style={{ fontSize: 11, color: "#98a2b3", marginLeft: "auto" }}>
                  {formatDate(event.timestamp)}
                </span>
              </div>
              <div style={{ fontSize: 12, color: "#344054", lineHeight: 1.5 }}>{event.message}</div>
              {event.path ? <div style={monoPathStyle}>{event.path}</div> : null}
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">
          {loading ? "Loading events..." : "No run events were discovered for this run."}
        </div>
      )}
    </div>
  );
}
