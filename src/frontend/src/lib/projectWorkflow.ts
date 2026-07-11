import type { NativeFullPreprocResponse, ProjectCreateResponse } from "../types";
import type { TaskStatus } from "./types/task";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "./types/project";

export type WorkflowTab =
  | "data"
  | "plan"
  | "preprocessing"
  | "runs"
  | "reports"
  | "results"
  | "environment";

export type ProjectDataState = "raw_dicom" | "converted_bids" | "empty" | "mixed" | "unknown";

export type WorkflowLifecycleState = "current" | "completed" | "available" | "blocked";

export type WorkflowTabItem = {
  id: WorkflowTab;
  label: string;
  description: string;
};

export const workflowTabItems: WorkflowTabItem[] = [
  { id: "data", label: "Data & Conversion", description: "DICOM, BIDS, dry-run" },
  { id: "plan", label: "Plan", description: "Review and approve" },
  { id: "preprocessing", label: "Preprocessing", description: "Validation and reports" },
  { id: "runs", label: "Runs", description: "Events and diagnostics" },
  { id: "reports", label: "QC", description: "Quality review" },
  { id: "results", label: "Results", description: "Artifacts and exports" },
  { id: "environment", label: "Settings / Environment", description: "Planning tools" },
];

export function deriveWorkflowLifecycleState(
  tabId: WorkflowTab,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): WorkflowLifecycleState {
  const isConverted = dataState === "converted_bids" || dataState === "mixed";
  const isEmpty = dataState === "empty" || !dataState;

  switch (tabId) {
    case "data":
      if (isConverted) return "completed";
      return "current";
    case "plan":
      if (isEmpty) return "blocked";
      if (hasPreprocessingRun) return "completed";
      return "available";
    case "preprocessing":
      if (isConverted && hasPreprocessingRun) return "completed";
      if (isConverted) return "current";
      return "blocked";
    case "runs":
      if (isEmpty) return "blocked";
      return "available";
    case "reports":
      if (isConverted && hasPreprocessingRun) return "current";
      if (isConverted) return "available";
      return "blocked";
    case "results":
      if (isConverted && hasPreprocessingRun) return "available";
      return "blocked";
    case "environment":
      return "available";
    default:
      return "available";
  }
}

export function isWorkflowTabBlocked(
  tabId: WorkflowTab,
  dataState: ProjectDataState | undefined,
  hasPreprocessingRun: boolean,
): boolean {
  return deriveWorkflowLifecycleState(tabId, dataState, hasPreprocessingRun) === "blocked";
}

type NativePreprocessingRunEvidence = Pick<
  NativeFullPreprocResponse,
  "dry_run" | "status" | "stage_results"
>;

const RESULT_READY_NATIVE_STAGES = new Set([
  "functional_connectivity",
  "roi_time_series",
  "temporal_filtering",
  "nuisance_regression",
]);

export function hasNativePreprocessingRunEvidence(
  nativeRun: NativePreprocessingRunEvidence | null | undefined,
): boolean {
  if (!nativeRun || nativeRun.dry_run) return false;
  if (nativeRun.status === "succeeded") return true;
  if (nativeRun.status !== "partial") return false;

  return nativeRun.stage_results.some((stage) => {
    if (!RESULT_READY_NATIVE_STAGES.has(stage.stage_id)) return false;
    if (stage.status !== "succeeded" && stage.status !== "simplified") return false;
    return stage.capability_level === "computed" || stage.output_artifacts.length > 0;
  });
}

export type DefaultWorkflowRouteReason =
  | "active_or_failed_run"
  | "qc_attention"
  | "converted_data"
  | "data_review";

export type DefaultWorkflowRoute = {
  reason: DefaultWorkflowRouteReason;
  tab: WorkflowTab;
};

export type DefaultWorkflowTaskSignal = {
  status?: TaskStatus | string | null;
};

export type DefaultWorkflowInput = {
  diagnostics?: SignalRecord | null;
  hasPreprocessingRun?: boolean;
  inventory?: Pick<ProjectInventory, "dataState"> | null;
  tasks?: DefaultWorkflowTaskSignal[] | null;
};

export function deriveDefaultWorkflowRoute({
  diagnostics,
  hasPreprocessingRun = false,
  inventory,
  tasks = [],
}: DefaultWorkflowInput): DefaultWorkflowRoute {
  if (hasActiveOrFailedRun(tasks)) {
    return { reason: "active_or_failed_run", tab: "runs" };
  }

  if (hasQcAttentionSignal(diagnostics) && hasPreprocessingRun) {
    return { reason: "qc_attention", tab: "reports" };
  }

  if (inventory?.dataState === "converted_bids" || inventory?.dataState === "mixed") {
    return { reason: "converted_data", tab: "preprocessing" };
  }

  return { reason: "data_review", tab: "data" };
}

export function deriveDefaultWorkflowTab(input: DefaultWorkflowInput): WorkflowTab {
  return deriveDefaultWorkflowRoute(input).tab;
}

export type ProjectInventory = {
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
  metadataOnlyNiftiInventory: boolean;
};

type SignalRecord = Record<string, unknown>;

type ProjectWorkflowSignals = {
  metadata?: SignalRecord & {
    diagnostics?: SignalRecord;
    rawdata_dir?: unknown;
  };
  subjects_count?: unknown;
};

function asSignalRecord(value: unknown): SignalRecord {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as SignalRecord) : {};
}

function nestedSignal(value: unknown, key: string): SignalRecord {
  return asSignalRecord(asSignalRecord(value)[key]);
}

function arrayItem(value: unknown, index: number): unknown {
  return Array.isArray(value) ? value[index] : undefined;
}

function maxNumericSignal(...values: unknown[]): number {
  let max = 0;
  for (const value of values) {
    if (Array.isArray(value)) {
      max = Math.max(max, value.length);
      continue;
    }
    const numeric = Number(value);
    if (Number.isFinite(numeric) && numeric > max) {
      max = numeric;
    }
  }
  return max;
}

function countSignal(...values: unknown[]): number {
  return maxNumericSignal(...values);
}

function textSignal(value: unknown): string {
  if (typeof value === "string") {
    return value;
  }
  if (Array.isArray(value)) {
    return value.map(textSignal).filter(Boolean).join(" ");
  }
  if (value && typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return "";
    }
  }
  return "";
}

function isMetadataOnlySignal(...values: unknown[]): boolean {
  return /metadata[-_\s]?only|Metadata-/.test(values.map(textSignal).join(" "));
}

function hasActiveOrFailedRun(tasks: DefaultWorkflowTaskSignal[] | null | undefined): boolean {
  return Boolean(
    tasks?.some((task) => {
      const status = String(task.status ?? "").toLowerCase();
      return status === "running" || status === "pending" || status === "failed";
    }),
  );
}

function booleanSignal(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return value > 0;
  if (typeof value === "string")
    return /^(true|yes|required|attention|review|warning|failed)$/i.test(value);
  return false;
}

function hasQcAttentionSignal(diagnostics: SignalRecord | null | undefined): boolean {
  const record = asSignalRecord(diagnostics);
  const qcRecord = asSignalRecord(record.qc ?? record.quality ?? record.qc_dashboard);
  const statusText = textSignal([
    record.qc_status,
    record.qc_health,
    record.quality_status,
    qcRecord.status,
    qcRecord.health,
  ]);
  return (
    booleanSignal(record.qc_attention_required) ||
    booleanSignal(record.qc_attention) ||
    booleanSignal(record.qc_requires_review) ||
    maxNumericSignal(
      record.qc_failed_count,
      record.qc_warning_count,
      record.qc_outlier_count,
      record.outlier_count,
      qcRecord.failed_count,
      qcRecord.warning_count,
      qcRecord.outlier_count,
    ) > 0 ||
    /attention|required|review|warning|failed|fail|outlier/i.test(statusText)
  );
}

export function deriveProjectWorkflowState(
  project: ProjectWorkflowSignals | null | undefined,
  readiness?: SignalRecord | null,
  bidsValidation?: SignalRecord | null,
  dicomPreflight?: SignalRecord | null,
): ProjectDataState {
  if (!project) return "unknown";

  const projectMetadata = asSignalRecord(project.metadata);
  const projectDiagnostics = asSignalRecord(projectMetadata.diagnostics);
  const readinessRecord = asSignalRecord(readiness);
  const bidsRecord = asSignalRecord(bidsValidation);
  const dicomRecord = asSignalRecord(dicomPreflight);
  const readinessDicomPreflight = nestedSignal(readinessRecord, "dicom_preflight");
  const readinessDicomPreflightCamel = nestedSignal(readinessRecord, "dicomPreflight");
  const preprocessingInputInventory = asSignalRecord(projectMetadata.preprocessing_input_inventory);
  const nativeFullPreprocHandoff = asSignalRecord(projectMetadata.native_full_preproc_handoff);
  const lastConversionStatus = String(projectMetadata.last_conversion_status ?? "").toLowerCase();
  const handoffStatus = String(nativeFullPreprocHandoff.status ?? "").toLowerCase();

  const dicomFileCount = maxNumericSignal(
    dicomRecord.dicom_file_count,
    dicomRecord.dicom_files,
    readinessRecord.dicom_file_count,
    readinessRecord.dicom_files,
    readinessDicomPreflight.dicom_file_count,
    readinessDicomPreflightCamel.dicom_file_count,
    projectDiagnostics.dicom_file_count,
    projectDiagnostics.dicom_files,
    projectDiagnostics.raw_dicom_file_count,
  );

  const dicomSeriesCount = maxNumericSignal(
    dicomRecord.dicom_series_count,
    dicomRecord.series_count,
    readinessRecord.dicom_series_count,
    readinessRecord.dicom_series,
    readinessRecord.series_count,
    readinessDicomPreflight.series_count,
    readinessDicomPreflightCamel.series_count,
    projectDiagnostics.dicom_series_count,
    projectDiagnostics.dicom_series,
    projectDiagnostics.series_count,
  );

  const niftiCount = maxNumericSignal(
    bidsRecord.nifti_file_count,
    readinessRecord.nifti_file_count,
    readinessRecord.nifti_files,
    readinessRecord.image_source_count,
    projectMetadata.last_conversion_nifti_count,
    projectMetadata.preprocessing_input_nifti_count,
    preprocessingInputInventory.nifti_count,
    projectDiagnostics.nifti_file_count,
    projectDiagnostics.nifti_files,
    projectDiagnostics.image_source_count,
  );

  const bidsRootCount = countSignal(
    bidsRecord.roots,
    bidsRecord.bids_roots,
    readinessRecord.bids_roots,
    readinessRecord.bids_root_count,
    projectDiagnostics.bids_roots,
    projectDiagnostics.bids_root_count,
  );

  const metadataOnly = isMetadataOnlySignal(projectDiagnostics, readinessRecord, bidsRecord);
  const rawText = textSignal([
    projectDiagnostics,
    readinessRecord.warnings,
    readinessRecord.errors,
    readinessRecord.next_actions,
    readinessRecord.checks,
    bidsRecord.warnings,
    bidsRecord.errors,
    bidsRecord.issues,
  ]);
  const readinessIndicatesRawDicom =
    /funraw|t1raw|raw dicom|dicom rawdata|dicom layout detected|dicom files are present/i.test(
      rawText,
    );
  const dicomPreflightSucceeded =
    Boolean(dicomRecord.ok) &&
    (dicomFileCount > 0 || dicomSeriesCount > 0 || countSignal(dicomRecord.series) > 0);

  const hasRawDicomEvidence =
    dicomFileCount > 0 ||
    dicomSeriesCount > 0 ||
    dicomPreflightSucceeded ||
    readinessIndicatesRawDicom;

  const bidsValidationSubjects = maxNumericSignal(bidsRecord.subject_count);
  const explicitConvertedSubjects = maxNumericSignal(
    hasRawDicomEvidence && niftiCount === 0 ? 0 : bidsValidationSubjects,
    readinessRecord.converted_subject_count,
    readinessRecord.converted_subjects,
    readinessRecord.nifti_subject_count,
    readinessRecord.image_subject_count,
    projectMetadata.last_conversion_subject_count,
    projectMetadata.preprocessing_input_subject_count,
    preprocessingInputInventory.subjects,
    projectDiagnostics.converted_subject_count,
    projectDiagnostics.converted_subjects,
    projectDiagnostics.nifti_subject_count,
    projectDiagnostics.image_subject_count,
  );

  const overviewSubjectCount = maxNumericSignal(readinessRecord.subjects);
  const projectSubjectCount = maxNumericSignal(project.subjects_count);
  const hasConvertedSubjectEvidence =
    !metadataOnly &&
    (explicitConvertedSubjects > 0 ||
      (!hasRawDicomEvidence && (overviewSubjectCount > 0 || projectSubjectCount > 0)));

  const hasRealBidsRoots =
    bidsRootCount > 0 && (!hasRawDicomEvidence || niftiCount > 0 || explicitConvertedSubjects > 0);
  const hasRegisteredConvertedOutput =
    (booleanSignal(projectMetadata.converted_bids_available) ||
      lastConversionStatus === "succeeded" ||
      handoffStatus === "ready" ||
      Boolean(projectMetadata.preprocessing_input_registry_path)) &&
    (niftiCount > 0 ||
      explicitConvertedSubjects > 0 ||
      maxNumericSignal(preprocessingInputInventory.bold_count, preprocessingInputInventory.t1w_count) >
        0);
  const hasRealConvertedData =
    niftiCount > 0 ||
    hasRealBidsRoots ||
    hasConvertedSubjectEvidence ||
    hasRegisteredConvertedOutput;
  const convertedDataAbsent = niftiCount === 0 && !hasRealBidsRoots && !hasConvertedSubjectEvidence;

  const importCount = readinessRecord.import_count ?? projectDiagnostics.import_count ?? 0;
  const rawdataDir = projectMetadata.rawdata_dir ?? arrayItem(bidsRecord.roots, 0) ?? "";

  if (hasRawDicomEvidence && hasRealConvertedData) {
    return "mixed";
  }
  if (hasRawDicomEvidence && convertedDataAbsent) {
    return "raw_dicom";
  }
  if (hasRealConvertedData) {
    return "converted_bids";
  }
  if (!rawdataDir && !hasRawDicomEvidence && !hasRealConvertedData && importCount === 0) {
    return "empty";
  }

  if (hasRawDicomEvidence) {
    return "raw_dicom";
  }
  return "empty";
}

export function directoryBasename(path: string): string {
  const normalized = path.trim().replace(/[\\/]+$/, "");
  const parts = normalized.split(/[\\/]/).filter(Boolean);
  return parts.length ? parts[parts.length - 1] : "New Project";
}

export function diagnosticNumber(diagnostics: Record<string, unknown>, key: string): number {
  const value = Number(diagnostics[key]);
  return Number.isFinite(value) ? value : 0;
}

export function firstDiagnosticNumber(
  diagnostics: Record<string, unknown>,
  keys: string[],
  fallback = 0,
): number {
  for (const key of keys) {
    const value = Number(diagnostics[key]);
    if (Number.isFinite(value)) {
      return value;
    }
  }
  return fallback;
}

export function diagnosticArrayLength(diagnostics: Record<string, unknown>, key: string): number {
  const value = diagnostics[key];
  return Array.isArray(value) ? value.length : 0;
}

export function buildProjectInventory(
  project: ProjectDetail,
  overview: StudyOverview,
  diagnostics: Record<string, unknown>,
): ProjectInventory {
  const projectMetadata = asSignalRecord(project.metadata);
  const preprocessingInputInventory = asSignalRecord(projectMetadata.preprocessing_input_inventory);
  const metadataNiftiFileCount = maxNumericSignal(
    projectMetadata.last_conversion_nifti_count,
    projectMetadata.preprocessing_input_nifti_count,
    preprocessingInputInventory.nifti_count,
  );
  const metadataConvertedSubjects = maxNumericSignal(
    projectMetadata.last_conversion_subject_count,
    projectMetadata.preprocessing_input_subject_count,
    preprocessingInputInventory.subjects,
  );
  const dicomFileCount = firstDiagnosticNumber(
    diagnostics,
    ["dicom_file_count", "dicom_files"],
    overview.dicom_files ?? 0,
  );
  const dicomSeriesCount = firstDiagnosticNumber(
    diagnostics,
    ["dicom_series_count", "series_count"],
    overview.dicom_series ?? 0,
  );
  const niftiFileCount = firstDiagnosticNumber(diagnostics, [
    "nifti_file_count",
    "nifti_files",
    "image_source_count",
  ]);
  const resolvedNiftiFileCount = Math.max(niftiFileCount, metadataNiftiFileCount);
  const convertedSubjectInventory = maxNumericSignal(
    firstDiagnosticNumber(diagnostics, [
      "converted_subject_count",
      "nifti_subject_count",
      "image_subject_count",
    ]),
    metadataConvertedSubjects,
    project.subjects_count,
  );
  const rawDicomCandidates = firstDiagnosticNumber(
    diagnostics,
    ["raw_dicom_candidate_subjects", "dicom_candidate_subjects", "dicom_subject_count"],
    diagnosticArrayLength(diagnostics, "subject_candidates") ||
      overview.dicom_subjects ||
      (dicomFileCount > 0 || dicomSeriesCount > 0 ? project.subjects_count : 0),
  );
  const hasRawDicom = dicomFileCount > 0 || dicomSeriesCount > 0 || rawDicomCandidates > 0;
  const convertedSubjects = hasRawDicom
    ? maxNumericSignal(
        firstDiagnosticNumber(diagnostics, [
          "converted_subject_count",
          "nifti_subject_count",
          "image_subject_count",
        ]),
        metadataConvertedSubjects,
      )
    : convertedSubjectInventory;
  const metadataOnlyNiftiInventory =
    resolvedNiftiFileCount === 0 && isMetadataOnlySignal(diagnostics);
  const workflowSignals: SignalRecord = {
    ...overview,
    ...diagnostics,
    dicom_file_count: dicomFileCount,
    dicom_files: dicomFileCount,
    dicom_series_count: dicomSeriesCount,
    dicom_series: dicomSeriesCount,
    raw_dicom_candidate_subjects: rawDicomCandidates,
    nifti_file_count: resolvedNiftiFileCount,
    nifti_files: resolvedNiftiFileCount,
    converted_subject_count: convertedSubjects,
    image_subject_count: convertedSubjects,
  };
  const dataState = deriveProjectWorkflowState(project, workflowSignals, null, null);
  const hasConvertedData = dataState === "converted_bids" || dataState === "mixed";
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
    niftiFileCount: resolvedNiftiFileCount,
    hasRawDicom,
    hasConvertedData,
    metadataOnlyNiftiInventory,
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

export function mergeCreatedProjectIntoList(
  result: ProjectCreateResponse,
  projects: ProjectSummary[],
): ProjectSummary[] {
  const createdProject = projectSummaryFromCreateResult(result);
  return [createdProject, ...projects.filter((item) => item.id !== result.project_id)];
}

export function uniqueProjectName(baseName: string, projects: ProjectSummary[]): string {
  const trimmed = baseName.trim() || "DICOM Project";
  const existingNames = new Set(projects.map((item) => item.name.trim().toLowerCase()));
  if (!existingNames.has(trimmed.toLowerCase())) {
    return trimmed;
  }
  for (let index = 2; index < 1000; index += 1) {
    const candidate = `${trimmed} ${index}`;
    if (!existingNames.has(candidate.toLowerCase())) {
      return candidate;
    }
  }
  const stamp = new Date()
    .toISOString()
    .replace(/[-:TZ.]/g, "")
    .slice(0, 12);
  return `${trimmed} ${stamp}`;
}

export function isProjectNameConflict(message: string): boolean {
  return /already exists|Set overwrite=true|Project directory already exists/i.test(message);
}
