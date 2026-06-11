import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { createProjectFromDirectory, DEFAULT_API_BASE, getHealth } from "./api";
import AdvancedModePanel from "./components/workflow/AdvancedModePanel";
import BidsValidationPanel from "./components/BidsValidationPanel";
import ConversionDryRunPanel from "./components/ConversionDryRunPanel";
import DicomConversionReviewPanel from "./components/DicomConversionReviewPanel";
import DataReadinessPanel from "./components/DataReadinessPanel";
import AdvancedPreprocessingPipelinePanel from "./components/AdvancedPreprocessingPipelinePanel";
const AdvancedPreprocessingPipelineCard = AdvancedPreprocessingPipelinePanel;
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
import { ActionList, MetricTile, StatusPill as DashboardStatusPill, cleanupNextActions } from "./components/dashboardUi";
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

type WorkflowTab = "data" | "preprocessing" | "reports" | "environment";

type ProjectDataState = "raw_dicom" | "converted_bids" | "empty" | "mixed" | "unknown";

type ProjectInventory = {
  projectName: string;
  modality: string;
  dataState: ProjectDataState;
  dataStateLabel: string;
  stateSentence: string;
  rawDicomCandidates: number;
  dicomSeriesCount: number;
  dicomFileCount: number;
  convertedSubjects: number;
  niftiFileCount: number;
  hasRawDicom: boolean;
  hasConvertedData: boolean;
};

export function deriveProjectWorkflowState(
  project: any,
  readiness: any,
  bidsValidation: any,
  dicomPreflight: any
): ProjectDataState {
  if (!project) return "unknown";

  const projectMetadata = project?.metadata || {};
  const projectDiagnostics = projectMetadata.diagnostics || {};

  const dicomFileCount =
    dicomPreflight?.dicom_file_count ??
    readiness?.dicom_files ??
    projectDiagnostics.dicom_file_count ??
    projectDiagnostics.dicom_files ??
    0;

  const dicomSeriesCount =
    dicomPreflight?.dicom_series_count ??
    readiness?.dicom_series ??
    projectDiagnostics.dicom_series_count ??
    projectDiagnostics.dicom_series ??
    0;

  const niftiCount =
    bidsValidation?.nifti_file_count ??
    readiness?.nifti_files ??
    projectDiagnostics.nifti_file_count ??
    projectDiagnostics.nifti_files ??
    0;

  const convertedSubjects =
    bidsValidation?.subject_count ??
    readiness?.subjects ??
    projectDiagnostics.converted_subject_count ??
    projectDiagnostics.nifti_subject_count ??
    projectDiagnostics.image_subject_count ??
    project?.subjects_count ??
    0;

  const importCount = readiness?.import_count ?? projectDiagnostics.import_count ?? 0;
  const rawdataDir = projectMetadata.rawdata_dir ?? bidsValidation?.roots?.[0] ?? "";

  const hasRawDicom = dicomFileCount > 0 || dicomSeriesCount > 0;
  const hasConvertedData = convertedSubjects > 0 || niftiCount > 0;

  if (hasRawDicom && hasConvertedData) {
    return "mixed";
  }
  if (hasRawDicom && niftiCount === 0 && convertedSubjects === 0) {
    return "raw_dicom";
  }
  if (hasConvertedData && dicomFileCount === 0 && dicomSeriesCount === 0) {
    return "converted_bids";
  }
  if (!rawdataDir && !hasRawDicom && !hasConvertedData && importCount === 0) {
    return "empty";
  }

  // fallback logic
  if (hasConvertedData) {
    return "converted_bids";
  }
  if (hasRawDicom) {
    return "raw_dicom";
  }
  return "empty";
}

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

function firstDiagnosticNumber(
  diagnostics: Record<string, unknown>,
  keys: string[],
  fallback = 0
): number {
  for (const key of keys) {
    const value = Number(diagnostics[key]);
    if (Number.isFinite(value)) {
      return value;
    }
  }
  return fallback;
}

function diagnosticArrayLength(
  diagnostics: Record<string, unknown>,
  key: string
): number {
  const value = diagnostics[key];
  return Array.isArray(value) ? value.length : 0;
}

function buildProjectInventory(
  project: ProjectDetail,
  overview: StudyOverview,
  diagnostics: Record<string, unknown>
): ProjectInventory {
  const dicomFileCount = firstDiagnosticNumber(diagnostics, ["dicom_file_count", "dicom_files"], overview.dicom_files ?? 0);
  const dicomSeriesCount = firstDiagnosticNumber(diagnostics, ["dicom_series_count", "series_count"], overview.dicom_series ?? 0);
  const niftiFileCount = firstDiagnosticNumber(diagnostics, ["nifti_file_count", "nifti_files", "image_source_count"]);
  const convertedSubjectInventory = firstDiagnosticNumber(
    diagnostics,
    ["converted_subject_count", "nifti_subject_count", "image_subject_count"],
    project.subjects_count,
  );
  const hasRawDicom = dicomFileCount > 0;
  const hasConvertedData = niftiFileCount > 0 || convertedSubjectInventory > 0;
  const convertedSubjects = hasRawDicom
    ? firstDiagnosticNumber(diagnostics, ["converted_subject_count", "nifti_subject_count", "image_subject_count"])
    : convertedSubjectInventory;
  const rawDicomCandidates = firstDiagnosticNumber(
    diagnostics,
    ["raw_dicom_candidate_subjects", "dicom_candidate_subjects", "dicom_subject_count"],
    diagnosticArrayLength(diagnostics, "subject_candidates") || overview.dicom_subjects || (hasRawDicom ? project.subjects_count : 0),
  );
  const dataState = deriveProjectWorkflowState(project, overview, null, null);
  const dataStateLabel =
    dataState === "raw_dicom"
      ? "Raw DICOM"
      : dataState === "mixed"
        ? "Mixed"
        : dataState === "converted_bids"
          ? "Converted BIDS/NIfTI"
          : "Empty project";
  const stateSentence =
    dataState === "raw_dicom"
      ? "Raw DICOM data detected. Convert to BIDS/NIfTI before NIfTI QC or preprocessing."
      : dataState === "mixed"
        ? "Raw DICOM and converted imaging outputs are both present. Review conversion state before preprocessing."
        : dataState === "converted_bids"
          ? "Converted BIDS/NIfTI data is available for QC and preprocessing validation."
          : "Import a BIDS/NIfTI dataset or raw DICOM directory to begin.";

  return {
    projectName: overview.study_name || project.name,
    modality: project.modality || overview.modality || "rs-fMRI",
    dataState,
    dataStateLabel,
    stateSentence,
    rawDicomCandidates,
    dicomSeriesCount,
    dicomFileCount,
    convertedSubjects,
    niftiFileCount,
    hasRawDicom,
    hasConvertedData,
  };
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
  const [activeWorkflow, setActiveWorkflow] = useState<WorkflowTab>("data");
  const [health, setHealth] = useState<boolean | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
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
  const projectDiagnostics = useMemo(() => {
    if (projectCreateResult?.project_id === selectedProjectId) {
      return projectCreateResult.diagnostics;
    }
    const diagnostics = selectedProjectMetadata?.diagnostics;
    return diagnostics && typeof diagnostics === "object"
      ? diagnostics as Record<string, unknown>
      : {};
  }, [projectCreateResult, selectedProjectId, selectedProjectMetadata]);
  const overview = useProjectOverview(project.data.study_id);
  const projectInventory = useMemo(
    () => buildProjectInventory(project.data, overview.data, projectDiagnostics),
    [project.data, overview.data, projectDiagnostics],
  );
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
    if (projectInventory) {
      if (projectInventory.dataState === "converted_bids") {
        setActiveWorkflow("preprocessing");
      } else if (projectInventory.dataState === "raw_dicom") {
        setActiveWorkflow("data");
      } else if (projectInventory.dataState === "mixed") {
        setActiveWorkflow("data");
      } else if (projectInventory.dataState === "empty") {
        setActiveWorkflow("data");
      } else {
        setActiveWorkflow("data");
      }
    }
  }, [selectedProjectId, projectInventory.dataState]);

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

  const hasPreprocessingRun = useMemo(() => {
    return tasks.data.some(
      (task) =>
        task.pipeline?.toLowerCase().includes("preprocess") ||
        task.run_name?.toLowerCase().includes("preprocess")
    );
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
        overwrite: true,
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

  function handleScrollToPanel(panelId: string) {
    document.getElementById(panelId)?.scrollIntoView({ behavior: "smooth", block: "start" });
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

        <main className="workflow-main">
          <section className="project-overview-grid" aria-label="Project overview">
            <ProjectHeroPanel inventory={projectInventory} />
            <RecommendedNextStepCard
              inventory={projectInventory}
              hasPreprocessingRun={hasPreprocessingRun}
              onPrimaryAction={() => {
                setActiveWorkflow(projectInventory.dataState === "converted_bids" ? "preprocessing" : "data");
                window.setTimeout(() => handleScrollToPanel("workflow-workspace"), 0);
              }}
              onSecondaryAction={() => {
                setActiveWorkflow(projectInventory.dataState === "converted_bids" ? "reports" : "data");
                window.setTimeout(() => handleScrollToPanel("workflow-workspace"), 0);
              }}
            />
          </section>

          <ReadinessStatusStrip inventory={projectInventory} health={health} hasPreprocessingRun={hasPreprocessingRun} />

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

          <WorkflowTabs activeTab={activeWorkflow} onChange={setActiveWorkflow} />

          <section id="workflow-workspace" className="workflow-workspace" aria-live="polite">
            {activeWorkflow === "data" ? (
              <DataConversionWorkspace baseUrl={baseUrl} projectId={selectedProjectId} inventory={projectInventory} />
            ) : activeWorkflow === "preprocessing" ? (
              <PreprocessingWorkspace
                projectId={selectedProjectId}
                dataState={projectInventory.dataState}
                inventory={projectInventory}
                hasPreprocessingRun={hasPreprocessingRun}
                onOpenDataConversion={() => setActiveWorkflow("data")}
                onOpenToolsDrawer={() => setDrawerOpen(true)}
              />
            ) : activeWorkflow === "reports" ? (
              <QCReportsWorkspace baseUrl={baseUrl} projectId={selectedProjectId} />
            ) : (
              <SettingsEnvironmentWorkspace
                baseUrl={baseUrl}
                projectId={selectedProjectId}
                onReviewDraft={(draft) => {
                  setPresetPlanDraft(draft);
                  setMode("planner");
                  setNotice("Preset draft loaded into Plan Review Console. Review and save before dry-run.");
                }}
              />
            )}
          </section>

          <CompactTaskLog
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

        <SecondaryToolsDrawer
          isOpen={drawerOpen}
          onToggle={() => setDrawerOpen(!drawerOpen)}
          onSetMode={(m) => setMode(m)}
          project={project.data}
          model={model.data}
          dataset={dataset.data}
          executionMode={executionMode}
          externalSmokeApprovedRun={externalSmokeApprovedRun}
          externalSmokeApprovedBy={externalSmokeApprovedBy}
          assistantMessages={chatMessages}
          assistantInput={assistantInput}
          assistantLoading={assistantLoading}
          assistantError={assistantError}
          pipelineLoading={pipeline.loading}
          onExecutionModeChange={setExecutionMode}
          onExternalSmokeApprovedRunChange={setExternalSmokeApprovedRun}
          onExternalSmokeApprovedByChange={setExternalSmokeApprovedBy}
          onConfigure={() => setMode("advanced")}
          onAssistantInput={setAssistantInput}
          onAssistantSubmit={handleAssistantSubmit}
          onNewChat={() => setChatMessages(fallbackChat)}
          onQuickAction={handleQuickAction}
        />
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
          title={item.name}
        >
          <span className="project-pill-name">{item.name}</span>
          {item.id === selectedProjectId ? <span className="project-pill-dot" /> : null}
        </button>
      ))}
    </div>
  );
}

function ProjectHeroPanel({ inventory }: { inventory: ProjectInventory }) {
  const niftiDisplayVal =
    (inventory.dataState === "converted_bids" || inventory.convertedSubjects > 0) && inventory.niftiFileCount === 0
      ? "Metadata-only inventory"
      : inventory.niftiFileCount.toLocaleString();

  return (
    <section className="project-hero-panel" aria-label="Project summary">
      <div className="summary-meta-row">
        <DashboardStatusPill status={inventory.dataState === "converted_bids" ? "ready" : inventory.dataState === "empty" ? "not_started" : "warning"}>
          {inventory.dataStateLabel}
        </DashboardStatusPill>
        <span className="panel-kicker">{inventory.modality}</span>
      </div>
      <h1>{inventory.projectName}</h1>
      <p style={{ marginBottom: "20px" }}>{inventory.stateSentence}</p>

      <div className="hero-metrics-grid">
        <MetricTile label="Raw DICOM candidates" value={inventory.rawDicomCandidates} tone={inventory.hasRawDicom ? "blue" : "neutral"} />
        <MetricTile label="DICOM series" value={inventory.dicomSeriesCount} />
        <MetricTile label="DICOM files" value={inventory.dicomFileCount.toLocaleString()} />
        <MetricTile label="Converted subjects" value={inventory.convertedSubjects} tone={inventory.convertedSubjects > 0 ? "green" : "neutral"} />
        <MetricTile label="NIfTI files" value={niftiDisplayVal} tone={inventory.niftiFileCount > 0 ? "green" : "neutral"} />
      </div>
    </section>
  );
}

function RecommendedNextStepCard({
  inventory,
  hasPreprocessingRun,
  onPrimaryAction,
  onSecondaryAction,
}: {
  inventory: ProjectInventory;
  hasPreprocessingRun: boolean;
  onPrimaryAction: () => void;
  onSecondaryAction: () => void;
}) {
  const primary =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Generate conversion dry-run"
      : inventory.dataState === "converted_bids"
        ? (hasPreprocessingRun ? "Check preprocessing validation" : "Create preprocessing run")
        : "Import dataset";
  const explanation =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Create a read-only conversion plan before NIfTI QC or preprocessing."
      : inventory.dataState === "converted_bids"
        ? "Inspect preprocessing readiness before creating or reviewing a run."
        : "Import a BIDS/NIfTI dataset or raw DICOM directory to begin.";
  const secondary =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? "Review conversion readiness"
      : inventory.dataState === "converted_bids"
        ? "Review QC report status"
        : "";
  const steps =
    inventory.dataState === "raw_dicom" || inventory.dataState === "mixed"
      ? ["Generate conversion dry-run", "Review conversion readiness", "Persist review package"]
      : inventory.dataState === "converted_bids"
        ? [
            hasPreprocessingRun ? "Check preprocessing validation" : "Create preprocessing run",
            "Review QC report status",
            "Open Plan Review when ready"
          ]
        : ["Import dataset", "Review data readiness", "Check environment health"];

  return (
    <aside className="recommended-card" aria-label="Recommended next step">
      <div>
        <h2>Recommended Next Step</h2>
        <p>{explanation}</p>
      </div>
      <ol className="recommended-steps">
        {steps.slice(0, 3).map((step, index) => (
          <li key={step}><span>{index + 1}</span>{step}</li>
        ))}
      </ol>
      <div className="recommended-actions">
        <button type="button" className="primary-scroll-button" onClick={onPrimaryAction}>
          {primary}
        </button>
        {secondary ? (
          <button type="button" className="secondary-scroll-button" onClick={onSecondaryAction}>
            {secondary}
          </button>
        ) : null}
      </div>
    </aside>
  );
}

function ReadinessStatusStrip({
  inventory,
  health,
  hasPreprocessingRun,
}: {
  inventory: ProjectInventory;
  health: boolean | null;
  hasPreprocessingRun: boolean;
}) {
  const isConverted = inventory.dataState === "converted_bids";
  const isRawDicom = inventory.dataState === "raw_dicom";
  const isMixed = inventory.dataState === "mixed";
  const isEmpty = inventory.dataState === "empty";

  // Data status
  let dataStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" = "unknown";
  if (isConverted) {
    dataStatus = "ready";
  } else if (isRawDicom || isMixed) {
    dataStatus = inventory.rawDicomCandidates > 0 ? "ready" : "warning";
  } else if (isEmpty) {
    dataStatus = "not_started";
  }

  // DICOM status
  const dicomStatus = inventory.dicomFileCount > 0 ? "ready" : "not_applicable";

  // BIDS/NIfTI status
  let bidsStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" = "unknown";
  if (isConverted) {
    bidsStatus = "ready";
  } else if (isRawDicom) {
    bidsStatus = "warning";
  } else if (isMixed) {
    bidsStatus = "ready";
  } else if (isEmpty) {
    bidsStatus = "not_started";
  }

  // Conversion Safety status
  let safetyStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" = "unknown";
  if (isConverted) {
    safetyStatus = "not_applicable";
  } else if (isRawDicom || isMixed) {
    safetyStatus = "warning";
  } else {
    safetyStatus = "not_applicable";
  }

  // Preprocessing status
  let prepStatus: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown" = "unknown";
  if (isConverted || isMixed) {
    prepStatus = hasPreprocessingRun ? "ready" : "not_started";
  } else if (isRawDicom) {
    prepStatus = "not_applicable";
  } else {
    prepStatus = "not_started";
  }

  // Environment status
  const envStatus = health === false ? "blocked" : health ? "ready" : "unknown";

  return (
    <section className="readiness-status-strip" aria-label="Readiness status strip">
      <StatusStripItem label="Data" status={dataStatus} />
      <StatusStripItem label="DICOM" status={dicomStatus} />
      <StatusStripItem label="BIDS/NIfTI" status={bidsStatus} projectState={inventory.dataState} />
      <StatusStripItem label="Conversion Safety" status={safetyStatus} projectState={inventory.dataState} />
      <StatusStripItem label="Preprocessing" status={prepStatus} />
      <StatusStripItem label="Environment" status={envStatus} />
    </section>
  );
}

function StatusStripItem({
  label,
  status,
  projectState,
}: {
  label: string;
  status: "ready" | "warning" | "blocked" | "not_applicable" | "not_started" | "unknown";
  projectState?: string;
}) {
  let copy: string | undefined = undefined;
  if (label === "BIDS/NIfTI" && status === "warning" && projectState === "raw_dicom") {
    copy = "Expected before conversion";
  } else if (label === "Conversion Safety" && status === "warning" && projectState === "raw_dicom") {
    copy = "Review required";
  }
  return (
    <div className="status-strip-item">
      <small>{label}</small>
      <DashboardStatusPill status={status}>{copy}</DashboardStatusPill>
    </div>
  );
}

function WorkflowTabs({
  activeTab,
  onChange,
}: {
  activeTab: WorkflowTab;
  onChange: (tab: WorkflowTab) => void;
}) {
  const tabs: Array<{ id: WorkflowTab; label: string; description: string }> = [
    { id: "data", label: "Data & Conversion", description: "DICOM, BIDS, dry-run" },
    { id: "preprocessing", label: "Preprocessing", description: "Validation and reports" },
    { id: "reports", label: "QC & Reports", description: "Artifacts and warnings" },
    { id: "environment", label: "Settings / Environment", description: "Planning tools" },
  ];

  return (
    <nav className="workflow-tabs" aria-label="Workflow stages">
      {tabs.map((tab) => (
        <button
          key={tab.id}
          type="button"
          className={activeTab === tab.id ? "active" : ""}
          onClick={() => onChange(tab.id)}
        >
          <span>{tab.label}</span>
          <small>{tab.description}</small>
        </button>
      ))}
    </nav>
  );
}

function WorkspaceHeader({
  title,
  subtitle,
  status,
}: {
  title: string;
  subtitle: string;
  status?: string;
}) {
  return (
    <div className="workspace-header">
      <div>
        <h2>{title}</h2>
        <p>{subtitle}</p>
      </div>
      {status ? <DashboardStatusPill status={status}>{status}</DashboardStatusPill> : null}
    </div>
  );
}

function DataConversionWorkspace({
  baseUrl,
  projectId,
  inventory,
}: {
  baseUrl: string;
  projectId: string | null;
  inventory: ProjectInventory;
}) {
  const isConverted = inventory.dataState === "converted_bids";

  if (isConverted) {
    return (
      <div className="workspace-stack data-conversion-workspace">
        <WorkspaceHeader
          title="Data & Conversion"
          subtitle="Converted BIDS/NIfTI project overview."
          status="Ready"
        />
        <div style={{ padding: 12, border: "1px solid rgba(10, 132, 255, 0.18)", borderRadius: 8, background: "rgba(239, 246, 255, 0.82)", color: "#1557a5", fontSize: 12 }}>
          This project is already in converted BIDS/NIfTI mode. DICOM conversion is not the primary workflow.
        </div>
        <div className="workspace-summary-row">
          <div>
            <span>Primary action</span>
            <strong>Check preprocessing validation</strong>
          </div>
          <div>
            <span>Key blocker</span>
            <strong>None</strong>
          </div>
        </div>
        <div className="workspace-panel-grid">
          <div id="bids-validation-panel"><BidsValidationPanel baseUrl={baseUrl} projectId={projectId} projectState={inventory.dataState} /></div>
          <div id="preprocessing-validation-card"><AdvancedPreprocessingPipelineCard projectId={projectId} preprocessingRunId={null} /></div>
          <div id="qc-dashboard-summary-panel"><QcDashboardSummaryPanel baseUrl={baseUrl} projectId={projectId} /></div>
        </div>
      </div>
    );
  }

  return (
    <div className="workspace-stack data-conversion-workspace">
      <WorkspaceHeader
        title="Data & Conversion"
        subtitle="Review raw input state, BIDS/NIfTI readiness, and conversion safety without writing files."
        status={inventory.hasRawDicom ? "Expected before conversion" : inventory.hasConvertedData ? "Ready" : "Not started"}
      />
      {inventory.dataState === "mixed" && (
        <div style={{ padding: 10, border: "1px solid rgba(10, 132, 255, 0.18)", borderRadius: 8, background: "rgba(239, 246, 255, 0.82)", color: "#1557a5", fontSize: 12, marginBottom: 10 }}>
          <strong>Notice:</strong> Converted BIDS/NIfTI outputs are already present in this project, but raw DICOM files have also been detected. Review the conversion state before preprocessing.
        </div>
      )}
      <div className="workspace-summary-row">
        <div>
          <span>Primary action</span>
          <strong>{inventory.hasRawDicom ? "Generate conversion dry-run" : inventory.hasConvertedData ? "Review BIDS/NIfTI validation" : "Import dataset"}</strong>
        </div>
        <div>
          <span>Key blocker</span>
          <strong>{inventory.hasRawDicom ? "NIfTI QC waits for conversion" : inventory.hasConvertedData ? "Preprocessing run required" : "No imaging inventory"}</strong>
        </div>
      </div>
      <div className="workspace-panel-grid">
        <div id="data-readiness-panel"><DataReadinessPanel baseUrl={baseUrl} projectId={projectId} projectState={inventory.dataState} /></div>
        <div id="bids-validation-panel"><BidsValidationPanel baseUrl={baseUrl} projectId={projectId} projectState={inventory.dataState} /></div>
        <div id="conversion-dry-run-panel"><ConversionDryRunPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div id="dicom-conversion-review-panel"><DicomConversionReviewPanel baseUrl={baseUrl} projectId={projectId} /></div>
      </div>
    </div>
  );
}

function PreprocessingWorkspace({
  projectId,
  dataState,
  inventory,
  hasPreprocessingRun,
  onOpenDataConversion,
  onOpenToolsDrawer,
}: {
  projectId: string | null;
  dataState?: ProjectDataState;
  inventory: ProjectInventory;
  hasPreprocessingRun: boolean;
  onOpenDataConversion: () => void;
  onOpenToolsDrawer: () => void;
}) {
  const isRawDicom = dataState === "raw_dicom";

  if (isRawDicom) {
    return (
      <div className="workspace-stack preprocessing-workspace">
        <WorkspaceHeader
          title="Preprocessing"
          subtitle="Validate the preprocessing pipeline after conversion or BIDS registration. No full preprocessing action is exposed here."
          status="Blocked"
        />
        <section className="workflow-empty-note">
          <h3>Preprocessing validation</h3>
          <p>Convert DICOM to BIDS/NIfTI before preprocessing validation.</p>
          <button type="button" onClick={onOpenDataConversion}>Open Data & Conversion</button>
        </section>
      </div>
    );
  }

  const isMissingRegistration = dataState === "empty" || (dataState === "converted_bids" && inventory.convertedSubjects === 0);
  const ctaTitle = isMissingRegistration
    ? "Register converted outputs before preprocessing"
    : "Create preprocessing run";
  const ctaDescription = isMissingRegistration
    ? "Configure your BIDS dataset directory or import converted NIfTI outputs before setting up preprocessing."
    : "Set up and run the preprocessing pipeline using the local workstation tool stack.";
  const ctaButtonText = isMissingRegistration
    ? "Open Data & Conversion"
    : "Configure Preprocessing Run";
  const handleCtaClick = isMissingRegistration
    ? onOpenDataConversion
    : onOpenToolsDrawer;

  return (
    <div className="workspace-stack preprocessing-workspace">
      <WorkspaceHeader
        title="Preprocessing"
        subtitle="Validate the preprocessing pipeline after conversion or BIDS registration. No full preprocessing action is exposed here."
        status={hasPreprocessingRun ? "Ready" : "Not started"}
      />
      {!hasPreprocessingRun && (
        <section className="workflow-empty-note">
          <h3>{ctaTitle}</h3>
          <p>{ctaDescription}</p>
          <button type="button" onClick={handleCtaClick}>{ctaButtonText}</button>
        </section>
      )}
      <AdvancedPreprocessingPipelinePanel projectId={projectId} preprocessingRunId={null} />
    </div>
  );
}

function QCReportsWorkspace({ baseUrl, projectId }: { baseUrl: string; projectId: string | null }) {
  return (
    <div className="workspace-stack qc-reports-workspace">
      <WorkspaceHeader
        title="QC & Reports"
        subtitle="Compact report status, latest artifacts, warnings, and export actions."
        status="Review"
      />
      <div className="workspace-panel-grid">
        <div><QcDashboardSummaryPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><NiftiQcSnapshotPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><BoldReferenceReadinessPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><MotionQcReadinessPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><MotionMetricsDraftPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><RsfmriQcPlanningReportPanel baseUrl={baseUrl} projectId={projectId} /></div>
      </div>
    </div>
  );
}

function SettingsEnvironmentWorkspace({
  baseUrl,
  projectId,
  onReviewDraft,
}: {
  baseUrl: string;
  projectId: string | null;
  onReviewDraft: (draft: PresetPlanDraft) => void;
}) {
  return (
    <div className="workspace-stack settings-environment-workspace">
      <WorkspaceHeader
        title="Settings / Environment"
        subtitle="Planning-only checks for environment health, SPM wrappers, and preset review."
        status="Planning only"
      />
      <div className="planning-note">
        These tools produce readiness previews and review packages. They do not enable MATLAB/SPM execution or DPABI execution.
      </div>
      <div className="workspace-panel-grid">
        <div><EnvironmentHealthPanel baseUrl={baseUrl} /></div>
        <div><SpmRealignDryRunPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div><SpmRealignWrapperSkeletonPanel baseUrl={baseUrl} projectId={projectId} /></div>
        <div>
          <RsfmriPresetPanel
            baseUrl={baseUrl}
            projectId={projectId}
            onReviewDraft={onReviewDraft}
          />
        </div>
      </div>
    </div>
  );
}

function CompactTaskLog({
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
  const visibleTasks = tasks.slice(0, 2);
  return (
    <section className="compact-task-log" aria-label="Compact task log" style={{ padding: "10px 16px" }}>
      <details className="activity-details" style={{ width: "100%" }}>
        <summary style={{ cursor: "pointer", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <h2 style={{ margin: 0, fontSize: "14px" }}>Recent Activity</h2>
            <small style={{ color: "#667085" }}>(Click to view recent task logs / demo runs)</small>
          </div>
          {error ? <button type="button" onClick={(e) => { e.stopPropagation(); onRetry(); }} style={{ fontSize: 10, minHeight: 20, padding: "2px 6px" }}>Retry</button> : null}
        </summary>
        <div style={{ marginTop: 10 }}>
          {visibleTasks.length ? (
            <div className="compact-task-list">
              {visibleTasks.map((task) => (
                <button
                  type="button"
                  key={task.id}
                  className={task.id === selectedTaskId ? "selected" : ""}
                  onClick={() => onSelectTask(task.id)}
                >
                  <span>{task.run_name}</span>
                  <StatusPill status={task.status} />
                  <small>{task.progress}%</small>
                </button>
              ))}
            </div>
          ) : (
            <div className="empty">No recent task activity for this project yet.</div>
          )}
        </div>
      </details>
    </section>
  );
}

function SecondaryToolsDrawer({
  isOpen,
  onToggle,
  onSetMode,
  project,
  model,
  dataset,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  assistantMessages,
  assistantInput,
  assistantLoading,
  assistantError,
  pipelineLoading,
  onExecutionModeChange,
  onExternalSmokeApprovedRunChange,
  onExternalSmokeApprovedByChange,
  onConfigure,
  onAssistantInput,
  onAssistantSubmit,
  onNewChat,
  onQuickAction,
}: {
  isOpen: boolean;
  onToggle: () => void;
  onSetMode: (mode: "dashboard" | "advanced" | "planner") => void;
  project: ProjectDetail;
  model: ModelStatus;
  dataset: DatasetSummary;
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  externalSmokeApprovedBy: string;
  assistantMessages: ChatMessage[];
  assistantInput: string;
  assistantLoading: boolean;
  assistantError: string;
  pipelineLoading: boolean;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onExternalSmokeApprovedRunChange: (value: boolean) => void;
  onExternalSmokeApprovedByChange: (value: string) => void;
  onConfigure: () => void;
  onAssistantInput: (value: string) => void;
  onAssistantSubmit: (event: FormEvent) => void;
  onNewChat: () => void;
  onQuickAction: (action: string) => void;
}) {
  if (!isOpen) {
    return (
      <aside className="secondary-tools-drawer collapsed" aria-label="Secondary tools drawer collapsed">
        <button
          type="button"
          className="drawer-toggle-btn"
          onClick={onToggle}
          title="Open Tools Drawer"
          aria-label="Open Tools Drawer"
        >
          <span style={{ fontSize: 16 }}>🛠️</span>
          <div className="vertical-text">Tools</div>
        </button>
      </aside>
    );
  }

  return (
    <aside className="secondary-tools-drawer open" aria-label="Secondary tools drawer">
      <details open>
        <summary onClick={(e) => { e.preventDefault(); onToggle(); }} style={{ cursor: "pointer" }}>
          <span>Tools Drawer</span>
          <span style={{ fontSize: 14, fontWeight: "bold", padding: "0 6px" }}>✕</span>
        </summary>
        <div className="secondary-tools-stack">
          <PipelineSettingsCard
            project={project}
            model={model}
            dataset={dataset}
            executionMode={executionMode}
            externalSmokeApprovedRun={externalSmokeApprovedRun}
            externalSmokeApprovedBy={externalSmokeApprovedBy}
            onExecutionModeChange={onExecutionModeChange}
            onExternalSmokeApprovedRunChange={onExternalSmokeApprovedRunChange}
            onExternalSmokeApprovedByChange={onExternalSmokeApprovedByChange}
            onConfigure={onConfigure}
          />

          <details className="drawer-section">
            <summary style={{ cursor: "pointer" }}>Assistant</summary>
            <AssistantPanel
              messages={assistantMessages}
              input={assistantInput}
              loading={assistantLoading}
              error={assistantError}
              onInput={onAssistantInput}
              onSubmit={onAssistantSubmit}
              onNewChat={onNewChat}
            />
          </details>

          <details className="drawer-section">
            <summary style={{ cursor: "pointer" }}>Legacy Actions</summary>
            <div className="quick-grid compact">
              {quickActions.map((item) => (
                <button
                  key={item.title}
                  className={`quick-action ${item.kind}`}
                  onClick={() => onQuickAction(item.action)}
                  disabled={pipelineLoading && item.action === "run-pipeline"}
                >
                  <span>{item.title.slice(0, 1)}</span>
                  <strong>{item.action === "run-pipeline" && pipelineLoading ? "Running..." : item.title}</strong>
                  <small>{item.subtitle}</small>
                </button>
              ))}
            </div>
          </details>

          <details className="drawer-section">
            <summary style={{ cursor: "pointer" }}>Planning Tools</summary>
            <div style={{ display: "grid", gap: 8, paddingTop: 8 }}>
              <button
                type="button"
                className="soft-button"
                onClick={() => onSetMode("planner")}
                style={{ width: "100%", minHeight: 34, fontSize: 12, fontWeight: 800 }}
              >
                Plan Review Console
              </button>
              <button
                type="button"
                className="soft-button"
                onClick={() => onSetMode("advanced")}
                style={{ width: "100%", minHeight: 34, fontSize: 12, fontWeight: 800 }}
              >
                Advanced Console
              </button>
            </div>
          </details>
        </div>
      </details>
    </aside>
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
  const [showTechDetails, setShowTechDetails] = useState(false);

  if (!result && !loading && !error) {
    return null;
  }

  const diagnostics = result?.diagnostics ?? {};
  const status = String(diagnostics.status ?? "UNKNOWN");
  const dicomFileCount = diagnosticNumber(diagnostics, "dicom_file_count");
  const hasRawDicom = dicomFileCount > 0 && diagnosticNumber(diagnostics, "image_source_count") === 0;
  const rawDicomCandidates = firstDiagnosticNumber(
    diagnostics,
    ["raw_dicom_candidate_subjects", "dicom_candidate_subjects", "dicom_subject_count"],
    diagnosticArrayLength(diagnostics, "subject_candidates") || diagnosticNumber(diagnostics, "subjects_total"),
  );
  const nextActions = cleanupNextActions(result?.next_actions ?? [], { rawDicom: hasRawDicom });
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
            <div><span>Converted subjects</span><strong>{diagnosticNumber(diagnostics, "image_subject_count")}</strong></div>
            <div><span>Raw DICOM candidates</span><strong>{rawDicomCandidates}</strong></div>
            <div><span>DICOM files</span><strong>{dicomFileCount.toLocaleString()}</strong></div>
            <div><span>Complete</span><strong>{diagnosticNumber(diagnostics, "subjects_complete")}</strong></div>
            <div><span>Warning</span><strong>{diagnosticNumber(diagnostics, "subjects_warning")}</strong></div>
            <div><span>Incomplete</span><strong>{diagnosticNumber(diagnostics, "subjects_incomplete")}</strong></div>
          </div>

          <div style={{ marginTop: 10, marginBottom: 10 }}>
            <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#667085", cursor: "pointer" }}>
              <input
                type="checkbox"
                checked={showTechDetails}
                onChange={(e) => setShowTechDetails(e.target.checked)}
              />
              Show technical details
            </label>
          </div>

          {showTechDetails && (
            <>
              <div className="event-list">
                <div className="event-row"><span>Project directory</span><p>{result.project_dir}</p></div>
                <div className="event-row"><span>Rawdata directory</span><p>{result.rawdata_dir}</p></div>
                <div className="event-row"><span>Dataset index</span><p>{result.dataset_index_path || "Not generated"}</p></div>
              </div>

              <div className="tool-result-list">
                <div className="panel-kicker">Next actions</div>
                <ActionList actions={nextActions} rawDicom={hasRawDicom} />
              </div>
            </>
          )}

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
  const hasDicom = overview.dicom_files !== undefined && overview.dicom_files > 0;
  return (
    <section className="overview-card">
      <div className="card-title">Study Overview {loading ? "..." : error ? "(fallback)" : ""}</div>
      <dl>
        <dt>Study Name</dt><dd>{overview.study_name}</dd>
        <dt>Study ID</dt><dd>{overview.study_id}</dd>
        <dt>Modality</dt><dd>{overview.modality}</dd>
        <dt>Sequences</dt><dd>{overview.sequences.join(", ")}</dd>
        <dt>Subjects</dt><dd>{overview.subjects || (hasDicom ? `${overview.dicom_subjects} (candidate)` : "0")}</dd>
        {hasDicom && (
          <>
            <dt>DICOM Series</dt><dd>{overview.dicom_series} series</dd>
            <dt>DICOM Files</dt><dd>{overview.dicom_files?.toLocaleString()} files</dd>
          </>
        )}
        <dt>Date</dt><dd>{overview.date}</dd>
      </dl>
      <button className="soft-button">View Details</button>
    </section>
  );
}

function DatasetSummaryCard({ summary, loading, error }: { summary: DatasetSummary; loading: boolean; error: string }) {
  const isRawDicom = summary.dicom_files !== undefined && summary.dicom_files > 0 && summary.subjects === 0;
  return (
    <MetricCard
      title={`Dataset Summary ${loading ? "..." : error ? "(fallback)" : ""}`}
      values={
        isRawDicom
          ? [
              [String(summary.dicom_subjects || 0), "Candidate Subjects"],
              [String(summary.dicom_series || 0), "DICOM Series"],
              [summary.total_size || "0 KB", "Total Size (DICOM)"],
            ]
          : [
              [String(summary.subjects), "Subjects"],
              [summary.scans.toLocaleString(), "Scans"],
              [summary.total_size, "Total Size"],
            ]
      }
      tone="blue"
      note={isRawDicom ? "Raw DICOM (Expected before conversion)" : summary.health_status}
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
  const [showTechDetails, setShowTechDetails] = useState(false);

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

      <div style={{ marginTop: 10, marginBottom: 10 }}>
        <label style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: 11, color: "#667085", cursor: "pointer" }}>
          <input
            type="checkbox"
            checked={showTechDetails}
            onChange={(e) => setShowTechDetails(e.target.checked)}
          />
          Show technical details
        </label>
      </div>

      {showTechDetails && (
        <>
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
        </>
      )}
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
