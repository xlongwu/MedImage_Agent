import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ChatMessage } from "../../lib/types/assistant";
import type {
  ImagePlane,
  ImagePreview,
  ImageSources,
  ImageValidationReport,
} from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import type { NativeFullPreprocResponse } from "../../types";
import type { ModelStatus } from "../../lib/types/model";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { AppController } from "../app/useAppController";
import type { ProjectController } from "../projects/useProjectController";
import type { TaskController } from "../tasks/useTaskController";
import type { ThemePreference } from "../../hooks/useAppState";
import type { LocalePreference } from "../../hooks/useAppState";
import { getLatestNativeFullPreprocessingRun } from "../../lib/api/preprocessing";
import { hasNativePreprocessingRunEvidence } from "../../lib/projectWorkflow";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type {
  ArtifactSelection,
  DataSeriesSelection,
  PlanNodeSelection,
  WorkspaceSelectionContext,
} from "../../lib/workspaceSelection";
import { TopBar, WorkspaceSuspenseFallback } from "../dashboard/DashboardChrome";
import { ProjectCreateSheet } from "../projects/ProjectCreateSheet";
import { ProjectsPage } from "../projects/ProjectsPage";
import { DataConversionWorkspace } from "../workspaces/DataConversionWorkspace";
import { PlanWorkspace } from "../workspaces/PlanWorkspace";
import { PreprocessingWorkspace } from "../workspaces/PreprocessingWorkspace";
import { RunsWorkspace } from "../workspaces/RunsWorkspace";
import { OverviewWorkspace } from "../workspaces/OverviewWorkspace";
import { ProjectCreateResultPanel } from "./ProjectCreateResultPanel";
import { RunActivityBar } from "../tasks/RunActivityBar";
import { MedicalImageViewer } from "./MedicalImageViewer";
import { AssistantSheet } from "../tools/AssistantSheet";
import { ContextInspector } from "../tools/ContextInspector";
import { AppShell } from "../../layouts/AppShell";
import { ProjectShell } from "../../layouts/ProjectShell";
import { LifecycleRail } from "../navigation/LifecycleRail";
import { buildLifecycleItems, isPrimaryWorkspace } from "../navigation/workspaceModel";
import type { AppLocation, ProjectWorkspace } from "../navigation/workspaceModel";
import { useI18n } from "../../i18n/useI18n";
import styles from "./AppShellView.module.css";

const QCReportsWorkspace = lazy(() =>
  import("../workspaces/QCReportsWorkspace").then((module) => ({
    default: module.QCReportsWorkspace,
  })),
);
const ResultsWorkspace = lazy(() =>
  import("../workspaces/ResultsWorkspace").then((module) => ({ default: module.ResultsWorkspace })),
);
const SettingsEnvironmentWorkspace = lazy(() =>
  import("../workspaces/SettingsEnvironmentWorkspace").then((module) => ({
    default: module.SettingsEnvironmentWorkspace,
  })),
);

export type AppShellViewProps = {
  baseUrl: string;
  drawerOpen: boolean;
  health: boolean | null;
  selectedProjectId: string | null;
  onSelectProject: (id: string) => void;
  project: { data: ProjectDetail; reload: () => Promise<ProjectDetail | null> };
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
    | "latestPreprocessingRunId"
  >;
  taskStream: { error: string | null };
  app: Pick<
    AppController,
    | "notice"
    | "setNotice"
    | "apiError"
    | "version"
    | "versionFromBackend"
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
    localePreference: LocalePreference;
    setLocalePreference: (localePreference: LocalePreference) => void;
  };
  navigation: {
    location: AppLocation;
    openProject: (projectId: string) => void;
    openProjects: () => void;
    openWorkspace: (projectId: string, workspace: ProjectWorkspace) => void;
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
  externalSmokeApprovedBy: string;
  model: ModelStatus | null;
  dataset: DatasetSummary | null;
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
  navigation,
  image,
  assistant,
  approval,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  model,
  dataset,
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
  const { t } = useI18n();
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [projectCreateOpen, setProjectCreateOpen] = useState(false);
  const [nativeRunState, setNativeRunState] = useState<{
    projectId: string;
    run: NativeFullPreprocResponse | null;
  }>({ projectId: "", run: null });
  const latestNativePreprocessingRun =
    nativeRunState.projectId === selectedProjectId ? nativeRunState.run : null;
  const selectedProject = selectedProjectId ? project : null;
  const projectDir =
    typeof selectedProject?.data.metadata?.project_dir === "string"
      ? selectedProject.data.metadata.project_dir
      : null;
  const workflowLabels: Record<ProjectWorkspace, string> = {
    overview: t("nav.overview"),
    data: t("nav.data"),
    plan: t("nav.plan"),
    preprocessing: t("nav.preprocessing"),
    runs: t("nav.runs"),
    qc: t("nav.qc"),
    results: t("nav.results"),
    settings: t("nav.settings"),
  };
  const activeWorkspace =
    navigation.location.kind === "project" ? navigation.location.workspace : null;
  const activePageLabel = activeWorkspace ? workflowLabels[activeWorkspace] : t("nav.projects");
  const topBarProjectName =
    navigation.location.kind === "projects"
      ? t("projects.library")
      : (projectInventory?.projectName ?? project.data.name);
  const showImageViewer =
    activeWorkspace === "results" && Boolean(projectInventory?.hasConvertedData);
  const hasPreprocessingRun =
    taskController.hasPreprocessingRun ||
    hasNativePreprocessingRunEvidence(latestNativePreprocessingRun);
  const latestPreprocessingRunId =
    taskController.latestPreprocessingRunId ||
    (hasNativePreprocessingRunEvidence(latestNativePreprocessingRun)
      ? (latestNativePreprocessingRun?.run_id ?? null)
      : null);
  const lifecycleItems = useMemo(
    () =>
      buildLifecycleItems({
        activeWorkspace: activeWorkspace ?? "overview",
        dataState: projectInventory?.dataState,
        hasPreprocessingRun,
      }),
    [activeWorkspace, hasPreprocessingRun, projectInventory?.dataState],
  );
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

  useEffect(() => {
    if (!selectedProjectId) return;

    let cancelled = false;

    const refreshLatestNativeRun = () => {
      void getLatestNativeFullPreprocessingRun(baseUrl, selectedProjectId)
        .then((response) => {
          if (!cancelled && response?.run_id) {
            setNativeRunState({ projectId: selectedProjectId, run: response });
          }
        })
        .catch(() => {
          // Native preprocessing is optional for new projects; keep the shell quiet.
        });
    };

    refreshLatestNativeRun();
    const intervalId = window.setInterval(refreshLatestNativeRun, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(intervalId);
    };
  }, [baseUrl, selectedProjectId]);

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
          onBackToProjects={navigation.openProjects}
          onOpenRuns={() => {
            if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "runs");
          }}
          onOpenSettings={() => {
            if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "settings");
          }}
          locale={appState.localePreference}
          onLocaleChange={appState.setLocalePreference}
          version={app.version}
          versionFromBackend={app.versionFromBackend}
        />
      }
      lifecycle={
        navigation.location.kind === "project" ? (
          <LifecycleRail
            activeWorkspace={
              activeWorkspace && isPrimaryWorkspace(activeWorkspace) ? activeWorkspace : null
            }
            items={lifecycleItems}
            onNavigate={(workspace) => {
              if (selectedProjectId) navigation.openWorkspace(selectedProjectId, workspace);
            }}
          />
        ) : undefined
      }
      systemMessages={
        hasSystemMessages ? (
          <>
            {app.notice ? (
              <div className={styles.toastLine}>
                {app.notice}
                <button onClick={() => app.setNotice("")}>{t("common.dismiss")}</button>
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
                {t("shell.taskStreamDisconnected", { error: taskStream.error })}
                <button onClick={handleReconnectTaskStream}>{t("shell.reconnect")}</button>
              </div>
            ) : null}
          </>
        ) : undefined
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
              if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "settings");
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
            if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "runs");
          }}
          onOpenRuns={() => {
            if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "runs");
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

      {navigation.location.kind === "projects" ? (
        <ProjectsPage
          deletingProjectId={null}
          error={projectController.projectsError}
          loading={projectController.projectsLoading}
          onClose={() => undefined}
          onCreateProject={() => setProjectCreateOpen(true)}
          onDeleteProject={projectController.handleDeleteProject}
          onSelectProject={onSelectProject}
          projects={projectController.projects.data}
          selectedProjectId={selectedProjectId}
        />
      ) : (
        <ProjectShell
          overview={null}
          viewer={undefined}
          workspaceLabel={`${activePageLabel} workspace`}
        >
          <Suspense fallback={<WorkspaceSuspenseFallback label="Loading workspace..." />}>
            {activeWorkspace === "overview" ? (
              <OverviewWorkspace
                inventory={projectInventory}
                tasks={taskController.tasks}
                onNavigate={(workspace) => {
                  if (selectedProjectId) navigation.openWorkspace(selectedProjectId, workspace);
                }}
              />
            ) : activeWorkspace === "data" ? (
              <DataConversionWorkspace
                baseUrl={baseUrl}
                projectId={selectedProjectId}
                inventory={projectInventory}
                onSelectedDataSeriesChange={onSelectedDataSeriesChange}
                onConversionRegistered={async () => {
                  await project.reload();
                }}
              />
            ) : activeWorkspace === "plan" ? (
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
                onOpenDataConversion={() =>
                  selectedProjectId && navigation.openWorkspace(selectedProjectId, "data")
                }
                onOpenEnvironment={() =>
                  selectedProjectId && navigation.openWorkspace(selectedProjectId, "settings")
                }
              />
            ) : activeWorkspace === "preprocessing" ? (
              <PreprocessingWorkspace
                baseUrl={baseUrl}
                projectId={selectedProjectId}
                dataState={projectInventory?.dataState ?? "raw_dicom"}
                inventory={projectInventory}
                hasPreprocessingRun={hasPreprocessingRun}
                preprocessingRunId={latestPreprocessingRunId}
                onOpenDataConversion={() =>
                  selectedProjectId && navigation.openWorkspace(selectedProjectId, "data")
                }
                onOpenToolsDrawer={() => app.setDrawerOpen(true)}
                onOpenRuns={(runId) => {
                  setSelectedTaskId(runId ?? null);
                  if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "runs");
                }}
              />
            ) : activeWorkspace === "runs" ? (
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
            ) : activeWorkspace === "qc" ? (
              <QCReportsWorkspace baseUrl={baseUrl} projectId={selectedProjectId} />
            ) : activeWorkspace === "results" ? (
              <ResultsWorkspace
                baseUrl={baseUrl}
                projectId={selectedProjectId}
                onSelectedArtifactChange={onSelectedArtifactChange}
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
              />
            ) : (
              <SettingsEnvironmentWorkspace
                baseUrl={baseUrl}
                projectId={selectedProjectId}
                rawdataDir={selectedProject?.data.metadata?.rawdata_dir}
                themePreference={appState.themePreference}
                onThemePreferenceChange={appState.setThemePreference}
                localePreference={appState.localePreference}
                onLocalePreferenceChange={appState.setLocalePreference}
                onReviewDraft={() => {
                  if (selectedProjectId) navigation.openWorkspace(selectedProjectId, "plan");
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
