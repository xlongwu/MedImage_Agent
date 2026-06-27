import { useMemo, useState } from "react";
import type {
  TaskAuditPackage,
  TaskDiagnostics,
  TaskEvent,
  TaskLogEntry,
  TaskStatus,
} from "../../lib/types/task";
import {
  Badge,
  Button,
  Card,
  EmptyState,
  SegmentedControl,
  Table,
  TableEmpty,
} from "../../components/ui";
import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import styles from "./RunsWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface RunsWorkspaceProps {
  auditLoading: boolean;
  auditPackage: TaskAuditPackage | null;
  error: string;
  events: TaskEvent[];
  eventsError: string;
  eventsLoading: boolean;
  diagnostics: TaskDiagnostics;
  loading: boolean;
  onApprovalNameChange: (value: string) => void;
  onApprove: () => void;
  onGenerateAudit: () => void;
  onReconnect: () => void;
  onRetryEvents: () => void;
  onRetryTasks: () => void;
  onSelectTask: (taskId: string) => void;
  projectId: string | null;
  selectedTask: TaskLogEntry | null;
  selectedTaskId: string | null;
  streamConnected: boolean;
  taskApprovalName: string;
  tasks: TaskLogEntry[];
}

type RunStatusFilter = "all" | "active" | "failed" | "completed";
type RunDetailTab = "events" | "logs" | "diagnostics" | "artifacts" | "audit";

const RUN_LIST_RENDER_LIMIT = 50;
const RUN_LOG_RENDER_LIMIT = 12;
const DIAGNOSIS_RENDER_LIMIT = 8;
const EXTERNAL_TOOL_RENDER_LIMIT = 4;

export function RunsWorkspace({
  auditLoading,
  auditPackage,
  diagnostics,
  error,
  events,
  eventsError,
  eventsLoading,
  loading,
  onApprovalNameChange,
  onApprove,
  onGenerateAudit,
  onReconnect,
  onRetryEvents,
  onRetryTasks,
  onSelectTask,
  projectId,
  selectedTask,
  selectedTaskId,
  streamConnected,
  taskApprovalName,
  tasks,
}: RunsWorkspaceProps) {
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState<RunStatusFilter>("all");
  const [detailTab, setDetailTab] = useState<RunDetailTab>("events");
  const hasProject = Boolean(projectId);
  const filteredTasks = useMemo(
    () =>
      tasks.filter((task) => {
        const query = searchTerm.trim().toLowerCase();
        const matchesQuery =
          !query ||
          [
            task.id,
            task.run_name,
            task.pipeline,
            task.dataset,
            task.owner,
            task.execution_mode ?? "",
          ].some((value) => value.toLowerCase().includes(query));
        const matchesStatus =
          statusFilter === "all" ||
          (statusFilter === "active" &&
            (task.status === "running" || task.status === "pending")) ||
          (statusFilter === "failed" && task.status === "failed") ||
          (statusFilter === "completed" && task.status === "completed");

        return matchesQuery && matchesStatus;
      }),
    [searchTerm, statusFilter, tasks],
  );
  const visibleTasks = filteredTasks.slice(0, RUN_LIST_RENDER_LIMIT);
  const isFiltered = searchTerm.trim().length > 0 || statusFilter !== "all";
  const hasActiveRun = tasks.some((task) => task.status === "running" || task.status === "pending");
  const streamLabel = hasActiveRun
    ? streamConnected
      ? "Run stream connected"
      : "Run stream disconnected"
    : "No active run stream";
  const emptyRunListMessage = runListEmptyMessage({
    error,
    filtered: isFiltered,
    loading,
    projectId,
    taskCount: tasks.length,
  });

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Runs"
        subtitle="Review persisted execution runs. Review packages that have not created an execution record remain in their source workspace."
        status={hasProject ? "Run history" : "Select project"}
      />

      {!hasProject ? (
        <EmptyState
          title="Select a project before reviewing runs"
          description="Run records and diagnostics are project-scoped. Choose a project before opening execution history."
        />
      ) : (
        <RunsOverview tasks={tasks} />
      )}

      <section className={styles.runLayout} aria-label="Run list and diagnostics">
        <Card className={styles.runListCard} tone="muted">
          <div className={styles.sectionHeader}>
            <div>
              <h3>Execution runs</h3>
              <p>
                Review / audit packages without an execution record stay in their source
                workspace; this page lists backend task runs only.
              </p>
            </div>
            <div className={styles.headerActions}>
              <span
                className={`${styles.streamChip} ${
                  streamConnected && hasActiveRun ? styles.online : ""
                } ${!hasActiveRun ? styles.idle : ""}`}
                aria-label="Run stream status"
              >
                {streamLabel}
              </span>
              {error ? (
                <Button size="sm" variant="secondary" onClick={onRetryTasks}>
                  Retry
                </Button>
              ) : null}
            </div>
          </div>

          {hasProject ? (
            <div className={styles.runControls}>
              <label className={styles.searchField}>
                <span>Search runs</span>
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder="Run name, ID, pipeline, owner"
                />
              </label>
              <SegmentedControl
                aria-label="Filter runs by status"
                value={statusFilter}
                onChange={(value) => setStatusFilter(value as RunStatusFilter)}
                options={[
                  { label: "All", value: "all" },
                  { label: "Active", value: "active" },
                  { label: "Failed", value: "failed" },
                  { label: "Completed", value: "completed" },
                ]}
              />
            </div>
          ) : null}

          {loading && tasks.length ? <div className={styles.loadingLine}>Refreshing runs...</div> : null}
          {error ? (
            <div className={styles.errorLine}>
              {tasks.length ? "Run refresh failed; showing last loaded rows. " : ""}
              {error}
            </div>
          ) : null}

          {hasProject ? (
            <Table caption="Project run history">
              <thead>
                <tr>
                  <th>Run</th>
                  <th>Project</th>
                  <th>Pipeline</th>
                  <th>Status</th>
                  <th>Progress</th>
                  <th>Started</th>
                  <th>Duration</th>
                  <th>Triggered by</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {visibleTasks.length ? (
                  visibleTasks.map((task) => (
                    <tr
                      key={task.id}
                      className={task.id === selectedTaskId ? styles.selectedRow : undefined}
                    >
                      <td>
                        <strong className={styles.runName}>{task.run_name}</strong>
                        <small className={styles.runMeta}>{task.id}</small>
                      </td>
                      <td>{task.dataset || projectId}</td>
                      <td>{task.pipeline}</td>
                      <td>
                        <Badge tone={statusTone(task.status)} size="sm">
                          {task.status}
                        </Badge>
                      </td>
                      <td>
                        <RunProgress value={task.progress} />
                      </td>
                      <td>{task.started_at}</td>
                      <td>{task.duration || "In progress"}</td>
                      <td>{task.owner}</td>
                      <td>
                        <Button
                          size="sm"
                          variant={task.id === selectedTaskId ? "primary" : "secondary"}
                          onClick={() => onSelectTask(task.id)}
                        >
                          Open
                        </Button>
                      </td>
                    </tr>
                  ))
                ) : (
                  <TableEmpty colSpan={9}>{emptyRunListMessage}</TableEmpty>
                )}
              </tbody>
            </Table>
          ) : (
            <EmptyState
              title="Run list unavailable"
              description="Select a project before loading task history."
            />
          )}
          {filteredTasks.length > visibleTasks.length ? (
            <div className={styles.trimNote}>
              Showing the first {visibleTasks.length} of {filteredTasks.length} matching runs.
              Narrow the search to inspect older records.
            </div>
          ) : null}
        </Card>

        <Card className={styles.detailCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>Run detail</h3>
              <p>
                Status summary, run timeline, diagnostics, artifacts, and audit evidence stay tied
                to one selected run.
              </p>
            </div>
          </div>
          {selectedTask ? (
            <RunDetailPanel
              task={selectedTask}
              events={events}
              diagnostics={diagnostics}
              loading={eventsLoading}
              error={eventsError}
              streamConnected={streamConnected}
              approvalName={taskApprovalName}
              auditPackage={auditPackage}
              auditLoading={auditLoading}
              onApprovalNameChange={onApprovalNameChange}
              onApprove={onApprove}
              onGenerateAudit={onGenerateAudit}
              onRetry={onRetryEvents}
              onReconnect={onReconnect}
              activeTab={detailTab}
              onTabChange={setDetailTab}
            />
          ) : (
            <EmptyState
              title="Select a run to inspect"
              description="Choose a real execution run to review persisted events, diagnostics, approval state, and audit package evidence."
            />
          )}
        </Card>
      </section>
    </div>
  );
}

interface RunDetailPanelProps {
  activeTab: RunDetailTab;
  auditLoading: boolean;
  auditPackage: TaskAuditPackage | null;
  approvalName: string;
  diagnostics: TaskDiagnostics;
  error: string;
  events: TaskEvent[];
  loading: boolean;
  onApprovalNameChange: (value: string) => void;
  onApprove: () => void;
  onGenerateAudit: () => void;
  onReconnect: () => void;
  onRetry: () => void;
  onTabChange: (value: RunDetailTab) => void;
  streamConnected: boolean;
  task: TaskLogEntry;
}

function RunDetailPanel({
  activeTab,
  auditLoading,
  auditPackage,
  approvalName,
  diagnostics,
  error,
  events,
  loading,
  onApprovalNameChange,
  onApprove,
  onGenerateAudit,
  onReconnect,
  onRetry,
  onTabChange,
  streamConnected,
  task,
}: RunDetailPanelProps) {
  const latestEvents = events.length ? events : eventsFromLogs(task);
  const timeline = buildRunTimeline(task, latestEvents);
  const artifactEntries = flattenArtifactEntries(diagnostics.artifacts);
  const logMessages = useMemo(
    () => [...task.logs, ...diagnostics.logs],
    [diagnostics.logs, task.logs],
  );
  const visibleLogMessages = logMessages.slice(-RUN_LOG_RENDER_LIMIT);
  const nodeInspector = buildNodeInspector(task, diagnostics, latestEvents);
  const retryAllowed = diagnosticsRetryAllowed(diagnostics);
  const [failureActionStatus, setFailureActionStatus] = useState("");
  const [showFailureExplanation, setShowFailureExplanation] = useState(false);
  const hasDiagnostics =
    diagnostics.diagnosis.length ||
    diagnostics.errors.length ||
    diagnostics.warnings.length ||
    diagnostics.external_tool_results.length;
  const taskHasActiveStream = task.status === "running" || task.status === "pending";
  const detailStreamLabel = taskHasActiveStream
    ? streamConnected
      ? "Stream live"
      : "Run stream disconnected"
    : "No active stream";

  async function handleCopyDiagnostics() {
    const payload = buildDiagnosticsCopyPayload(task, diagnostics, latestEvents);
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error("Clipboard API unavailable");
      }
      await navigator.clipboard.writeText(payload);
      setFailureActionStatus("Diagnostics copied");
    } catch {
      setFailureActionStatus("Clipboard unavailable");
    }
  }

  function handleRetryAllowedStep() {
    setFailureActionStatus(
      retryAllowed
        ? "Retry handoff requires the reviewed backend retry workflow."
        : "Retry is disabled until backend diagnostics mark a step as retry eligible.",
    );
  }

  return (
    <section className={styles.detailPanel} aria-label="Selected run detail">
      <div className={styles.detailSummary}>
        <div className={styles.detailTitleBlock}>
          <span className={styles.kicker}>Run detail</span>
          <strong>{task.run_name}</strong>
          <small>{task.id}</small>
        </div>
        <div className={styles.detailActions}>
          <Badge tone={statusTone(task.status)}>{statusLabel(task.status)}</Badge>
          <span
            className={`${styles.streamChip} ${
              streamConnected && taskHasActiveStream ? styles.online : ""
            } ${!taskHasActiveStream ? styles.idle : ""}`}
          >
            {detailStreamLabel}
          </span>
          {error ? (
            <Button size="sm" variant="secondary" onClick={onRetry}>
              Reload Events
            </Button>
          ) : null}
          {!streamConnected && task.status === "running" ? (
            <Button size="sm" variant="secondary" onClick={onReconnect}>
              Reconnect
            </Button>
          ) : null}
          <Button size="sm" variant="secondary" onClick={onGenerateAudit} disabled={auditLoading}>
            {auditLoading ? "Requesting" : "Request Audit Package"}
          </Button>
        </div>
      </div>

      <div className={styles.detailFacts} aria-label="Run facts">
        <RunFact label="Pipeline" value={task.pipeline} />
        <RunFact label="Status" value={statusLabel(task.status)} />
        <RunFact label="Progress" value={`${clampProgress(task.progress)}%`} />
        <RunFact label="Started" value={task.started_at} />
        <RunFact label="Duration" value={task.duration || "In progress"} />
        <RunFact label="Triggered by" value={task.owner} />
        <RunFact label="Execution" value={task.execution_mode || "Not reported"} />
        <RunFact label="Result" value={formatResultFact(task)} />
      </div>

      <div className={styles.timelinePanel}>
        <div className={styles.panelHeader}>
          <span>Pipeline timeline</span>
          <small>{timeline.length} recorded checkpoints</small>
        </div>
        <ol className={styles.timeline} aria-label="Pipeline timeline">
          {timeline.map((item, index) => (
            <li key={`${item.label}-${item.message}-${index}`} data-status={item.status}>
              <span>{item.label}</span>
              <p>{item.message}</p>
              <small>{item.time}</small>
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.nodeInspector} aria-label="Selected node inspector">
        <div className={styles.panelHeader}>
          <span>Node inspector</span>
          <small>{nodeInspector.source}</small>
        </div>
        <div className={styles.nodeGrid}>
          <RunFact label="Node" value={nodeInspector.node} />
          <RunFact label="State" value={nodeInspector.state} />
          <RunFact label="Evidence" value={nodeInspector.evidence} />
          <RunFact label="Retry" value={nodeInspector.retry} />
        </div>
      </div>

      <SegmentedControl
        aria-label="Run detail sections"
        value={activeTab}
        onChange={(value) => onTabChange(value as RunDetailTab)}
        options={[
          { label: "Events", value: "events" },
          { label: "Logs", value: "logs" },
          { label: "Diagnostics", value: "diagnostics" },
          { label: "Artifacts", value: "artifacts" },
          { label: "Audit", value: "audit" },
        ]}
      />

      <div className={styles.tabPanel}>
        {activeTab === "events" ? (
          <section aria-label="Run events">
            {loading ? <div className={styles.loadingLine}>Loading persisted events...</div> : null}
            {error ? <div className={styles.errorLine}>{error}</div> : null}
            <div className={styles.eventList}>
              {latestEvents.map((event) => (
                <div className={styles.eventRow} key={`${event.id}-${event.timestamp}-${event.message}`}>
                  <span>{event.timestamp}</span>
                  <strong>{clampProgress(event.progress)}%</strong>
                  <p>{event.message}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {activeTab === "logs" ? (
          <section aria-label="Run logs">
            {logMessages.length ? (
              <>
                {logMessages.length > visibleLogMessages.length ? (
                  <div className={styles.trimNote} role="status">
                    Showing latest {visibleLogMessages.length} of {logMessages.length} log lines.
                    Open persisted diagnostics or narrow the run context for older records.
                  </div>
                ) : null}
                <div className={styles.logList}>
                  {visibleLogMessages.map((message, index) => (
                    <p key={`${message}-${index}`}>{message}</p>
                  ))}
                </div>
              </>
            ) : (
              <EmptyState
                title="No run logs recorded"
                description="Logs will appear here after the runtime records task output."
              />
            )}
          </section>
        ) : null}

        {activeTab === "diagnostics" ? (
          <section aria-label="Run diagnostics">
            {task.status === "failed" ? (
              <div className={styles.failureBanner} role="alert">
                Failed run. Review the persisted events and diagnostic records before retrying any
                allowed workflow step.
              </div>
            ) : null}
            {task.status === "failed" ? (
              <div className={styles.failureActions} aria-label="Failed node actions">
                <div>
                  <strong>Failed node response</strong>
                  <p>
                    These actions organize diagnostics only. Retrying remains disabled unless the
                    backend marks a reviewed step as eligible.
                  </p>
                </div>
                <div className={styles.failureButtonRow}>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setShowFailureExplanation((value) => !value)}
                  >
                    Explain Error
                  </Button>
                  <Button size="sm" variant="secondary" onClick={handleCopyDiagnostics}>
                    Copy Diagnostics
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!retryAllowed}
                    onClick={handleRetryAllowedStep}
                  >
                    Retry Allowed Step
                  </Button>
                </div>
                {showFailureExplanation ? (
                  <div className={styles.failureExplanation} aria-label="Failure explanation">
                    <span>{nodeInspector.node}</span>
                    <p>{nodeInspector.evidence}</p>
                  </div>
                ) : null}
                <small>{failureActionStatus || nodeInspector.retry}</small>
              </div>
            ) : null}
            {hasDiagnostics ? (
              <div className={styles.diagnosticsList}>
                {diagnostics.errors.map((message, index) => (
                  <DiagnosticItem key={`error-${index}`} tone="danger" label="Error" message={message} />
                ))}
                {diagnostics.warnings.map((message, index) => (
                  <DiagnosticItem key={`warning-${index}`} tone="warning" label="Warning" message={message} />
                ))}
                {diagnostics.diagnosis.slice(0, DIAGNOSIS_RENDER_LIMIT).map((item, index) => (
                  <DiagnosticItem
                    key={`diagnosis-${index}`}
                    tone={diagnosticTone(item.severity)}
                    label={String(item.code || item.severity || "diagnostic")}
                    message={String(item.message || "Diagnostic record available.")}
                  />
                ))}
                {diagnostics.external_tool_results
                  .slice(0, EXTERNAL_TOOL_RENDER_LIMIT)
                  .map((result, index) => (
                    <DiagnosticItem
                      key={`tool-${index}`}
                      tone={String(result.returncode ?? "0") === "0" ? "info" : "warning"}
                      label={String(
                        result.command || result.function || `External tool ${index + 1}`,
                      )}
                      message={`returncode ${String(result.returncode ?? "n/a")}`}
                    />
                  ))}
              </div>
            ) : (
              <EmptyState
                title="No diagnostics recorded"
                description="The selected run has no persisted diagnostic records yet."
              />
            )}
          </section>
        ) : null}

        {activeTab === "artifacts" ? (
          <section aria-label="Run artifacts">
            {task.result_path ? (
              <div className={styles.artifactPath}>
                <span>Reported result path</span>
                <strong>{task.result_path}</strong>
              </div>
            ) : null}
            {artifactEntries.length ? (
              <div className={styles.artifactList}>
                {artifactEntries.map((entry) => (
                  <div className={styles.artifactRow} key={`${entry.label}-${entry.value}`}>
                    <span>{entry.label}</span>
                    <strong>{entry.value}</strong>
                  </div>
                ))}
              </div>
            ) : !task.result_path ? (
              <EmptyState
                title="No artifacts registered"
                description="Artifacts appear here only after the runtime reports persisted outputs."
              />
            ) : null}
          </section>
        ) : null}

        {activeTab === "audit" ? (
          <section className={styles.auditPanel} aria-label="Run audit">
            {task.execution_mode === "external_smoke" && !diagnostics.approval ? (
              <div className={styles.approvalBox}>
                <div>
                  <span>Approval required</span>
                  <strong>External smoke runs require manual review</strong>
                </div>
                <label>
                  <span>Approved by</span>
                  <input
                    value={approvalName}
                    onChange={(event) => onApprovalNameChange(event.target.value)}
                    placeholder="Research lead name"
                  />
                </label>
                <Button size="sm" variant="primary" onClick={onApprove}>
                  Submit Approval to Backend
                </Button>
              </div>
            ) : (
              <div className={styles.auditRecord}>
                <span>Approval</span>
                <strong>
                  {diagnostics.approval
                    ? `${diagnostics.approval.approved_by} at ${diagnostics.approval.approved_at}`
                    : "No approval record required or available"}
                </strong>
              </div>
            )}
            {auditPackage ? (
              <div className={styles.auditPackage}>
                <div>
                  <span>Audit package</span>
                  <strong>{auditPackage.generated_at}</strong>
                </div>
                <p>{auditPackage.report_path}</p>
                <p>{auditPackage.json_path}</p>
              </div>
            ) : (
              <EmptyState
                title="Audit package not generated"
                description="Request backend audit package generation from the selected run when evidence export is needed."
                action={
                  <Button size="sm" variant="secondary" onClick={onGenerateAudit} disabled={auditLoading}>
                    {auditLoading ? "Requesting" : "Request Audit Package"}
                  </Button>
                }
              />
            )}
          </section>
        ) : null}
      </div>
    </section>
  );
}

function RunsOverview({ tasks }: { tasks: TaskLogEntry[] }) {
  const running = tasks.filter((task) => task.status === "running").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  const pending = tasks.filter((task) => task.status === "pending").length;

  return (
    <section className={styles.summaryGrid} aria-label="Run history overview">
      <Card tone="muted">
        <div className={styles.summaryItem}>
          <span>Total</span>
          <strong>{tasks.length}</strong>
          <small>Loaded task records</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>Active</span>
          <strong>{running + pending}</strong>
          <small>{running} running / {pending} pending</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>Failed</span>
          <strong>{failed}</strong>
          <small>Needs diagnostics review</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>Completed</span>
          <strong>{completed}</strong>
          <small>Available for audit review</small>
        </div>
      </Card>
    </section>
  );
}

function runListEmptyMessage({
  error,
  filtered,
  loading,
  projectId,
  taskCount,
}: {
  error: string;
  filtered: boolean;
  loading: boolean;
  projectId: string | null;
  taskCount: number;
}): string {
  if (!projectId) return "Select a project before loading run history.";
  if (loading && taskCount === 0) return "Loading run records...";
  if (error && taskCount === 0) return "Run history unavailable. Retry to reload backend records.";
  if (filtered) {
    return "No runs match the current search and status filters. Active or failed runs will also appear in the bottom activity bar.";
  }
  return "No execution runs recorded for this project yet. Dry-run review packages stay in Data & Conversion until an approved execution creates run history.";
}

function RunProgress({ value }: { value: number }) {
  const progress = clampProgress(value);

  return (
    <div className={styles.progressCell} aria-label={`Progress ${progress}%`}>
      <span className={styles.progressTrack}>
        <span className={styles.progressFill} style={{ width: `${progress}%` }} />
      </span>
      <strong>{progress}%</strong>
    </div>
  );
}

function RunFact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function formatResultFact(task: TaskLogEntry): string {
  if (task.result_path) return task.result_path;
  if (task.status === "running" || task.status === "pending") return "Pending backend report";
  if (task.status === "failed") return "No completed result";
  return "No result path reported";
}

function DiagnosticItem({
  label,
  message,
  tone,
}: {
  label: string;
  message: string;
  tone: "danger" | "info" | "neutral" | "warning";
}) {
  return (
    <div className={styles.diagnosticItem} data-tone={tone}>
      <span>{label}</span>
      <p>{message}</p>
    </div>
  );
}

function eventsFromLogs(task: TaskLogEntry): TaskEvent[] {
  const logs = task.logs.length ? task.logs : ["No run events recorded."];
  return logs.map((message, index) => ({
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
}

function buildRunTimeline(task: TaskLogEntry, events: TaskEvent[]) {
  const checkpoints = events.slice(-5).map((event, index) => ({
    label: index === events.slice(-5).length - 1 ? "Latest" : `Step ${index + 1}`,
    message: event.message,
    status: event.status,
    time: event.timestamp,
  }));

  if (checkpoints.length) {
    return checkpoints;
  }

  return [
    {
      label: "Latest",
      message: task.logs[task.logs.length - 1] ?? "No run events recorded.",
      status: task.status,
      time: task.started_at,
    },
  ];
}

function flattenArtifactEntries(artifacts: Record<string, unknown>) {
  return Object.entries(artifacts)
    .slice(0, 12)
    .map(([label, value]) => ({
      label,
      value: formatArtifactValue(value),
    }));
}

function formatArtifactValue(value: unknown): string {
  if (value === null || value === undefined) return "Unavailable";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return `${value.length} entries`;
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function buildNodeInspector(
  task: TaskLogEntry,
  diagnostics: TaskDiagnostics,
  events: TaskEvent[],
) {
  const diagnostic = pickPrimaryDiagnostic(diagnostics);
  const node =
    firstStringValue(diagnostic, ["node_id", "node", "node_name", "stage", "step_id", "code"]) ||
    task.pipeline;
  const evidence =
    diagnostics.errors[0] ||
    firstStringValue(diagnostic, ["message", "error", "detail", "recommendation"]) ||
    events[events.length - 1]?.message ||
    task.logs[task.logs.length - 1] ||
    "No node-level evidence recorded.";
  const retry = diagnosticsRetryAllowed(diagnostics)
    ? "Backend marked retry eligible"
    : "Backend retry eligibility not recorded";

  return {
    evidence,
    node,
    retry,
    source: diagnostic ? "diagnostic record" : "run event fallback",
    state: statusLabel(task.status),
  };
}

function pickPrimaryDiagnostic(diagnostics: TaskDiagnostics): Record<string, unknown> | null {
  const failed = diagnostics.diagnosis.find((item) => {
    const severity = String(item.severity ?? item.status ?? "").toLowerCase();
    return severity.includes("error") || severity.includes("fail");
  });
  return failed ?? diagnostics.diagnosis[0] ?? null;
}

function firstStringValue(record: Record<string, unknown> | null, keys: string[]): string {
  if (!record) return "";
  for (const key of keys) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return "";
}

function diagnosticsRetryAllowed(diagnostics: TaskDiagnostics): boolean {
  return diagnostics.diagnosis.some((item) =>
    ["retry_allowed", "retry_eligible", "retry_supported"].some((key) => item[key] === true),
  );
}

function buildDiagnosticsCopyPayload(
  task: TaskLogEntry,
  diagnostics: TaskDiagnostics,
  events: TaskEvent[],
): string {
  return JSON.stringify(
    {
      task_id: task.id,
      run_name: task.run_name,
      pipeline: task.pipeline,
      status: task.status,
      errors: diagnostics.errors,
      warnings: diagnostics.warnings,
      diagnosis: diagnostics.diagnosis,
      latest_events: events.slice(-5).map((event) => ({
        message: event.message,
        progress: event.progress,
        status: event.status,
        timestamp: event.timestamp,
      })),
    },
    null,
    2,
  );
}

function diagnosticTone(severity: unknown): "danger" | "info" | "neutral" | "warning" {
  const value = String(severity ?? "").toLowerCase();
  if (value.includes("error") || value.includes("fail")) return "danger";
  if (value.includes("warn")) return "warning";
  if (value.includes("info")) return "info";
  return "neutral";
}

function statusLabel(status: TaskStatus): string {
  if (status === "completed") return "Completed";
  if (status === "failed") return "Failed";
  if (status === "running") return "Running";
  if (status === "pending") return "Pending";
  return "Disconnected";
}

function clampProgress(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function statusTone(status: TaskStatus): "neutral" | "info" | "success" | "warning" | "danger" {
  if (status === "completed") return "success";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  if (status === "pending" || status === "disconnected") return "warning";
  return "neutral";
}
