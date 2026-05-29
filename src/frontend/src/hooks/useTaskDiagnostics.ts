import { useCallback } from "react";
import { getTaskDiagnostics } from "../lib/api";
import type { TaskDiagnostics } from "../lib/types/task";
import { useAsyncResource } from "./useAsyncResource";

const emptyDiagnostics: TaskDiagnostics = {
  ok: true,
  task_id: "",
  status: "pending",
  diagnosis: [],
  external_tool_results: [],
  logs: [],
  artifacts: {},
  approval: null,
  errors: [],
  warnings: [],
};

export function useTaskDiagnostics(taskId: string | null) {
  const loader = useCallback(() => {
    if (!taskId) {
      return Promise.resolve(emptyDiagnostics);
    }
    return getTaskDiagnostics(taskId);
  }, [taskId]);

  return useAsyncResource<TaskDiagnostics>(loader, emptyDiagnostics, [taskId]);
}

