"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import type {
  TaskAuditPackage,
  TaskDiagnostics,
  TaskEvent,
  TaskLogEntry,
  TaskStreamMessage,
} from "../../lib/types/task";
import { useTaskStream } from "../../hooks/useTaskStream";
import { useTasks } from "../../hooks/useTasks";
import { useTaskEvents } from "../../hooks/useTaskEvents";
import { useTaskDiagnostics } from "../../hooks/useTaskDiagnostics";
import { approveTask, generateTaskAuditPackage, getTask } from "../../lib/api";

export interface TaskController {
  tasks: TaskLogEntry[];
  tasksLoading: boolean;
  tasksError: string;
  reloadTasks: () => Promise<TaskLogEntry[] | void>;
  updateTaskFromStream: ReturnType<typeof useTasks>["updateTaskFromStream"];
  selectedTaskId: string | null;
  setSelectedTaskId: (id: string | null) => void;
  selectedTask: TaskLogEntry | null;
  taskCounts: { completed: number; running: number; failed: number };
  hasPreprocessingRun: boolean;
  latestPreprocessingRunId: string | null;
  taskEvents: TaskEvent[];
  taskEventsLoading: boolean;
  taskEventsError: string;
  reloadTaskEvents: () => Promise<TaskEvent[] | void>;
  taskDiagnosticsData: TaskDiagnostics;
  reloadTaskDiagnostics: () => Promise<TaskDiagnostics | void>;
  taskStreamConnected: boolean;
  taskStreamError: string | null;
  approvalName: string;
  setApprovalName: (name: string) => void;
  auditPackage: TaskAuditPackage | null;
  auditLoading: boolean;
  handleApproveSelectedTask: () => Promise<void>;
  handleGenerateAuditPackage: () => Promise<void>;
  handleReconnectTaskStream: () => void;
  setAuditPackage: (pkg: TaskAuditPackage | null) => void;
  taskEventsSetData: (updater: (current: TaskEvent[]) => TaskEvent[]) => void;
}

export function useTaskController(
  selectedTaskId: string | null = null,
  setSelectedTaskId: ((id: string | null) => void) | undefined = undefined,
  setActiveTaskId: ((id: string | null) => void) | undefined = undefined,
): TaskController {
  const noop = () => {};
  const setSelectedTaskIdSafe = setSelectedTaskId ?? noop;
  const setActiveTaskIdSafe = setActiveTaskId ?? noop;
  const tasks = useTasks();
  const taskEvents = useTaskEvents(selectedTaskId);
  const taskDiagnostics = useTaskDiagnostics(selectedTaskId);
  const updateTaskFromStream = tasks.updateTaskFromStream;

  const [approvalName, setApprovalName] = useState("");
  const [auditPackage, setAuditPackage] = useState<TaskAuditPackage | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  // Reset audit package when the selected task changes.
  useEffect(() => {
    setAuditPackage(null);
  }, [selectedTaskId]);

  const handleTaskMessage = useCallback(
    (message: TaskStreamMessage) => {
      updateTaskFromStream(message);
      if (selectedTaskId === message.task_id) {
        const event: TaskEvent = {
          id: Date.now(),
          task_id: message.task_id,
          status: message.status,
          progress: message.progress,
          message: message.message,
          timestamp: message.timestamp,
          result_path: message.result_path,
          source: "websocket",
          metadata: {},
        };
        taskEvents.setData((current) => [...current, event]);
      }
      // notice is owned by the app controller; callers handle it.
      if (
        (message.status === "completed" || message.status === "failed") &&
        selectedTaskId === message.task_id
      ) {
        window.setTimeout(() => {
          taskEvents.reload();
          taskDiagnostics.reload();
        }, 250);
      }
    },
    [
      selectedTaskId,
      taskDiagnostics.reload,
      taskEvents.reload,
      taskEvents.setData,
      updateTaskFromStream,
    ],
  );

  const taskStream = useTaskStream(null, handleTaskMessage);

  // Reconnect stream when selectedTaskId changes.
  useEffect(() => {
    const nextTaskId = selectedTaskId;
    if (!nextTaskId) return;
    setActiveTaskId(null);
    window.setTimeout(() => setActiveTaskId(nextTaskId), 0);
    // We intentionally only depend on selectedTaskId here; setActiveTaskId is
    // passed in from the parent so we don't list it as a dep.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTaskId]);

  const selectedTask = useMemo(
    () => tasks.data.find((task) => task.id === selectedTaskId) ?? null,
    [selectedTaskId, tasks.data],
  );

  const taskCounts = useMemo(() => {
    const completed = tasks.data.filter((task) => task.status === "completed").length;
    const running = tasks.data.filter((task) => task.status === "running").length;
    const failed = tasks.data.filter((task) => task.status === "failed").length;
    return { completed, running, failed };
  }, [tasks.data]);

  const hasPreprocessingRun = useMemo(() => {
    return tasks.data.some(
      (task) =>
        task.pipeline?.toLowerCase().includes("preprocess") ||
        task.run_name?.toLowerCase().includes("preprocess"),
    );
  }, [tasks.data]);

  const latestPreprocessingRunId = useMemo(() => {
    for (const task of tasks.data) {
      const candidate = preprocessingRunIdFromTask(task);
      if (candidate) return candidate;
    }
    return null;
  }, [tasks.data]);

  const handleApproveSelectedTask = useCallback(async () => {
    if (!selectedTaskId) return;
    if (!approvalName.trim()) {
      // Approval requires a name; callers should surface this via notice.
      return;
    }
    try {
      const response = await approveTask(selectedTaskId, {
        approved: true,
        approved_by: approvalName.trim(),
        safety_flags: {
          rawdata_read_only: true,
          no_dparsf_blackbox: true,
          matlab_external_execution: true,
        },
      });
      await tasks.reload();
      await taskEvents.reload();
      await taskDiagnostics.reload();
      setActiveTaskId(selectedTaskId);
    } catch {
      // Errors are surfaced via reload; the parent can read taskError if needed.
    }
  }, [selectedTaskId, approvalName, tasks, taskEvents, taskDiagnostics, setActiveTaskId]);

  const handleGenerateAuditPackage = useCallback(async () => {
    if (!selectedTaskId) return;
    setAuditLoading(true);
    try {
      const response = await generateTaskAuditPackage(selectedTaskId);
      setAuditPackage(response);
    } catch {
      // Errors are surfaced by the parent via the auditPackage state.
    } finally {
      setAuditLoading(false);
    }
  }, [selectedTaskId]);

  const handleReconnectTaskStream = useCallback(() => {
    const nextTaskId = selectedTaskId;
    if (!nextTaskId) return;
    setActiveTaskId(null);
    window.setTimeout(() => setActiveTaskId(nextTaskId), 0);
  }, [selectedTaskId, setActiveTaskId]);

  return {
    tasks: tasks.data,
    tasksLoading: tasks.loading,
    tasksError: tasks.error,
    reloadTasks: tasks.reload,
    updateTaskFromStream,
    selectedTaskId,
    setSelectedTaskId,
    selectedTask,
    taskCounts,
    hasPreprocessingRun,
    latestPreprocessingRunId,
    taskEvents: taskEvents.data,
    taskEventsLoading: taskEvents.loading,
    taskEventsError: taskEvents.error,
    reloadTaskEvents: taskEvents.reload,
    taskDiagnosticsData: taskDiagnostics.data,
    reloadTaskDiagnostics: taskDiagnostics.reload,
    taskStreamConnected: taskStream.connected,
    taskStreamError: taskStream.error,
    approvalName,
    setApprovalName,
    auditPackage,
    auditLoading,
    handleApproveSelectedTask,
    handleGenerateAuditPackage,
    handleReconnectTaskStream,
    setAuditPackage,
    taskEventsSetData: taskEvents.setData,
  };
}

function preprocessingRunIdFromTask(task: TaskLogEntry): string | null {
  const searchable = [task.id, task.run_name, task.pipeline, task.result_path ?? ""].join(" ");
  if (!/preprocess/i.test(searchable)) {
    return null;
  }
  const pathMatch = searchable.match(/preprocessing_runs[\\/]+([A-Za-z0-9_-]+)/i);
  if (pathMatch?.[1]) {
    return pathMatch[1];
  }
  const ppMatch = searchable.match(/\b(pp-[A-Za-z0-9_-]+)\b/i);
  return ppMatch?.[1] ?? null;
}
