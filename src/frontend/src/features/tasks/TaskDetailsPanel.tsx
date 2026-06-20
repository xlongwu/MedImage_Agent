import { useState } from "react";
import type { TaskAuditPackage, TaskDiagnostics, TaskEvent, TaskLogEntry } from "../../lib/types/task";

export interface TaskDetailsPanelProps {
  task: TaskLogEntry | null;
  events: TaskEvent[];
  diagnostics: TaskDiagnostics;
  loading: boolean;
  error: string;
  streamConnected: boolean;
  approvalName: string;
  auditPackage: TaskAuditPackage | null;
  auditLoading: boolean;
  onApprovalNameChange: (value: string) => void;
  onApprove: () => void;
  onGenerateAudit: () => void;
  onRetry: () => void;
  onReconnect: () => void;
}

export function TaskDetailsPanel({
  task,
  events,
  diagnostics,
  loading,
  error,
  streamConnected,
  approvalName,
  auditPackage,
  auditLoading,
  onApprovalNameChange,
  onApprove,
  onGenerateAudit,
  onRetry,
  onReconnect,
}: TaskDetailsPanelProps) {
  const [showTechDetails, setShowTechDetails] = useState(false);

  if (!task) {
    return null;
  }

  const latestEvents = events.length
    ? events
    : task.logs.map((message, index) => ({
        id: index,
        task_id: task.id,
        status: task.status,
        progress: task.progress,
        message,
        timestamp: task.started_at,
        result_path: task.result_path,
        source: "task-log",
        metadata: {},
      }));

  return (
    <section className="task-detail-panel">
      <div className="card-row">
        <div>
          <div className="card-title">Task Details</div>
          <span>{task.run_name}</span>
        </div>
        <div className="detail-actions">
          <StatusPill status={task.status} />
          <span className={`stream-chip ${streamConnected ? "online" : ""}`}>
            {streamConnected ? "Stream live" : "Stream idle"}
          </span>
          {error ? <button onClick={onRetry}>Reload Events</button> : null}
          {!streamConnected && task.status === "running" ? <button onClick={onReconnect}>Reconnect</button> : null}
          <button onClick={onGenerateAudit} disabled={auditLoading}>
            {auditLoading ? "Generating..." : "Audit Package"}
          </button>
        </div>
      </div>
      <div className="detail-grid">
        <div><span>Mode</span><strong>{task.execution_mode || "simulated"}</strong></div>
        <div><span>Progress</span><strong>{task.progress}%</strong></div>
        <div><span>Owner</span><strong>{task.owner}</strong></div>
        <div><span>Result</span><strong>{task.result_path || "Pending"}</strong></div>
      </div>
      {task.execution_mode === "external_smoke" ? (
        <div className="approval-strip">
          <div>
            <span>Approval</span>
            <strong>
              {diagnostics.approval
                ? `${diagnostics.approval.approved_by} at ${diagnostics.approval.approved_at}`
                : "Manual review only; approved smoke is locked"}
            </strong>
          </div>
          {!diagnostics.approval ? (
            <label>
              <span>Approved by</span>
              <input
                value={approvalName}
                onChange={(event) => onApprovalNameChange(event.target.value)}
                placeholder="Research lead name"
              />
            </label>
          ) : null}
          {!diagnostics.approval ? <button onClick={onApprove}>Approve Smoke</button> : null}
        </div>
      ) : null}
      {diagnostics.diagnosis.length ? (
        <div className="diagnostic-list">
          {diagnostics.diagnosis.slice(0, 4).map((item, index) => (
            <div key={`${item.code}-${index}`} className={`diagnostic-item ${String(item.severity || "info")}`}>
              <span>{String(item.code || "diagnostic")}</span>
              <p>{String(item.message || "")}</p>
            </div>
          ))}
        </div>
      ) : null}

      <div className="section-spacer">
        <label className="tech-details-toggle">
          <input
            type="checkbox"
            checked={showTechDetails}
            onChange={(e) => setShowTechDetails(e.target.checked)}
          />
          Show technical details
        </label>
      </div>

      {showTechDetails && (
        <>
          {diagnostics.external_tool_results.length ? (
            <div className="tool-result-list">
              <div className="panel-kicker">External tool results</div>
              {diagnostics.external_tool_results.slice(0, 3).map((result, index) => (
                <div className="tool-result-row" key={index}>
                  <strong>{String(result.command || result.function || `External run ${index + 1}`)}</strong>
                  <span>returncode {String(result.returncode ?? "n/a")}</span>
                </div>
              ))}
            </div>
          ) : null}
          {auditPackage ? (
            <div className="audit-package-box">
              <div>
                <span>Audit package</span>
                <strong>{auditPackage.generated_at}</strong>
              </div>
              <p>{auditPackage.report_path}</p>
              <p>{auditPackage.json_path}</p>
            </div>
          ) : null}
          <div className="event-list">
            {loading ? <div className="event-row muted">Loading persisted events...</div> : null}
            {latestEvents.map((event) => (
              <div className="event-row" key={`${event.id}-${event.timestamp}-${event.message}`}>
                <span>{event.timestamp}</span>
                <strong>{event.progress}%</strong>
                <p>{event.message}</p>
              </div>
            ))}
          </div>
        </>
      )}
      {error ? <div className="detail-error">{error}</div> : null}
    </section>
  );
}

function StatusPill({ status }: { status: string }) {
  const tone = status.toLowerCase();
  return <span className={`status-pill ${tone}`}>{status}</span>;
}
