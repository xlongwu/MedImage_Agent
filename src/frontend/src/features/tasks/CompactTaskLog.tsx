import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";
import { StatusPill } from "../app/StatusPill";

export interface CompactTaskLogProps {
  tasks: TaskLogEntry[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
}

export function CompactTaskLog({
  tasks,
  loading,
  error,
  onRetry,
  selectedTaskId,
  onSelectTask,
}: CompactTaskLogProps) {
  const visibleTasks = tasks.slice(0, 2);
  return (
    <section className="compact-task-log compact-task-log-tight" aria-label="Compact task log">
      <details className="activity-details">
        <summary className="activity-summary">
          <div className="activity-summary-title">
            <h2>Recent Activity</h2>
            <small>(Click to view recent task logs / demo runs)</small>
          </div>
          {error ? (
            <button
              type="button"
              className="compact-retry-button"
              onClick={(e) => {
                e.stopPropagation();
                onRetry();
              }}
            >
              Retry
            </button>
          ) : null}
        </summary>
        <div className="activity-body">
          {visibleTasks.length ? (
            <div className="compact-task-list">
              {visibleTasks.map((task) => (
                <button
                  type="button"
                  key={task.id}
                  className={task.id === selectedTaskId ? "selected" : ""}
                  onClick={() => onSelectTask(task.id)}
                >
                  <span>{task.run_name}</span>
                  <StatusPill status={task.status} />
                  <small>{task.progress}%</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty">No recent task activity for this project yet.</div>
          )}
        </div>
      </details>
    </section>
  );
}
