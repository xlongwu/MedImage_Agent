import React, { useState, useEffect } from "react";
import { getExperimentDashboard, refreshExperimentDashboard } from "../lib/api/legacy";
import { SimpleBarChart, SimpleLineChart, SimplePieChart } from "./SimpleCharts";
import styles from "./ExperimentDashboard.module.css";

function cssVars(vars: Record<string, string>): React.CSSProperties {
  return vars as React.CSSProperties;
}

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
    <div className={styles.style001}>
      <h2>Experiment Dashboard</h2>

      <div className={styles.style002}>
        <button onClick={handleLoadDashboard} disabled={loading} className={styles.style003}>
          {loading ? "Loading..." : "Load Dashboard"}
        </button>
        <button onClick={handleRefresh} disabled={loading} className={styles.style004}>
          {loading ? "Refreshing..." : "Refresh Data"}
        </button>
      </div>

      {error && (
        <div className={styles.style005}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {dashboard && (
        <>
          {/* Summary Cards */}
          <div className={styles.style006}>
            <div className={styles.style007}>
              <div className={styles.style008}>Total Runs</div>
              <div className={styles.style009}>{dashboard.runs_total || 0}</div>
            </div>
            <div className={styles.style010}>
              <div className={styles.style011}>Success</div>
              <div className={styles.style012}>{dashboard.success_total || 0}</div>
            </div>
            <div className={styles.style013}>
              <div className={styles.style014}>Failed</div>
              <div className={styles.style015}>{dashboard.failed_total || 0}</div>
            </div>
            <div className={styles.style016}>
              <div className={styles.style017}>Partial</div>
              <div className={styles.style018}>{dashboard.partial_total || 0}</div>
            </div>
            <div className={styles.style019}>
              <div className={styles.style020}>Mean Duration</div>
              <div className={styles.style021}>
                {formatDuration(dashboard.mean_duration_seconds)}
              </div>
            </div>
            <div className={styles.style022}>
              <div className={styles.style023}>Total Outputs</div>
              <div className={styles.style024}>{dashboard.total_outputs || 0}</div>
            </div>
          </div>

          {/* Charts */}
          <div className={styles.style025}>
            {dashboard.status_distribution && (
              <SimplePieChart
                title="Status Distribution"
                data={toBarData(dashboard.status_distribution)}
              />
            )}
            {dashboard.pipeline_distribution &&
              Object.keys(dashboard.pipeline_distribution).length > 0 && (
                <SimpleBarChart
                  title="Pipeline Distribution"
                  data={toBarData(dashboard.pipeline_distribution)}
                />
              )}
            {dashboard.scheduler_distribution && (
              <SimpleBarChart
                title="Scheduler Distribution"
                data={toBarData(dashboard.scheduler_distribution)}
              />
            )}
            {dashboard.run_type_distribution && (
              <SimpleBarChart
                title="Run Type Distribution"
                data={toBarData(dashboard.run_type_distribution)}
              />
            )}
            {dashboard.duration_trend && dashboard.duration_trend.length > 0 && (
              <SimpleLineChart title="Duration Trend" data={toLineData(dashboard.duration_trend)} />
            )}
          </div>

          {/* Latest Runs Table */}
          {dashboard.runs && dashboard.runs.length > 0 && (
            <div className={styles.style026}>
              <h3>Latest Runs</h3>
              <div className={styles.style027}>
                <table className={styles.style028}>
                  <thead>
                    <tr className={styles.style029}>
                      <th className={styles.style030}>#</th>
                      <th className={styles.style031}>Run ID</th>
                      <th className={styles.style032}>Type</th>
                      <th className={styles.style033}>Pipeline</th>
                      <th className={styles.style034}>Status</th>
                      <th className={styles.style035}>Duration</th>
                      <th className={styles.style036}>Nodes</th>
                      <th className={styles.style037}>Outputs</th>
                      <th className={styles.style038}>⚠️</th>
                      <th className={styles.style039}>❌</th>
                    </tr>
                  </thead>
                  <tbody>
                    {dashboard.runs
                      .slice(-10)
                      .reverse()
                      .map((run, idx) => (
                        <tr key={idx} className={styles.style040}>
                          <td className={styles.style041}>{run.index}</td>
                          <td className={styles.style042}>{run.run_id}</td>
                          <td className={styles.style043}>
                            <span className={styles.style044}>{run.run_type}</span>
                          </td>
                          <td className={styles.style045}>{run.pipeline_id}</td>
                          <td className={styles.style046}>
                            <span
                              className={styles.style047}
                              style={cssVars({ "--status-bg": getStatusColor(run.status) })}
                            >
                              {run.status}
                            </span>
                          </td>
                          <td className={styles.style048}>
                            {formatDuration(run.duration_seconds)}
                          </td>
                          <td className={styles.style049}>
                            {run.nodes_success}/{run.nodes_total}
                          </td>
                          <td className={styles.style050}>{run.outputs_count}</td>
                          <td className={styles.style051}>
                            {run.warnings_count ? (
                              <span className={styles.style052}>{run.warnings_count}</span>
                            ) : (
                              "0"
                            )}
                          </td>
                          <td className={styles.style053}>
                            {run.errors_count ? (
                              <span className={styles.style054}>{run.errors_count}</span>
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
          <div className={styles.style055}>
            <h3>Metrics Summary</h3>
            <div className={styles.style056}>
              <div>
                <strong>Duration:</strong> Mean {formatDuration(dashboard.mean_duration_seconds)},
                Median {formatDuration(dashboard.median_duration_seconds)}, Max{" "}
                {formatDuration(dashboard.max_duration_seconds)}
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
