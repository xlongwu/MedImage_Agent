export type DataSourceType = "none" | "upload" | "directory" | "demo";

export interface DatasetState {
  sourceType: DataSourceType;
  datasetPath: string;
  uploadedFileName: string;
  inspectionStatus: "NOT_RUN" | "PASS" | "WARNING" | "FAIL";
  subjectCount: number;
  sessionCount: number;
  modality: string;
  warnings: string[];
  errors: string[];
}

export interface PreprocessingConfig {
  sliceTiming: { enabled: boolean; tr: number | null; referenceSlice: string };
  realignment: { enabled: boolean };
  coregistration: { enabled: boolean };
  segmentation: { enabled: boolean };
  normalization: { enabled: boolean; voxelSize: [number, number, number] };
  smoothing: { enabled: boolean; fwhm: [number, number, number] };
  nuisanceRegression: { enabled: boolean; model: string; includeWM: boolean; includeCSF: boolean; includeLinearTrend: boolean };
  temporalFiltering: { enabled: boolean; lowHz: number; highHz: number };
}

export interface AnalysisConfig {
  enabled: boolean;
  alffFalff: { enabled: boolean; lowHz: number; highHz: number };
  reho: { enabled: boolean; neighborhood: number };
  functionalConnectivity: { enabled: boolean; roiCount: number; generateSeedMap: boolean };
  groupSummary: { enabled: boolean };
  reportExport: { enabled: boolean; validateAfterExport: boolean };
}

export interface WorkflowState {
  step: number;
  dataSource: DataSourceType;
  datasetPath: string;
  preprocessing: PreprocessingConfig;
  analysis: AnalysisConfig;
  runId: string | null;
  runStatus: "IDLE" | "RUNNING" | "SUCCESS" | "FAILED" | "PARTIAL";
}

export type WorkflowAction =
  | { type: "SET_STEP"; step: number }
  | { type: "SET_DATA_SOURCE"; sourceType: DataSourceType; path: string }
  | { type: "SET_PREPROCESSING"; config: Partial<PreprocessingConfig> }
  | { type: "SET_ANALYSIS"; config: Partial<AnalysisConfig> }
  | { type: "SET_RUN_STATUS"; runId: string; status: WorkflowState["runStatus"] }
  | { type: "RESET" };

export interface WorkflowRunStepResult {
  step: string;
  ok: boolean;
}

export interface WorkflowSubjectMetrics {
  alff_mean?: number | string;
  reho_mean?: number | string;
  fc_mean?: number | string;
  shape?: Array<number | string>;
  time_s?: number | string;
}

export interface WorkflowRunResult {
  demo_id?: string;
  ok?: boolean;
  workflow_type?: string;
  total_time_s?: number | string;
  metrics?: Record<string, WorkflowSubjectMetrics>;
  steps?: WorkflowRunStepResult[];
  outputs?: Record<string, string | number | boolean | null>;
}

declare global {
  interface Window {
    __workflowResult?: WorkflowRunResult;
  }
}
