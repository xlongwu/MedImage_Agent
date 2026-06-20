import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import type { PresetPlanDraft } from "./types";
import { getApiBaseUrl } from "./lib/api";
import { useDatasetSummary } from "./hooks/useDatasetSummary";
import { useImagePreview } from "./hooks/useImagePreview";
import { useImageSources } from "./hooks/useImageSources";
import { useImageValidation } from "./hooks/useImageValidation";
import { useModelStatus } from "./hooks/useModelStatus";
import { useProject, useProjects } from "./hooks/useProjects";
import { useProjectOverview } from "./hooks/useProjectOverview";
import { useRunPipeline } from "./hooks/useRunPipeline";
import { useTaskEvents } from "./hooks/useTaskEvents";
import { useTaskDiagnostics } from "./hooks/useTaskDiagnostics";
import { useTaskStream } from "./hooks/useTaskStream";
import { useTasks } from "./hooks/useTasks";
import { buildProjectInventory } from "./lib/projectWorkflow";
import type { ProjectInventory } from "./lib/projectWorkflow";
import type { ChatMessage } from "./lib/types/assistant";
import type {
  ImagePlane,
  ImagePreview,
  ImageSources,
  ImageValidationReport,
} from "./lib/types/image";
import type { ModelStatus } from "./lib/types/model";
import type { ExecutionMode } from "./lib/types/pipeline";
import type { ProjectDetail } from "./lib/types/project";
import type { TaskEvent, TaskLogEntry, TaskStreamMessage } from "./lib/types/task";
import { fallbackChat } from "./lib/mockData";
import { useAppController } from "./features/app/useAppController";
import { useProjectController } from "./features/projects/useProjectController";
import { useTaskController } from "./features/tasks/useTaskController";
import type { ProjectController } from "./features/projects/useProjectController";
import type { TaskController } from "./features/tasks/useTaskController";
import { useToolsDrawerController } from "./features/tools/useToolsDrawerController";
import { AppShellView } from "./features/app/AppShellView";

export { deriveProjectWorkflowState } from "./lib/projectWorkflow";

export default function App() {
  const app = useAppController();
  const projectController = useProjectController() as ProjectController;
  const taskController = useTaskController() as TaskController;
  const toolsDrawer = useToolsDrawerController(
    app.setMode,
    async () => {
      await projectController.handleUploadData();
    },
    () =>
      app.handleRunPipeline({
        projectId: projectController.project.id,
        pipelineId: projectController.project.current_pipeline_id,
        modelId: projectController.project.current_model_id,
        sequences: projectController.project.sequences,
        executionMode: "simulated",
        externalSmokeApproved: false,
        externalSmokeApprovedBy: "",
        onTaskStarted: () => {},
      }),
    async () => {
      await app.handleQuickAction("view-results");
    },
    app.pipelineLoading,
  );

  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("simulated");
  const [externalSmokeApprovedRun, setExternalSmokeApprovedRun] = useState(false);
  const [externalSmokeApprovedBy, setExternalSmokeApprovedBy] = useState("");
  const [taskApprovalName, setTaskApprovalName] = useState("");
  const [auditPackage, setAuditPackage] = useState<{ report_path: string } | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [sequence, setSequence] = useState("T1");
  const [plane, setPlane] = useState<ImagePlane>("axial");
  const [sliceIndex, setSliceIndex] = useState<number | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(fallbackChat);

  const project = useProject(selectedProjectId);
  const selectedProjectForPlanReview = useMemo(
    () =>
      selectedProjectId && !project.fromFallback && project.data.id === selectedProjectId
        ? project.data
        : null,
    [selectedProjectId, project],
  );
  const selectedProjectMetadata = selectedProjectForPlanReview?.metadata;
  const projectDiagnostics = useMemo(() => {
    if (projectController.projectCreateResult?.project_id === selectedProjectId) {
      return projectController.projectCreateResult.diagnostics;
    }
    const diagnostics = selectedProjectMetadata?.diagnostics;
    return diagnostics && typeof diagnostics === "object"
      ? (diagnostics as Record<string, unknown>)
      : {};
  }, [projectController.projectCreateResult, selectedProjectId, selectedProjectMetadata]);

  const overview = useProjectOverview(project.data.study_id);
  const projectInventory = useMemo(
    () => buildProjectInventory(project.data, overview.data, projectDiagnostics),
    [project.data, overview.data, projectDiagnostics],
  );

  const dataset = useDatasetSummary(project.data.id);
  const model = useModelStatus(project.data.id);
  const imageSources = useImageSources(project.data.id);
  const imageValidation = useImageValidation(project.data.id);
  const imagePreview = useImagePreview(
    project.data.id,
    sequence,
    selectedSubjectId,
    sliceIndex,
    plane,
  );
  const pipeline = useRunPipeline();
  const taskEvents = useTaskEvents(selectedTaskId);
  const taskDiagnostics = useTaskDiagnostics(selectedTaskId);

  const sequenceOptions = useMemo(
    () => Array.from(new Set([...project.data.sequences, ...imageSources.data.sequences])),
    [imageSources.data.sequences, project.data.sequences],
  );

  const selectedImageSource = useMemo(() => {
    const manifest = imageSources.data.manifest ?? [];
    return (
      manifest.find(
        (item) => item.subject_id === selectedSubjectId && item.sequence === sequence,
      ) ??
      manifest.find((item) => item.subject_id === selectedSubjectId) ??
      null
    );
  }, [imageSources.data.manifest, selectedSubjectId, sequence]);

  useEffect(() => {
    let active = true;
    getApiBaseUrl()
      .then((url) => {
        if (active) app.setBaseUrl(url);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, [app]);

  useEffect(() => {
    app.checkHealth();
  }, [app.baseUrl, app.checkHealth]);

  useEffect(() => {
    if (projectInventory) {
      if (projectInventory.dataState === "converted_bids") app.setActiveWorkflow("preprocessing");
      else if (projectInventory.dataState === "raw_dicom") app.setActiveWorkflow("data");
      else app.setActiveWorkflow("data");
    }
  }, [selectedProjectId, projectInventory, app]);

  useEffect(() => {
    if (!projectController.projects.data.length) return;
    const exists = selectedProjectId
      ? projectController.projects.data.some((item) => item.id === selectedProjectId)
      : false;
    if (!selectedProjectId || !exists) setSelectedProjectId(projectController.projects.data[0].id);
  }, [projectController.projects.data, selectedProjectId]);

  useEffect(() => {
    if (project.data.sequences.length && !project.data.sequences.includes(sequence))
      setSequence(project.data.sequences[0]);
  }, [project.data.sequences, sequence]);

  useEffect(() => {
    const subjects = imageSources.data.subjects;
    if (!subjects.length) return;
    if (!selectedSubjectId || !subjects.some((item) => item.subject_id === selectedSubjectId))
      setSelectedSubjectId(subjects[0].subject_id);
  }, [imageSources.data.subjects, selectedSubjectId]);

  useEffect(() => {
    setSliceIndex(null);
  }, [project.data.id, selectedSubjectId, sequence, plane]);

  useEffect(() => {
    taskController.setAuditPackage?.(null);
  }, [selectedTaskId, taskController]);

  const handleTaskMessage = useCallback(
    (message: TaskStreamMessage) => {
      taskController.updateTaskFromStream(message);
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
        taskController.taskEventsSetData((current) => [...current, event]);
      }
      app.setNotice(message.message);
      if (
        (message.status === "completed" || message.status === "failed") &&
        selectedTaskId === message.task_id
      ) {
        window.setTimeout(() => {
          taskController.reloadTaskEvents();
          taskController.reloadTaskDiagnostics();
        }, 250);
      }
    },
    [selectedTaskId, taskController, app],
  );

  const taskStream = useTaskStream(activeTaskId, handleTaskMessage);

  const handleRunPipeline = useCallback(async () => {
    await app.handleRunPipeline({
      projectId: project.data.id,
      pipelineId: project.data.current_pipeline_id,
      modelId: project.data.current_model_id,
      sequences: project.data.sequences,
      executionMode,
      externalSmokeApproved: externalSmokeApprovedRun,
      externalSmokeApprovedBy,
      onTaskStarted: (taskId) => {
        setActiveTaskId(taskId);
        setSelectedTaskId(taskId);
      },
    });
  }, [app, project.data, executionMode, externalSmokeApprovedRun, externalSmokeApprovedBy]);

  const handleApproveSelectedTask = useCallback(async () => {
    if (!selectedTaskId) {
      app.setNotice("Select an External Smoke task before approving a real smoke run.");
      return;
    }
    if (!taskApprovalName.trim()) {
      app.setNotice("Approval requires an approved-by name.");
      return;
    }
    try {
      const message = await app.handleApproveTask(selectedTaskId, taskApprovalName);
      await taskController.reloadTasks();
      await taskController.reloadTaskEvents();
      await taskController.reloadTaskDiagnostics();
      setActiveTaskId(selectedTaskId);
      app.setNotice(message);
    } catch (err) {
      app.setNotice(err instanceof Error ? err.message : String(err));
    }
  }, [selectedTaskId, taskApprovalName, taskController, app, setActiveTaskId]);

  const handleGenerateAuditPackage = useCallback(async () => {
    if (!selectedTaskId) {
      app.setNotice("Select a task before generating an audit package.");
      return;
    }
    setAuditLoading(true);
    try {
      const response = await app.handleGenerateAuditPackage(selectedTaskId);
      setAuditPackage(response);
      app.setNotice(`Audit package generated: ${response?.report_path}`);
    } catch (err) {
      app.setNotice(err instanceof Error ? err.message : String(err));
    } finally {
      setAuditLoading(false);
    }
  }, [selectedTaskId, app]);

  const handleReconnectTaskStream = useCallback(() => {
    app.handleReconnectTaskStream(activeTaskId || selectedTaskId, setActiveTaskId);
  }, [activeTaskId, selectedTaskId, app, setActiveTaskId]);

  const handleAssistantSubmit = useCallback(
    async (event: FormEvent) => {
      event.preventDefault();
      const message = assistantInput.trim();
      if (!message) return;
      setAssistantInput("");
      setAssistantError("");
      setAssistantLoading(true);
      setChatMessages((current) => [...current, { role: "user", text: message }]);
      await app.handleAssistantSubmit(
        project.data.id,
        message,
        (text) => setChatMessages((current) => [...current, { role: "assistant", text }]),
        (err) => setAssistantError(err),
      );
      setAssistantLoading(false);
    },
    [project.data.id, assistantInput, app],
  );

  const handleQuickAction = useCallback(
    (action: string) => {
      app.handleQuickAction(action);
      if (action === "upload-data") void projectController.handleUploadData();
      if (action === "run-pipeline") void handleRunPipeline();
    },
    [app, projectController, handleRunPipeline],
  );

  return (
    <AppShellView
      mode={app.mode}
      baseUrl={app.baseUrl}
      drawerOpen={app.drawerOpen}
      selectedProjectId={selectedProjectId}
      project={project}
      projectInventory={projectInventory}
      projectController={projectController}
      taskController={taskController}
      taskStream={taskStream}
      app={app}
      image={{
        sequence,
        setSequence,
        plane,
        setPlane,
        sliceIndex,
        setSliceIndex,
        selectedSubjectId,
        setSelectedSubjectId,
        sequenceOptions,
        selectedImageSource,
        imageSources,
        imageValidation,
        imagePreview,
      }}
      assistant={{
        input: assistantInput,
        setInput: setAssistantInput,
        loading: assistantLoading,
        error: assistantError,
        messages: chatMessages,
        setMessages: setChatMessages,
      }}
      approval={{
        taskApprovalName,
        setTaskApprovalName,
        auditPackage,
        setAuditPackage,
        auditLoading,
        setAuditLoading,
      }}
      executionMode={executionMode}
      externalSmokeApprovedRun={externalSmokeApprovedRun}
      setExternalSmokeApprovedRun={setExternalSmokeApprovedRun}
      externalSmokeApprovedBy={externalSmokeApprovedBy}
      setExternalSmokeApprovedBy={setExternalSmokeApprovedBy}
      model={model.data}
      dataset={dataset.data}
      setMode={app.setMode}
      setExecutionMode={setExecutionMode}
      onToggleDrawer={() => app.setDrawerOpen(!app.drawerOpen)}
      handleRunPipelineWrapper={handleRunPipeline}
      handleApproveSelectedTask={handleApproveSelectedTask}
      handleGenerateAuditPackage={handleGenerateAuditPackage}
      handleReconnectTaskStream={handleReconnectTaskStream}
      handleAssistantSubmit={handleAssistantSubmit}
      handleQuickAction={handleQuickAction}
      onNewChat={() => setChatMessages(fallbackChat)}
      selectedTaskId={selectedTaskId}
      setSelectedTaskId={setSelectedTaskId}
      activeTaskId={activeTaskId}
      setActiveTaskId={setActiveTaskId}
    />
  );
}
