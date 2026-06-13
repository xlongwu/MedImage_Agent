import type { ProjectCreateResponse } from "../types";
import type { ProjectDetail, ProjectSummary, StudyOverview } from "./types/project";

export type WorkflowTab = "data" | "preprocessing" | "reports" | "environment";

export type ProjectDataState = "raw_dicom" | "converted_bids" | "empty" | "mixed" | "unknown";

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
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as SignalRecord)
    : {};
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
    /funraw|t1raw|raw dicom|dicom rawdata|dicom layout detected|dicom files are present/i.test(rawText);
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
  const hasRealConvertedData =
    niftiCount > 0 || hasRealBidsRoots || hasConvertedSubjectEvidence;
  const convertedDataAbsent =
    niftiCount === 0 && !hasRealBidsRoots && !hasConvertedSubjectEvidence;

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

export function diagnosticNumber(
  diagnostics: Record<string, unknown>,
  key: string,
): number {
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

export function diagnosticArrayLength(
  diagnostics: Record<string, unknown>,
  key: string,
): number {
  const value = diagnostics[key];
  return Array.isArray(value) ? value.length : 0;
}

export function buildProjectInventory(
  project: ProjectDetail,
  overview: StudyOverview,
  diagnostics: Record<string, unknown>,
): ProjectInventory {
  const dicomFileCount = firstDiagnosticNumber(diagnostics, ["dicom_file_count", "dicom_files"], overview.dicom_files ?? 0);
  const dicomSeriesCount = firstDiagnosticNumber(diagnostics, ["dicom_series_count", "series_count"], overview.dicom_series ?? 0);
  const niftiFileCount = firstDiagnosticNumber(diagnostics, ["nifti_file_count", "nifti_files", "image_source_count"]);
  const convertedSubjectInventory = firstDiagnosticNumber(
    diagnostics,
    ["converted_subject_count", "nifti_subject_count", "image_subject_count"],
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
    ? firstDiagnosticNumber(diagnostics, ["converted_subject_count", "nifti_subject_count", "image_subject_count"])
    : convertedSubjectInventory;
  const metadataOnlyNiftiInventory = niftiFileCount === 0 && isMetadataOnlySignal(diagnostics);
  const workflowSignals: SignalRecord = {
    ...overview,
    ...diagnostics,
    dicom_file_count: dicomFileCount,
    dicom_files: dicomFileCount,
    dicom_series_count: dicomSeriesCount,
    dicom_series: dicomSeriesCount,
    raw_dicom_candidate_subjects: rawDicomCandidates,
    nifti_file_count: niftiFileCount,
    nifti_files: niftiFileCount,
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
    niftiFileCount,
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
  return [
    createdProject,
    ...projects.filter((item) => item.id !== result.project_id),
  ];
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
  const stamp = new Date().toISOString().replace(/[-:TZ.]/g, "").slice(0, 12);
  return `${trimmed} ${stamp}`;
}

export function isProjectNameConflict(message: string): boolean {
  return /already exists|Set overwrite=true|Project directory already exists/i.test(message);
}
