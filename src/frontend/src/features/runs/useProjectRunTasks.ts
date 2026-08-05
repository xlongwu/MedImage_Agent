import { useCallback, useEffect, useRef, useState } from "react";

import { listProjectRunLinks } from "../../lib/api/projectRuns";
import type { TaskLogEntry } from "../../lib/types/task";
import { latestProjectRunTasks, projectRunLinksToTasks } from "./projectRunTasks";

export function useProjectRunTasks(baseUrl: string, projectId: string | null) {
  const [tasks, setTasks] = useState<TaskLogEntry[]>([]);
  const [historyTasks, setHistoryTasks] = useState<TaskLogEntry[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const requestVersion = useRef(0);

  const reload = useCallback(async () => {
    const version = ++requestVersion.current;
    if (!projectId) {
      setTasks([]);
      setHistoryTasks([]);
      setError("");
      setLoading(false);
      return [];
    }
    setLoading(true);
    try {
      const response = await listProjectRunLinks(baseUrl, projectId);
      if (
        response.project_id !== projectId ||
        response.runs.some((run) => run.project_id !== projectId)
      ) {
        throw new Error("Project run list did not match the selected project.");
      }
      const nextHistoryTasks = projectRunLinksToTasks(response.runs);
      const next = latestProjectRunTasks(nextHistoryTasks);
      if (requestVersion.current === version) {
        setTasks(next);
        setHistoryTasks(nextHistoryTasks);
        setError("");
      }
      return next;
    } catch (reason) {
      if (requestVersion.current === version) {
        setTasks([]);
        setHistoryTasks([]);
        setError(reason instanceof Error ? reason.message : String(reason));
      }
      return [];
    } finally {
      if (requestVersion.current === version) {
        setLoading(false);
      }
    }
  }, [baseUrl, projectId]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Load backend-owned project history when the selected project changes.
    void reload();
    if (!projectId) return;
    const interval = window.setInterval(() => {
      void reload();
    }, 3000);
    return () => {
      window.clearInterval(interval);
      requestVersion.current += 1;
    };
  }, [projectId, reload]);

  return { tasks, historyTasks, loading, error, reload };
}
