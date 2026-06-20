import { useCallback } from "react";
import { getTasks } from "../lib/api";
import { fallbackTasks } from "../lib/mockData";
import type { TaskLogEntry, TaskStreamMessage } from "../lib/types/task";
import { useAsyncResource } from "./useAsyncResource";

export function useTasks() {
  const resource = useAsyncResource<TaskLogEntry[]>(getTasks, fallbackTasks, []);

  const upsertTask = useCallback(
    (task: TaskLogEntry) => {
      resource.setData((current) => {
        const exists = current.some((item) => item.id === task.id);
        if (exists) {
          return current.map((item) => (item.id === task.id ? { ...item, ...task } : item));
        }
        return [task, ...current];
      });
    },
    [resource.setData],
  );

  const updateTaskFromStream = useCallback(
    (message: TaskStreamMessage) => {
      resource.setData((current) =>
        current.map((task) =>
          task.id === message.task_id
            ? {
                ...task,
                status: message.status,
                progress: message.progress,
                logs: [...task.logs, message.message],
                result_path: message.result_path ?? task.result_path,
              }
            : task,
        ),
      );
    },
    [resource.setData],
  );

  return { ...resource, upsertTask, updateTaskFromStream };
}
