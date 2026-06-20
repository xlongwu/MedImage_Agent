import { useEffect, useState } from "react";
import { getProjectRunStateTimeline } from "../../lib/api/legacy";
import type { ProjectRunStateTimelineResponse } from "../../types";
import { statusPillStyle, subtitleStyle } from "./pathActions";

type Props = {
  baseUrl?: string;
  projectId?: string | null;
  runId?: string | null;
};

type Tone = "ok" | "info" | "warning" | "error" | "unknown";

function stateTone(state: string): Tone {
  const s = (state || "").toLowerCase();
  if (["succeeded", "reused"].includes(s)) return "ok";
  if (["running", "ready", "preflight", "queued", "created"].includes(s)) return "info";
  if (["failed", "blocked", "timeout", "interrupted", "invalidated"].includes(s)) return "error";
  if (["cancelled", "skipped"].includes(s)) return "unknown";
  return "unknown";
}

function toneColor(tone: Tone): string {
  switch (tone) {
    case "ok":
      return "#2e7d32";
    case "info":
      return "#1565c0";
    case "warning":
      return "#e65100";
    case "error":
      return "#c62828";
    default:
      return "#888";
  }
}

const badgeStyle = (tone: Tone): React.CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 4,
  fontSize: 11,
  fontWeight: 700,
  color: "#fff",
  background: toneColor(tone),
  whiteSpace: "nowrap",
});

const boolBadge = (v: boolean): React.CSSProperties => ({
  display: "inline-block",
  padding: "2px 8px",
  borderRadius: 4,
  fontSize: 10,
  fontWeight: 600,
  color: v ? "#2e7d32" : "#888",
  background: v ? "#e8f5e9" : "#f5f5f5",
});

export function RunStateTimelinePanel({ baseUrl, projectId, runId }: Props) {
  const [data, setData] = useState<ProjectRunStateTimelineResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!baseUrl || !projectId || !runId) {
      setData(null);
      setError(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);

    getProjectRunStateTimeline(baseUrl, projectId, runId)
      .then((res) => {
        if (!cancelled) {
          setData(res);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [baseUrl, projectId, runId]);

  // Empty state
  if (!projectId || !runId) {
    return <div className="empty">Select a run to view state timeline.</div>;
  }

  // Loading
  if (loading) {
    return <div className="empty">Loading state timeline...</div>;
  }

  // Error
  if (error) {
    return <div style={{ color: "#c62828", fontSize: 13 }}>Failed to load timeline: {error}</div>;
  }

  // No data
  if (!data) {
    return <div className="empty">No timeline data available.</div>;
  }

  const runTone = stateTone(data.current_run_state);

  return (
    <div>
      {/* ── Run State Summary ── */}
      <div style={{ marginBottom: 14 }}>
        <h4 style={{ margin: "0 0 4px 0", fontSize: 13, fontWeight: 700 }}>Run State</h4>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span style={badgeStyle(runTone)}>{data.current_run_state}</span>
          <span style={boolBadge(data.terminal)}>
            {data.terminal ? "terminal" : "non-terminal"}
          </span>
          {data.retry_eligible && <span style={boolBadge(true)}>retry eligible</span>}
          {data.resume_eligible && <span style={boolBadge(true)}>resume eligible</span>}
        </div>
      </div>

      {/* ── Warnings / Errors ── */}
      {(data.warnings.length > 0 || data.errors.length > 0) && (
        <div style={{ marginBottom: 14 }}>
          {data.warnings.map((w, i) => (
            <div key={`tw-${i}`} style={{ fontSize: 11, color: "#e65100" }}>
              ⚠ {w}
            </div>
          ))}
          {data.errors.map((e, i) => (
            <div key={`te-${i}`} style={{ fontSize: 11, color: "#c62828" }}>
              ✗ {e}
            </div>
          ))}
        </div>
      )}

      {/* ── Timeline Events ── */}
      <div style={{ marginBottom: 14 }}>
        <h4 style={{ margin: "0 0 4px 0", fontSize: 13, fontWeight: 700 }}>Timeline Events</h4>
        {data.events.length === 0 ? (
          <div style={{ fontSize: 12, color: "#888" }}>
            No timeline events were derived for this run.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 6 }}>
            {data.events.map((ev, i) => {
              const tone = stateTone(ev.state);
              return (
                <div
                  key={`ev-${i}`}
                  style={{
                    borderLeft: `3px solid ${toneColor(tone)}`,
                    paddingLeft: 8,
                    fontSize: 12,
                  }}
                >
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <span style={badgeStyle(tone)}>{ev.state}</span>
                    <span style={{ color: "#667085", fontSize: 10 }}>{ev.source}</span>
                    {ev.node_id && (
                      <span style={{ color: "#888", fontSize: 10 }}>node: {ev.node_id}</span>
                    )}
                    {ev.timestamp && (
                      <span style={{ color: "#999", fontSize: 10 }}>{ev.timestamp}</span>
                    )}
                  </div>
                  {ev.message && <div style={{ color: "#344054", marginTop: 2 }}>{ev.message}</div>}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Node States ── */}
      <div>
        <h4 style={{ margin: "0 0 4px 0", fontSize: 13, fontWeight: 700 }}>Node States</h4>
        {data.nodes.length === 0 ? (
          <div style={{ fontSize: 12, color: "#888" }}>
            No node-level state records were derived for this run.
          </div>
        ) : (
          <div style={{ display: "grid", gap: 6 }}>
            {data.nodes.map((n, i) => {
              const tone = stateTone(n.state);
              return (
                <div
                  key={`nd-${i}`}
                  style={{
                    borderLeft: `3px solid ${toneColor(tone)}`,
                    paddingLeft: 8,
                    fontSize: 12,
                  }}
                >
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <strong style={{ fontSize: 12 }}>{n.node_id}</strong>
                    <span style={badgeStyle(tone)}>{n.state}</span>
                    {n.terminal && <span style={boolBadge(true)}>terminal</span>}
                    {n.retry_eligible && <span style={boolBadge(true)}>retry</span>}
                    {n.reuse_eligible && <span style={boolBadge(true)}>reuse</span>}
                  </div>
                  {n.warnings.length > 0 && (
                    <div style={{ fontSize: 10, color: "#e65100", marginTop: 2 }}>
                      {n.warnings.length} warning{n.warnings.length > 1 ? "s" : ""}
                    </div>
                  )}
                  {n.errors.length > 0 && (
                    <div style={{ fontSize: 10, color: "#c62828", marginTop: 2 }}>
                      {n.errors.length} error{n.errors.length > 1 ? "s" : ""}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
