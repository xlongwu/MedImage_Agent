import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";
import { StatusPill } from "../app/StatusPill";

export interface TaskLogTableProps {
  tasks: TaskLogEntry[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
}

export function TaskLogTable({
  tasks,
  loading,
  error,
  onRetry,
  selectedTaskId,
  onSelectTask,
}: TaskLogTableProps) {
  return (
    <section className="task-log">
      <div className="log-header">
        <div>
          <h2>Task Log</h2>
          <span>
            {loading
              ? "Loading task activity"
              : error
                ? "Task activity unavailable"
                : "Live pipeline and execution activity"}
          </span>
        </div>
        <div className="tab-row">
          <button className="active">All Runs</button>
          <button>Running</button>
          <button>Completed</button>
          <button>Failed</button>
          {error ? <button onClick={onRetry}>Retry</button> : null}
        </div>
      </div>
      <div className="task-table">
        {tasks.length ? (
          tasks.map((task) => (
            <button
              key={task.id}
              className={`task-row ${task.id === selectedTaskId ? "selected" : ""}`}
              onClick={() => onSelectTask(task.id)}
            >
              <span>{task.run_name}</span>
              <span>{task.pipeline}</span>
              <span>{task.dataset}</span>
              <span>
                <StatusPill status={task.status} />
              </span>
              <span className="progress-cell">
                <i>
                  <b style={{ width: `${task.progress}%` }} />
                </i>
                {task.progress}%
              </span>
              <span>{task.started_at}</span>
              <span>{task.duration}</span>
            </button>
          ))
        ) : (
          <div className="empty">
            {error ? "Task activity could not be loaded." : "No task activity recorded."}
          </div>
        )}
      </div>
    </section>
  );
}
