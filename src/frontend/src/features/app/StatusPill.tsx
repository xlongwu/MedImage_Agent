import type { TaskStatus } from "../../lib/types/task";

export function StatusPill({ status }: { status: TaskStatus }) {
  const tone = status.toLowerCase();
  return <span className={`status-pill ${tone}`}>{status}</span>;
}
