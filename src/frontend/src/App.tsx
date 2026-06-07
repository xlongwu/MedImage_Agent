import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { createProjectFromDirectory, DEFAULT_API_BASE, getHealth } from "./api";
import AdvancedModePanel from "./components/workflow/AdvancedModePanel";
import BidsValidationPanel from "./components/BidsValidationPanel";
import ConversionDryRunPanel from "./components/ConversionDryRunPanel";
import DataReadinessPanel from "./components/DataReadinessPanel";
import BoldReferenceReadinessPanel from "./components/BoldReferenceReadinessPanel";
import EnvironmentHealthPanel from "./components/EnvironmentHealthPanel";
import SpmRealignDryRunPanel from "./components/SpmRealignDryRunPanel";
import SpmRealignWrapperSkeletonPanel from "./components/SpmRealignWrapperSkeletonPanel";
import MotionMetricsDraftPanel from "./components/MotionMetricsDraftPanel";
import NiftiQcSnapshotPanel from "./components/NiftiQcSnapshotPanel";
import QcDashboardSummaryPanel from "./components/QcDashboardSummaryPanel";
import MotionQcReadinessPanel from "./components/MotionQcReadinessPanel";
import RsfmriQcPlanningReportPanel from "./components/RsfmriQcPlanningReportPanel";
import RsfmriPresetPanel from "./components/RsfmriPresetPanel";
import type { PresetPlanDraft } from "./types";
import PlanReviewConsole from "./components/PlanReviewConsole";
import ProjectRunsPanel from "./components/ProjectRunsPanel";
import { useDatasetSummary } from "./hooks/useDatasetSummary";
import { useImagePreview } from "./hooks/useImagePreview";
import { useImageSources } from "./hooks/useImageSources";
import { useImageValidation } from "./hooks/useImageValidation";
import { useModelStatus } from "./hooks/useModelStatus";
import { useProject, useProjects } from "./hooks/useProjects";
import { useProjectOverview } from "./hooks/useProjectOverview";
import { useRunPipeline } from "./hooks/useRunPipeline";
import { useTaskDiagnostics } from "./hooks/useTaskDiagnostics";
import { useTaskEvents } from "./hooks/useTaskEvents";
import { useTasks } from "./hooks/useTasks";
import { useTaskStream } from "./hooks/useTaskStream";
import { approveTask, generateTaskAuditPackage, getTask, sendAssistantMessage } from "./lib/api";
import { fallbackChat } from "./lib/mockData";
import type { ChatMessage } from "./lib/types/assistant";
import type { DatasetSummary } from "./lib/types/dataset";
import type { ImagePlane, ImagePreview, ImageSourceFile, ImageSources, ImageValidationReport } from "./lib/types/image";
import type { ModelStatus } from "./lib/types/model";
import type { ExecutionMode } from "./lib/types/pipeline";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "./lib/types/project";
import type { TaskAuditPackage, TaskDiagnostics, TaskEvent, TaskLogEntry, TaskStatus, TaskStreamMessage } from "./lib/types/task";
import type { ProjectCreateResponse } from "./types";

const navItems = [
  ["Dashboard", "D"],
  ["Projects", "P"],
  ["Datasets", "S"],
  ["Pipeline", "N"],
  ["Results", "R"],
  ["Settings", "G"],
];

const quickActions = [
  { title: "New Pipeline", subtitle: "Create auditable workflow", kind: "flow", action: "new-pipeline" },
  { title: "Upload Data", subtitle: "Create project from BIDS directory", kind: "cloud", action: "upload-data" },
  { title: "Run Pipeline", subtitle: "Start analysis", kind: "play", action: "run-pipeline" },
  { title: "View Results", subtitle: "Open latest report", kind: "chart", action: "view-results" },
];

function directoryBasename(path: string): string {
  const normalized = path.trim().replace(/[\\/]+$/, "");
  const parts = normalized.split(/[\\/]/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : "New Project";
}

function diagnosticNumber(
  diagnostics: Record<string, unknown>,
  key: string
): number {
  const value = Number(diagnostics[key]);
  return Number.isFinite(value) ? value : 0;
}

function projectSummaryFromCreateResult(result: ProjectCreateResponse): ProjectSummary {
  return {
    id: result.project_id,
    name: result.project_name,
    study_id: result.project_id,
    modality: "rs-fMRI",
    created_date: new Date().toLocaleDateString(),
    subjects_count: diagnosticNumber(result.diagnostics, "subjects_total"),
    current_pipeline_id: "not-selected",
  };
}

export default function App() {
  const baseUrl = DEFAULT_API_BASE;
  const [mode, setMode] = useState<"dashboard" | "advanced" | "planner">("dashboard");
  const [health, setHealth] = useState<boolean | null>(null);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");
  const [presetPlanDraft, setPresetPlanDraft] = useState<PresetPlanDraft | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string | null>(null);
  const [sequence, setSequence] = useState("T1");
  const [plane, setPlane] = useState<ImagePlane>("axial");
  const [sliceIndex, setSliceIndex] = useState<number | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("simulated");
  const [externalSmokeApprovedRun, setExternalSmokeApprovedRun] = useState(false);
  const [externalSmokeApprovedBy, setExternalSmokeApprovedBy] = useState("");
  const [taskApprovalName, setTaskApprovalName] = useState("");
  const [auditPackage, setAuditPackage] = useState<TaskAuditPackage | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>(fallbackChat);
  const [projectCreateLoading, setProjectCreateLoading] = useState(false);
  const [projectCreateError, setProjectCreateError] = useState("");
  const [projectCreateResult, setProjectCreateResult] = useState<ProjectCreateResponse | null>(null);

  const projects = useProjects();
  const project = useProject(selectedProjectId);
  const selectedProjectForPlanReview =
    selectedProjectId &&
    !project.fromFallback &&
    project.data.id === selectedProjectId
      ? project.data
      : null;
  const selectedProjectMetadata = selectedProjectForPlanReview?.metadata;
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
  const updateTaskFromStream = tasks.updateTaskFromStream;

  useEffect(() => {
    checkHealth();
  }, []);

  useEffect(() => {
    if (!projects.data.length) {
      return;
    }
    const selectedProjectExists = selectedProjectId
      ? projects.data.some((item) => item.id === selectedProjectId)
      : false;
    if (!selectedProjectId || (!projects.fromFallback && !selectedProjectExists)) {
      setSelectedProjectId(projects.data[0].id);
    }
  }, [projects.data, projects.fromFallback, selectedProjectId]);

  useEffect(() => {
    if (project.data.sequences.length && !project.data.sequences.includes(sequence)) {
      setSequence(project.data.sequences[0]);
    }
  }, [project.data.sequences, sequence]);

  useEffect(() => {
    const subjects = imageSources.data.subjects;
    if (!subjects.length) {
      return;
    }
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
      setNotice(message.message);
      if ((message.status === "completed" || message.status === "failed") && selectedTaskId === message.task_id) {
        window.setTimeout(() => {
          taskEvents.reload();
          taskDiagnostics.reload();
        }, 250);
      }
    },
    [selectedTaskId, taskDiagnostics.reload, taskEvents.reload, taskEvents.setData, updateTaskFromStream]
  );
  const taskStream = useTaskStream(activeTaskId, handleTaskMessage);
  const selectedTask = useMemo(
    () => tasks.data.find((task) => task.id === selectedTaskId) ?? null,
    [selectedTaskId, tasks.data]
  );

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

  async function checkHealth() {
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
  }

  async function handleRunPipeline() {
    const approvedExternalSmoke = executionMode === "external_smoke" && externalSmokeApprovedRun;
    if (approvedExternalSmoke && !externalSmokeApprovedBy.trim()) {
      setNotice("Approved External Smoke requires an approved-by name.");
      return;
    }
    const response = await pipeline.start({
      project_id: project.data.id,
      pipeline_id: project.data.current_pipeline_id,
      model_id: project.data.current_model_id,
      input_sequences: project.data.sequences,
      output_type: "segmentation_metrics",
      execution_mode: executionMode,
      external_smoke_mode: approvedExternalSmoke ? "approved_smoke" : "manual_package",
      approved: approvedExternalSmoke,
      approved_by: approvedExternalSmoke ? externalSmokeApprovedBy.trim() : null,
      dpabi_function: "y_Smooth",
    });
    if (!response) {
      setNotice(pipeline.error || "Failed to start pipeline");
      return;
    }
    try {
      const detail = await getTask(response.task_id);
      tasks.upsertTask(detail);
    } catch {
      await tasks.reload();
    }
    setActiveTaskId(response.task_id);
    setSelectedTaskId(response.task_id);
    setNotice(`Pipeline started: ${response.task_id}`);
  }

  async function handleApproveSelectedTask() {
    if (!selectedTaskId) {
      setNotice("Select an External Smoke task before approving a real smoke run.");
      return;
    }
    if (!taskApprovalName.trim()) {
      setNotice("Approval requires an approved-by name.");
      return;
    }
    try {
      const response = await approveTask(selectedTaskId, {
        approved: true,
        approved_by: taskApprovalName.trim(),
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
      setNotice(response.message);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    }
  }

  async function handleGenerateAuditPackage() {
    if (!selectedTaskId) {
      setNotice("Select a task before generating an audit package.");
      return;
    }
    setAuditLoading(true);
    try {
      const response = await generateTaskAuditPackage(selectedTaskId);
      setAuditPackage(response);
      setNotice(`Audit package generated: ${response.report_path}`);
    } catch (err) {
      setNotice(err instanceof Error ? err.message : String(err));
    } finally {
      setAuditLoading(false);
    }
  }

  function handleReconnectTaskStream() {
    const nextTaskId = activeTaskId || selectedTaskId;
    if (!nextTaskId) {
      setNotice("Select a task before reconnecting the task stream.");
      return;
    }
    setActiveTaskId(null);
    window.setTimeout(() => setActiveTaskId(nextTaskId), 0);
  }

  async function handleUploadData() {
    setProjectCreateError("");
    setProjectCreateResult(null);
    let selectedPath: string | null = null;
    try {
      if (window.medimage?.selectDirectory) {
        selectedPath = await window.medimage.selectDirectory();
      } else {
        selectedPath = window.prompt("Enter a local BIDS / rawdata directory path");
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setProjectCreateError(message);
      setNotice(`Directory selection failed: ${message}`);
      return;
    }

    if (!selectedPath?.trim()) {
      setNotice("Project creation cancelled");
      return;
    }

    const defaultProjectName = directoryBasename(selectedPath);
    const projectName = window.prompt("Project name", defaultProjectName);
    if (projectName === null) {
      setNotice("Project creation cancelled");
      return;
    }
    if (!projectName.trim()) {
      setProjectCreateError("Project name is required.");
      setNotice("Project creation failed: project name is required.");
      return;
    }

    setProjectCreateLoading(true);
    setProjectCreateResult(null);
    try {
      const result = await createProjectFromDirectory(baseUrl, {
        project_name: projectName.trim(),
        rawdata_dir: selectedPath.trim(),
        copy_mode: "reference",
        run_inspection: true,
        overwrite: false,
      });

      const refreshedProjects = await projects.reload();
      const projectListSynced = Boolean(
        refreshedProjects?.some((item) => item.id === result.project_id)
      );
      const syncWarning =
        "Project was created, but the project list has not synchronized yet. Showing a temporary entry.";
      const displayedResult = projectListSynced
        ? result
        : {
            ...result,
            warnings: [...result.warnings, syncWarning],
          };
      if (!projectListSynced) {
        const temporaryProject = projectSummaryFromCreateResult(result);
        projects.setData((current) => [
          temporaryProject,
          ...current.filter((item) => item.id !== result.project_id),
        ]);
      }
      setSelectedProjectId(result.project_id);
      setSelectedSubjectId(null);
      setSliceIndex(null);
      setProjectCreateResult(displayedResult);
      const status = String(result.diagnostics.status ?? "UNKNOWN");
      const warningText = displayedResult.warnings.length
        ? ` with ${displayedResult.warnings.length} warning(s)`
        : "";
      setNotice(`Project created: ${result.project_name} (${status})${warningText}`);
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      setProjectCreateError(message);
      setNotice(`Project creation failed: ${message}`);
    } finally {
      setProjectCreateLoading(false);
    }
  }

  async function handleViewResults() {
    const latest = tasks.data.find((task) => task.result_path);
    if (!latest?.result_path) {
      setNotice("No completed result path is available yet.");
      return;
    }
    if (window.medimage?.openExternalPath) {
      const opened = await window.medimage.openExternalPath(latest.result_path);
      setNotice(opened ? `Opened ${latest.result_path}` : `Result path: ${latest.result_path}`);
      return;
    }
    setNotice(`Result path: ${latest.result_path}`);
  }

  async function handleQuickAction(action: string) {
    if (action === "new-pipeline") {
      setNotice("Pipeline builder is planned; current version keeps audited presets only.");
    } else if (action === "upload-data") {
      await handleUploadData();
    } else if (action === "run-pipeline") {
      await handleRunPipeline();
    } else if (action === "view-results") {
      await handleViewResults();
    }
  }

  async function handleAssistantSubmit(event: FormEvent) {
    event.preventDefault();
    const message = assistantInput.trim();
    if (!message) {
      return;
    }
    setAssistantInput("");
    setAssistantError("");
    setAssistantLoading(true);
    setChatMessages((current) => [...current, { role: "user", text: message }]);
    try {
      const response = await sendAssistantMessage({ project_id: project.data.id, message });
      setChatMessages((current) => [...current, { role: "assistant", text: response.reply }]);
    } catch (err) {
      const friendly = err instanceof Error ? err.message : String(err);
      setAssistantError(friendly);
      setChatMessages((current) => [
        ...current,
        { role: "assistant", text: "I could not reach the local assistant endpoint. Please retry after the backend reconnects." },
      ]);
    } finally {
      setAssistantLoading(false);
    }
  }

  if (mode === "advanced") {
    return (
      <div className="windows-workstation advanced-workstation">
        <TopBar
          health={health}
          apiError={apiError}
          onRetry={checkHealth}
          onToggleMode={() => setMode("dashboard")}
          modeLabel="Dashboard"
        />
        <AdvancedModePanel baseUrl={baseUrl} />
      </div>
    );
  }

  if (mode === "planner") {
    return (
      <div className="windows-workstation">
        <TopBar
          health={health}
          apiError={apiError}
          onRetry={checkHealth}
          onToggleMode={() => setMode("dashboard")}
          modeLabel="Dashboard"
        />
        <PlanReviewConsole
          selectedProjectId={selectedProjectId}
          selectedProject={selectedProjectForPlanReview}
          projectConfigPath={selectedProjectMetadata?.project_config_path}
          datasetIndexPath={selectedProjectMetadata?.dataset_index_path}
          rawdataDir={selectedProjectMetadata?.rawdata_dir}
          initialPresetDraft={presetPlanDraft}
        />
        <ProjectRunsPanel
          baseUrl={baseUrl}
          projectId={selectedProjectId}
          projectDir={
            typeof selectedProjectMetadata?.project_dir === "string"
              ? selectedProjectMetadata.project_dir
              : null
          }
        />
      </div>
    );
  }

  return (
    <div className="windows-workstation">
      <TopBar
        health={health}
        apiError={apiError}
        onRetry={checkHealth}
        onToggleMode={() => setMode("advanced")}
        modeLabel="Advanced Console"
      />
      <button onClick={() => setMode("planner")}>Plan Review</button>
      {notice ? <div className="toast-line">{notice}<button onClick={() => setNotice("")}>Dismiss</button></div> : null}
      <ProjectCreateResultPanel
        result={projectCreateResult}
        loading={projectCreateLoading}
        error={projectCreateError}
        onDismiss={() => {
          setProjectCreateResult(null);
          setProjectCreateError("");
        }}
      />
      {taskStream.error ? (
        <div className="api-banner stream-banner">
          Task stream disconnected: {taskStream.error}
          <button onClick={handleReconnectTaskStream}>Reconnect</button>
        </div>
      ) : null}
      <div className="dashboard-frame">
        <aside className="side-rail">
          <div className="brand-block">
            <div className="brand-glyph">M</div>
            <div>
              <strong>MedImage</strong>
              <span>Desktop workstation</span>
            </div>
          </div>
          <nav className="nav-stack" aria-label="Primary">
            {navItems.map(([label, glyph], index) => (
              <button
                key={label}
                className={`nav-item ${index === 0 ? "active" : ""}`}
                onClick={() => (label === "Settings" ? setMode("advanced") : setNotice(`${label} view is connected to the dashboard shell.`))}
              >
                <span>{glyph}</span>
                {label}
              </button>
            ))}
          </nav>
          <ProjectList
            projects={projects.data}
            selectedProjectId={selectedProjectId || project.data.id}
            loading={projects.loading}
            error={projects.error}
            onSelect={setSelectedProjectId}
          />
          <div className="license-card">
            <div className="diamond-mark" />
            <strong>Research Plan</strong>
            <p>{project.data.subjects_count} subjects tracked locally</p>
            <div className="meter"><span style={{ width: `${Math.min(project.data.subjects_count, 200) / 2}%` }} /></div>
            <button onClick={() => setMode("advanced")}>Manage</button>
          </div>
        </aside>

        <main className="workspace-grid">
          <MedicalImageViewer
            project={project.data}
            sequence={sequence}
            plane={plane}
            sequenceOptions={sequenceOptions}
            imageSources={imageSources.data}
            validation={imageValidation.data}
            subjectId={selectedSubjectId}
            preview={imagePreview.data}
            sourceFile={selectedImageSource}
            loading={imagePreview.loading}
            onSequenceChange={setSequence}
            onPlaneChange={setPlane}
            onSubjectChange={setSelectedSubjectId}
            onSliceChange={setSliceIndex}
          />

          <StudyOverviewCard overview={overview.data} loading={overview.loading} error={overview.error} />

          <DatasetSummaryCard summary={dataset.data} loading={dataset.loading} error={dataset.error} />

          <DataReadinessPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <BidsValidationPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <ConversionDryRunPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <EnvironmentHealthPanel baseUrl={baseUrl} />

          <QcDashboardSummaryPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <SpmRealignDryRunPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <SpmRealignWrapperSkeletonPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <NiftiQcSnapshotPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <BoldReferenceReadinessPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <MotionQcReadinessPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <MotionMetricsDraftPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <RsfmriQcPlanningReportPanel baseUrl={baseUrl} projectId={selectedProjectId} />

          <RsfmriPresetPanel
            baseUrl={baseUrl}
            projectId={selectedProjectId}
            onReviewDraft={(draft) => {
              setPresetPlanDraft(draft);
              setMode("planner");
              setNotice("Preset draft loaded into Plan Review Console. Review and save before dry-run.");
            }}
          />

          <ModelCard model={model.data} loading={model.loading} error={model.error} />
          <MetricCard
            title="Recent Tasks"
            values={[
              [String(taskCounts.completed), "Completed"],
              [String(taskCounts.running), "Running"],
              [String(taskCounts.failed), "Failed"],
            ]}
            tone="amber"
            note={tasks.fromFallback ? "fallback" : "live"}
          />

          <TaskLogTable
            tasks={tasks.data}
            loading={tasks.loading}
            error={tasks.error}
            onRetry={tasks.reload}
            selectedTaskId={selectedTaskId}
            onSelectTask={setSelectedTaskId}
          />
          <TaskDetailsPanel
            task={selectedTask}
            events={taskEvents.data}
            diagnostics={taskDiagnostics.data}
            loading={taskEvents.loading}
            error={taskEvents.error}
            streamConnected={taskStream.connected}
            approvalName={taskApprovalName}
            auditPackage={auditPackage}
            auditLoading={auditLoading}
            onApprovalNameChange={setTaskApprovalName}
            onApprove={handleApproveSelectedTask}
            onGenerateAudit={handleGenerateAuditPackage}
            onRetry={taskEvents.reload}
            onReconnect={handleReconnectTaskStream}
          />
        </main>

        <aside className="right-rail">
          <AssistantPanel
            messages={chatMessages}
            input={assistantInput}
            loading={assistantLoading}
            error={assistantError}
            onInput={setAssistantInput}
            onSubmit={handleAssistantSubmit}
            onNewChat={() => setChatMessages(fallbackChat)}
          />

          <PipelineSettingsCard
            project={project.data}
            model={model.data}
            dataset={dataset.data}
            executionMode={executionMode}
            externalSmokeApprovedRun={externalSmokeApprovedRun}
            externalSmokeApprovedBy={externalSmokeApprovedBy}
            onExecutionModeChange={setExecutionMode}
            onExternalSmokeApprovedRunChange={setExternalSmokeApprovedRun}
            onExternalSmokeApprovedByChange={setExternalSmokeApprovedBy}
            onConfigure={() => setMode("advanced")}
          />

          <section className="quick-card">
            <div className="card-title">Quick Actions</div>
            <div className="quick-grid">
              {quickActions.map((item) => (
                <button
                  key={item.title}
                  className={`quick-action ${item.kind}`}
                  onClick={() => handleQuickAction(item.action)}
                  disabled={pipeline.loading && item.action === "run-pipeline"}
                >
                  <span>{item.title.slice(0, 1)}</span>
                  <strong>{item.action === "run-pipeline" && pipeline.loading ? "Running..." : item.title}</strong>
                  <small>{item.subtitle}</small>
                </button>
              ))}
            </div>
          </section>
        </aside>
      </div>
    </div>
  );
}

function TopBar({
  health,
  apiError,
  onRetry,
  onToggleMode,
  modeLabel,
}: {
  health: boolean | null;
  apiError: string;
  onRetry: () => void;
  onToggleMode: () => void;
  modeLabel: string;
}) {
  return (
    <>
      <header className="topbar">
        <div className="window-caption">
          <span className="app-spark">M</span>
          <strong>MedImage Agent</strong>
        </div>
        <label className="search-box">
          <span>Search</span>
          <input aria-label="Search" placeholder="projects, datasets, studies..." />
          <kbd>Ctrl K</kbd>
        </label>
        <div className="top-actions">
          <span className={`backend-chip ${health ? "online" : health === false ? "offline" : ""}`}>
            {health === null ? "Checking" : health ? "Backend Connected" : "Backend Offline"}
          </span>
          {!health ? <button onClick={onRetry}>Retry</button> : null}
          <button onClick={onToggleMode}>{modeLabel}</button>
          <div className="profile-chip">
            <span>AM</span>
            <div><strong>Dr. Alex Morgan</strong><small>Local lab desktop</small></div>
          </div>
        </div>
      </header>
      {apiError ? <div className="api-banner">{apiError}</div> : null}
    </>
  );
}

function ProjectList({
  projects,
  selectedProjectId,
  loading,
  error,
  onSelect,
}: {
  projects: ProjectSummary[];
  selectedProjectId: string;
  loading: boolean;
  error: string;
  onSelect: (id: string) => void;
}) {
  return (
    <div className="project-stack">
      <div className="panel-kicker">Recent projects {loading ? "(loading)" : error ? "(fallback)" : ""}</div>
      {projects.map((item) => (
        <button
          key={item.id}
          className={`project-pill ${item.id === selectedProjectId ? "selected" : ""}`}
          onClick={() => onSelect(item.id)}
        >
          {item.name}
          {item.id === selectedProjectId ? <span /> : null}
        </button>
      ))}
    </div>
  );
}

function ProjectCreateResultPanel({
  result,
  loading,
  error,
  onDismiss,
}: {
  result: ProjectCreateResponse | null;
  loading: boolean;
  error: string;
  onDismiss: () => void;
}) {
  if (!result && !loading && !error) {
    return null;
  }

  const diagnostics = result?.diagnostics ?? {};
  const status = String(diagnostics.status ?? "UNKNOWN");
  return (
    <section className="task-detail-panel">
      <div className="card-row">
        <div>
          <div className="card-title">
            {loading ? "Creating project..." : error ? "Project creation failed" : `Project created: ${result?.project_name}`}
          </div>
          <span>{loading ? "Inspecting the selected BIDS/rawdata directory" : `Status: ${status}`}</span>
        </div>
        <div className="detail-actions">
          {!loading ? <button onClick={onDismiss}>Dismiss</button> : null}
        </div>
      </div>

      {error ? <div className="errorBox">{error}</div> : null}

      {result ? (
        <>
          <div className="detail-grid">
            <div><span>Status</span><strong>{status}</strong></div>
            <div><span>Subjects</span><strong>{diagnosticNumber(diagnostics, "subjects_total")}</strong></div>
            <div><span>Complete</span><strong>{diagnosticNumber(diagnostics, "subjects_complete")}</strong></div>
            <div><span>Warning</span><strong>{diagnosticNumber(diagnostics, "subjects_warning")}</strong></div>
            <div><span>Incomplete</span><strong>{diagnosticNumber(diagnostics, "subjects_incomplete")}</strong></div>
          </div>

          <div className="event-list">
            <div className="event-row"><span>Project directory</span><p>{result.project_dir}</p></div>
            <div className="event-row"><span>Rawdata directory</span><p>{result.rawdata_dir}</p></div>
            <div className="event-row"><span>Dataset index</span><p>{result.dataset_index_path || "Not generated"}</p></div>
          </div>

          {result.warnings.length ? (
            <div className="diagnostic-list">
              {result.warnings.map((warning, index) => (
                <div className="diagnostic-item warning" key={`${warning}-${index}`}>
                  <span>Warning</span>
                  <p>{warning}</p>
                </div>
              ))}
            </div>
          ) : null}

          <div className="tool-result-list">
            <div className="panel-kicker">Next actions</div>
            {result.next_actions.map((action, index) => (
              <div className="tool-result-row" key={`${action}-${index}`}>
                <strong>{index + 1}. {action}</strong>
              </div>
            ))}
          </div>
        </>
      ) : null}
    </section>
  );
}

function MedicalImageViewer({
  project,
  sequence,
  plane,
  sequenceOptions,
  imageSources,
  validation,
  subjectId,
  preview,
  sourceFile,
  loading,
  onSequenceChange,
  onPlaneChange,
  onSubjectChange,
  onSliceChange,
}: {
  project: ProjectDetail;
  sequence: string;
  plane: ImagePlane;
  sequenceOptions: string[];
  imageSources: ImageSources;
  validation: ImageValidationReport;
  subjectId: string | null;
  preview: ImagePreview;
  sourceFile: ImageSourceFile | null;
  loading: boolean;
  onSequenceChange: (sequence: string) => void;
  onPlaneChange: (plane: ImagePlane) => void;
  onSubjectChange: (subjectId: string) => void;
  onSliceChange: (sliceIndex: number) => void;
}) {
  const currentSlice = preview.slice_index ?? 0;
  const sliceCount = preview.slice_count ?? 0;
  const activePlane = plane;
  const planeOptions: Array<{ axis: string; value: ImagePlane; label: string }> = [
    { axis: "S", value: "sagittal", label: "Sagittal" },
    { axis: "A", value: "axial", label: "Axial" },
    { axis: "C", value: "coronal", label: "Coronal" },
  ];
  const planeLabel = planeOptions.find((item) => item.value === activePlane)?.label ?? "Axial";
  const dimensions = sourceFile?.dimensions?.length ? sourceFile.dimensions : preview.dimensions ?? [];
  const spacing = sourceFile?.voxel_spacing ?? [];
  const sourceSummary = sourceFile?.relative_path ?? preview.source_path ?? preview.message;
  const visibleValidationIssues = validation.issues.slice(0, 3);
  return (
    <section className="viewer-card">
      <div className="viewer-tools">
        <select
          className="scan-select subject-select"
          value={subjectId || ""}
          onChange={(event) => onSubjectChange(event.target.value)}
          disabled={!imageSources.subjects.length}
          aria-label="Subject"
        >
          {imageSources.subjects.length ? (
            imageSources.subjects.map((item) => (
              <option key={item.subject_id} value={item.subject_id}>{item.subject_id}</option>
            ))
          ) : (
            <option value="">No sources</option>
          )}
        </select>
        <select className="scan-select" value={sequence} onChange={(event) => onSequenceChange(event.target.value)}>
          {(sequenceOptions.length ? sequenceOptions : project.sequences).map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </select>
        <button aria-label="Window level">WL</button>
        <button aria-label="Fullscreen">[]</button>
        <button aria-label="More">...</button>
      </div>
      <div className="scan-thumbs">
        {planeOptions.map((item) => (
          <button
            key={item.value}
            type="button"
            className={`scan-thumb ${activePlane === item.value ? "active" : ""}`}
            onClick={() => onPlaneChange(item.value)}
            aria-label={`${item.label} plane`}
            title={`${item.label} plane`}
          >
            <MiniScan axis={item.axis} />
          </button>
        ))}
      </div>
      <div className="scan-canvas">
        {preview.preview_url ? (
          <img className="brain-preview-img" src={preview.preview_url} alt={`${sequence} preview`} />
        ) : (
          <BrainScan />
        )}
        <div className="slice-rule"><span>S</span><i /><span>I</span></div>
        <div className="scan-count">{loading ? "loading" : sliceCount ? `${currentSlice + 1} / ${sliceCount}` : "126 / 256"}</div>
      </div>
      <div className="preview-status">
        <strong>{preview.source === "nifti" ? `${planeLabel} NIfTI preview` : "Fallback preview"}</strong>
        <span>
          {preview.source === "nifti"
            ? `slice ${(preview.slice_index ?? 0) + 1} / ${preview.slice_count ?? "?"}`
            : preview.message}
        </span>
        <div className="preview-meta">
          <span>Dims <b>{dimensions.length ? dimensions.join(" x ") : "unknown"}</b></span>
          <span>Spacing <b>{spacing.length ? spacing.slice(0, 3).join(" x ") : "pending"}</b></span>
          <span>Source <b>{sourceSummary}</b></span>
        </div>
        <div className={`validation-checklist ${validation.status}`}>
          <span>Validation <b>{validation.status}</b></span>
          {visibleValidationIssues.length ? (
            visibleValidationIssues.map((issue) => (
              <span key={`${issue.code}-${issue.subject_id ?? "project"}-${issue.sequence ?? "all"}`}>
                {issue.severity}: <b>{issue.message}</b>
              </span>
            ))
          ) : (
            <span><b>No checklist issues</b></span>
          )}
        </div>
        {sliceCount > 1 ? (
          <input
            className="slice-slider"
            type="range"
            min={0}
            max={sliceCount - 1}
            value={currentSlice}
            onChange={(event) => onSliceChange(Number(event.target.value))}
            aria-label="Slice index"
          />
        ) : null}
      </div>
      <div className="viewer-dock">
        {["Pan", "Cross", "Zoom", "WL", "Grid", "Measure", "Expand"].map((item, index) => (
          <button key={item} className={index === 0 ? "selected" : ""}>{item.slice(0, 2)}</button>
        ))}
      </div>
    </section>
  );
}

function BrainScan() {
  return (
    <svg className="brain-scan" viewBox="0 0 760 420" role="img" aria-label="Synthetic MRI scan preview">
      <defs>
        <radialGradient id="brainFill" cx="48%" cy="43%" r="62%">
          <stop offset="0%" stopColor="#c7ced8" />
          <stop offset="50%" stopColor="#7d8796" />
          <stop offset="100%" stopColor="#151a22" />
        </radialGradient>
        <filter id="softGlow">
          <feGaussianBlur stdDeviation="1.5" />
        </filter>
      </defs>
      <rect width="760" height="420" fill="#05070b" />
      <path d="M196 289 C129 281 91 243 84 196 C76 138 113 86 177 70 C257 49 357 63 429 111 C498 157 517 229 482 286 C448 341 361 363 281 337 C251 327 227 298 196 289 Z" fill="url(#brainFill)" stroke="#e7edf8" strokeOpacity=".58" strokeWidth="4" />
      <path d="M152 220 C218 206 266 201 334 219 C383 232 425 259 465 295" fill="none" stroke="#06080d" strokeWidth="18" strokeLinecap="round" opacity=".72" />
      <path d="M168 142 C252 105 355 116 421 173" fill="none" stroke="#edf3fb" strokeWidth="7" opacity=".45" filter="url(#softGlow)" />
      <path d="M207 101 C227 145 222 190 187 235" fill="none" stroke="#121723" strokeWidth="11" opacity=".7" />
      <path d="M312 83 C282 146 287 208 343 259" fill="none" stroke="#e8eef7" strokeWidth="5" opacity=".36" />
      <path d="M411 132 C372 174 351 216 363 270" fill="none" stroke="#0a0d14" strokeWidth="12" opacity=".62" />
      <path d="M481 219 C541 224 584 251 614 298 C557 304 514 293 482 266" fill="#101620" stroke="#d6dfeb" strokeOpacity=".36" strokeWidth="3" />
      <path d="M623 300 C653 319 684 330 720 331" stroke="#eff4fb" strokeWidth="5" opacity=".35" />
      <g opacity=".28">
        {Array.from({ length: 9 }).map((_, index) => (
          <line key={index} x1={82 + index * 68} y1="32" x2={64 + index * 68} y2="392" stroke="#e8eef7" strokeWidth="1" />
        ))}
      </g>
    </svg>
  );
}

function MiniScan({ axis }: { axis: string }) {
  return (
    <>
      <div className="mini-scan-core" />
      <span>{axis}</span>
    </>
  );
}

function StudyOverviewCard({ overview, loading, error }: { overview: StudyOverview; loading: boolean; error: string }) {
  return (
    <section className="overview-card">
      <div className="card-title">Study Overview {loading ? "..." : error ? "(fallback)" : ""}</div>
      <dl>
        <dt>Study Name</dt><dd>{overview.study_name}</dd>
        <dt>Study ID</dt><dd>{overview.study_id}</dd>
        <dt>Modality</dt><dd>{overview.modality}</dd>
        <dt>Sequences</dt><dd>{overview.sequences.join(", ")}</dd>
        <dt>Subjects</dt><dd>{overview.subjects}</dd>
        <dt>Date</dt><dd>{overview.date}</dd>
      </dl>
      <button className="soft-button">View Details</button>
    </section>
  );
}

function DatasetSummaryCard({ summary, loading, error }: { summary: DatasetSummary; loading: boolean; error: string }) {
  return (
    <MetricCard
      title={`Dataset Summary ${loading ? "..." : error ? "(fallback)" : ""}`}
      values={[
        [String(summary.subjects), "Subjects"],
        [summary.scans.toLocaleString(), "Scans"],
        [summary.total_size, "Total Size"],
      ]}
      tone="blue"
      note={summary.health_status}
    />
  );
}

function MetricCard({
  title,
  values,
  tone,
  note,
}: {
  title: string;
  values: Array<[string, string]>;
  tone: string;
  note?: string;
}) {
  return (
    <section className={`metric-card ${tone}`}>
      <div className="card-row">
        <div className="card-title">{title}</div>
        {note ? <span className="micro-badge">{note}</span> : null}
      </div>
      <div className="metric-grid">
        {values.map(([value, label]) => (
          <div key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function ModelCard({ model, loading, error }: { model: ModelStatus; loading: boolean; error: string }) {
  return (
    <section className="metric-card model-card">
      <div className="card-row">
        <div className="card-title">Model Status {loading ? "..." : error ? "(fallback)" : ""}</div>
        <span className="micro-badge">{model.status}</span>
      </div>
      <div className="model-body">
        <div>
          <strong>{model.model_name} ({model.version})</strong>
          <span>{model.dice_score > 0 ? `Dice Score ${model.dice_score.toFixed(3)}` : "QC metrics mode"}</span>
          <small>Last trained {model.last_trained}</small>
        </div>
        <svg viewBox="0 0 160 80" aria-label="Model performance trend">
          <path d="M0 58 C22 54 26 30 48 38 C75 49 74 12 103 16 C125 19 123 45 160 35" fill="none" stroke="#7556f2" strokeWidth="4" />
          <path d="M0 80 L0 58 C22 54 26 30 48 38 C75 49 74 12 103 16 C125 19 123 45 160 35 L160 80 Z" fill="#7556f2" opacity=".12" />
        </svg>
      </div>
    </section>
  );
}

function TaskLogTable({
  tasks,
  loading,
  error,
  onRetry,
  selectedTaskId,
  onSelectTask,
}: {
  tasks: TaskLogEntry[];
  loading: boolean;
  error: string;
  onRetry: () => void;
  selectedTaskId: string | null;
  onSelectTask: (taskId: string) => void;
}) {
  return (
    <section className="task-log">
      <div className="log-header">
        <div>
          <h2>Task Log</h2>
          <span>{loading ? "Loading task activity" : error ? "Using fallback task data" : "Live pipeline and execution activity"}</span>
        </div>
        <div className="tab-row">
          <button className="active">All Runs</button>
          <button>Running</button>
          <button>Completed</button>
          <button>Failed</button>
          {error ? <button onClick={onRetry}>Retry</button> : null}
        </div>
      </div>
      <div className="task-table">
        {tasks.map((task) => (
          <button
            key={task.id}
            className={`task-row ${task.id === selectedTaskId ? "selected" : ""}`}
            onClick={() => onSelectTask(task.id)}
          >
            <span>{task.run_name}</span>
            <span>{task.pipeline}</span>
            <span>{task.dataset}</span>
            <span><StatusPill status={task.status} /></span>
            <span className="progress-cell"><i><b style={{ width: `${task.progress}%` }} /></i>{task.progress}%</span>
            <span>{task.started_at}</span>
            <span>{task.duration}</span>
          </button>
        ))}
      </div>
    </section>
  );
}

function TaskDetailsPanel({
  task,
  events,
  diagnostics,
  loading,
  error,
  streamConnected,
  approvalName,
  auditPackage,
  auditLoading,
  onApprovalNameChange,
  onApprove,
  onGenerateAudit,
  onRetry,
  onReconnect,
}: {
  task: TaskLogEntry | null;
  events: TaskEvent[];
  diagnostics: TaskDiagnostics;
  loading: boolean;
  error: string;
  streamConnected: boolean;
  approvalName: string;
  auditPackage: TaskAuditPackage | null;
  auditLoading: boolean;
  onApprovalNameChange: (value: string) => void;
  onApprove: () => void;
  onGenerateAudit: () => void;
  onRetry: () => void;
  onReconnect: () => void;
}) {
  if (!task) {
    return null;
  }
  const latestEvents = events.length
    ? events
    : task.logs.map((message, index) => ({
        id: index,
        task_id: task.id,
        status: task.status,
        progress: task.progress,
        message,
        timestamp: task.started_at,
        result_path: task.result_path,
        source: "task-log",
        metadata: {},
      }));
  return (
    <section className="task-detail-panel">
      <div className="card-row">
        <div>
          <div className="card-title">Task Details</div>
          <span>{task.run_name}</span>
        </div>
        <div className="detail-actions">
          <StatusPill status={task.status} />
          <span className={`stream-chip ${streamConnected ? "online" : ""}`}>
            {streamConnected ? "Stream live" : "Stream idle"}
          </span>
          {error ? <button onClick={onRetry}>Reload Events</button> : null}
          {!streamConnected && task.status === "running" ? <button onClick={onReconnect}>Reconnect</button> : null}
          <button onClick={onGenerateAudit} disabled={auditLoading}>
            {auditLoading ? "Generating..." : "Audit Package"}
          </button>
        </div>
      </div>
      <div className="detail-grid">
        <div><span>Mode</span><strong>{task.execution_mode || "simulated"}</strong></div>
        <div><span>Progress</span><strong>{task.progress}%</strong></div>
        <div><span>Owner</span><strong>{task.owner}</strong></div>
        <div><span>Result</span><strong>{task.result_path || "Pending"}</strong></div>
      </div>
      {task.execution_mode === "external_smoke" ? (
        <div className="approval-strip">
          <div>
            <span>Approval</span>
            <strong>
              {diagnostics.approval
                ? `${diagnostics.approval.approved_by} at ${diagnostics.approval.approved_at}`
                : "Manual review only; approved smoke is locked"}
            </strong>
          </div>
          {!diagnostics.approval ? (
            <label>
              <span>Approved by</span>
              <input
                value={approvalName}
                onChange={(event) => onApprovalNameChange(event.target.value)}
                placeholder="Research lead name"
              />
            </label>
          ) : null}
          {!diagnostics.approval ? <button onClick={onApprove}>Approve Smoke</button> : null}
        </div>
      ) : null}
      {diagnostics.diagnosis.length ? (
        <div className="diagnostic-list">
          {diagnostics.diagnosis.slice(0, 4).map((item, index) => (
            <div key={`${item.code}-${index}`} className={`diagnostic-item ${String(item.severity || "info")}`}>
              <span>{String(item.code || "diagnostic")}</span>
              <p>{String(item.message || "")}</p>
            </div>
          ))}
        </div>
      ) : null}
      {diagnostics.external_tool_results.length ? (
        <div className="tool-result-list">
          <div className="panel-kicker">External tool results</div>
          {diagnostics.external_tool_results.slice(0, 3).map((result, index) => (
            <div className="tool-result-row" key={index}>
              <strong>{String(result.command || result.function || `External run ${index + 1}`)}</strong>
              <span>returncode {String(result.returncode ?? "n/a")}</span>
            </div>
          ))}
        </div>
      ) : null}
      {auditPackage ? (
        <div className="audit-package-box">
          <div>
            <span>Audit package</span>
            <strong>{auditPackage.generated_at}</strong>
          </div>
          <p>{auditPackage.report_path}</p>
          <p>{auditPackage.json_path}</p>
        </div>
      ) : null}
      <div className="event-list">
        {loading ? <div className="event-row muted">Loading persisted events...</div> : null}
        {latestEvents.map((event) => (
          <div className="event-row" key={`${event.id}-${event.timestamp}-${event.message}`}>
            <span>{event.timestamp}</span>
            <strong>{event.progress}%</strong>
            <p>{event.message}</p>
          </div>
        ))}
      </div>
      {error ? <div className="detail-error">{error}</div> : null}
    </section>
  );
}

function AssistantPanel({
  messages,
  input,
  loading,
  error,
  onInput,
  onSubmit,
  onNewChat,
}: {
  messages: ChatMessage[];
  input: string;
  loading: boolean;
  error: string;
  onInput: (value: string) => void;
  onSubmit: (event: FormEvent) => void;
  onNewChat: () => void;
}) {
  return (
    <section className="assistant-card">
      <div className="card-row">
        <div className="card-title">AI Assistant</div>
        <button onClick={onNewChat}>New Chat</button>
      </div>
      <div className="chat-thread">
        {messages.map((message, index) => (
          <div key={`${message.role}-${index}`} className={`chat-bubble ${message.role}`}>
            {message.text}
          </div>
        ))}
        {loading ? <div className="chat-bubble assistant">Thinking...</div> : null}
        {error ? <div className="chat-error">{error}</div> : null}
      </div>
      <form className="prompt-box" onSubmit={onSubmit}>
        <input
          value={input}
          onChange={(event) => onInput(event.target.value)}
          placeholder="Ask a question..."
          aria-label="Ask AI Assistant"
        />
        <button type="submit" disabled={loading}>Go</button>
      </form>
    </section>
  );
}

function PipelineSettingsCard({
  project,
  model,
  dataset,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  onExecutionModeChange,
  onExternalSmokeApprovedRunChange,
  onExternalSmokeApprovedByChange,
  onConfigure,
}: {
  project: ProjectDetail;
  model: ModelStatus;
  dataset: DatasetSummary;
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  externalSmokeApprovedBy: string;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onExternalSmokeApprovedRunChange: (value: boolean) => void;
  onExternalSmokeApprovedByChange: (value: string) => void;
  onConfigure: () => void;
}) {
  const executionModes: Array<{ value: ExecutionMode; label: string }> = [
    { value: "simulated", label: "Simulated" },
    { value: "external_smoke", label: "External Smoke" },
    { value: "rsfmri_python", label: "rs-fMRI Python" },
  ];
  return (
    <section className="settings-card">
      <div className="card-row">
        <div className="card-title">Pipeline Settings</div>
        <button onClick={onConfigure}>Configure</button>
      </div>
      {[
        ["Pipeline", project.current_pipeline_id],
        ["Model", `${model.model_name} ${model.version}`],
        ["Input", project.sequences.join(", ")],
        ["Output", "Segmentation + metrics"],
        ["Dataset", dataset.health_status],
      ].map(([key, value]) => (
        <div className="setting-line" key={key}><span>{key}</span><strong>{value}</strong></div>
      ))}
      <div className="execution-mode-group" aria-label="Execution mode">
        {executionModes.map((item) => (
          <button
            key={item.value}
            className={executionMode === item.value ? "selected" : ""}
            onClick={() => onExecutionModeChange(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>
      <p className="mode-note">
        {executionMode === "external_smoke"
          ? externalSmokeApprovedRun
            ? "Approved smoke will launch MATLAB/SPM/DPABI after run-level approval is recorded."
            : "Generates an auditable SPM/DPABI smoke package without launching MATLAB."
          : executionMode === "rsfmri_python"
            ? "Runs the synthetic Python rs-fMRI quickstart adapter."
            : "Runs the fast in-memory demo task stream."}
      </p>
      {executionMode === "external_smoke" ? (
        <div className="external-approval-box">
          <label className="check-line">
            <input
              type="checkbox"
              checked={externalSmokeApprovedRun}
              onChange={(event) => onExternalSmokeApprovedRunChange(event.target.checked)}
            />
            Run approved MATLAB smoke
          </label>
          <input
            value={externalSmokeApprovedBy}
            onChange={(event) => onExternalSmokeApprovedByChange(event.target.value)}
            placeholder="Approved by"
            disabled={!externalSmokeApprovedRun}
            aria-label="Approved by"
          />
        </div>
      ) : null}
    </section>
  );
}

function StatusPill({ status }: { status: TaskStatus }) {
  const tone = status.toLowerCase();
  return <span className={`status-pill ${tone}`}>{status}</span>;
}
