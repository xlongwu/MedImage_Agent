import { useCallback, useEffect, useState } from "react";
import { getSessionRuns, postSessionIndex, querySessions } from "../lib/api/sessions";
import type { SessionRunSummary, SessionSearchResult, SessionStats } from "../lib/api/sessions";
import styles from "./SessionMemoryBrowserPanel.module.css";

interface Props {
  baseUrl: string;
}

export default function SessionMemoryBrowserPanel({ baseUrl }: Props) {
  const [stats, setStats] = useState<SessionStats | null>(null);
  const [runs, setRuns] = useState<SessionRunSummary[]>([]);
  const [search, setSearch] = useState("");
  const [results, setResults] = useState<SessionSearchResult[]>([]);
  const [loading, setLoading] = useState(false);

  const loadRuns = useCallback(async () => {
    setLoading(true);
    try {
      const res = await getSessionRuns(baseUrl);
      setStats(res.stats ?? null);
      setRuns(res.runs || []);
    } catch (error) {
      console.error("Failed to load runs", error);
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    void loadRuns();
  }, [loadRuns]);

  async function doIndex() {
    setLoading(true);
    try {
      await postSessionIndex(baseUrl);
      await loadRuns();
    } catch (error) {
      console.error("Failed to index", error);
      setLoading(false);
    }
  }

  async function doSearch() {
    if (!search.trim()) return;
    setLoading(true);
    try {
      const res = await querySessions(baseUrl, search);
      setResults(res.results || []);
    } catch (error) {
      console.error("Search failed", error);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className={styles.panel}>
      <h2>Session Memory Browser</h2>

      {stats && (
        <div className={styles.statsBar}>
          <span className={styles.statBadge}>
            Runs: <strong>{stats.total_runs}</strong>
          </span>
          <span className={styles.statBadge}>
            Success: <strong>{stats.success_runs}</strong>
          </span>
          <span className={styles.statBadge}>
            Nodes: <strong>{stats.total_nodes}</strong>
          </span>
          <span className={styles.statBadge}>
            Failed: <strong className={styles.statDanger}>{stats.failed_nodes}</strong>
          </span>
          <span className={styles.statBadge}>
            Errors: <strong>{stats.total_errors}</strong>
          </span>
        </div>
      )}

      <div className={styles.toolbar}>
        <button onClick={doIndex} disabled={loading} className={styles.actionButton}>
          {loading ? "Indexing..." : "Index All Runs"}
        </button>
        <input
          type="text"
          placeholder="Search runs, errors, subjects..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && doSearch()}
          className={styles.searchInput}
        />
        <button
          onClick={doSearch}
          disabled={loading || !search.trim()}
          className={styles.actionButton}
        >
          Search
        </button>
      </div>

      {results.length > 0 && (
        <div className={styles.searchResults}>
          <h3>Search Results ({results.length})</h3>
          {results.map((r: SessionSearchResult, i: number) => (
            <div key={i} className={styles.resultItem}>
              <strong>[{r.record_type}]</strong> {r.title}
              {r.snippet && (
                <p
                  className={styles.resultSnippet}
                  dangerouslySetInnerHTML={{ __html: r.snippet }}
                />
              )}
            </div>
          ))}
        </div>
      )}

      <h3>Recent Runs</h3>
      <table className={styles.runsTable}>
        <thead>
          <tr className={styles.tableHead}>
            <th className={styles.headerCell}>Run ID</th>
            <th className={styles.headerCell}>Pipeline</th>
            <th className={styles.headerCell}>Status</th>
            <th className={styles.headerCell}>Started</th>
            <th className={styles.headerCell}>Duration (s)</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((r: SessionRunSummary) => (
            <tr
              key={r.run_id}
              className={`${styles.tableRow} ${r.status === "FAILED" ? styles.failedRow : ""}`}
            >
              <td className={styles.cell}>{r.run_id}</td>
              <td className={styles.cell}>{r.pipeline_id}</td>
              <td className={styles.cell}>
                <span
                  className={
                    r.status === "SUCCESS"
                      ? styles.statusSuccess
                      : r.status === "FAILED"
                        ? styles.statusFailed
                        : styles.statusMuted
                  }
                >
                  {r.status}
                </span>
              </td>
              <td className={styles.cell}>{r.started_at?.slice(0, 19)}</td>
              <td className={styles.cell}>{r.duration_seconds?.toFixed(1)}</td>
            </tr>
          ))}
          {runs.length === 0 && (
            <tr>
              <td colSpan={5} className={`${styles.cell} ${styles.emptyCell}`}>
                No runs indexed yet. Click "Index All Runs" to scan existing data.
              </td>
            </tr>
          )}
        </tbody>
      </table>

      {loading && <div className={styles.loadingState}>Loading...</div>}
    </div>
  );
}
