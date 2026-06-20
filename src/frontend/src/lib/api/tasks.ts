import { getJson, postJson } from "./client";
import type {
  TaskApprovalRequest,
  TaskApprovalResponse,
  TaskArtifacts,
  TaskAuditPackage,
  TaskDetail,
  TaskDiagnostics,
  TaskEvent,
  TaskLogEntry,
} from "../types/task";

export function getTasks(): Promise<TaskLogEntry[]> {
  return getJson<TaskLogEntry[]>("/api/tasks");
}

export function getTask(taskId: string): Promise<TaskDetail> {
  return getJson<TaskDetail>(`/api/tasks/${encodeURIComponent(taskId)}`);
}

export function getTaskEvents(taskId: string): Promise<TaskEvent[]> {
  return getJson<TaskEvent[]>(`/api/tasks/${encodeURIComponent(taskId)}/events`);
}

export function approveTask(
  taskId: string,
  payload: TaskApprovalRequest,
): Promise<TaskApprovalResponse> {
  return postJson<TaskApprovalResponse>(
    `/api/tasks/${encodeURIComponent(taskId)}/approve`,
    payload,
  );
}

export function getTaskDiagnostics(taskId: string): Promise<TaskDiagnostics> {
  return getJson<TaskDiagnostics>(`/api/tasks/${encodeURIComponent(taskId)}/diagnostics`);
}

export function getTaskArtifacts(taskId: string): Promise<TaskArtifacts> {
  return getJson<TaskArtifacts>(`/api/tasks/${encodeURIComponent(taskId)}/artifacts`);
}

export function generateTaskAuditPackage(taskId: string): Promise<TaskAuditPackage> {
  return postJson<TaskAuditPackage>(`/api/tasks/${encodeURIComponent(taskId)}/audit-package`, {});
}
