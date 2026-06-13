import React, { useEffect, useState } from "react";
import { DEFAULT_API_BASE, getInsights, getLatestQuickstartDemo } from "../../lib/api";
import type { InsightsDashboard } from "../../lib/api";
import type { WorkflowAction, WorkflowRunResult, WorkflowState } from "../../state/workflowTypes";

interface Props { state: WorkflowState; dispatch: React.Dispatch<WorkflowAction>; }

export function ResultsOverviewStep({ state, dispatch }: Props) {
  const [demoData, setDemoData] = useState<WorkflowRunResult | null>(null);
  const [insights, setInsights] = useState<InsightsDashboard | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void loadResults();
  }, []);

  const loadResults = async () => {
    setLoading(true);
    try {
      // Use workflow result if available, otherwise fallback to latest demo
      const stored = window.__workflowResult;
      if (stored) {
        setDemoData(stored);
      } else {
        try {
          setDemoData(await getLatestQuickstartDemo(DEFAULT_API_BASE));
        } catch {
          setDemoData(null);
        }
      }
      try {
        setInsights(await getInsights(DEFAULT_API_BASE));
      } catch {
        setInsights(null);
      }
    } catch {}
    setLoading(false);
  };

  const steps = demoData?.steps || [];
  const passed = steps.filter((s) => s.ok).length;

  return (
    <div>
      <h2>Step 5: Results</h2>

      {loading && <div style={{ textAlign: "center", padding: 20, color: "#666" }}>Loading results...</div>}

      {demoData && (
        <div style={{ marginBottom: 20 }}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))", gap: 12, marginBottom: 16 }}>
            <ResultCard label="Run Status" value={demoData.ok ? "PASS" : "FAIL"} color={demoData.ok ? "#4caf50" : "#f44336"} />
            <ResultCard label="Steps" value={`${passed}/${steps.length}`} color={passed === steps.length ? "#4caf50" : "#ff9800"} />
            <ResultCard label="Type" value={demoData.workflow_type === "real_data_pipeline" ? "Real Data" : "Synthetic"} color="#1976d2" />
            {demoData.total_time_s && <ResultCard label="Time" value={`${demoData.total_time_s}s`} color="#1976d2" />}
          </div>

          {demoData.metrics && (
            <div style={{ marginBottom: 16 }}>
              <h3>Subject Metrics (Real Data Pipeline)</h3>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead><tr style={{ background: "#f5f5f5" }}>
                  <th style={th}>Subject</th><th style={th}>ALFF Mean</th><th style={th}>ReHo Mean</th>
                  <th style={th}>FC |r|</th><th style={th}>Shape</th><th style={th}>Time</th>
                </tr></thead>
                <tbody>
                  {Object.entries(demoData.metrics).map(([sid, m]) => (
                    <tr key={sid} style={{ borderBottom: "1px solid #eee" }}>
                      <td style={td}>{sid}</td>
                      <td style={td}>{m.alff_mean}</td>
                      <td style={td}>{m.reho_mean}</td>
                      <td style={td}>{m.fc_mean}</td>
                      <td style={{ ...td, fontSize: 11 }}>{m.shape?.join("×")}</td>
                      <td style={td}>{m.time_s}s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Step Results</h3>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: "#f5f5f5" }}>
              <th style={th}>Step</th><th style={th}>Status</th>
            </tr></thead>
            <tbody>
              {steps.map((s, i: number) => (
                <tr key={i} style={{ borderBottom: "1px solid #eee" }}>
                  <td style={td}>{s.step}</td>
                  <td style={{ ...td, color: s.ok ? "#4caf50" : "#f44336", fontWeight: 600 }}>{s.ok ? "PASS" : "FAIL"}</td>
                </tr>
              ))}
            </tbody>
          </table>

          {demoData.outputs && (
            <div style={{ marginTop: 12, padding: 8, background: "#e8f5e9", borderRadius: 4, fontSize: 12 }}>
              <strong>Output directories:</strong> {Object.entries(demoData.outputs).map(([k, v]) => `${k}=${String(v)}`).join(", ")}
            </div>
          )}
        </div>
      )}

      {insights && insights.summary && (
        <div style={{ padding: 16, background: "#e3f2fd", borderRadius: 8, marginBottom: 16 }}>
          <h3 style={{ marginTop: 0 }}>Insights Dashboard</h3>
          <div style={{ fontSize: 14 }}>
            Runs: <strong>{insights.summary.total_runs}</strong>
            {" | "}Success Rate: <strong>{insights.summary.success_rate}%</strong>
            {" | "}Avg Duration: <strong>{insights.summary.avg_duration_seconds}s</strong>
            {" | "}Errors: <strong>{insights.summary.total_errors_logged}</strong>
          </div>
        </div>
      )}

      {!demoData && !loading && (
        <div style={{ padding: 24, textAlign: "center", color: "#999" }}>
          No results yet. Go back to Step 4 and run a demo first.
        </div>
      )}

      <div style={{ display: "flex", gap: 8, marginTop: 20 }}>
        <button onClick={() => dispatch({ type: "SET_STEP", step: 4 })} style={btnBack}>Back</button>
        <button onClick={() => { dispatch({ type: "RESET" }); dispatch({ type: "SET_STEP", step: 0 }); }} style={btnNew}>
          Start New Project
        </button>
        <button onClick={loadResults} style={btnRefresh}>Refresh</button>
      </div>
    </div>
  );
}

function ResultCard({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div style={{ padding: 12, borderRadius: 8, background: "#f9f9f9", border: "1px solid #eee", textAlign: "center" }}>
      <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

const th: React.CSSProperties = { padding: "6px 12px", textAlign: "left", fontWeight: 600 };
const td: React.CSSProperties = { padding: "5px 12px" };
const btnBack: React.CSSProperties = { padding: "8px 20px", background: "#f5f5f5", border: "1px solid #ccc", borderRadius: 4, cursor: "pointer" };
const btnNew: React.CSSProperties = { padding: "8px 20px", background: "#1976d2", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer", fontWeight: 600 };
const btnRefresh: React.CSSProperties = { padding: "8px 20px", background: "#ff9800", color: "#fff", border: "none", borderRadius: 4, cursor: "pointer" };
