import { useState } from "react";
import { inspectRun, listRuns, readLog } from "../lib/api/legacy";
import type { NodeStateSummary, RunInspection } from "../types";
import { JsonBlock } from "./JsonBlock";
import { StatusBadge } from "./StatusBadge";
import { TextViewer } from "./TextViewer";

type Props = {
  baseUrl: string;
};

function NodeStateCard({
  node,
  onSelect,
  onReadLog
}: {
  node: NodeStateSummary;
  onSelect: (node: NodeStateSummary) => void;
  onReadLog: (path: string) => void;
}) {
  return (
    <div className="stateCard">
      <div className="stateCardHeader">
        <strong>{node.node || "unknown node"}</strong>
        <StatusBadge status={node.status} />
      </div>

      <div className="stateMeta">
        <span>Subject: {node.subject || "project"}</span>
        <span>Return code: {node.returncode ?? "n/a"}</span>
      </div>

      {node.errors && node.errors.length > 0 ? (
        <div className="smallError">
          {node.errors.slice(0, 2).map((item, index) => (
            <div key={index}>{item}</div>
          ))}
        </div>
      ) : null}

      <div className="row">
        <button onClick={() => onSelect(node)}>查看 State</button>
        {node.stdout_log ? (
          <button onClick={() => onReadLog(node.stdout_log as string)}>
            stdout
          </button>
        ) : null}
        {node.stderr_log ? (
          <button onClick={() => onReadLog(node.stderr_log as string)}>
            stderr
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function RunMonitor({ baseUrl }: Props) {
  const [runs, setRuns] = useState<Array<Record<string, unknown>>>([]);
  const [selectedRunId, setSelectedRunId] = useState("run_subject_preprocess_001");
  const [inspection, setInspection] = useState<RunInspection | null>(null);
  const [selectedState, setSelectedState] = useState<NodeStateSummary | null>(null);
  const [logContent, setLogContent] = useState<string | null>(null);
  const [logPath, setLogPath] = useState<string>("");
  const [error, setError] = useState("");

  async function refreshRuns() {
    setError("");
    try {
      const result = await listRuns(baseUrl);
      setRuns(result.runs || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function loadRun(runId = selectedRunId) {
    setError("");
    setSelectedState(null);
    setLogContent(null);

    try {
      const result = await inspectRun(baseUrl, runId);
      setInspection(result);
      setSelectedRunId(runId);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleReadLog(path: string) {
    setError("");
    setLogContent(null);
    setLogPath(path);

    try {
      const result = await readLog(baseUrl, path);
      setLogContent(result.content);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }

  const summaryStatus =
    inspection?.summary &&
    typeof inspection.summary === "object" &&
    "status" in inspection.summary
      ? String((inspection.summary as { status?: unknown }).status)
      : "UNKNOWN";

  return (
    <div>
      <div className="formGrid">
        <label>
          Run ID
          <input
            value={selectedRunId}
            onChange={(event) => setSelectedRunId(event.target.value)}
          />
        </label>
      </div>

      <div className="row">
        <button onClick={refreshRuns}>刷新 Run 列表</button>
        <button onClick={() => loadRun()}>加载 Run</button>
        {inspection ? <StatusBadge status={summaryStatus} /> : null}
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {runs.length > 0 ? (
        <div className="pipelineList">
          {runs.map((run) => {
            const runId = String(run.run_id || "");
            return (
              <button
                key={runId}
                className={runId === selectedRunId ? "listItem selected" : "listItem"}
                onClick={() => loadRun(runId)}
              >
                {runId} · {String(run.status || "UNKNOWN")}
              </button>
            );
          })}
        </div>
      ) : null}

      <h3>Pipeline Summary</h3>
      <JsonBlock value={inspection?.summary} emptyText="尚未加载 run summary" />

      <h3>Project-level States</h3>
      {inspection?.project_states?.length ? (
        <div className="stateGrid">
          {inspection.project_states.map((node) => (
            <NodeStateCard
              key={node.path}
              node={node}
              onSelect={setSelectedState}
              onReadLog={handleReadLog}
            />
          ))}
        </div>
      ) : (
        <div className="empty">暂无 project-level state</div>
      )}

      <h3>Subject-level States</h3>
      {inspection?.subjects?.length ? (
        <div className="subjectList">
          {inspection.subjects.map((subject) => (
            <div key={subject.subject_id} className="subjectPanel">
              <div className="stateCardHeader">
                <strong>{subject.subject_id}</strong>
                <StatusBadge status={subject.status} />
              </div>
              <div className="stateGrid">
                {subject.nodes.map((node) => (
                  <NodeStateCard
                    key={node.path}
                    node={node}
                    onSelect={setSelectedState}
                    onReadLog={handleReadLog}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="empty">暂无 subject-level state</div>
      )}

      <h3>Selected State Detail</h3>
      <JsonBlock value={selectedState} emptyText="请选择一个节点 state" />

      <h3>Log Viewer {logPath ? `· ${logPath}` : ""}</h3>
      <TextViewer text={logContent} emptyText="请选择 stdout 或 stderr 日志" />
    </div>
  );
}
