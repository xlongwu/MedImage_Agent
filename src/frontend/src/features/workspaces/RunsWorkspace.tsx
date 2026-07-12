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
import { useI18n } from "../../i18n/useI18n";

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
type Translate = ReturnType<typeof useI18n>["t"];

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
  const { t } = useI18n();
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
          (statusFilter === "active" && (task.status === "running" || task.status === "pending")) ||
          (statusFilter === "failed" && task.status === "failed") ||
          (statusFilter === "completed" &&
            (task.status === "completed" || task.status === "partial"));

        return matchesQuery && matchesStatus;
      }),
    [searchTerm, statusFilter, tasks],
  );
  const visibleTasks = filteredTasks.slice(0, RUN_LIST_RENDER_LIMIT);
  const isFiltered = searchTerm.trim().length > 0 || statusFilter !== "all";
  const hasActiveRun = tasks.some((task) => task.status === "running" || task.status === "pending");
  const streamLabel = hasActiveRun
    ? streamConnected
      ? t("runs.stream.connected")
      : t("runs.stream.disconnected")
    : t("runs.stream.none");
  const emptyRunListMessage = runListEmptyMessage({
    error,
    filtered: isFiltered,
    loading,
    projectId,
    taskCount: tasks.length,
    t,
  });

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title={t("runs.title")}
        subtitle={t("runs.subtitle")}
        status={hasProject ? t("runs.header.history") : t("runs.header.selectProject")}
      />

      {!hasProject ? (
        <EmptyState
          title={t("runs.noProject.title")}
          description={t("runs.noProject.description")}
        />
      ) : (
        <RunsOverview tasks={tasks} />
      )}

      <section className={styles.runLayout} aria-label={t("runs.layoutAria")}>
        <Card className={styles.runListCard} tone="muted">
          <div className={styles.sectionHeader}>
            <div>
              <h3>{t("runs.execution.title")}</h3>
              <p>{t("runs.execution.description")}</p>
            </div>
            <div className={styles.headerActions}>
              <span
                className={`${styles.streamChip} ${
                  streamConnected && hasActiveRun ? styles.online : ""
                } ${!hasActiveRun ? styles.idle : ""}`}
                aria-label={t("runs.stream.status")}
              >
                {streamLabel}
              </span>
              {error ? (
                <Button size="sm" variant="secondary" onClick={onRetryTasks}>
                  {t("common.retry")}
                </Button>
              ) : null}
            </div>
          </div>

          {hasProject ? (
            <div className={styles.runControls}>
              <label className={styles.searchField}>
                <span>{t("runs.search")}</span>
                <input
                  value={searchTerm}
                  onChange={(event) => setSearchTerm(event.target.value)}
                  placeholder={t("runs.searchPlaceholder")}
                />
              </label>
              <SegmentedControl
                aria-label={t("runs.filterAria")}
                value={statusFilter}
                onChange={(value) => setStatusFilter(value as RunStatusFilter)}
                options={[
                  { label: t("runs.filter.all"), value: "all" },
                  { label: t("runs.filter.active"), value: "active" },
                  { label: t("runs.filter.failed"), value: "failed" },
                  { label: t("runs.filter.completed"), value: "completed" },
                ]}
              />
            </div>
          ) : null}

          {loading && tasks.length ? (
            <div className={styles.loadingLine}>{t("runs.refreshing")}</div>
          ) : null}
          {error ? (
            <div className={styles.errorLine}>
              {tasks.length ? t("runs.refreshFailedStale") : ""}
              {error}
            </div>
          ) : null}

          {hasProject ? (
            <Table caption={t("runs.table.caption")}>
              <thead>
                <tr>
                  <th>{t("runs.table.run")}</th>
                  <th>{t("runs.table.project")}</th>
                  <th>{t("runs.table.pipeline")}</th>
                  <th>{t("runs.table.status")}</th>
                  <th>{t("runs.table.progress")}</th>
                  <th>{t("runs.table.started")}</th>
                  <th>{t("runs.table.duration")}</th>
                  <th>{t("runs.table.triggeredBy")}</th>
                  <th>{t("runs.table.action")}</th>
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
                          {statusLabel(task.status, t)}
                        </Badge>
                      </td>
                      <td>
                        <RunProgress value={task.progress} />
                      </td>
                      <td>{task.started_at}</td>
                      <td>{task.duration || t("runs.inProgress")}</td>
                      <td>{task.owner}</td>
                      <td>
                        <Button
                          size="sm"
                          variant={task.id === selectedTaskId ? "primary" : "secondary"}
                          onClick={() => onSelectTask(task.id)}
                        >
                          {t("common.open")}
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
              title={t("runs.listUnavailable.title")}
              description={t("runs.listUnavailable.description")}
            />
          )}
          {filteredTasks.length > visibleTasks.length ? (
            <div className={styles.trimNote}>
              {t("runs.trimmed", {
                visible: visibleTasks.length,
                total: filteredTasks.length,
              })}
            </div>
          ) : null}
        </Card>

        <Card className={styles.detailCard}>
          <div className={styles.sectionHeader}>
            <div>
              <h3>{t("runs.detail.title")}</h3>
              <p>{t("runs.detail.description")}</p>
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
              title={t("runs.selectRun.title")}
              description={t("runs.selectRun.description")}
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
  const { t } = useI18n();
  const latestEvents = events.length ? events : eventsFromLogs(task, t);
  const timeline = buildRunTimeline(task, latestEvents, t);
  const artifactEntries = flattenArtifactEntries(diagnostics.artifacts, t);
  const logMessages = useMemo(
    () => [...task.logs, ...diagnostics.logs],
    [diagnostics.logs, task.logs],
  );
  const visibleLogMessages = logMessages.slice(-RUN_LOG_RENDER_LIMIT);
  const nodeInspector = buildNodeInspector(task, diagnostics, latestEvents, t);
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
      ? t("runs.detail.streamLive")
      : t("runs.detail.streamDisconnected")
    : t("runs.detail.noStream");

  async function handleCopyDiagnostics() {
    const payload = buildDiagnosticsCopyPayload(task, diagnostics, latestEvents);
    try {
      if (!navigator.clipboard?.writeText) {
        throw new Error(t("runs.diagnostics.clipboardApiUnavailable"));
      }
      await navigator.clipboard.writeText(payload);
      setFailureActionStatus(t("runs.diagnostics.copied"));
    } catch {
      setFailureActionStatus(t("runs.diagnostics.clipboardUnavailable"));
    }
  }

  function handleRetryAllowedStep() {
    setFailureActionStatus(
      retryAllowed ? t("runs.diagnostics.retryHandoff") : t("runs.diagnostics.retryDisabled"),
    );
  }

  return (
    <section className={styles.detailPanel} aria-label={t("runs.detail.aria")}>
      <div className={styles.detailSummary}>
        <div className={styles.detailTitleBlock}>
          <span className={styles.kicker}>{t("runs.detail.title")}</span>
          <strong>{task.run_name}</strong>
          <small>{task.id}</small>
        </div>
        <div className={styles.detailActions}>
          <Badge tone={statusTone(task.status)}>{statusLabel(task.status, t)}</Badge>
          <span
            className={`${styles.streamChip} ${
              streamConnected && taskHasActiveStream ? styles.online : ""
            } ${!taskHasActiveStream ? styles.idle : ""}`}
          >
            {detailStreamLabel}
          </span>
          {error ? (
            <Button size="sm" variant="secondary" onClick={onRetry}>
              {t("runs.detail.reloadEvents")}
            </Button>
          ) : null}
          {!streamConnected && task.status === "running" ? (
            <Button size="sm" variant="secondary" onClick={onReconnect}>
              {t("runs.detail.reconnect")}
            </Button>
          ) : null}
          <Button size="sm" variant="secondary" onClick={onGenerateAudit} disabled={auditLoading}>
            {auditLoading ? t("runs.detail.requesting") : t("runs.detail.requestAudit")}
          </Button>
        </div>
      </div>

      <div className={styles.detailFacts} aria-label={t("runs.facts")}>
        <RunFact label={t("runs.table.pipeline")} value={task.pipeline} />
        <RunFact label={t("runs.table.status")} value={statusLabel(task.status, t)} />
        <RunFact label={t("runs.table.progress")} value={`${clampProgress(task.progress)}%`} />
        <RunFact label={t("runs.table.started")} value={task.started_at} />
        <RunFact label={t("runs.table.duration")} value={task.duration || t("runs.inProgress")} />
        <RunFact label={t("runs.table.triggeredBy")} value={task.owner} />
        <RunFact
          label={t("runs.fact.execution")}
          value={task.execution_mode || t("runs.notReported")}
        />
        <RunFact label={t("runs.fact.result")} value={formatResultFact(task, t)} />
      </div>

      <div className={styles.timelinePanel}>
        <div className={styles.panelHeader}>
          <span>{t("runs.timeline")}</span>
          <small>{t("runs.timeline.checkpoints", { count: timeline.length })}</small>
        </div>
        <ol className={styles.timeline} aria-label={t("runs.timeline")}>
          {timeline.map((item, index) => (
            <li key={`${item.label}-${item.message}-${index}`} data-status={item.status}>
              <span>{item.label}</span>
              <p>{item.message}</p>
              <small>{item.time}</small>
            </li>
          ))}
        </ol>
      </div>

      <div className={styles.nodeInspector} aria-label={t("runs.node.aria")}>
        <div className={styles.panelHeader}>
          <span>{t("runs.node.title")}</span>
          <small>{nodeInspector.source}</small>
        </div>
        <div className={styles.nodeGrid}>
          <RunFact label={t("runs.node.node")} value={nodeInspector.node} />
          <RunFact label={t("runs.node.state")} value={nodeInspector.state} />
          <RunFact label={t("runs.node.evidence")} value={nodeInspector.evidence} />
          <RunFact label={t("runs.node.retry")} value={nodeInspector.retry} />
        </div>
      </div>

      <SegmentedControl
        aria-label={t("runs.sections")}
        value={activeTab}
        onChange={(value) => onTabChange(value as RunDetailTab)}
        options={[
          { label: t("runs.tab.events"), value: "events" },
          { label: t("runs.tab.logs"), value: "logs" },
          { label: t("runs.tab.diagnostics"), value: "diagnostics" },
          { label: t("runs.tab.artifacts"), value: "artifacts" },
          { label: t("runs.tab.audit"), value: "audit" },
        ]}
      />

      <div className={styles.tabPanel}>
        {activeTab === "events" ? (
          <section aria-label={t("runs.events.aria")}>
            {loading ? <div className={styles.loadingLine}>{t("runs.events.loading")}</div> : null}
            {error ? <div className={styles.errorLine}>{error}</div> : null}
            <div className={styles.eventList}>
              {latestEvents.map((event) => (
                <div
                  className={styles.eventRow}
                  key={`${event.id}-${event.timestamp}-${event.message}`}
                >
                  <span>{event.timestamp}</span>
                  <strong>{clampProgress(event.progress)}%</strong>
                  <p>{event.message}</p>
                </div>
              ))}
            </div>
          </section>
        ) : null}

        {activeTab === "logs" ? (
          <section aria-label={t("runs.logs.aria")}>
            {logMessages.length ? (
              <>
                {logMessages.length > visibleLogMessages.length ? (
                  <div className={styles.trimNote} role="status">
                    {t("runs.logs.trimmed", {
                      visible: visibleLogMessages.length,
                      total: logMessages.length,
                    })}
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
                title={t("runs.logs.emptyTitle")}
                description={t("runs.logs.emptyDescription")}
              />
            )}
          </section>
        ) : null}

        {activeTab === "diagnostics" ? (
          <section aria-label={t("runs.diagnostics.aria")}>
            {task.status === "failed" ? (
              <div className={styles.failureBanner} role="alert">
                {t("runs.diagnostics.failedBanner")}
              </div>
            ) : null}
            {task.status === "failed" ? (
              <div className={styles.failureActions} aria-label={t("runs.diagnostics.actions")}>
                <div>
                  <strong>{t("runs.diagnostics.failedResponse")}</strong>
                  <p>{t("runs.diagnostics.actionsDescription")}</p>
                </div>
                <div className={styles.failureButtonRow}>
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={() => setShowFailureExplanation((value) => !value)}
                  >
                    {t("runs.diagnostics.explain")}
                  </Button>
                  <Button size="sm" variant="secondary" onClick={handleCopyDiagnostics}>
                    {t("runs.diagnostics.copy")}
                  </Button>
                  <Button
                    size="sm"
                    variant="secondary"
                    disabled={!retryAllowed}
                    onClick={handleRetryAllowedStep}
                  >
                    {t("runs.diagnostics.retryAllowed")}
                  </Button>
                </div>
                {showFailureExplanation ? (
                  <div
                    className={styles.failureExplanation}
                    aria-label={t("runs.diagnostics.explanation")}
                  >
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
                  <DiagnosticItem
                    key={`error-${index}`}
                    tone="danger"
                    label={t("runs.diagnostics.error")}
                    message={message}
                  />
                ))}
                {diagnostics.warnings.map((message, index) => (
                  <DiagnosticItem
                    key={`warning-${index}`}
                    tone="warning"
                    label={t("runs.diagnostics.warning")}
                    message={message}
                  />
                ))}
                {diagnostics.diagnosis.slice(0, DIAGNOSIS_RENDER_LIMIT).map((item, index) => (
                  <DiagnosticItem
                    key={`diagnosis-${index}`}
                    tone={diagnosticTone(item.severity)}
                    label={String(item.code || item.severity || t("runs.diagnostics.defaultLabel"))}
                    message={String(item.message || t("runs.diagnostics.defaultMessage"))}
                  />
                ))}
                {diagnostics.external_tool_results
                  .slice(0, EXTERNAL_TOOL_RENDER_LIMIT)
                  .map((result, index) => (
                    <DiagnosticItem
                      key={`tool-${index}`}
                      tone={String(result.returncode ?? "0") === "0" ? "info" : "warning"}
                      label={String(
                        result.command ||
                          result.function ||
                          t("runs.diagnostics.externalTool", { index: index + 1 }),
                      )}
                      message={t("runs.diagnostics.returnCode", {
                        code: String(result.returncode ?? "n/a"),
                      })}
                    />
                  ))}
              </div>
            ) : (
              <EmptyState
                title={t("runs.diagnostics.emptyTitle")}
                description={t("runs.diagnostics.emptyDescription")}
              />
            )}
          </section>
        ) : null}

        {activeTab === "artifacts" ? (
          <section aria-label={t("runs.artifacts.aria")}>
            {task.result_path ? (
              <div className={styles.artifactPath}>
                <span>{t("runs.artifacts.resultPath")}</span>
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
                title={t("runs.artifacts.emptyTitle")}
                description={t("runs.artifacts.emptyDescription")}
              />
            ) : null}
          </section>
        ) : null}

        {activeTab === "audit" ? (
          <section className={styles.auditPanel} aria-label={t("runs.audit.aria")}>
            {task.execution_mode === "external_smoke" && !diagnostics.approval ? (
              <div className={styles.approvalBox}>
                <div>
                  <span>{t("runs.audit.approvalRequired")}</span>
                  <strong>{t("runs.audit.externalReview")}</strong>
                </div>
                <label>
                  <span>{t("runs.audit.approvedBy")}</span>
                  <input
                    value={approvalName}
                    onChange={(event) => onApprovalNameChange(event.target.value)}
                    placeholder={t("runs.audit.approverPlaceholder")}
                  />
                </label>
                <Button size="sm" variant="primary" onClick={onApprove}>
                  {t("runs.audit.submitApproval")}
                </Button>
              </div>
            ) : (
              <div className={styles.auditRecord}>
                <span>{t("runs.audit.approval")}</span>
                <strong>
                  {diagnostics.approval
                    ? `${diagnostics.approval.approved_by} at ${diagnostics.approval.approved_at}`
                    : t("runs.audit.noApproval")}
                </strong>
              </div>
            )}
            {auditPackage ? (
              <div className={styles.auditPackage}>
                <div>
                  <span>{t("runs.audit.package")}</span>
                  <strong>{auditPackage.generated_at}</strong>
                </div>
                <p>{auditPackage.report_path}</p>
                <p>{auditPackage.json_path}</p>
              </div>
            ) : (
              <EmptyState
                title={t("runs.audit.emptyTitle")}
                description={t("runs.audit.emptyDescription")}
                action={
                  <Button
                    size="sm"
                    variant="secondary"
                    onClick={onGenerateAudit}
                    disabled={auditLoading}
                  >
                    {auditLoading ? t("runs.detail.requesting") : t("runs.detail.requestAudit")}
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
  const { t } = useI18n();
  const running = tasks.filter((task) => task.status === "running").length;
  const failed = tasks.filter((task) => task.status === "failed").length;
  const completed = tasks.filter((task) => task.status === "completed").length;
  const pending = tasks.filter((task) => task.status === "pending").length;

  return (
    <section className={styles.summaryGrid} aria-label={t("runs.overview.aria")}>
      <Card tone="muted">
        <div className={styles.summaryItem}>
          <span>{t("runs.overview.total")}</span>
          <strong>{tasks.length}</strong>
          <small>{t("runs.overview.loaded")}</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>{t("runs.overview.active")}</span>
          <strong>{running + pending}</strong>
          <small>{t("runs.overview.activeDetail", { running, pending })}</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>{t("runs.overview.failed")}</span>
          <strong>{failed}</strong>
          <small>{t("runs.overview.failedDetail")}</small>
        </div>
      </Card>
      <Card>
        <div className={styles.summaryItem}>
          <span>{t("runs.overview.completed")}</span>
          <strong>{completed}</strong>
          <small>{t("runs.overview.completedDetail")}</small>
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
  t,
}: {
  error: string;
  filtered: boolean;
  loading: boolean;
  projectId: string | null;
  taskCount: number;
  t: Translate;
}): string {
  if (!projectId) return t("runs.empty.selectProject");
  if (loading && taskCount === 0) return t("runs.empty.loading");
  if (error && taskCount === 0) return t("runs.empty.unavailable");
  if (filtered) {
    return t("runs.empty.filtered");
  }
  return t("runs.empty.none");
}

function RunProgress({ value }: { value: number }) {
  const { t } = useI18n();
  const progress = clampProgress(value);

  return (
    <div className={styles.progressCell} aria-label={t("runs.progressAria", { progress })}>
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

function formatResultFact(task: TaskLogEntry, t: Translate): string {
  if (task.result_path) return task.result_path;
  if (task.status === "running" || task.status === "pending") return t("runs.result.pending");
  if (task.status === "failed") return t("runs.result.failed");
  return t("runs.result.none");
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

function eventsFromLogs(task: TaskLogEntry, t: Translate): TaskEvent[] {
  const logs = task.logs.length ? task.logs : [t("runs.events.none")];
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

function buildRunTimeline(task: TaskLogEntry, events: TaskEvent[], t: Translate) {
  const checkpoints = events.slice(-5).map((event, index) => ({
    label:
      index === events.slice(-5).length - 1
        ? t("runs.timeline.latest")
        : t("runs.timeline.step", { index: index + 1 }),
    message: event.message,
    status: event.status,
    time: event.timestamp,
  }));

  if (checkpoints.length) {
    return checkpoints;
  }

  return [
    {
      label: t("runs.timeline.latest"),
      message: task.logs[task.logs.length - 1] ?? t("runs.events.none"),
      status: task.status,
      time: task.started_at,
    },
  ];
}

function flattenArtifactEntries(artifacts: Record<string, unknown>, t: Translate) {
  return Object.entries(artifacts)
    .slice(0, 12)
    .map(([label, value]) => ({
      label,
      value: formatArtifactValue(value, t),
    }));
}

function formatArtifactValue(value: unknown, t: Translate): string {
  if (value === null || value === undefined) return t("common.unavailable");
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) return t("runs.artifact.entries", { count: value.length });
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
}

function buildNodeInspector(
  task: TaskLogEntry,
  diagnostics: TaskDiagnostics,
  events: TaskEvent[],
  t: Translate,
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
    t("runs.node.noEvidence");
  const retry = diagnosticsRetryAllowed(diagnostics)
    ? t("runs.node.retryEligible")
    : t("runs.node.retryUnknown");

  return {
    evidence,
    node,
    retry,
    source: diagnostic ? t("runs.node.diagnosticSource") : t("runs.node.eventSource"),
    state: statusLabel(task.status, t),
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

function statusLabel(status: TaskStatus, t: Translate): string {
  if (status === "completed") return t("runs.status.completed");
  if (status === "partial") return t("runs.status.partial");
  if (status === "failed") return t("runs.status.failed");
  if (status === "running") return t("runs.status.running");
  if (status === "pending") return t("runs.status.pending");
  return t("runs.status.disconnected");
}

function clampProgress(value: number): number {
  return Math.min(100, Math.max(0, Math.round(value)));
}

function statusTone(status: TaskStatus): "neutral" | "info" | "success" | "warning" | "danger" {
  if (status === "completed") return "success";
  if (status === "partial") return "warning";
  if (status === "failed") return "danger";
  if (status === "running") return "info";
  if (status === "pending" || status === "disconnected") return "warning";
  return "neutral";
}
