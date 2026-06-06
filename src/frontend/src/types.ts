export type ApiResult<T = unknown> = {
  ok?: boolean;
  error?: string;
} & T;

export type PipelineSummary = {
  pipeline_id: string;
  version: string;
  modality: string;
  description: string;
  nodes_total: number;
  nodes: Array<{
    id: string;
    name: string;
    backend: string;
    parallel_level: string;
    depends_on: string[];
  }>;
};

export type AgentPlanRequest = {
  agent_run_id: string;
  project_config_path: string;
  pipeline_path: string;
};

export type AgentExecuteRequest = AgentPlanRequest & {
  approved: boolean;
};

export type AgentRun = {
  ok: boolean;
  agent_run_id: string;
  plan: unknown | null;
  agent_summary: unknown | null;
  review_summary: string | null;
  proposed_memory_patch: string | null;
};

export type DatasetEvaluationReport = {
  ok: boolean;
  dataset_summary: unknown | null;
  subject_qc_table: string | null;
  exclusion_recommendations: string | null;
  report_markdown: string | null;
  report_html: string | null;
};

export type ProjectCreateRequest = {
  project_name: string;
  rawdata_dir: string;
  project_dir?: string | null;
  copy_mode?: "reference";
  run_inspection?: boolean;
  overwrite?: boolean;
};

export type ProjectCreateResponse = {
  ok: boolean;
  project_id: string;
  project_name: string;
  project_dir: string;
  rawdata_dir: string;
  project_config_path: string;
  dataset_index_path: string | null;
  diagnostics: Record<string, unknown>;
  warnings: string[];
  next_actions: string[];
};

export type ReviewedPlanRecord = {
  reviewed_plan_id: string;
  project_id: string;
  project_config_path: string;
  dataset_index_path: string | null;
  rawdata_dir: string | null;
  plan_hash: string;
  plan_path: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  approval_status: string;
  execution_status: string;
  last_audit_id: string | null;
  last_execution_id: string | null;
  warnings: string[];
  payload: {
    plan?: Record<string, unknown>;
    validation?: Record<string, unknown>;
    goal?: string | null;
    provider?: string | null;
    [key: string]: unknown;
  };
};

export type RunLinkRecord = {
  run_link_id: string;
  project_id: string;
  reviewed_plan_id: string;
  run_id: string;
  task_id: string | null;
  pipeline_path: string | null;
  summary_path: string | null;
  project_config_path: string;
  audit_id: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  warnings: string[];
  payload: Record<string, unknown>;
};

export type RunSummaryPreview = {
  run_id?: string;
  status?: string;
  started_at?: string | null;
  finished_at?: string | null;
  nodes_total?: number | null;
  nodes_succeeded?: number | null;
  nodes_failed?: number | null;
  nodes_skipped?: number | null;
  warnings?: string[];
  outputs?: Record<string, unknown>;
  errors?: unknown[];
  failed_nodes?: Array<Record<string, unknown>>;
  raw?: Record<string, unknown>;
  raw_truncated?: boolean;
};

export type ProjectRunDetailResponse = {
  ok: boolean;
  run_link: RunLinkRecord;
  summary_preview?: RunSummaryPreview | null;
  summary_preview_error?: string | null;
  warnings?: string[];
};

export type RunArtifactRecord = {
  artifact_id: string;
  name: string;
  kind: string;
  path: string;
  relative_path: string;
  exists: boolean;
  size_bytes: number | null;
  modified_at: string | null;
  previewable: boolean;
  warnings: string[];
  source?: string;
  suffix?: string;
  node_id?: string | null;
  category?: string | null;
  error_excerpt?: string | null;
  json_summary?: JsonPreviewSummary | null;
  qc_summary?: {
    status?: string | number | boolean | null;
    passed?: boolean | null;
    failed?: boolean | null;
    warnings?: string[];
    metrics?: Array<{ label: string; value: string }> | Record<string, unknown>;
    subject_id?: string | null;
    node_id?: string | null;
    error_message?: string | null;
    json_summary?: JsonPreviewSummary | null;
    truncated?: boolean;
  } | null;
};

export type CsvPreviewTable = {
  columns: string[];
  rows: string[][];
  row_count: number;
  displayed_rows: number;
  truncated: boolean;
  columns_truncated?: boolean;
};

export type JsonFieldSummary = {
  key: string;
  type: string;
  size?: number | null;
  keys?: string[];
  sample_types?: string[];
};

export type JsonMessageSummary = {
  count: number;
  sample: string[];
};

export type JsonPreviewSummary = {
  type: string;
  size?: number | null;
  top_level_keys: string[];
  status?: string | number | boolean | null;
  warnings: JsonMessageSummary;
  errors: JsonMessageSummary;
  field_summaries: JsonFieldSummary[];
};

export type ProjectRunArtifactsResponse = {
  ok: boolean;
  project_id: string;
  run_id: string;
  artifacts: RunArtifactRecord[];
  warnings: string[];
};

export type RunArtifactPreviewResponse = {
  ok: boolean;
  project_id: string;
  run_id: string;
  artifact_id: string;
  artifact: RunArtifactRecord;
  kind: string;
  path: string;
  exists: boolean;
  preview_type: "json" | "csv" | "markdown" | "text" | "log" | "metadata_only" | string;
  content: string | null;
  json: unknown | null;
  json_summary?: JsonPreviewSummary | null;
  csv?: CsvPreviewTable | null;
  truncated: boolean;
  warnings: string[];
  errors: string[];
};

export type RunListItem = {
  run_id: string;
  summary_path: string;
  status: string;
  pipeline_id?: string | null;
};

export type NodeStateSummary = {
  path: string;
  run_id?: string;
  subject?: string;
  node?: string;
  status?: string;
  started_at?: string;
  ended_at?: string;
  outputs?: string[];
  errors?: string[];
  warnings?: string[];
  metrics?: Record<string, unknown>;
  stdout_log?: string | null;
  stderr_log?: string | null;
  result_json?: string | null;
  returncode?: number | null;
};

export type SubjectRunSummary = {
  subject_id: string;
  status: string;
  nodes: NodeStateSummary[];
};

export type RunInspection = {
  ok: boolean;
  run_id: string;
  summary_path: string;
  summary: unknown | null;
  project_states: NodeStateSummary[];
  subjects: SubjectRunSummary[];
  warnings: string[];
};
