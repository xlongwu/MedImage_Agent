import { useCallback, useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";
import { useDatasetSummary } from "./hooks/useDatasetSummary";
import { useModelStatus } from "./hooks/useModelStatus";
import { useProject } from "./hooks/useProjects";
import { useProjectOverview } from "./hooks/useProjectOverview";
import { useTaskStream } from "./hooks/useTaskStream";
import { useAppState } from "./hooks/useAppState";
import { buildProjectInventory } from "./lib/projectWorkflow";
import type { ChatMessage } from "./lib/types/assistant";
import type { ExecutionMode } from "./lib/types/pipeline";
import type { TaskEvent, TaskStreamMessage } from "./lib/types/task";
import type {
  ArtifactSelection,
  DataSeriesSelection,
  PlanNodeSelection,
} from "./lib/workspaceSelection";
import { fallbackChat } from "./lib/mockData";
import { useAppController } from "./features/app/useAppController";
import { useProjectController } from "./features/projects/useProjectController";
import { useTaskController } from "./features/tasks/useTaskController";
import type { ProjectController } from "./features/projects/useProjectController";
import type { TaskController } from "./features/tasks/useTaskController";
import { AppShellView } from "./features/app/AppShellView";
import { useWorkspaceNavigation } from "./features/navigation/useWorkspaceNavigation";
import { I18nProvider } from "./i18n/I18nProvider";
import { useImageWorkspaceController } from "./features/app/useImageWorkspaceController";

export default function App() {
  const appState = useAppState();
  const app = useAppController();
  const navigation = useWorkspaceNavigation();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const executionMode: ExecutionMode = "simulated";
  const externalSmokeApprovedRun = false;
  const externalSmokeApprovedBy = "";
  const [taskApprovalName, setTaskApprovalName] = useState("");
  const [auditPackage, setAuditPackage] = useState<{ report_path: string } | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [selectedDataSeries, setSelectedDataSeries] = useState<DataSeriesSelection | null>(null);
  const [selectedPlanNode, setSelectedPlanNode] = useState<PlanNodeSelection | null>(null);
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactSelection | null>(null);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(fallbackChat);

  const updateSelectedProject = useCallback(
    (projectId: string | null) => {
      setSelectedProjectId(projectId);
      setSelectedDataSeries(null);
      setSelectedPlanNode(null);
      setSelectedArtifact(null);
      setSelectedTaskId(null);
      if (navigation.location.kind === "project") {
        if (projectId) navigation.openProject(projectId);
        else navigation.openProjects();
      }
    },
    [navigation],
  );
  const openSelectedProject = useCallback(
    (projectId: string) => {
      updateSelectedProject(projectId);
      navigation.openProject(projectId);
    },
    [navigation, updateSelectedProject],
  );
  const projectController = useProjectController(
    selectedProjectId,
    updateSelectedProject,
  ) as ProjectController;
  const taskController = useTaskController(
    selectedTaskId,
    setSelectedTaskId,
    setActiveTaskId,
  ) as TaskController;

  const project = useProject(selectedProjectId);
  const activeProjectId = selectedProjectId && !project.fromFallback ? project.data.id : null;
  const activeStudyId = !project.fromFallback ? project.data.study_id : null;
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

  const overview = useProjectOverview(activeStudyId);
  const projectInventory = useMemo(
    () => buildProjectInventory(project.data, overview.data, projectDiagnostics),
    [project.data, overview.data, projectDiagnostics],
  );

  const dataset = useDatasetSummary(activeProjectId);
  const model = useModelStatus(activeProjectId);
  const image = useImageWorkspaceController(activeProjectId, project.data);

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

  const selectionContext = useMemo(
    () => ({
      artifact: selectedArtifact,
      dataSeries: selectedDataSeries,
      image: {
        plane: image.plane,
        series: image.sequence || null,
        source:
          image.selectedImageSource?.relative_path ?? image.selectedImageSource?.file_path ?? null,
        subjectId: image.selectedSubjectId,
      },
      planNode: selectedPlanNode,
      run: {
        id: selectedTaskId,
        name: taskController.selectedTask?.run_name ?? null,
        pipeline: taskController.selectedTask?.pipeline ?? null,
        status: taskController.selectedTask?.status ?? null,
      },
    }),
    [
      image.plane,
      image.selectedImageSource?.file_path,
      image.selectedImageSource?.relative_path,
      image.selectedSubjectId,
      image.sequence,
      selectedArtifact,
      selectedDataSeries,
      selectedPlanNode,
      selectedTaskId,
      taskController.selectedTask?.pipeline,
      taskController.selectedTask?.run_name,
      taskController.selectedTask?.status,
    ],
  );

  return (
    <I18nProvider locale={appState.localePreference}>
      <AppShellView
        baseUrl={app.baseUrl}
        drawerOpen={app.drawerOpen}
        health={app.health}
        selectedProjectId={selectedProjectId}
        onSelectProject={openSelectedProject}
        navigation={navigation}
        project={project}
        projectInventory={projectInventory}
        projectController={projectController}
        taskController={taskController}
        taskStream={taskStream}
        app={app}
        appState={appState}
        image={image}
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
        externalSmokeApprovedBy={externalSmokeApprovedBy}
        model={model.data}
        dataset={dataset.data}
        onToggleDrawer={() => app.setDrawerOpen(!app.drawerOpen)}
        handleApproveSelectedTask={handleApproveSelectedTask}
        handleGenerateAuditPackage={handleGenerateAuditPackage}
        handleReconnectTaskStream={handleReconnectTaskStream}
        handleAssistantSubmit={handleAssistantSubmit}
        onNewChat={() => setChatMessages(fallbackChat)}
        selectedTaskId={selectedTaskId}
        setSelectedTaskId={setSelectedTaskId}
        selectionContext={selectionContext}
        onSelectedArtifactChange={setSelectedArtifact}
        onSelectedDataSeriesChange={setSelectedDataSeries}
        onSelectedPlanNodeChange={setSelectedPlanNode}
      />
    </I18nProvider>
  );
}
