import { useCallback, useEffect, useState } from "react";
import type { ReactNode } from "react";
import { buildInsights as buildInsightsApi, getInsights } from "../lib/api/insights";
import type {
  InsightsDashboard,
  InsightErrorCategory,
  InsightFailedNode,
  InsightNodeTiming,
  InsightTrendPoint,
} from "../lib/api/insights";
import styles from "./InsightsDashboardPanel.module.css";

interface Props {
  baseUrl: string;
}

export default function InsightsDashboardPanel({ baseUrl }: Props) {
  const [insights, setInsights] = useState<InsightsDashboard | null>(null);
  const [loading, setLoading] = useState(false);

  const loadInsights = useCallback(async () => {
    setLoading(true);
    try {
      setInsights(await getInsights(baseUrl));
    } catch (error) {
      console.error("Failed to load insights", error);
      setInsights(null);
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    void loadInsights();
  }, [loadInsights]);

  async function buildInsights() {
    setLoading(true);
    try {
      await buildInsightsApi(baseUrl);
      await loadInsights();
    } catch (error) {
      console.error("Failed to build insights", error);
      setLoading(false);
    }
  }

  const s = insights?.summary;

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2>Insights Dashboard</h2>
        <button onClick={buildInsights} disabled={loading} className={styles.buildButton}>
          {loading ? "Building..." : "Build Insights"}
        </button>
      </div>

      {s && (
        <div className={styles.kpiGrid}>
          <KpiCard label="Total Runs" value={s.total_runs} />
          <KpiCard
            label="Success Rate"
            value={`${s.success_rate}%`}
            color={s.success_rate >= 80 ? "#4caf50" : s.success_rate >= 50 ? "#ff9800" : "#f44336"}
          />
          <KpiCard
            label="Failure Rate"
            value={`${s.failure_rate}%`}
            color={s.failure_rate <= 20 ? "#4caf50" : s.failure_rate <= 50 ? "#ff9800" : "#f44336"}
          />
          <KpiCard label="Avg Duration" value={`${s.avg_duration_seconds}s`} />
          <KpiCard
            label="Total Errors"
            value={s.total_errors_logged}
            color={s.total_errors_logged === 0 ? "#4caf50" : "#f44336"}
          />
        </div>
      )}

      {insights && (
        <>
          {insights.recent_trend && insights.recent_trend.length > 0 && (
            <div className={styles.section}>
              <h3>Recent Trend</h3>
              <div className={styles.trendBars}>
                {insights.recent_trend
                  .slice()
                  .reverse()
                  .map((r: InsightTrendPoint, i: number) => (
                    <div
                      key={i}
                      title={`${r.run_id}: ${r.status}`}
                      className={styles.trendBar}
                      style={{
                        height: r.status === "SUCCESS" ? 40 : r.status === "PARTIAL" ? 25 : 15,
                        background:
                          r.status === "SUCCESS"
                            ? "#4caf50"
                            : r.status === "PARTIAL"
                              ? "#ff9800"
                              : "#f44336",
                      }}
                    />
                  ))}
              </div>
            </div>
          )}

          <div className={styles.dataGrid}>
            {insights.slowest_nodes && insights.slowest_nodes.length > 0 && (
              <div>
                <h3>Slowest Nodes</h3>
                <table className={styles.dataTable}>
                  <thead>
                    <tr className={styles.tableHead}>
                      {["Node", "Avg (s)", "Count", "Fail %"].map((h) => (
                        <th key={h} className={styles.tableHeaderCell}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {insights.slowest_nodes.map((n: InsightNodeTiming) => (
                      <tr key={n.node_id} className={styles.tableRow}>
                        <td className={styles.tableCell}>{n.node_id}</td>
                        <td className={styles.tableCell}>{n.avg_duration}</td>
                        <td className={styles.tableCell}>{n.count}</td>
                        <td
                          className={`${styles.tableCell} ${n.failure_rate > 20 ? styles.dangerCell : ""}`}
                        >
                          {n.failure_rate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {insights.most_failed_nodes && insights.most_failed_nodes.length > 0 && (
              <div>
                <h3>Most Failed Nodes</h3>
                <table className={styles.dataTable}>
                  <thead>
                    <tr className={styles.tableHead}>
                      {["Node", "Failed", "Total", "Fail %"].map((h) => (
                        <th key={h} className={styles.tableHeaderCell}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {insights.most_failed_nodes.map((n: InsightFailedNode) => (
                      <tr key={n.node_id} className={styles.tableRow}>
                        <td className={styles.tableCell}>{n.node_id}</td>
                        <td className={`${styles.tableCell} ${styles.dangerCell}`}>{n.failed}</td>
                        <td className={styles.tableCell}>{n.total}</td>
                        <td
                          className={`${styles.tableCell} ${n.failure_rate > 20 ? styles.dangerCell : ""}`}
                        >
                          {n.failure_rate}%
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {insights.top_error_categories && insights.top_error_categories.length > 0 && (
              <div>
                <h3>Top Error Categories</h3>
                <table className={styles.dataTable}>
                  <thead>
                    <tr className={styles.tableHead}>
                      {["Category", "Count"].map((h) => (
                        <th key={h} className={styles.tableHeaderCell}>
                          {h}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {insights.top_error_categories.map((c: InsightErrorCategory) => (
                      <tr key={c.category} className={styles.tableRow}>
                        <td className={styles.tableCell}>{c.category}</td>
                        <td className={`${styles.tableCell} ${styles.dangerCell}`}>{c.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </>
      )}

      {!insights && !loading && (
        <div className={styles.emptyState}>
          No insights generated. Click "Build Insights" to analyze run history from SessionDB.
        </div>
      )}

      {loading && <div className={styles.loadingState}>Loading...</div>}
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: ReactNode; color?: string }) {
  return (
    <div className={styles.kpiCard}>
      <div className={styles.kpiLabel}>{label}</div>
      <div className={styles.kpiValue} style={{ color: color || "#333" }}>
        {value}
      </div>
    </div>
  );
}
