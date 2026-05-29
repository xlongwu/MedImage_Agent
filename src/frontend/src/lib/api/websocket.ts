import { getApiBaseUrl, toWebSocketUrl } from "./client";
import type { TaskStreamMessage } from "../types/task";

export interface TaskStreamHandle {
  close: () => void;
}

export async function connectTaskStream(
  taskId: string,
  handlers: {
    onMessage: (message: TaskStreamMessage) => void;
    onError?: (message: string) => void;
    onClose?: () => void;
  }
): Promise<TaskStreamHandle> {
  const baseUrl = await getApiBaseUrl();
  const socket = new WebSocket(toWebSocketUrl(baseUrl, `/ws/tasks/${encodeURIComponent(taskId)}`));
  socket.onmessage = (event) => {
    try {
      handlers.onMessage(JSON.parse(event.data) as TaskStreamMessage);
    } catch {
      handlers.onError?.("Received malformed task stream message");
    }
  };
  socket.onerror = () => handlers.onError?.("Task stream disconnected");
  socket.onclose = () => handlers.onClose?.();
  return {
    close: () => socket.close(),
  };
}

