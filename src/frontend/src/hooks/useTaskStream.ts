import { useEffect, useState } from "react";
import { connectTaskStream } from "../lib/api";
import type { TaskStreamMessage } from "../lib/types/task";

export function useTaskStream(
  taskId: string | null,
  onMessage: (message: TaskStreamMessage) => void,
) {
  const [error, setError] = useState("");
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let cleanup: (() => void) | null = null;

    async function connect() {
      if (!taskId) {
        setConnected(false);
        return;
      }
      setError("");
      try {
        const handle = await connectTaskStream(taskId, {
          onMessage: (message) => {
            if (!cancelled) {
              setConnected(message.status !== "completed" && message.status !== "failed");
              onMessage(message);
            }
          },
          onError: (message) => {
            if (!cancelled) {
              setError(message);
              setConnected(false);
            }
          },
          onClose: () => {
            if (!cancelled) {
              setConnected(false);
            }
          },
        });
        cleanup = handle.close;
        if (!cancelled) {
          setConnected(true);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : String(err));
          setConnected(false);
        }
      }
    }

    connect();
    return () => {
      cancelled = true;
      cleanup?.();
    };
  }, [taskId, onMessage]);

  return { connected, error };
}
