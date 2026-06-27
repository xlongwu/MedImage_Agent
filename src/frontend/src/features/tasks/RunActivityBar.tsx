import { memo, useMemo, useState } from "react";
import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";
import styles from "./RunActivityBar.module.css";

export interface RunActivityBarProps {
  tasks: TaskLogEntry[];
  selectedTaskId: string | null;
  onSelectTask: (id: string) => void;
  onExpand?: () => void;
  onOpenRuns?: () => void;
}

const STATUS_LABEL: Record<TaskStatus, string> = {
  running: "Running",
  pending: "Pending",
  completed: "Completed",
  failed: "Failed",
  disconnected: "Disconnected",
};

function statusTone(status: TaskStatus): "running" | "ok" | "warn" | "error" | "idle" {
  switch (status) {
    case "running":
      return "running";
    case "completed":
      return "ok";
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
  const timelineEvents = buildTimeline(focusedTask);
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
      await navigator.clipboard?.writeText(payload);
      setCopyStatus("Copied diagnostics");
    } catch {
      setCopyStatus("Clipboard unavailable");
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
      <div className={styles.bar} role="status" aria-label="Background run activity">
        <div className={`${styles.status} ${toneClass[primaryTone]}`}>
          <span className={styles.dot} aria-hidden="true" />
          <span className={styles.statusLabel}>{STATUS_LABEL[primaryTask.status]}</span>
        </div>
        <button
          type="button"
          className={styles.primary}
          onClick={() => handleSelectTask(primaryTask)}
          title={primaryTask.run_name}
        >
          <span className={styles.name}>{primaryTask.run_name}</span>
          <span className={styles.pipeline}>{primaryTask.pipeline}</span>
        </button>
        {primaryTask.status === "running" ? (
          <div className={styles.progress} aria-label={`Progress ${primaryTask.progress}%`}>
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
          <span className={styles.errorSummary}>
            Run failed. Open details to review diagnostics.
          </span>
        ) : null}
        {hasMultiple ? (
          <span className={styles.count} title={`${activeTasks.length + failedTasks.length} runs`}>
            +{activeTasks.length + failedTasks.length - 1}
          </span>
        ) : null}
        <button
          type="button"
          className={styles.expandButton}
          onClick={handleExpand}
          aria-expanded={expanded}
          aria-controls="run-activity-drawer"
          aria-label={expanded ? "Collapse run activity" : "Expand run activity"}
          title={expanded ? "Collapse run activity" : "Expand run activity"}
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
        <div id="run-activity-drawer" className={styles.drawer} aria-label="Run activity drawer">
          <div className={styles.drawerHeader}>
            <div>
              <strong>Run activity</strong>
              <span>{visibleTasks.length} active or failed</span>
            </div>
            <div className={styles.drawerStats} aria-label="Run activity summary">
              <span>{runningCount} running</span>
              <span>{pendingCount} pending</span>
              <span>{failedCount} failed</span>
            </div>
            <button type="button" className={styles.openRunsButton} onClick={handleOpenRuns}>
              Open Runs
            </button>
          </div>
          <div className={styles.drawerBody}>
            <div className={styles.drawerList} aria-label="Active and failed runs">
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
                      {STATUS_LABEL[task.status]}
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
            <section className={styles.detailPanel} aria-label="Selected run detail">
              <div className={styles.detailHeader}>
                <div>
                  <strong>{focusedTask.run_name}</strong>
                  <span>{focusedTask.pipeline}</span>
                </div>
                <button type="button" className={styles.copyButton} onClick={handleCopyDiagnostics}>
                  Copy diagnostics
                </button>
              </div>
              <div className={styles.detailFacts} aria-label="Run facts">
                <div>
                  <span>Status</span>
                  <strong>{STATUS_LABEL[focusedTask.status]}</strong>
                </div>
                <div>
                  <span>Progress</span>
                  <strong>{Math.min(100, Math.max(0, focusedTask.progress))}%</strong>
                </div>
                <div>
                  <span>Started</span>
                  <strong>{focusedTask.started_at}</strong>
                </div>
                <div>
                  <span>Duration</span>
                  <strong>{focusedTask.duration || "In progress"}</strong>
                </div>
              </div>
              <ol className={styles.timeline} aria-label="Run timeline">
                {timelineEvents.map((event) => (
                  <li key={`${event.label}-${event.message}`}>
                    <span>{event.label}</span>
                    <p>{event.message}</p>
                  </li>
                ))}
              </ol>
              {focusedLogCount > 5 ? (
                <p className={styles.logBudget}>Showing latest 5 of {focusedLogCount}</p>
              ) : null}
              <div className={styles.latestLog} aria-label="Latest run log">
                <strong>Latest log</strong>
                <p>
                  {focusedTask.logs?.[focusedTask.logs.length - 1] ?? "No run events recorded."}
                </p>
              </div>
              {focusedTask.status === "failed" ? (
                <div className={styles.failureNote} role="alert">
                  Failed run. Select this task to review full diagnostics and approval context.
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

function buildTimeline(task: TaskLogEntry): Array<{ label: string; message: string }> {
  const logs = task.logs?.length ? task.logs : ["No run events have been recorded yet."];
  return logs.slice(-5).map((message, index, visibleLogs) => {
    if (index === 0 && visibleLogs.length === 1) {
      return { label: "Latest", message };
    }
    if (index === visibleLogs.length - 1) {
      return { label: "Latest", message };
    }
    return { label: `Event ${index + 1}`, message };
  });
}
