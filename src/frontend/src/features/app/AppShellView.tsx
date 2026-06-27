import { Suspense, useEffect, useState } from "react";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ChatMessage } from "../../lib/types/assistant";
import type {
  ImagePlane,
  ImagePreview,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import type { PresetPlanDraft } from "../../types";
import type { ModelStatus } from "../../lib/types/model";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { AppController } from "../app/useAppController";
import type { ProjectController } from "../projects/useProjectController";
import type { TaskController } from "../tasks/useTaskController";
import type { ThemePreference } from "../../hooks/useAppState";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { WorkflowTab } from "../../lib/projectWorkflow";
import type {
  ArtifactSelection,
  DataSeriesSelection,
  PlanNodeSelection,
  WorkspaceSelectionContext,
} from "../../lib/workspaceSelection";
import { TopBar, WorkspaceSuspenseFallback } from "../dashboard/DashboardChrome";
import { ProjectOverviewHeader } from "../projects/ProjectOverviewHeader";
import { ProjectCreateSheet } from "../projects/ProjectCreateSheet";
import { ProjectsPage } from "../projects/ProjectsPage";
import { ProjectSwitcher } from "../dashboard/ProjectSwitcher";
import { DataConversionWorkspace } from "../workspaces/DataConversionWorkspace";
import { PlanWorkspace } from "../workspaces/PlanWorkspace";
import { PreprocessingWorkspace } from "../workspaces/PreprocessingWorkspace";
import { RunsWorkspace } from "../workspaces/RunsWorkspace";
import { QCReportsWorkspace } from "../workspaces/QCReportsWorkspace";
import { ResultsWorkspace } from "../workspaces/ResultsWorkspace";
import { SettingsEnvironmentWorkspace } from "../workspaces/SettingsEnvironmentWorkspace";
import { ProjectCreateResultPanel } from "./ProjectCreateResultPanel";
import { RunActivityBar } from "../tasks/RunActivityBar";
import { MedicalImageViewer } from "./MedicalImageViewer";
import { ProjectLifecycleSidebar } from "./ProjectLifecycleSidebar";
import { AssistantSheet } from "../tools/AssistantSheet";
import { ContextInspector } from "../tools/ContextInspector";
import { AppShell } from "../../layouts/AppShell";
import { ProjectShell } from "../../layouts/ProjectShell";
import { shouldRenderProjectImageViewer } from "./viewerVisibility";
import styles from "./AppShellView.module.css";

export type AppShellViewProps = {
  baseUrl: string;
  drawerOpen: boolean;
  health: boolean | null;
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  project: { data: ProjectDetail };
  projectInventory: ProjectInventory | null;
  projectController: Pick<
    ProjectController,
    | "projectCreateResult"
    | "projectCreateLoading"
    | "projectCreateError"
    | "setProjectCreateResult"
    | "setProjectCreateError"
    | "projects"
    | "projectsLoading"
    | "projectsError"
    | "handleDeleteProject"
    | "selectProjectDirectory"
    | "createProjectFromDirectoryPath"
  >;
  taskController: Pick<
    TaskController,
    | "tasks"
    | "tasksLoading"
    | "tasksError"
    | "reloadTasks"
    | "selectedTask"
    | "taskEvents"
    | "taskEventsLoading"
    | "taskEventsError"
    | "reloadTaskEvents"
    | "taskDiagnosticsData"
    | "reloadTaskDiagnostics"
    | "taskStreamConnected"
    | "hasPreprocessingRun"
  >;
  taskStream: { error: string | null };
  app: Pick<
    AppController,
    | "notice"
    | "setNotice"
    | "apiError"
    | "activeWorkflow"
    | "setActiveWorkflow"
    | "checkHealth"
    | "handleScrollToPanel"
    | "setDrawerOpen"
    | "handleApproveTask"
    | "handleGenerateAuditPackage"
    | "handleReconnectTaskStream"
    | "handleAssistantSubmit"
    | "presetPlanDraft"
  >;
  appState: {
    themePreference: ThemePreference;
    setThemePreference: (themePreference: ThemePreference) => void;
  };
  image: {
    sequence: string;
    setSequence: (seq: string) => void;
    plane: ImagePlane;
    setPlane: (plane: ImagePlane) => void;
    sliceIndex: number | null;
    setSliceIndex: (index: number | null) => void;
    selectedSubjectId: string | null;
    setSelectedSubjectId: (id: string | null) => void;
    sequenceOptions: string[];
    selectedImageSource: ImageSources["manifest"][number] | null;
    imageSources: { data: ImageSources };
    imageValidation: { data: ImageValidationReport };
    imagePreview: { data: ImagePreview | null; loading: boolean };
  };
  assistant: {
    input: string;
    setInput: (input: string) => void;
    loading: boolean;
    error: string;
    messages: ChatMessage[];
    setMessages: (messages: ChatMessage[]) => void;
  };
  approval: {
    taskApprovalName: string;
    setTaskApprovalName: (name: string) => void;
    auditPackage: { report_path: string } | null;
    setAuditPackage: (pkg: { report_path: string } | null) => void;
    auditLoading: boolean;
    setAuditLoading: (loading: boolean) => void;
  };
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  setExternalSmokeApprovedRun: (approved: boolean) => void;
  externalSmokeApprovedBy: string;
  setExternalSmokeApprovedBy: (by: string) => void;
  model: ModelStatus | null;
  dataset: DatasetSummary | null;
  setExecutionMode: (mode: ExecutionMode) => void;
  onToggleDrawer: () => void;
  handleApproveSelectedTask: () => Promise<void>;
  handleGenerateAuditPackage: () => Promise<void>;
  handleReconnectTaskStream: () => void;
  handleAssistantSubmit: (event: React.FormEvent) => Promise<void>;
  onNewChat: () => void;
  selectedTaskId: string | null;
  setSelectedTaskId: (id: string | null) => void;
  selectionContext: WorkspaceSelectionContext;
  onSelectedArtifactChange: (artifact: ArtifactSelection | null) => void;
  onSelectedDataSeriesChange: (selection: DataSeriesSelection | null) => void;
  onSelectedPlanNodeChange: (node: PlanNodeSelection | null) => void;
};

export function AppShellView({
  baseUrl,
  drawerOpen,
  health,
  selectedProjectId,
  onSelectProject,
  project,
  projectInventory,
  projectController,
  taskController,
  taskStream,
  app,
  appState,
  image,
  assistant,
  approval,
  executionMode,
  externalSmokeApprovedRun,
  setExternalSmokeApprovedRun,
  externalSmokeApprovedBy,
  setExternalSmokeApprovedBy,
  model,
  dataset,
  setExecutionMode,
  onToggleDrawer,
  handleApproveSelectedTask,
  handleGenerateAuditPackage,
  handleReconnectTaskStream,
  handleAssistantSubmit,
  onNewChat,
  selectedTaskId,
  setSelectedTaskId,
  selectionContext,
  onSelectedArtifactChange,
  onSelectedDataSeriesChange,
  onSelectedPlanNodeChange,
}: AppShellViewProps) {
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [projectCreateOpen, setProjectCreateOpen] = useState(false);
  const [projectsPageOpen, setProjectsPageOpen] = useState(false);
  const selectedProject = selectedProjectId ? project : null;
  const projectDir =
    typeof selectedProject?.data.metadata?.project_dir === "string"
      ? selectedProject.data.metadata.project_dir
      : null;
  const workflowLabels: Record<WorkflowTab, string> = {
    data: "Data & Conversion",
    plan: "Plan",
    preprocessing: "Preprocessing",
    runs: "Runs",
    reports: "QC",
    results: "Results",
    environment: "Settings / Environment",
  };
  const activePageLabel = projectsPageOpen
    ? "Projects"
    : (workflowLabels[app.activeWorkflow as WorkflowTab] ?? "Workspace");
  const topBarProjectName = projectsPageOpen
    ? "Project Library"
    : (projectInventory?.projectName ?? project.data.name);
  const showImageViewer = shouldRenderProjectImageViewer({
    activeWorkflow: app.activeWorkflow as WorkflowTab,
    inventory: projectInventory,
  });
  const hasSystemMessages = Boolean(
    app.notice ||
      projectController.projectCreateResult ||
      projectController.projectCreateLoading ||
      projectController.projectCreateError ||
      taskStream.error,
  );

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "j") {
        event.preventDefault();
        setAssistantOpen(true);
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return (
    <AppShell
      topBar={
        <TopBar
          health={health}
          apiError={app.apiError}
          onRetry={app.checkHealth}
          projectName={topBarProjectName}
          activePageLabel={activePageLabel}
          onOpenAssistant={() => setAssistantOpen(true)}
          onOpenInspector={() => app.setDrawerOpen(true)}
        />
      }
      systemMessages={
        hasSystemMessages ? (
          <>
            {app.notice ? (
              <div className={styles.toastLine}>
                {app.notice}
                <button onClick={() => app.setNotice("")}>Dismiss</button>
              </div>
            ) : null}
            <ProjectCreateResultPanel
              result={projectController.projectCreateResult}
              loading={projectController.projectCreateLoading}
              error={projectController.projectCreateError}
              onDismiss={() => {
                projectController.setProjectCreateResult(null);
                projectController.setProjectCreateError("");
              }}
            />
            {taskStream.error ? (
              <div className={styles.streamBanner}>
                Task stream disconnected: {taskStream.error}
                <button onClick={handleReconnectTaskStream}>Reconnect</button>
              </div>
            ) : null}
          </>
        ) : undefined
      }
      sidebar={
        <aside className={styles.sideRail}>
          <ProjectSwitcher
            projects={projectController.projects.data}
            selectedProjectId={selectedProjectId || project.data.id}
            loading={projectController.projectsLoading}
            error={projectController.projectsError}
            deletingProjectId={null}
            onSelect={(projectId) => {
              onSelectProject(projectId);
              setProjectsPageOpen(false);
            }}
            onCreateProject={() => setProjectCreateOpen(true)}
            onOpenProjects={() => setProjectsPageOpen(true)}
            onDelete={projectController.handleDeleteProject}
          />
          <ProjectLifecycleSidebar
            activeTab={app.activeWorkflow as WorkflowTab}
            dataState={projectInventory?.dataState}
            hasPreprocessingRun={taskController.hasPreprocessingRun}
            projectsPageOpen={projectsPageOpen}
            onChange={app.setActiveWorkflow}
            onOpenWorkspace={() => setProjectsPageOpen(false)}
          />
          <div className={styles.sideRailFooter}>
            <span className={styles.researchOnlyTag}>Research Only</span>
            <span className={styles.versionTag}>v0.6</span>
          </div>
        </aside>
      }
      mainClassName={styles.workflowMain}
      inspector={
        drawerOpen ? (
          <ContextInspector
            activePageLabel={activePageLabel}
            inventory={projectInventory}
            isOpen={true}
            onToggle={onToggleDrawer}
            project={project.data}
            model={model}
            dataset={dataset}
            executionMode={executionMode}
            externalSmokeApprovedRun={externalSmokeApprovedRun}
            externalSmokeApprovedBy={externalSmokeApprovedBy}
            selectionContext={selectionContext}
            onConfigure={() => {
              setProjectsPageOpen(false);
              app.setActiveWorkflow("environment");
            }}
          />
        ) : null
      }
      inspectorOpen={drawerOpen}
      runActivity={
        <RunActivityBar
          tasks={taskController.tasks}
          selectedTaskId={selectedTaskId}
          onSelectTask={(taskId) => {
            setSelectedTaskId(taskId);
            setProjectsPageOpen(false);
            app.setActiveWorkflow("runs");
          }}
          onOpenRuns={() => {
            setProjectsPageOpen(false);
            app.setActiveWorkflow("runs");
          }}
        />
      }
    >
      <AssistantSheet
        activePageLabel={activePageLabel}
        error={assistant.error}
        input={assistant.input}
        loading={assistant.loading}
        messages={assistant.messages}
        onInput={assistant.setInput}
        onNewChat={onNewChat}
        onOpenChange={setAssistantOpen}
        onSubmit={handleAssistantSubmit}
        open={assistantOpen}
        projectName={projectInventory?.projectName ?? project.data.name}
        selectionContext={selectionContext}
      />

      <ProjectCreateSheet
        error={projectController.projectCreateError}
        loading={projectController.projectCreateLoading}
        onCreate={projectController.createProjectFromDirectoryPath}
        onOpenChange={setProjectCreateOpen}
        onSelectDirectory={projectController.selectProjectDirectory}
        open={projectCreateOpen}
      />

      {projectsPageOpen ? (
        <ProjectsPage
          deletingProjectId={null}
          error={projectController.projectsError}
          loading={projectController.projectsLoading}
          onClose={() => setProjectsPageOpen(false)}
          onCreateProject={() => setProjectCreateOpen(true)}
          onDeleteProject={projectController.handleDeleteProject}
          onSelectProject={onSelectProject}
          projects={projectController.projects.data}
          selectedProjectId={selectedProjectId}
        />
      ) : (
        <ProjectShell
          overview={
            <ProjectOverviewHeader
              inventory={projectInventory}
              hasPreprocessingRun={taskController.hasPreprocessingRun}
              onPrimaryAction={() => {
                app.setActiveWorkflow(
                  projectInventory?.dataState === "converted_bids" ? "preprocessing" : "data",
                );
                window.setTimeout(() => app.handleScrollToPanel("workflow-workspace"), 0);
              }}
              onSecondaryAction={() => {
                app.setActiveWorkflow(
                  projectInventory?.dataState === "converted_bids" ? "reports" : "data",
                );
                window.setTimeout(() => app.handleScrollToPanel("workflow-workspace"), 0);
              }}
            />
          }
          viewer={
            showImageViewer ? (
              <MedicalImageViewer
                project={project.data}
                sequence={image.sequence}
                plane={image.plane}
                sequenceOptions={image.sequenceOptions}
                imageSources={image.imageSources.data}
                validation={image.imageValidation.data}
                subjectId={image.selectedSubjectId}
                preview={image.imagePreview.data}
                sourceFile={image.selectedImageSource}
                loading={image.imagePreview.loading}
                dataState={projectInventory?.dataState}
                onSequenceChange={image.setSequence}
                onPlaneChange={image.setPlane}
                onSubjectChange={image.setSelectedSubjectId}
                onSliceChange={image.setSliceIndex}
              />
            ) : undefined
          }
          workspaceLabel={`${activePageLabel} workspace`}
        >
            <Suspense fallback={<WorkspaceSuspenseFallback label="Loading workspace..." />}>
              {app.activeWorkflow === "data" ? (
                <DataConversionWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  inventory={projectInventory}
                  onSelectedDataSeriesChange={onSelectedDataSeriesChange}
                />
              ) : app.activeWorkflow === "plan" ? (
                <PlanWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  selectedProject={selectedProject?.data ?? null}
                  projectConfigPath={selectedProject?.data.metadata?.project_config_path}
                  datasetIndexPath={selectedProject?.data.metadata?.dataset_index_path}
                  rawdataDir={selectedProject?.data.metadata?.rawdata_dir}
                  projectDir={projectDir}
                  initialPresetDraft={app.presetPlanDraft}
                  onSelectedNodeChange={onSelectedPlanNodeChange}
                  onOpenDataConversion={() => app.setActiveWorkflow("data")}
                  onOpenEnvironment={() => app.setActiveWorkflow("environment")}
                />
              ) : app.activeWorkflow === "preprocessing" ? (
                <PreprocessingWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  dataState={projectInventory?.dataState ?? "raw_dicom"}
                  inventory={projectInventory}
                  hasPreprocessingRun={taskController.hasPreprocessingRun}
                  onOpenDataConversion={() => app.setActiveWorkflow("data")}
                  onOpenToolsDrawer={() => app.setDrawerOpen(true)}
                />
              ) : app.activeWorkflow === "runs" ? (
                <RunsWorkspace
                  projectId={selectedProjectId}
                  tasks={taskController.tasks}
                  loading={taskController.tasksLoading}
                  error={taskController.tasksError}
                  onRetryTasks={taskController.reloadTasks}
                  selectedTaskId={selectedTaskId}
                  onSelectTask={setSelectedTaskId}
                  selectedTask={taskController.selectedTask}
                  events={taskController.taskEvents}
                  eventsLoading={taskController.taskEventsLoading}
                  eventsError={taskController.taskEventsError}
                  diagnostics={taskController.taskDiagnosticsData}
                  streamConnected={taskController.taskStreamConnected}
                  taskApprovalName={approval.taskApprovalName}
                  auditPackage={
                    approval.auditPackage as import("../../lib/types/task").TaskAuditPackage | null
                  }
                  auditLoading={approval.auditLoading}
                  onApprovalNameChange={approval.setTaskApprovalName}
                  onApprove={handleApproveSelectedTask}
                  onGenerateAudit={handleGenerateAuditPackage}
                  onRetryEvents={taskController.reloadTaskEvents}
                  onReconnect={handleReconnectTaskStream}
                />
              ) : app.activeWorkflow === "reports" ? (
                <QCReportsWorkspace baseUrl={baseUrl} projectId={selectedProjectId} />
              ) : app.activeWorkflow === "results" ? (
                <ResultsWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  onSelectedArtifactChange={onSelectedArtifactChange}
                />
              ) : (
                <SettingsEnvironmentWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  rawdataDir={selectedProject?.data.metadata?.rawdata_dir}
                  themePreference={appState.themePreference}
                  onThemePreferenceChange={appState.setThemePreference}
                  onReviewDraft={(draft: PresetPlanDraft) => {
                    app.setActiveWorkflow("plan");
                    app.setNotice(
                      "Preset draft loaded into the Plan workspace. Review and save before dry-run.",
                    );
                  }}
                />
              )}
            </Suspense>
        </ProjectShell>
      )}
    </AppShell>
  );
}
