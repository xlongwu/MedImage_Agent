import React, { useEffect, useState } from 'react';
import { getSessionRuns, postSessionIndex, querySessions } from '../api';

interface Props {
  baseUrl: string;
}

export default function SessionMemoryBrowserPanel({ baseUrl }: Props) {
  const [stats, setStats] = useState<any>(null);
  const [runs, setRuns] = useState<any[]>([]);
  const [search, setSearch] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadRuns();
  }, []);

  async function loadRuns() {
    setLoading(true);
    try {
      const res = await getSessionRuns(baseUrl) as any;
      setStats(res.stats);
      setRuns(res.runs || []);
    } catch (e) {
      console.error('Failed to load runs', e);
    }
    setLoading(false);
  }

  async function doIndex() {
    setLoading(true);
    try {
      await postSessionIndex(baseUrl);
      await loadRuns();
    } catch (e) {
      console.error('Failed to index', e);
    }
    setLoading(false);
  }

  async function doSearch() {
    if (!search.trim()) return;
    setLoading(true);
    try {
      const res = await querySessions(baseUrl, search) as any;
      setResults(res.results || []);
    } catch (e) {
      console.error('Search failed', e);
    }
    setLoading(false);
  }

  return (
    <div className="session-memory-panel" style={{ padding: 16 }}>
      <h2>Session Memory Browser</h2>

      {stats && (
        <div className="stats-bar" style={{ display: 'flex', gap: 16, marginBottom: 16, flexWrap: 'wrap' }}>
          <span style={statBadge}>Runs: <strong>{stats.total_runs}</strong></span>
          <span style={statBadge}>Success: <strong>{stats.success_runs}</strong></span>
          <span style={statBadge}>Nodes: <strong>{stats.total_nodes}</strong></span>
          <span style={statBadge}>Failed: <strong style={{ color: 'red' }}>{stats.failed_nodes}</strong></span>
          <span style={statBadge}>Errors: <strong>{stats.total_errors}</strong></span>
        </div>
      )}

      <div className="toolbar" style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <button onClick={doIndex} disabled={loading} style={btnStyle}>
          {loading ? 'Indexing...' : 'Index All Runs'}
        </button>
        <input
          type="text"
          placeholder="Search runs, errors, subjects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && doSearch()}
          style={{ flex: 1, padding: '6px 12px', borderRadius: 4, border: '1px solid #ccc' }}
        />
        <button onClick={doSearch} disabled={loading || !search.trim()} style={btnStyle}>
          Search
        </button>
      </div>

      {results.length > 0 && (
        <div className="search-results" style={{ marginBottom: 16 }}>
          <h3>Search Results ({results.length})</h3>
          {results.map((r: any, i: number) => (
            <div key={i} className="result-item" style={resultItemStyle}>
              <strong>[{r.record_type}]</strong> {r.title}
              {r.snippet && <p dangerouslySetInnerHTML={{ __html: r.snippet }} />}
            </div>
          ))}
        </div>
      )}

      <h3>Recent Runs</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ background: '#f5f5f5' }}>
            <th style={thStyle}>Run ID</th>
            <th style={thStyle}>Pipeline</th>
            <th style={thStyle}>Status</th>
            <th style={thStyle}>Started</th>
            <th style={thStyle}>Duration (s)</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r: any) => (
            <tr key={r.run_id} style={{ borderBottom: '1px solid #eee', background: r.status === 'FAILED' ? '#fff0f0' : undefined }}>
              <td style={tdStyle}>{r.run_id}</td>
              <td style={tdStyle}>{r.pipeline_id}</td>
              <td style={tdStyle}>
                <span style={{ color: r.status === 'SUCCESS' ? 'green' : r.status === 'FAILED' ? 'red' : '#666' }}>
                  {r.status}
                </span>
              </td>
              <td style={tdStyle}>{r.started_at?.slice(0, 19)}</td>
              <td style={tdStyle}>{r.duration_seconds?.toFixed(1)}</td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr><td colSpan={5} style={{ ...tdStyle, textAlign: 'center', color: '#999' }}>No runs indexed yet. Click "Index All Runs" to scan existing data.</td></tr>
          )}
        </tbody>
      </table>

      {loading && <div style={{ textAlign: 'center', padding: 16, color: '#666' }}>Loading...</div>}
    </div>
  );
}

const statBadge: React.CSSProperties = {
  padding: '4px 12px',
  background: '#e3f2fd',
  borderRadius: 16,
  fontSize: 13,
};

const btnStyle: React.CSSProperties = {
  padding: '6px 16px',
  border: '1px solid #2196f3',
  borderRadius: 4,
  background: '#2196f3',
  color: 'white',
  cursor: 'pointer',
  fontWeight: 500,
};

const thStyle: React.CSSProperties = {
  padding: '8px 12px',
  textAlign: 'left',
  fontWeight: 600,
  borderBottom: '2px solid #ddd',
};

const tdStyle: React.CSSProperties = {
  padding: '6px 12px',
  fontSize: 13,
};

const resultItemStyle: React.CSSProperties = {
  padding: '8px 12px',
  marginBottom: 4,
  background: '#f9f9f9',
  borderRadius: 4,
  border: '1px solid #eee',
};
