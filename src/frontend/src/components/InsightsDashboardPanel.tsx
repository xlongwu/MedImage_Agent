import React, { useEffect, useState } from 'react';
import { getSessionRuns } from '../api';

interface Props {
  baseUrl: string;
}

export default function InsightsDashboardPanel({ baseUrl }: Props) {
  const [insights, setInsights] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadInsights(); }, []);

  async function loadInsights() {
    setLoading(true);
    try {
      const res = await fetch(`${baseUrl}/api/insights`);
      if (res.ok) {
        setInsights(await res.json());
      } else {
        setInsights(null);
      }
    } catch (e) {
      console.error('Failed to load insights', e);
    }
    setLoading(false);
  }

  async function buildInsights() {
    setLoading(true);
    try {
      await fetch(`${baseUrl}/api/insights/build`, { method: 'POST' });
      await loadInsights();
    } catch (e) {
      console.error('Failed to build insights', e);
    }
    setLoading(false);
  }

  const s = insights?.summary;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2>Insights Dashboard</h2>
        <button onClick={buildInsights} disabled={loading} style={btnStyle}>
          {loading ? 'Building...' : 'Build Insights'}
        </button>
      </div>

      {s && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 12, marginBottom: 20 }}>
          <KpiCard label="Total Runs" value={s.total_runs} />
          <KpiCard label="Success Rate" value={`${s.success_rate}%`} color={s.success_rate >= 80 ? '#4caf50' : s.success_rate >= 50 ? '#ff9800' : '#f44336'} />
          <KpiCard label="Failure Rate" value={`${s.failure_rate}%`} color={s.failure_rate <= 20 ? '#4caf50' : s.failure_rate <= 50 ? '#ff9800' : '#f44336'} />
          <KpiCard label="Avg Duration" value={`${s.avg_duration_seconds}s`} />
          <KpiCard label="Total Errors" value={s.total_errors_logged} color={s.total_errors_logged === 0 ? '#4caf50' : '#f44336'} />
        </div>
      )}

      {insights && (
        <>
          {insights.recent_trend && insights.recent_trend.length > 0 && (
            <div style={{ marginBottom: 20 }}>
              <h3>Recent Trend</h3>
              <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', height: 60 }}>
                {insights.recent_trend.slice().reverse().map((r: any, i: number) => (
                  <div key={i} title={`${r.run_id}: ${r.status}`} style={{
                    width: 20,
                    height: r.status === 'SUCCESS' ? 40 : r.status === 'PARTIAL' ? 25 : 15,
                    background: r.status === 'SUCCESS' ? '#4caf50' : r.status === 'PARTIAL' ? '#ff9800' : '#f44336',
                    borderRadius: '2px 2px 0 0',
                    transition: 'height 0.2s',
                  }} />
                ))}
              </div>
            </div>
          )}

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(350px, 1fr))', gap: 16 }}>
            {insights.slowest_nodes && insights.slowest_nodes.length > 0 && (
              <div>
                <h3>Slowest Nodes</h3>
                <table style={tableStyle}>
                  <thead><tr style={trHead}>{['Node', 'Avg (s)', 'Count', 'Fail %'].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
                  <tbody>
                    {insights.slowest_nodes.map((n: any) => (
                      <tr key={n.node_id} style={trStyle}>
                        <td style={tdStyle}>{n.node_id}</td>
                        <td style={tdStyle}>{n.avg_duration}</td>
                        <td style={tdStyle}>{n.count}</td>
                        <td style={{ ...tdStyle, color: n.failure_rate > 20 ? '#f44336' : undefined }}>{n.failure_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {insights.most_failed_nodes && insights.most_failed_nodes.length > 0 && (
              <div>
                <h3>Most Failed Nodes</h3>
                <table style={tableStyle}>
                  <thead><tr style={trHead}>{['Node', 'Failed', 'Total', 'Fail %'].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
                  <tbody>
                    {insights.most_failed_nodes.map((n: any) => (
                      <tr key={n.node_id} style={trStyle}>
                        <td style={tdStyle}>{n.node_id}</td>
                        <td style={{ ...tdStyle, color: '#f44336' }}>{n.failed}</td>
                        <td style={tdStyle}>{n.total}</td>
                        <td style={{ ...tdStyle, color: n.failure_rate > 20 ? '#f44336' : undefined }}>{n.failure_rate}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {insights.top_error_categories && insights.top_error_categories.length > 0 && (
              <div>
                <h3>Top Error Categories</h3>
                <table style={tableStyle}>
                  <thead><tr style={trHead}>{['Category', 'Count'].map(h => <th key={h} style={thStyle}>{h}</th>)}</tr></thead>
                  <tbody>
                    {insights.top_error_categories.map((c: any) => (
                      <tr key={c.category} style={trStyle}>
                        <td style={tdStyle}>{c.category}</td>
                        <td style={{ ...tdStyle, color: '#f44336' }}>{c.count}</td>
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
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
          No insights generated. Click "Build Insights" to analyze run history from SessionDB.
        </div>
      )}

      {loading && <div style={{ textAlign: 'center', padding: 16, color: '#666' }}>Loading...</div>}
    </div>
  );
}

function KpiCard({ label, value, color }: { label: string; value: any; color?: string }) {
  return (
    <div style={{ padding: '12px 16px', background: '#f9f9f9', borderRadius: 8, border: '1px solid #eee' }}>
      <div style={{ fontSize: 12, color: '#888', marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: color || '#333' }}>{value}</div>
    </div>
  );
}

const btnStyle: React.CSSProperties = {
  padding: '8px 20px', border: 'none', borderRadius: 4,
  background: '#2196f3', color: 'white', cursor: 'pointer', fontWeight: 600,
};
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: 13 };
const trHead: React.CSSProperties = { background: '#f5f5f5' };
const trStyle: React.CSSProperties = { borderBottom: '1px solid #eee' };
const thStyle: React.CSSProperties = { padding: '6px 10px', textAlign: 'left', fontWeight: 600 };
const tdStyle: React.CSSProperties = { padding: '5px 10px' };
