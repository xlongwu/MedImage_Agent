import { Suspense } from "react";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ChatMessage } from "../../lib/types/assistant";
import type { ImagePlane, ImagePreview, ImageSources, ImageValidationReport } from "../../lib/types/image";
import type { ProjectDetail } from "../../lib/types/project";
import type { TaskEvent, TaskLogEntry, TaskStreamMessage } from "../../lib/types/task";
import type { PresetPlanDraft } from "../../types";
import type { ModelStatus } from "../../lib/types/model";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { AppController } from "../app/useAppController";
import type { ProjectController } from "../projects/useProjectController";
import type { TaskController } from "../tasks/useTaskController";
import type { ProjectInventory } from "../../lib/projectWorkflow";
import type { WorkflowTab } from "../../lib/projectWorkflow";
import {
  ProjectHeroPanel,
  ProjectList,
  ReadinessStatusStrip,
  RecommendedNextStepCard,
  TopBar,
  WorkflowTabs,
  WorkspaceSuspenseFallback,
} from "../dashboard/DashboardChrome";
import AdvancedModePanel from "../../components/workflow/AdvancedModePanel";
import PlanReviewConsole from "../../components/PlanReviewConsole";
import ProjectRunsPanel from "../../components/ProjectRunsPanel";
import { DataConversionWorkspace } from "../workspaces/DataConversionWorkspace";
import { PreprocessingWorkspace } from "../workspaces/PreprocessingWorkspace";
import { QCReportsWorkspace } from "../workspaces/QCReportsWorkspace";
import { SettingsEnvironmentWorkspace } from "../workspaces/SettingsEnvironmentWorkspace";
import { ProjectCreateResultPanel } from "./ProjectCreateResultPanel";
import { CompactTaskLog } from "../tasks/CompactTaskLog";
import { TaskDetailsPanel } from "../tasks/TaskDetailsPanel";
import { MedicalImageViewer } from "./MedicalImageViewer";
import { SecondaryToolsDrawer } from "../tools/SecondaryToolsDrawer";

export type AppShellViewProps = {
  mode: AppController["mode"];
  baseUrl: string;
  drawerOpen: boolean;
  selectedProjectId: string | null;
  project: { data: ProjectDetail };
  projectInventory: ProjectInventory | null;
  projectController: Pick<ProjectController, "projectCreateResult" | "projectCreateLoading" | "projectCreateError" | "setProjectCreateResult" | "setProjectCreateError" | "projects" | "projectsLoading" | "projectsError" | "handleDeleteProject" | "handleUploadData">;
  taskController: Pick<TaskController, "tasks" | "tasksLoading" | "tasksError" | "reloadTasks" | "selectedTask" | "taskEvents" | "taskEventsLoading" | "taskEventsError" | "reloadTaskEvents" | "taskDiagnosticsData" | "reloadTaskDiagnostics" | "taskStreamConnected" | "hasPreprocessingRun">;
  taskStream: { error: string | null };
  app: Pick<AppController, "notice" | "setNotice" | "activeWorkflow" | "setActiveWorkflow" | "handleScrollToPanel" | "setDrawerOpen" | "handleRunPipeline" | "handleApproveTask" | "handleGenerateAuditPackage" | "handleReconnectTaskStream" | "handleAssistantSubmit" | "handleQuickAction" | "pipelineLoading" | "presetPlanDraft">;
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
  setMode: AppController["setMode"];
  setExecutionMode: (mode: ExecutionMode) => void;
  onToggleDrawer: () => void;
  handleRunPipelineWrapper: () => Promise<void>;
  handleApproveSelectedTask: () => Promise<void>;
  handleGenerateAuditPackage: () => Promise<void>;
  handleReconnectTaskStream: () => void;
  handleAssistantSubmit: (event: React.FormEvent) => Promise<void>;
  handleQuickAction: (action: string) => void;
  onNewChat: () => void;
  selectedTaskId: string | null;
  setSelectedTaskId: (id: string | null) => void;
  activeTaskId: string | null;
  setActiveTaskId: (id: string | null) => void;
};

export function AppShellView({
  mode,
  baseUrl,
  drawerOpen,
  selectedProjectId,
  project,
  projectInventory,
  projectController,
  taskController,
  taskStream,
  app,
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
  setMode,
  setExecutionMode,
  onToggleDrawer,
  handleRunPipelineWrapper,
  handleApproveSelectedTask,
  handleGenerateAuditPackage,
  handleReconnectTaskStream,
  handleAssistantSubmit,
  handleQuickAction,
  onNewChat,
  selectedTaskId,
  setSelectedTaskId,
  activeTaskId,
  setActiveTaskId,
}: AppShellViewProps) {
  if (mode === "advanced") {
    return (
      <div className="windows-workstation advanced-workstation">
        <TopBar health={null} apiError={null} onRetry={() => {}} onToggleMode={() => setMode("dashboard")} modeLabel="Dashboard" />
        <Suspense fallback={<WorkspaceSuspenseFallback label="Loading advanced console..." />}>
          <AdvancedModePanel baseUrl={baseUrl} />
        </Suspense>
      </div>
    );
  }

  if (mode === "planner") {
    const selectedProject = selectedProjectId ? project : null;
    const projectDir = typeof selectedProject?.data.metadata?.project_dir === "string" ? selectedProject.data.metadata.project_dir : null;
    return (
      <div className="windows-workstation">
        <TopBar health={null} apiError={null} onRetry={() => {}} onToggleMode={() => setMode("dashboard")} modeLabel="Dashboard" />
        <Suspense fallback={<WorkspaceSuspenseFallback label="Loading planning tools..." />}>
          <PlanReviewConsole
            selectedProjectId={selectedProjectId}
            selectedProject={selectedProject?.data}
            projectConfigPath={selectedProject?.data.metadata?.project_config_path}
            datasetIndexPath={selectedProject?.data.metadata?.dataset_index_path}
            rawdataDir={selectedProject?.data.metadata?.rawdata_dir}
            initialPresetDraft={app.presetPlanDraft}
          />
          <ProjectRunsPanel baseUrl={baseUrl} projectId={selectedProjectId} projectDir={projectDir} />
        </Suspense>
      </div>
    );
  }

  return (
    <div className="windows-workstation">
      <TopBar health={null} apiError={null} onRetry={() => {}} onToggleMode={() => setMode("advanced")} modeLabel="Advanced Console" />
      <button onClick={() => setMode("planner")}>Plan Review</button>
      {app.notice ? (
        <div className="toast-line">
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
        <div className="api-banner stream-banner">
          Task stream disconnected: {taskStream.error}
          <button onClick={handleReconnectTaskStream}>Reconnect</button>
        </div>
      ) : null}
      <div className={`dashboard-frame ${drawerOpen ? "drawer-open" : "drawer-collapsed"}`}>
        <aside className="side-rail">
          <div className="brand-block">
            <div className="brand-glyph">M</div>
            <div>
              <strong>MedImage</strong>
              <span>Desktop workstation</span>
            </div>
          </div>
          <nav className="nav-stack" aria-label="Primary">
            {[
              ["Dashboard", "D"],
              ["Projects", "P"],
              ["Datasets", "S"],
              ["Pipeline", "N"],
              ["Results", "R"],
              ["Settings", "G"],
            ].map(([label, glyph], index) => (
              <button
                key={label}
                className={`nav-item ${index === 0 ? "active" : ""}`}
                onClick={() =>
                  label === "Settings"
                    ? setMode("advanced")
                    : app.setNotice(`${label} view is connected to the dashboard shell.`)
                }
                aria-current={index === 0 ? "page" : undefined}
              >
                <span>{glyph}</span>
                {label}
              </button>
            ))}
          </nav>
          <ProjectList
            projects={projectController.projects.data}
            selectedProjectId={selectedProjectId || project.data.id}
            loading={projectController.projectsLoading}
            error={projectController.projectsError}
            deletingProjectId={null}
            onSelect={setSelectedTaskId}
            onDelete={projectController.handleDeleteProject}
          />
          <div className="license-card">
            <div className="diamond-mark" />
            <strong>Research Plan</strong>
            <p>{project.data.subjects_count} subjects tracked locally</p>
            <div className="meter">
              <span style={{ width: `${Math.min(project.data.subjects_count, 200) / 2}%` }} />
            </div>
            <button onClick={() => setMode("advanced")}>Manage</button>
          </div>
        </aside>

        <main className="workflow-main">
          <section className="project-overview-grid" aria-label="Project overview">
            <ProjectHeroPanel inventory={projectInventory} />
            <RecommendedNextStepCard
              inventory={projectInventory}
              hasPreprocessingRun={taskController.hasPreprocessingRun}
              onPrimaryAction={() => {
                app.setActiveWorkflow(projectInventory?.dataState === "converted_bids" ? "preprocessing" : "data");
                window.setTimeout(() => app.handleScrollToPanel("workflow-workspace"), 0);
              }}
              onSecondaryAction={() => {
                app.setActiveWorkflow(projectInventory?.dataState === "converted_bids" ? "reports" : "data");
                window.setTimeout(() => app.handleScrollToPanel("workflow-workspace"), 0);
              }}
            />
          </section>

          <ReadinessStatusStrip inventory={projectInventory} health={null} hasPreprocessingRun={taskController.hasPreprocessingRun} />

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
            onSequenceChange={image.setSequence}
            onPlaneChange={image.setPlane}
            onSubjectChange={image.setSelectedSubjectId}
            onSliceChange={image.setSliceIndex}
          />

          <WorkflowTabs activeTab={app.activeWorkflow as WorkflowTab} onChange={app.setActiveWorkflow} />

          <section
            id="workflow-workspace"
            className="workflow-workspace"
            role="tabpanel"
            aria-live="polite"
            aria-labelledby={`workflow-tab-${app.activeWorkflow}`}
          >
            <Suspense fallback={<WorkspaceSuspenseFallback label="Loading workspace..." />}>
              {app.activeWorkflow === "data" ? (
                <DataConversionWorkspace baseUrl={baseUrl} projectId={selectedProjectId} inventory={projectInventory} />
              ) : app.activeWorkflow === "preprocessing" ? (
                <PreprocessingWorkspace
                  projectId={selectedProjectId}
                  dataState={projectInventory?.dataState ?? "raw_dicom"}
                  inventory={projectInventory}
                  hasPreprocessingRun={taskController.hasPreprocessingRun}
                  onOpenDataConversion={() => app.setActiveWorkflow("data")}
                  onOpenToolsDrawer={() => app.setDrawerOpen(true)}
                />
              ) : app.activeWorkflow === "reports" ? (
                <QCReportsWorkspace baseUrl={baseUrl} projectId={selectedProjectId} />
              ) : (
                <SettingsEnvironmentWorkspace
                  baseUrl={baseUrl}
                  projectId={selectedProjectId}
                  onReviewDraft={(draft: PresetPlanDraft) => {
                    app.setActiveWorkflow("settings" as WorkflowTab);
                    app.setNotice("Preset draft loaded into Plan Review Console. Review and save before dry-run.");
                  }}
                />
              )}
            </Suspense>
          </section>

          <CompactTaskLog
            tasks={taskController.tasks}
            loading={taskController.tasksLoading}
            error={taskController.tasksError}
            onRetry={taskController.reloadTasks}
            selectedTaskId={selectedTaskId}
            onSelectTask={setSelectedTaskId}
          />
          <TaskDetailsPanel
            task={taskController.selectedTask}
            events={taskController.taskEvents}
            diagnostics={taskController.taskDiagnosticsData}
            loading={taskController.taskEventsLoading}
            error={taskController.taskEventsError}
            streamConnected={taskController.taskStreamConnected}
            approvalName={approval.taskApprovalName}
            auditPackage={approval.auditPackage as import("../../lib/types/task").TaskAuditPackage | null}
            auditLoading={approval.auditLoading}
            onApprovalNameChange={approval.setTaskApprovalName}
            onApprove={handleApproveSelectedTask}
            onGenerateAudit={handleGenerateAuditPackage}
            onRetry={taskController.reloadTaskEvents}
            onReconnect={handleReconnectTaskStream}
          />
        </main>
      </div>

      <SecondaryToolsDrawer
        isOpen={drawerOpen}
        onToggle={onToggleDrawer}
        onSetMode={setMode}
        project={project.data}
        model={model}
        dataset={dataset}
        executionMode={executionMode}
        externalSmokeApprovedRun={externalSmokeApprovedRun}
        externalSmokeApprovedBy={externalSmokeApprovedBy}
        assistantMessages={assistant.messages}
        assistantInput={assistant.input}
        assistantLoading={assistant.loading}
        assistantError={assistant.error}
        pipelineLoading={app.pipelineLoading}
        onExecutionModeChange={setExecutionMode}
        onExternalSmokeApprovedRunChange={setExternalSmokeApprovedRun}
        onExternalSmokeApprovedByChange={setExternalSmokeApprovedBy}
        onConfigure={() => setMode("advanced")}
        onAssistantInput={assistant.setInput}
        onAssistantSubmit={handleAssistantSubmit}
        onNewChat={onNewChat}
        onQuickAction={handleQuickAction}
        projectId={selectedProjectId}
      />
    </div>
  );
}
