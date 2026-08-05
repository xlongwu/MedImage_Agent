import type { RunLinkRecord } from "../../types";
import type { TaskLogEntry, TaskStatus } from "../../lib/types/task";

function statusFromRun(value: string): TaskStatus {
  const status = value.trim().toUpperCase();
  if (["SUCCESS", "SUCCEEDED", "COMPLETED", "GOAL_SATISFIED"].includes(status)) {
    return "completed";
  }
  if (["PARTIAL", "NEEDS_ATTENTION", "GOAL_NOT_SATISFIED", "INDETERMINATE"].includes(status)) {
    return "partial";
  }
  if (
    ["FAILED", "FAILURE", "ERROR", "INTERRUPTED", "CANCELED", "CANCELLED", "BLOCKED"].includes(
      status,
    )
  ) {
    return "failed";
  }
  if (status === "RUNNING") return "running";
  if (["REQUESTED", "SUBMITTED", "QUEUED", "PENDING"].includes(status)) return "pending";
  return "disconnected";
}

function payloadString(payload: Record<string, unknown>, key: string): string {
  const value = payload[key];
  return typeof value === "string" ? value : "";
}

export function projectRunToTask(run: RunLinkRecord): TaskLogEntry {
  const status = statusFromRun(run.status);
  const terminal = ["completed", "partial", "failed"].includes(status);
  return {
    id: run.run_id,
    run_link_id: run.run_link_id,
    reviewed_plan_id: run.reviewed_plan_id,
    agent_task_id: run.task_id,
    run_name: payloadString(run.payload, "goal") || `Agent Task run ${run.run_id}`,
    pipeline: payloadString(run.payload, "pipeline_id") || run.reviewed_plan_id,
    dataset: run.project_id,
    status,
    progress: terminal ? 100 : status === "running" ? 50 : 0,
    started_at: payloadString(run.payload, "started_at") || run.created_at,
    duration: "",
    owner:
      payloadString(run.payload, "actor") ||
      payloadString(run.payload, "triggered_by") ||
      "Agent Task",
    logs: run.warnings,
    result_path: run.summary_path,
    updated_at: run.updated_at,
  };
}

function updatedAtMillis(task: Pick<TaskLogEntry, "updated_at" | "started_at">): number {
  const parsed = Date.parse(task.updated_at || task.started_at || "");
  return Number.isFinite(parsed) ? parsed : 0;
}

export function projectRunLinksToTasks(runs: RunLinkRecord[]): TaskLogEntry[] {
  const latestByRunId = new Map<string, RunLinkRecord>();
  for (const run of runs) {
    const existing = latestByRunId.get(run.run_id);
    if (!existing || Date.parse(run.updated_at) >= Date.parse(existing.updated_at)) {
      latestByRunId.set(run.run_id, run);
    }
  }

  return Array.from(latestByRunId.values())
    .map(projectRunToTask)
    .sort((left, right) => updatedAtMillis(right) - updatedAtMillis(left));
}

export function latestProjectRunTasks(tasks: TaskLogEntry[]): TaskLogEntry[] {
  const latestByAssociation = new Map<string, TaskLogEntry>();
  for (const task of [...tasks].sort(
    (left, right) => updatedAtMillis(right) - updatedAtMillis(left),
  )) {
    const associationKey = task.agent_task_id
      ? `agent-task:${task.agent_task_id}`
      : task.reviewed_plan_id
        ? `reviewed-plan:${task.reviewed_plan_id}`
        : `run:${task.id}`;
    if (!latestByAssociation.has(associationKey)) {
      latestByAssociation.set(associationKey, task);
    }
  }
  return Array.from(latestByAssociation.values());
}
