import React, { useState, useEffect } from "react";
import {
  getExperimentsRunIndex,
  createExperimentRecord,
  compareExperimentRuns,
  getExperimentRecord,
  getExperimentComparison,
} from "../api";

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
    <div style={{ padding: 16, borderTop: "2px solid #9c27b0", marginTop: 24 }}>
      <h2>Experiment Tracking Dashboard</h2>

      <div style={{ marginBottom: 16 }}>
        <button
          onClick={handleLoadRunIndex}
          disabled={loadingIndex}
          style={{ marginRight: 8 }}
        >
          {loadingIndex ? "Loading..." : "Refresh Run Index"}
        </button>
        <button onClick={handleSelectAll} style={{ marginRight: 8 }}>
          Select All
        </button>
        <button onClick={handleDeselectAll}>Deselect All</button>
      </div>

      {runIndex && (
        <div style={{ marginBottom: 24 }}>
          <h3>Run Index ({runIndex.runs_total || 0} runs)</h3>

          {runIndex.artifacts && runIndex.artifacts.length > 0 && (
            <div style={{ marginBottom: 16, padding: 12, background: "#f5f5f5", borderRadius: 4 }}>
              <h4>Report Artifacts</h4>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
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

          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 14 }}>
              <thead>
                <tr style={{ background: "#f5f5f5" }}>
                  <th style={{ padding: 8, textAlign: "left" }}>Select</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Run ID</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Pipeline</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                  <th style={{ padding: 8, textAlign: "right" }}>Duration</th>
                  <th style={{ padding: 8, textAlign: "left" }}>Scheduler</th>
                  <th style={{ padding: 8, textAlign: "center" }}>Nodes</th>
                  <th style={{ padding: 8, textAlign: "center" }}>Outputs</th>
                  <th style={{ padding: 8, textAlign: "center" }}>⚠️</th>
                  <th style={{ padding: 8, textAlign: "center" }}>❌</th>
                </tr>
              </thead>
              <tbody>
                {runIndex.runs?.map((run, idx) => (
                  <tr key={idx} style={{ borderBottom: "1px solid #eee" }}>
                    <td style={{ padding: 8 }}>
                      <input
                        type="checkbox"
                        checked={selectedRunIds.includes(run.run_id || "")}
                        onChange={() => handleToggleRunSelection(run.run_id || "")}
                      />
                    </td>
                    <td style={{ padding: 8, fontFamily: "monospace", fontSize: 12 }}>
                      {run.run_id}
                    </td>
                    <td style={{ padding: 8 }}>
                      <span
                        style={{
                          padding: "2px 6px",
                          borderRadius: 4,
                          background: "#e3f2fd",
                          fontSize: 11,
                        }}
                      >
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
                    <td style={{ padding: 8, fontSize: 12 }}>
                      {run.scheduler_mode} ({run.max_workers}/{run.matlab_max_workers})
                    </td>
                    <td style={{ padding: 8, textAlign: "center" }}>
                      {run.nodes_success}/{run.nodes_total}
                      {run.nodes_failed ? (
                        <span style={{ color: "red" }}> ({run.nodes_failed} failed)</span>
                      ) : null}
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

      <div style={{ marginBottom: 24, padding: 16, background: "#f5f5f5", borderRadius: 4 }}>
        <h3>Create Experiment Record</h3>
        <p style={{ fontSize: 14, color: "#666" }}>
          Selected runs: {selectedRunIds.length}
        </p>

        <label style={{ display: "block", marginBottom: 8 }}>
          Experiment ID:
          <input
            type="text"
            value={experimentId}
            onChange={(e) => setExperimentId(e.target.value)}
            style={{ marginLeft: 8, width: 200 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Name:
          <input
            type="text"
            value={experimentName}
            onChange={(e) => setExperimentName(e.target.value)}
            style={{ marginLeft: 8, width: 250 }}
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Tags (comma-separated):
          <input
            type="text"
            value={tags}
            onChange={(e) => setTags(e.target.value)}
            style={{ marginLeft: 8, width: 300 }}
            placeholder="tag1, tag2, tag3"
          />
        </label>

        <label style={{ display: "block", marginBottom: 8 }}>
          Notes:
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            style={{ marginLeft: 8, width: 400, height: 60, display: "block" }}
          />
        </label>

        <div style={{ marginTop: 12 }}>
          <button
            onClick={handleCreateExperiment}
            disabled={loadingCreate || selectedRunIds.length === 0}
            style={{ backgroundColor: "#4caf50", color: "white", marginRight: 8 }}
          >
            {loadingCreate ? "Creating..." : "Create Experiment Record"}
          </button>
          <button
            onClick={handleCompareRuns}
            disabled={loadingCompare}
            style={{ backgroundColor: "#2196f3", color: "white" }}
          >
            {loadingCompare ? "Comparing..." : "Compare Runs"}
          </button>
        </div>
      </div>

      {error && (
        <div style={{ color: "red", marginBottom: 16, padding: 12, background: "#ffebee", borderRadius: 4 }}>
          <strong>Error:</strong> {error}
        </div>
      )}

      {experimentRecord && (
        <div style={{ marginBottom: 24, padding: 12, background: "#e8f5e9", borderRadius: 4 }}>
          <h3>Experiment Record Created</h3>
          <p><strong>Experiment ID:</strong> {experimentRecord.experiment_id}</p>
          <p><strong>Name:</strong> {experimentRecord.name}</p>
          <p><strong>Runs:</strong> {experimentRecord.run_ids?.length || 0}</p>
          <p><strong>Tags:</strong> {experimentRecord.tags?.join(", ") || "None"}</p>
          {experimentRecord.missing_run_ids && experimentRecord.missing_run_ids.length > 0 && (
            <p style={{ color: "orange" }}>
              <strong>Missing runs:</strong> {experimentRecord.missing_run_ids.join(", ")}
            </p>
          )}
        </div>
      )}

      {comparisonResult && (
        <div style={{ marginBottom: 24, padding: 12, background: "#e3f2fd", borderRadius: 4 }}>
          <h3>Comparison Result</h3>
          <p><strong>Experiment ID:</strong> {comparisonResult.experiment_id}</p>
          <p><strong>Runs compared:</strong> {comparisonResult.runs_compared}</p>

          {comparisonResult.missing_run_ids && comparisonResult.missing_run_ids.length > 0 && (
            <p style={{ color: "orange" }}>
              <strong>Missing runs:</strong> {comparisonResult.missing_run_ids.join(", ")}
            </p>
          )}

          {comparisonResult.rows && comparisonResult.rows.length > 0 && (
            <div style={{ overflowX: "auto", marginTop: 16 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#bbdefb" }}>
                    <th style={{ padding: 8, textAlign: "left" }}>Run ID</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Type</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Pipeline</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Status</th>
                    <th style={{ padding: 8, textAlign: "right" }}>Duration</th>
                    <th style={{ padding: 8, textAlign: "left" }}>Scheduler</th>
                    <th style={{ padding: 8, textAlign: "center" }}>Nodes OK/Total</th>
                    <th style={{ padding: 8, textAlign: "center" }}>Errors</th>
                    <th style={{ padding: 8, textAlign: "center" }}>Warnings</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonResult.rows.map((row, idx) => (
                    <tr key={idx} style={{ borderBottom: "1px solid #90caf9" }}>
                      <td style={{ padding: 8, fontFamily: "monospace", fontSize: 11 }}>
                        {row.run_id}
                      </td>
                      <td style={{ padding: 8 }}>{row.run_type}</td>
                      <td style={{ padding: 8 }}>{row.pipeline_id}</td>
                      <td style={{ padding: 8 }}>
                        <span
                          style={{
                            padding: "2px 6px",
                            borderRadius: 4,
                            background: getStatusColor(row.status),
                            color: "white",
                            fontSize: 11,
                          }}
                        >
                          {row.status}
                        </span>
                      </td>
                      <td style={{ padding: 8, textAlign: "right" }}>
                        {formatDuration(row.duration_seconds)}
                      </td>
                      <td style={{ padding: 8, fontSize: 12 }}>
                        {row.scheduler_mode} ({row.max_workers}/{row.matlab_max_workers})
                      </td>
                      <td style={{ padding: 8, textAlign: "center" }}>
                        {row.nodes_success}/{row.nodes_total}
                      </td>
                      <td style={{ padding: 8, textAlign: "center" }}>
                        {row.errors_count ? (
                          <span style={{ color: "red" }}>{row.errors_count}</span>
                        ) : (
                          "0"
                        )}
                      </td>
                      <td style={{ padding: 8, textAlign: "center" }}>
                        {row.warnings_count ? (
                          <span style={{ color: "orange" }}>{row.warnings_count}</span>
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
