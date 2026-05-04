import React, { useState, useEffect } from "react";
import {
  getExperimentDashboard,
  refreshExperimentDashboard,
} from "../api";
import {
  SimpleBarChart,
  SimpleLineChart,
  SimplePieChart,
} from "./SimpleCharts";

interface DashboardData {
  ok?: boolean;
  runs_total?: number;
  success_total?: number;
  failed_total?: number;
  partial_total?: number;
  invalid_total?: number;
  unknown_total?: number;
  mean_duration_seconds?: number;
  median_duration_seconds?: number;
  max_duration_seconds?: number;
  total_outputs?: number;
  total_warnings?: number;
  total_errors?: number;
  status_distribution?: Record<string, number>;
  pipeline_distribution?: Record<string, number>;
  scheduler_distribution?: Record<string, number>;
  run_type_distribution?: Record<string, number>;
  duration_trend?: Array<{
    index?: number;
    run_id?: string;
    duration_seconds?: number;
    status?: string;
  }>;
  error_warning_trend?: Array<{
    index?: number;
    run_id?: string;
    warnings_count?: number;
    errors_count?: number;
  }>;
  output_trend?: Array<{
    index?: number;
    run_id?: string;
    outputs_count?: number;
  }>;
  runs?: Array<{
    index?: number;
    run_id?: string;
    run_type?: string;
    pipeline_id?: string;
    status?: string;
    duration_seconds?: number;
    scheduler_mode?: string;
    nodes_total?: number;
    nodes_success?: number;
    nodes_failed?: number;
    outputs_count?: number;
    warnings_count?: number;
    errors_count?: number;
  }>;
}

interface ExperimentDashboardProps {
  baseUrl: string;
}

export function ExperimentDashboard({ baseUrl }: ExperimentDashboardProps) {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleLoadDashboard();
  }, [baseUrl]);

  const handleLoadDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = (await getExperimentDashboard(baseUrl)) as { dashboard?: DashboardData };
      setDashboard(result.dashboard || null);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = (await refreshExperimentDashboard(baseUrl)) as DashboardData;
      setDashboard(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return "N/A";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${(seconds % 60).toFixed(0)}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const getStatusColor = (status?: string) => {
    switch (status?.toUpperCase()) {
      case "SUCCESS":
        return "#4caf50";
      case "FAILED":
        return "#f44336";
      case "PARTIAL":
        return "#ff9800";
      case "INVALID":
        return "#9c27b0";
      default:
        return "#607d8b";
    }
  };

  const toBarData = (distribution?: Record<string, number>) => {
    if (!distribution) return [];
    return Object.entries(distribution).map(([label, value]) => ({ label, value }));
  };

  const toLineData = (trend?: Array<{ index?: number; duration_seconds?: number }>) => {
    if (!trend) return [];
    return trend.map((item) => ({
      label: `Run ${item.index}`,
      value: item.duration_seconds || 0,
    }));
  };

  return (
    <div style={{ padding: 16, borderTop: "2px solid #ff5722", marginTop: 24 }}>
      <h2>Experiment Dashboard</h2>

      <div style={{ marginBottom: 16 }}>
        <button onClick={handleLoadDashboard} disabled={loading} style={{ marginRight: 8 }}>
          {loading ? "Loading..." : "Load Dashboard"}
        </button>
        <button onClick={handleRefresh} disabled={loading} style={{ backgroundColor: "#2196f3", color: "white" }}>
          {loading ? "Refreshing..." : "Refresh Data"}
        </button>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {dashboard && (
        <>
          {/* Summary Cards */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 12, marginBottom: 24 }}>
            <div style={{ padding: 16, background: "#e3f2fd", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Total Runs</div>
              <div style={{ fontSize: 24, fontWeight: "bold" }}>{dashboard.runs_total || 0}</div>
            </div>
            <div style={{ padding: 16, background: "#e8f5e9", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Success</div>
              <div style={{ fontSize: 24, fontWeight: "bold", color: "#4caf50" }}>{dashboard.success_total || 0}</div>
            </div>
            <div style={{ padding: 16, background: "#ffebee", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Failed</div>
              <div style={{ fontSize: 24, fontWeight: "bold", color: "#f44336" }}>{dashboard.failed_total || 0}</div>
            </div>
            <div style={{ padding: 16, background: "#fff3e0", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Partial</div>
              <div style={{ fontSize: 24, fontWeight: "bold", color: "#ff9800" }}>{dashboard.partial_total || 0}</div>
            </div>
            <div style={{ padding: 16, background: "#f3e5f5", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Mean Duration</div>
              <div style={{ fontSize: 18, fontWeight: "bold" }}>
                {formatDuration(dashboard.mean_duration_seconds)}
              </div>
            </div>
            <div style={{ padding: 16, background: "#fce4ec", borderRadius: 4 }}>
              <div style={{ fontSize: 12, color: "#666" }}>Total Outputs</div>
              <div style={{ fontSize: 24, fontWeight: "bold" }}>{dashboard.total_outputs || 0}</div>
            </div>
          </div>

          {/* Charts */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: 16, marginBottom: 24 }}>
            {dashboard.status_distribution && (
              <SimplePieChart title="Status Distribution" data={toBarData(dashboard.status_distribution)} />
            )}
            {dashboard.pipeline_distribution && Object.keys(dashboard.pipeline_distribution).length > 0 && (
              <SimpleBarChart title="Pipeline Distribution" data={toBarData(dashboard.pipeline_distribution)} />
            )}
            {dashboard.scheduler_distribution && (
              <SimpleBarChart title="Scheduler Distribution" data={toBarData(dashboard.scheduler_distribution)} />
            )}
            {dashboard.run_type_distribution && (
              <SimpleBarChart title="Run Type Distribution" data={toBarData(dashboard.run_type_distribution)} />
            )}
            {dashboard.duration_trend && dashboard.duration_trend.length > 0 && (
              <SimpleLineChart title="Duration Trend" data={toLineData(dashboard.duration_trend)} />
            )}
          </div>

          {/* Latest Runs Table */}
          {dashboard.runs && dashboard.runs.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3>Latest Runs</h3>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                  <thead>
                    <tr style={{ background: "#f5f5f5" }}>
                      <th style={{ padding: 8, textAlign: "left" }}>#</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Run ID</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Pipeline</th>
                      <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                      <th style={{ padding: 8, textAlign: "right" }}>Duration</th>
                      <th style={{ padding: 8, textAlign: "center" }}>Nodes</th>
                      <th style={{ padding: 8, textAlign: "center" }}>Outputs</th>
                      <th style={{ padding: 8, textAlign: "center" }}>⚠️</th>
                      <th style={{ padding: 8, textAlign: "center" }}>❌</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.runs.slice(-10).reverse().map((run, idx) => (
                      <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                        <td style={{ padding: 8 }}>{run.index}</td>
                        <td style={{ padding: 8, fontFamily: "monospace", fontSize: 11 }}>{run.run_id}</td>
                        <td style={{ padding: 8 }}>
                          <span style={{ padding: "2px 6px", borderRadius: 4, background: "#e3f2fd", fontSize: 11 }}>
                            {run.run_type}
                          </span>
                        </td>
                        <td style={{ padding: 8, fontSize: 12 }}>{run.pipeline_id}</td>
                        <td style={{ padding: 8 }}>
                          <span
                            style={{
                              padding: "2px 6px",
                              borderRadius: 4,
                              background: getStatusColor(run.status),
                              color: "white",
                              fontSize: 11,
                            }}
                          >
                            {run.status}
                          </span>
                        </td>
                        <td style={{ padding: 8, textAlign: "right" }}>
                          {formatDuration(run.duration_seconds)}
                        </td>
                        <td style={{ padding: 8, textAlign: "center" }}>
                          {run.nodes_success}/{run.nodes_total}
                        </td>
                        <td style={{ padding: 8, textAlign: "center" }}>{run.outputs_count}</td>
                        <td style={{ padding: 8, textAlign: "center" }}>
                          {run.warnings_count ? (
                            <span style={{ color: "orange" }}>{run.warnings_count}</span>
                          ) : (
                            "0"
                          )}
                        </td>
                        <td style={{ padding: 8, textAlign: "center" }}>
                          {run.errors_count ? (
                            <span style={{ color: "red" }}>{run.errors_count}</span>
                          ) : (
                            "0"
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Metrics Summary */}
          <div style={{ padding: 16, background: "#f5f5f5", borderRadius: 4 }}>
            <h3>Metrics Summary</h3>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 12 }}>
              <div>
                <strong>Duration:</strong> Mean {formatDuration(dashboard.mean_duration_seconds)}, Median{" "}
                {formatDuration(dashboard.median_duration_seconds)}, Max {formatDuration(dashboard.max_duration_seconds)}
              </div>
              <div>
                <strong>Outputs:</strong> {dashboard.total_outputs} total
              </div>
              <div>
                <strong>Warnings:</strong> {dashboard.total_warnings} total
              </div>
              <div>
                <strong>Errors:</strong> {dashboard.total_errors} total
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
