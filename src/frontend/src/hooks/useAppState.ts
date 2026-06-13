/**
 * Consolidated app state hook — bundles all data-fetching hooks
 * used by App.tsx so the component stays thin.
 *
 * Extracted from App.tsx (~70 lines of hook calls reduced to one).
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { DEFAULT_API_BASE, getHealth } from "../lib/api/legacy";
import { useDatasetSummary } from "./useDatasetSummary";
import { useImagePreview } from "./useImagePreview";
import { useImageSources } from "./useImageSources";
import { useImageValidation } from "./useImageValidation";
import { useModelStatus } from "./useModelStatus";
import { useProject, useProjects } from "./useProjects";
import { useProjectOverview } from "./useProjectOverview";
import { useRunPipeline } from "./useRunPipeline";
import { useTaskDiagnostics } from "./useTaskDiagnostics";
import { useTaskEvents } from "./useTaskEvents";
import { useTasks } from "./useTasks";
import { useTaskStream } from "./useTaskStream";
import type { ImagePlane } from "../lib/types/image";
import type { ExecutionMode } from "../lib/types/pipeline";
import type { TaskAuditPackage, TaskStreamMessage, TaskEvent } from "../lib/types/task";

export function useAppState() {
  // ── Core ────────────────────────────────────────────────────────────
  const baseUrl = DEFAULT_API_BASE;
  const [mode, setMode] = useState<"dashboard" | "advanced">("dashboard");
  const [health, setHealth] = useState<boolean | null>(null);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");

  // ── Selection state ──────────────────────────────────────────────────
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);

  // ── Media state ──────────────────────────────────────────────────────
  const [sequence, setSequence] = useState("T1");
  const [plane, setPlane] = useState<ImagePlane>("axial");
  const [sliceIndex, setSliceIndex] = useState<number | null>(null);

  // ── Pipeline state ───────────────────────────────────────────────────
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("simulated");
  const [externalSmokeApprovedRun, setExternalSmokeApprovedRun] = useState(false);
  const [externalSmokeApprovedBy, setExternalSmokeApprovedBy] = useState("");
  const [taskApprovalName, setTaskApprovalName] = useState("");

  // ── Audit state ──────────────────────────────────────────────────────
  const [auditPackage, setAuditPackage] = useState<TaskAuditPackage | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);

  // ── Assistant state ──────────────────────────────────────────────────
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");

  // ── Data hooks ───────────────────────────────────────────────────────
  const projects = useProjects();
  const project = useProject(selectedProjectId);
  const overview = useProjectOverview(project.data.study_id);
  const dataset = useDatasetSummary(project.data.id);
  const model = useModelStatus(project.data.id);
  const tasks = useTasks();
  const imageSources = useImageSources(project.data.id);
  const imageValidation = useImageValidation(project.data.id);
  const imagePreview = useImagePreview(project.data.id, sequence, selectedSubjectId, sliceIndex, plane);
  const pipeline = useRunPipeline();
  const taskEvents = useTaskEvents(selectedTaskId);
  const taskDiagnostics = useTaskDiagnostics(selectedTaskId);

  // ── Auto-selection effects ───────────────────────────────────────────
  useEffect(() => {
    if (!selectedProjectId && projects.data.length) {
      setSelectedProjectId(projects.data[0].id);
    }
  }, [projects.data, selectedProjectId]);

  useEffect(() => {
    if (project.data.sequences.length && !project.data.sequences.includes(sequence)) {
      setSequence(project.data.sequences[0]);
    }
  }, [project.data.sequences, sequence]);

  useEffect(() => {
    const subjects = imageSources.data.subjects;
    if (!subjects.length) return;
    if (!selectedSubjectId || !subjects.some((item) => item.subject_id === selectedSubjectId)) {
      setSelectedSubjectId(subjects[0].subject_id);
    }
  }, [imageSources.data.subjects, selectedSubjectId]);

  useEffect(() => {
    setSliceIndex(null);
  }, [project.data.id, selectedSubjectId, sequence, plane]);

  useEffect(() => {
    setAuditPackage(null);
  }, [selectedTaskId]);

  // ── Health check ─────────────────────────────────────────────────────
  const checkHealth = useCallback(async () => {
    setApiError("");
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const result = await getHealth(baseUrl);
        setHealth((result as { status?: string }).status === "ok" || !!result);
        return;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 450));
      }
    }
    setHealth(false);
    setApiError(
      "Backend disconnected. Start it with:\npython -m uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000"
    );
  }, [baseUrl]);

  // ── Task stream handler ──────────────────────────────────────────────
  const handleTaskMessage = useCallback(
    (message: TaskStreamMessage) => {
      tasks.updateTaskFromStream(message);
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
      setNotice(message.message);
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
    [selectedTaskId, taskDiagnostics.reload, taskEvents.reload, taskEvents.setData, tasks.updateTaskFromStream]
  );

  const taskStream = useTaskStream(activeTaskId, handleTaskMessage);

  // ── Derived values ───────────────────────────────────────────────────
  const taskCounts = useMemo(() => {
    const completed = tasks.data.filter((task) => task.status === "completed").length;
    const running = tasks.data.filter((task) => task.status === "running").length;
    const failed = tasks.data.filter((task) => task.status === "failed").length;
    return { completed, running, failed };
  }, [tasks.data]);

  const sequenceOptions = useMemo(() => {
    return Array.from(new Set([...project.data.sequences, ...imageSources.data.sequences]));
  }, [imageSources.data.sequences, project.data.sequences]);

  const selectedImageSource = useMemo(() => {
    const manifest = imageSources.data.manifest ?? [];
    return (
      manifest.find((item) => item.subject_id === selectedSubjectId && item.sequence === sequence) ??
      manifest.find((item) => item.subject_id === selectedSubjectId) ??
      null
    );
  }, [imageSources.data.manifest, selectedSubjectId, sequence]);

  return {
    // state
    baseUrl, mode, health, apiError, notice,
    selectedProjectId, selectedSubjectId, selectedTaskId, activeTaskId,
    sequence, plane, sliceIndex,
    executionMode, externalSmokeApprovedRun, externalSmokeApprovedBy, taskApprovalName,
    auditPackage, auditLoading,
    assistantInput, assistantLoading, assistantError,
    // data hooks
    projects, project, overview, dataset, model, tasks,
    imageSources, imageValidation, imagePreview,
    pipeline, taskEvents, taskDiagnostics, taskStream,
    // derived
    taskCounts, sequenceOptions, selectedImageSource,
    // setters
    setMode, setHealth, setApiError, setNotice,
    setSelectedProjectId, setSelectedSubjectId, setSelectedTaskId, setActiveTaskId,
    setSequence, setPlane, setSliceIndex,
    setExecutionMode, setExternalSmokeApprovedRun, setExternalSmokeApprovedBy,
    setTaskApprovalName,
    setAuditPackage, setAuditLoading,
    setAssistantInput, setAssistantLoading, setAssistantError,
    // actions
    checkHealth,
  };
}
