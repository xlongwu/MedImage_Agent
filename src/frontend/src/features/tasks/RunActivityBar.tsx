import { memo, useMemo, useState } from "react";
import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";
import { useI18n } from "../../i18n/useI18n";
import styles from "./RunActivityBar.module.css";

export interface RunActivityBarProps {
  tasks: TaskLogEntry[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
  onExpand?: () => void;
  onOpenRuns?: () => void;
}

function statusTone(status: TaskStatus): "running" | "ok" | "warn" | "error" | "idle" {
  switch (status) {
    case "running":
      return "running";
    case "completed":
      return "ok";
    case "partial":
      return "warn";
    case "pending":
      return "idle";
    case "disconnected":
      return "warn";
    case "failed":
      return "error";
    default:
      return "idle";
  }
}

const toneClass: Record<ReturnType<typeof statusTone>, string> = {
  running: styles.toneRunning,
  ok: styles.toneOk,
  warn: styles.toneWarn,
  error: styles.toneError,
  idle: styles.toneIdle,
};

export const RunActivityBar = memo(function RunActivityBar({
  tasks,
  selectedTaskId,
  onSelectTask,
  onExpand,
  onOpenRuns,
}: RunActivityBarProps) {
  const { t } = useI18n();
  const [expanded, setExpanded] = useState(false);
  const [focusedTaskId, setFocusedTaskId] = useState<string | null>(null);
  const [copyStatus, setCopyStatus] = useState("");
  const activeTasks = useMemo(
    () => tasks.filter((task) => task.status === "running" || task.status === "pending"),
    [tasks],
  );
  const failedTasks = useMemo(() => tasks.filter((task) => task.status === "failed"), [tasks]);

  // Hide entirely when no active or failed tasks per design 2.8.8
  if (activeTasks.length === 0 && failedTasks.length === 0) {
    return null;
  }

  const primaryTask = activeTasks[0] ?? failedTasks[0];
  const primaryTone = statusTone(primaryTask.status);
  const hasMultiple = activeTasks.length + failedTasks.length > 1;
  const visibleTasks = [...activeTasks, ...failedTasks];
  const focusedTask =
    visibleTasks.find((task) => task.id === focusedTaskId) ??
    visibleTasks.find((task) => task.id === selectedTaskId) ??
    primaryTask;
  const runningCount = visibleTasks.filter((task) => task.status === "running").length;
  const pendingCount = visibleTasks.filter((task) => task.status === "pending").length;
  const failedCount = failedTasks.length;
  const timelineEvents = buildTimeline(focusedTask, t);
  const focusedLogCount = focusedTask.logs?.length ?? 0;

  const handleExpand = () => {
    setExpanded((current) => {
      const next = !current;
      if (next) {
        setFocusedTaskId(selectedTaskId ?? primaryTask.id);
      }
      return next;
    });
    onExpand?.();
  };

  const handleSelectTask = (task: TaskLogEntry) => {
    setFocusedTaskId(task.id);
    onSelectTask(task.id);
  };

  const handleCopyDiagnostics = async () => {
    const payload = JSON.stringify(
      {
        id: focusedTask.id,
        run_name: focusedTask.run_name,
        pipeline: focusedTask.pipeline,
        status: focusedTask.status,
        progress: focusedTask.progress,
        started_at: focusedTask.started_at,
        duration: focusedTask.duration,
        result_path: focusedTask.result_path ?? null,
        execution_mode: focusedTask.execution_mode ?? null,
        logs: focusedTask.logs,
      },
      null,
      2,
    );
    try {
      if (!navigator.clipboard?.writeText) throw new Error(t("activity.clipboardUnavailable"));
      await navigator.clipboard.writeText(payload);
      setCopyStatus(t("activity.copied"));
    } catch {
      setCopyStatus(t("activity.clipboardUnavailable"));
    }
    window.setTimeout(() => setCopyStatus(""), 1800);
  };

  const handleOpenRuns = () => {
    setFocusedTaskId(focusedTask.id);
    onSelectTask(focusedTask.id);
    onOpenRuns?.();
  };

  return (
    <div className={`${styles.shell} ${expanded ? styles.expanded : ""}`}>
      <div className={styles.bar} role="status" aria-label={t("activity.background")}>
        <div className={`${styles.status} ${toneClass[primaryTone]}`}>
          <span className={styles.dot} aria-hidden="true" />
          <span className={styles.statusLabel}>{statusLabel(primaryTask.status, t)}</span>
        </div>
        <button
          type="button"
          className={styles.primary}
          onClick={() => handleSelectTask(primaryTask)}
          title={primaryTask.run_name}
        >
          <span className={styles.name}>{primaryTask.run_name}</span>
          <span className={styles.pipeline}>{t("activity.agentManaged")}</span>
        </button>
        {primaryTask.status === "running" ? (
          <div
            className={styles.progress}
            aria-label={t("runs.progressAria", { progress: primaryTask.progress })}
          >
            <div className={styles.progressTrack}>
              <div
                className={styles.progressFill}
                style={{ width: `${Math.min(100, Math.max(0, primaryTask.progress))}%` }}
              />
            </div>
            <span className={styles.progressReadout}>{primaryTask.progress}%</span>
          </div>
        ) : null}
        {primaryTask.status === "failed" ? (
          <span className={styles.errorSummary}>{t("activity.failedSummary")}</span>
        ) : null}
        {hasMultiple ? (
          <span
            className={styles.count}
            title={t("activity.runCount", { count: activeTasks.length + failedTasks.length })}
          >
            +{activeTasks.length + failedTasks.length - 1}
          </span>
        ) : null}
        <button
          type="button"
          className={styles.expandButton}
          onClick={handleExpand}
          aria-expanded={expanded}
          aria-controls="run-activity-drawer"
          aria-label={expanded ? t("activity.collapse") : t("activity.expand")}
          title={expanded ? t("activity.collapse") : t("activity.expand")}
        >
          <svg viewBox="0 0 16 16" width="14" height="14" aria-hidden="true">
            <path
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
              d={expanded ? "M4 10l4-4 4 4" : "M4 6l4 4 4-4"}
            />
          </svg>
        </button>
      </div>
      {expanded ? (
        <div id="run-activity-drawer" className={styles.drawer} aria-label={t("activity.drawer")}>
          <div className={styles.drawerHeader}>
            <div>
              <strong>{t("activity.title")}</strong>
              <span>{t("activity.activeFailed", { count: visibleTasks.length })}</span>
            </div>
            <div className={styles.drawerStats} aria-label={t("activity.summary")}>
              <span>{t("activity.running", { count: runningCount })}</span>
              <span>{t("activity.pending", { count: pendingCount })}</span>
              <span>{t("activity.failed", { count: failedCount })}</span>
            </div>
            <button type="button" className={styles.openRunsButton} onClick={handleOpenRuns}>
              {t("activity.openRuns")}
            </button>
          </div>
          <div className={styles.drawerBody}>
            <div className={styles.drawerList} aria-label={t("activity.list")}>
              {visibleTasks.map((task) => {
                const tone = statusTone(task.status);
                return (
                  <button
                    key={task.id}
                    type="button"
                    className={`${styles.drawerRow} ${
                      task.id === focusedTask.id ? styles.selected : ""
                    }`}
                    onClick={() => handleSelectTask(task)}
                  >
                    <span className={`${styles.rowStatus} ${toneClass[tone]}`}>
                      {statusLabel(task.status, t)}
                    </span>
                    <span className={styles.rowMain}>
                      <strong>{task.run_name}</strong>
                      <small>{task.pipeline}</small>
                    </span>
                    <span className={styles.rowMeta}>
                      <b>{Math.min(100, Math.max(0, task.progress))}%</b>
                      <small>{task.duration || task.started_at}</small>
                    </span>
                  </button>
                );
              })}
            </div>
            <section className={styles.detailPanel} aria-label={t("runs.detail.aria")}>
              <div className={styles.detailHeader}>
                <div>
                  <strong>{focusedTask.run_name}</strong>
                  <span>{focusedTask.pipeline}</span>
                </div>
                <button type="button" className={styles.copyButton} onClick={handleCopyDiagnostics}>
                  {t("activity.copyDiagnostics")}
                </button>
              </div>
              <div className={styles.detailFacts} aria-label={t("runs.facts")}>
                <div>
                  <span>{t("runs.table.status")}</span>
                  <strong>{statusLabel(focusedTask.status, t)}</strong>
                </div>
                <div>
                  <span>{t("runs.table.progress")}</span>
                  <strong>{Math.min(100, Math.max(0, focusedTask.progress))}%</strong>
                </div>
                <div>
                  <span>{t("runs.table.started")}</span>
                  <strong>{focusedTask.started_at}</strong>
                </div>
                <div>
                  <span>{t("runs.table.duration")}</span>
                  <strong>{focusedTask.duration || t("runs.inProgress")}</strong>
                </div>
              </div>
              <ol className={styles.timeline} aria-label={t("activity.timeline")}>
                {timelineEvents.map((event) => (
                  <li key={`${event.label}-${event.message}`}>
                    <span>{event.label}</span>
                    <p>{event.message}</p>
                  </li>
                ))}
              </ol>
              {focusedLogCount > 5 ? (
                <p className={styles.logBudget}>
                  {t("activity.logBudget", { count: focusedLogCount })}
                </p>
              ) : null}
              <div className={styles.latestLog} aria-label={t("activity.latestLog")}>
                <strong>{t("activity.latestLogTitle")}</strong>
                <p>{focusedTask.logs?.[focusedTask.logs.length - 1] ?? t("activity.noEvents")}</p>
              </div>
              {focusedTask.status === "failed" ? (
                <div className={styles.failureNote} role="alert">
                  {t("activity.failureNote")}
                </div>
              ) : null}
              {copyStatus ? <span className={styles.copyStatus}>{copyStatus}</span> : null}
            </section>
          </div>
        </div>
      ) : null}
    </div>
  );
});

type Translate = ReturnType<typeof useI18n>["t"];

function buildTimeline(
  task: TaskLogEntry,
  t: Translate,
): Array<{ label: string; message: string }> {
  const logs = task.logs?.length ? task.logs : [t("activity.noEventsYet")];
  return logs.slice(-5).map((message, index, visibleLogs) => {
    if (index === 0 && visibleLogs.length === 1) {
      return { label: t("activity.latest"), message };
    }
    if (index === visibleLogs.length - 1) {
      return { label: t("activity.latest"), message };
    }
    return { label: t("activity.event", { index: index + 1 }), message };
  });
}

function statusLabel(status: TaskStatus, t: Translate): string {
  if (status === "completed") return t("runs.status.completed");
  if (status === "partial") return t("runs.status.partial");
  if (status === "failed") return t("runs.status.failed");
  if (status === "running") return t("runs.status.running");
  if (status === "pending") return t("runs.status.pending");
  return t("runs.status.disconnected");
}
