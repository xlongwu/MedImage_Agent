import React, { useState, useEffect } from "react";
import {
  getExperimentsRunIndex,
  createExperimentRecord,
  compareExperimentRuns,
  getExperimentRecord,
  getExperimentComparison,
} from "../lib/api/legacy";
import styles from "./ExperimentTrackingDashboard.module.css";

function cssVars(vars: Record<string, string>): React.CSSProperties {
  return vars as React.CSSProperties;
}

interface RunItem {
  run_id?: string;
  run_type?: string;
  pipeline_id?: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  scheduler_mode?: string;
  max_workers?: number;
  matlab_max_workers?: number;
  nodes_total?: number;
  nodes_success?: number;
  nodes_failed?: number;
  outputs_count?: number;
  warnings_count?: number;
  errors_count?: number;
  summary_path?: string;
}

interface ArtifactItem {
  name?: string;
  exists?: boolean;
  path?: string;
}

interface RunIndex {
  ok?: boolean;
  runs_total?: number;
  runs?: RunItem[];
  artifacts?: ArtifactItem[];
  warnings?: string[];
  errors?: string[];
}

interface ExperimentRecord {
  ok?: boolean;
  experiment_id?: string;
  name?: string;
  run_ids?: string[];
  tags?: string[];
  notes?: string;
  created_at?: string;
  runs?: RunItem[];
  missing_run_ids?: string[];
}

interface ComparisonRow {
  run_id?: string;
  run_type?: string;
  pipeline_id?: string;
  status?: string;
  duration_seconds?: number;
  scheduler_mode?: string;
  max_workers?: number;
  matlab_max_workers?: number;
  nodes_total?: number;
  nodes_success?: number;
  nodes_failed?: number;
  outputs_count?: number;
  warnings_count?: number;
  errors_count?: number;
}

interface ComparisonResult {
  ok?: boolean;
  experiment_id?: string;
  runs_compared?: number;
  rows?: ComparisonRow[];
  missing_run_ids?: string[];
  warnings?: string[];
  errors?: string[];
}

interface ExperimentTrackingDashboardProps {
  baseUrl: string;
}

export function ExperimentTrackingDashboard({ baseUrl }: ExperimentTrackingDashboardProps) {
  const [runIndex, setRunIndex] = useState<RunIndex | null>(null);
  const [loadingIndex, setLoadingIndex] = useState(false);

  const [selectedRunIds, setSelectedRunIds] = useState<string[]>([]);
  const [experimentId, setExperimentId] = useState<string>("experiment_001");
  const [experimentName, setExperimentName] = useState<string>("Experiment 001");
  const [tags, setTags] = useState<string>("");
  const [notes, setNotes] = useState<string>("");

  const [experimentRecord, setExperimentRecord] = useState<ExperimentRecord | null>(null);
  const [loadingCreate, setLoadingCreate] = useState(false);

  const [comparisonResult, setComparisonResult] = useState<ComparisonResult | null>(null);
  const [loadingCompare, setLoadingCompare] = useState(false);

  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    handleLoadRunIndex();
  }, [baseUrl]);

  const handleLoadRunIndex = async () => {
    setLoadingIndex(true);
    setError(null);
    try {
      const result = (await getExperimentsRunIndex(baseUrl)) as RunIndex;
      setRunIndex(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingIndex(false);
    }
  };

  const handleToggleRunSelection = (runId: string) => {
    setSelectedRunIds((prev) => {
      if (prev.includes(runId)) {
        return prev.filter((id) => id !== runId);
      } else {
        return [...prev, runId];
      }
    });
  };

  const handleSelectAll = () => {
    if (runIndex?.runs) {
      setSelectedRunIds(runIndex.runs.map((r) => r.run_id || "").filter(Boolean));
    }
  };

  const handleDeselectAll = () => {
    setSelectedRunIds([]);
  };

  const handleCreateExperiment = async () => {
    if (selectedRunIds.length === 0) {
      setError("Please select at least one run.");
      return;
    }
    setLoadingCreate(true);
    setError(null);
    setExperimentRecord(null);
    try {
      const result = (await createExperimentRecord(baseUrl, {
        experiment_id: experimentId,
        name: experimentName,
        run_ids: selectedRunIds,
        tags: tags.split(",").map((t) => t.trim()).filter(Boolean),
        notes: notes,
      })) as ExperimentRecord;
      setExperimentRecord(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingCreate(false);
    }
  };

  const handleCompareRuns = async () => {
    setLoadingCompare(true);
    setError(null);
    setComparisonResult(null);
    try {
      const result = (await compareExperimentRuns(baseUrl, {
        experiment_id: experimentId,
        run_ids: selectedRunIds,
      })) as ComparisonResult;
      setComparisonResult(result);
    } catch (e) {
      setError(String(e));
    } finally {
      setLoadingCompare(false);
    }
  };

  const formatDuration = (seconds?: number) => {
    if (seconds === undefined || seconds === null) return "N/A";
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
  };

  const getStatusColor = (status?: string) => {
    switch (status?.toLowerCase()) {
      case "success":
      case "completed":
      case "ok":
        return "#4caf50";
      case "failed":
      case "error":
        return "#f44336";
      case "running":
        return "#2196f3";
      default:
        return "#9e9e9e";
    }
  };

  return (
    <div className={styles.style001}>
      <h2>Experiment Tracking Dashboard</h2>

      <div className={styles.style002}>
        <button
          onClick={handleLoadRunIndex}
          disabled={loadingIndex}
          className={styles.style003}
        >
          {loadingIndex ? "Loading..." : "Refresh Run Index"}
        </button>
        <button onClick={handleSelectAll} className={styles.style004}>
          Select All
        </button>
        <button onClick={handleDeselectAll}>Deselect All</button>
      </div>

      {runIndex && (
        <div className={styles.style005}>
          <h3>Run Index ({runIndex.runs_total || 0} runs)</h3>

          {runIndex.artifacts && runIndex.artifacts.length > 0 && (
            <div className={styles.style006}>
              <h4>Report Artifacts</h4>
              <div className={styles.style007}>
                {runIndex.artifacts.map((artifact, idx) => (
                  <span
                    key={idx}
                    style={{
                      padding: "4px 8px",
                      borderRadius: 4,
                      background: artifact.exists ? "#e8f5e9" : "#ffebee",
                      fontSize: 12,
                    }}
                  >
                    {artifact.name} {artifact.exists ? "✓" : "✗"}
                  </span>
                ))}
              </div>
            </div>
          )}

          <div className={styles.style008}>
            <table className={styles.style009}>
              <thead>
                <tr className={styles.style010}>
                  <th className={styles.style011}>Select</th>
                  <th className={styles.style012}>Run ID</th>
                  <th className={styles.style013}>Type</th>
                  <th className={styles.style014}>Pipeline</th>
                  <th className={styles.style015}>Status</th>
                  <th className={styles.style016}>Duration</th>
                  <th className={styles.style017}>Scheduler</th>
                  <th className={styles.style018}>Nodes</th>
                  <th className={styles.style019}>Outputs</th>
                  <th className={styles.style020}>⚠️</th>
                  <th className={styles.style021}>❌</th>
                </tr>
              </thead>
              <tbody>
                {runIndex.runs?.map((run, idx) => (
                  <tr key={idx} className={styles.style022}>
                    <td className={styles.style023}>
                      <input
                        type="checkbox"
                        checked={selectedRunIds.includes(run.run_id || "")}
                        onChange={() => handleToggleRunSelection(run.run_id || "")}
                      />
                    </td>
                    <td className={styles.style024}>
                      {run.run_id}
                    </td>
                    <td className={styles.style025}>
                      <span
                        className={styles.style026}
                      >
                        {run.run_type}
                      </span>
                    </td>
                    <td className={styles.style027}>{run.pipeline_id}</td>
                    <td className={styles.style028}>
                      <span
                        className={styles.style029}
                        style={cssVars({ "--status-bg": getStatusColor(run.status) })}
                      >
                        {run.status}
                      </span>
                    </td>
                    <td className={styles.style030}>
                      {formatDuration(run.duration_seconds)}
                    </td>
                    <td className={styles.style031}>
                      {run.scheduler_mode} ({run.max_workers}/{run.matlab_max_workers})
                    </td>
                    <td className={styles.style032}>
                      {run.nodes_success}/{run.nodes_total}
                      {run.nodes_failed ? (
                        <span className={styles.style033}> ({run.nodes_failed} failed)</span>
                      ) : null}
                    </td>
                    <td className={styles.style034}>{run.outputs_count}</td>
                    <td className={styles.style035}>
                      {run.warnings_count ? (
                        <span className={styles.style036}>{run.warnings_count}</span>
                      ) : (
                        "0"
                      )}
                    </td>
                    <td className={styles.style037}>
                      {run.errors_count ? (
                        <span className={styles.style038}>{run.errors_count}</span>
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

      <div className={styles.style039}>
        <h3>Create Experiment Record</h3>
        <p className={styles.style040}>
          Selected runs: {selectedRunIds.length}
        </p>

        <label className={styles.style041}>
          Experiment ID:
          <input
            type="text"
            value={experimentId}
            onChange={(e) => setExperimentId(e.target.value)}
            style={{ marginLeft: 8, width: 200 }}
          />
        </label>

        <label className={styles.style042}>
          Name:
          <input
            type="text"
            value={experimentName}
            onChange={(e) => setExperimentName(e.target.value)}
            style={{ marginLeft: 8, width: 250 }}
          />
        </label>

        <label className={styles.style043}>
          Tags (comma-separated):
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            style={{ marginLeft: 8, width: 300 }}
            placeholder="tag1, tag2, tag3"
          />
        </label>

        <label className={styles.style044}>
          Notes:
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            style={{ marginLeft: 8, width: 400, height: 60, display: "block" }}
          />
        </label>

        <div className={styles.style045}>
          <button
            onClick={handleCreateExperiment}
            disabled={loadingCreate || selectedRunIds.length === 0}
            className={styles.style046}
          >
            {loadingCreate ? "Creating..." : "Create Experiment Record"}
          </button>
          <button
            onClick={handleCompareRuns}
            disabled={loadingCompare}
            className={styles.style047}
          >
            {loadingCompare ? "Comparing..." : "Compare Runs"}
          </button>
        </div>
      </div>

      {error && (
        <div className={styles.style048}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {experimentRecord && (
        <div className={styles.style049}>
          <h3>Experiment Record Created</h3>
          <p><strong>Experiment ID:</strong> {experimentRecord.experiment_id}</p>
          <p><strong>Name:</strong> {experimentRecord.name}</p>
          <p><strong>Runs:</strong> {experimentRecord.run_ids?.length || 0}</p>
          <p><strong>Tags:</strong> {experimentRecord.tags?.join(", ") || "None"}</p>
          {experimentRecord.missing_run_ids && experimentRecord.missing_run_ids.length > 0 && (
            <p className={styles.style050}>
              <strong>Missing runs:</strong> {experimentRecord.missing_run_ids.join(", ")}
            </p>
          )}
        </div>
      )}

      {comparisonResult && (
        <div className={styles.style051}>
          <h3>Comparison Result</h3>
          <p><strong>Experiment ID:</strong> {comparisonResult.experiment_id}</p>
          <p><strong>Runs compared:</strong> {comparisonResult.runs_compared}</p>

          {comparisonResult.missing_run_ids && comparisonResult.missing_run_ids.length > 0 && (
            <p className={styles.style052}>
              <strong>Missing runs:</strong> {comparisonResult.missing_run_ids.join(", ")}
            </p>
          )}

          {comparisonResult.rows && comparisonResult.rows.length > 0 && (
            <div className={styles.style053}>
              <table className={styles.style054}>
                <thead>
                  <tr className={styles.style055}>
                    <th className={styles.style056}>Run ID</th>
                    <th className={styles.style057}>Type</th>
                    <th className={styles.style058}>Pipeline</th>
                    <th className={styles.style059}>Status</th>
                    <th className={styles.style060}>Duration</th>
                    <th className={styles.style061}>Scheduler</th>
                    <th className={styles.style062}>Nodes OK/Total</th>
                    <th className={styles.style063}>Errors</th>
                    <th className={styles.style064}>Warnings</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonResult.rows.map((row, idx) => (
                    <tr key={idx} className={styles.style065}>
                      <td className={styles.style066}>
                        {row.run_id}
                      </td>
                      <td className={styles.style067}>{row.run_type}</td>
                      <td className={styles.style068}>{row.pipeline_id}</td>
                      <td className={styles.style069}>
                        <span
                          className={styles.style070}
                          style={cssVars({ "--status-bg": getStatusColor(row.status) })}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td className={styles.style071}>
                        {formatDuration(row.duration_seconds)}
                      </td>
                      <td className={styles.style072}>
                        {row.scheduler_mode} ({row.max_workers}/{row.matlab_max_workers})
                      </td>
                      <td className={styles.style073}>
                        {row.nodes_success}/{row.nodes_total}
                      </td>
                      <td className={styles.style074}>
                        {row.errors_count ? (
                          <span className={styles.style075}>{row.errors_count}</span>
                        ) : (
                          "0"
                        )}
                      </td>
                      <td className={styles.style076}>
                        {row.warnings_count ? (
                          <span className={styles.style077}>{row.warnings_count}</span>
                        ) : (
                          "0"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
