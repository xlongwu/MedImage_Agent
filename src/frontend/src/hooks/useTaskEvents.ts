import { useCallback } from "react";
import { getTaskEvents } from "../lib/api";
import type { TaskEvent } from "../lib/types/task";
import { useAsyncResource } from "./useAsyncResource";

export function useTaskEvents(taskId: string | null) {
  const loader = useCallback(() => {
    if (!taskId) {
      return Promise.resolve([] as TaskEvent[]);
    }
    return getTaskEvents(taskId);
  }, [taskId]);

  return useAsyncResource<TaskEvent[]>(loader, [], [taskId]);
}
