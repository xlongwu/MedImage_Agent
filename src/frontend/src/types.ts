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

export type RunHealthLevel = "ok" | "warning" | "failed" | "unknown";

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

/** Response shape for POST /api/plans/execute-reviewed (dry_run or execute). */
export type ExecuteReviewedResponse = {
  ok?: boolean;
  status?: string;
  dry_run?: boolean;
  would_execute?: boolean;
  execution_allowed?: boolean;
  validation?: Record<string, unknown> | null;
  approval_gate?: Record<string, unknown> | null;
  adapter?: Record<string, unknown> | null;
  pipeline_yaml?: Record<string, unknown> | null;
  plan_summary?: Record<string, unknown> | null;
  project_config_path?: string | null;
  project_context?: Record<string, unknown> | null;
  execution?: {
    submitted?: boolean;
    run_id?: string | null;
    executor_called?: boolean;
  };
  audit?: {
    persisted?: boolean;
    audit_id?: string;
    audit_path?: string;
    event_type?: string;
    error?: string;
  };
  reviewed_plan_id?: string | null;
  run_link_id?: string | null;
  run_id?: string | null;
  pipeline_path?: string | null;
  summary_path?: string | null;
  executor_result?: Record<string, unknown> | null;
  errors?: unknown[];
  warnings?: unknown[];
};

/** Single event record from GET /api/projects/{id}/runs/{run_id}/events */
export type ProjectRunEventRecord = {
  timestamp?: string | null;
  level: string;
  source: string;
  message: string;
  node_id?: string | null;
  subject_id?: string | null;
  path?: string | null;
  metadata?: Record<string, unknown>;
};

export type ProjectRunEventsResponse = {
  ok: boolean;
  project_id: string;
  run_id: string;
  events: ProjectRunEventRecord[];
  warnings: string[];
  errors: string[];
};

/** Single log record from GET /api/projects/{id}/runs/{run_id}/logs */
export type ProjectRunLogRecord = {
  log_id: string;
  name: string;
  path: string;
  relative_path?: string | null;
  exists: boolean;
  size_bytes?: number | null;
  modified_at?: string | null;
  content?: string | null;
  truncated: boolean;
  warnings: string[];
};

export type ProjectRunLogsResponse = {
  ok: boolean;
  project_id: string;
  run_id: string;
  logs: ProjectRunLogRecord[];
  warnings: string[];
  errors: string[];
};

/** Single readiness check from GET /api/projects/{id}/data-readiness */
export type DataReadinessCheck = {
  name: string;
  status: "pass" | "warning" | "fail" | "unknown";
  message: string;
  details: Record<string, unknown>;
};

export type DataReadinessResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  checked_at: string;
  project_config_path?: string | null;
  dataset_index_path?: string | null;
  rawdata_dir?: string | null;
  import_count: number;
  image_source_count: number;
  subject_count: number;
  sequence_count: number;
  dicom_file_count: number;
  dicom_series_count: number;
  checks: DataReadinessCheck[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
};

/** BIDS validation types */
export type BidsValidationIssue = {
  severity: "info" | "warning" | "error";
  code: string;
  message: string;
  subject_id?: string | null;
  session_id?: string | null;
  modality?: string | null;
  file_path?: string | null;
  details: Record<string, unknown>;
};

export type BidsRepairSuggestion = {
  action_type: "rename_suggestion" | "move_suggestion" | "metadata_suggestion" | "missing_file_suggestion" | "manual_review" | "conversion_required";
  title: string;
  description: string;
  source_path?: string | null;
  suggested_path?: string | null;
  command_preview?: string | null;
  safe_to_auto_apply: boolean;
  requires_user_review: boolean;
  related_issue_codes: string[];
};

export type BidsValidationResponse = {
  ok: boolean;
  project_id: string;
  status: "pass" | "warning" | "fail" | "unknown";
  checked_at: string;
  roots: string[];
  subject_count: number;
  session_count: number;
  nifti_file_count: number;
  sidecar_json_count: number;
  tsv_file_count: number;
  issues: BidsValidationIssue[];
  repair_suggestions: BidsRepairSuggestion[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
};

/** Conversion dry-run types */
export type ConversionDryRunRequest = {
  source_import_ids?: string[];
  target_layout?: "bids";
  output_root_name?: string;
  subject_mapping_strategy?: "infer_from_dicom" | "infer_from_filename" | "manual_required";
  session_mapping_strategy?: "none" | "infer_from_dicom" | "infer_from_filename" | "manual_required";
  include_dicom?: boolean;
  include_loose_nifti?: boolean;
};

export type ConversionSourceSummary = {
  source_id: string;
  source_type: "dicom" | "loose_nifti" | "bids" | "unknown";
  root: string;
  exists: boolean;
  file_count: number;
  subject_candidates: string[];
  series_count: number;
  warnings: string[];
};

export type ConversionMappingPreview = {
  source_path?: string | null;
  source_series_uid?: string | null;
  source_type: "dicom_series" | "nifti_file";
  subject_id?: string | null;
  session_id?: string | null;
  modality?: string | null;
  suffix?: string | null;
  task?: string | null;
  suggested_relative_path?: string | null;
  confidence: "high" | "medium" | "low" | "manual_required";
  warnings: string[];
};

export type ConversionDryRunResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  dry_run: boolean;
  checked_at: string;
  target_layout: "bids";
  output_root_name: string;
  output_root_preview?: string | null;
  source_summaries: ConversionSourceSummary[];
  mapping_preview: ConversionMappingPreview[];
  blocking_issues: string[];
  warnings: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** Pipeline preset types */
export type PipelinePresetNode = {
  id: string;
  name: string;
  stage: string;
  backend: string;
  requires_approval: boolean;
  executable: boolean;
  description: string;
  inputs: string[];
  outputs: string[];
  params: Record<string, unknown>;
  safety_notes: string[];
};

export type PipelinePreset = {
  preset_id: string;
  name: string;
  modality: string;
  description: string;
  version: string;
  nodes: PipelinePresetNode[];
  non_goals: string[];
  readiness_requirements: string[];
  safety_flags: Record<string, boolean>;
};

export type PipelinePresetInstantiateResponse = {
  ok: boolean;
  project_id: string;
  preset_id: string;
  plan: Record<string, unknown>;
  validation: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** Draft handoff from preset instantiation to Plan Review Console */
export type PresetPlanDraft = {
  preset_id: string;
  project_id: string;
  goal: string;
  plan: Record<string, unknown>;
  validation?: Record<string, unknown>;
  warnings?: string[];
  next_actions?: string[];
  source: "pipeline_preset";
};

/** Motion QC readiness types */
export type MotionQcInputCandidate = {
  subject_id?: string | null;
  session_id?: string | null;
  bold_path: string;
  relative_path?: string | null;
  has_sidecar: boolean;
  has_motion_params: boolean;
  motion_param_paths: string[];
  has_fd_column: boolean;
  fd_source_path?: string | null;
  warnings: string[];
};

export type MotionQcReadinessResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  checked_at: string;
  candidate_count: number;
  candidates: MotionQcInputCandidate[];
  missing_motion_param_count: number;
  fd_available_count: number;
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** BOLD reference readiness types */
export type BoldReferenceCandidate = {
  subject_id?: string | null;
  session_id?: string | null;
  bold_path: string;
  relative_path?: string | null;
  dimensions: number[];
  voxel_spacing: number[];
  volume_count?: number | null;
  is_4d: boolean;
  has_sidecar: boolean;
  repetition_time?: number | null;
  task_name?: string | null;
  has_slice_timing: boolean;
  phase_encoding_direction?: string | null;
  reference_strategy: "middle_volume" | "single_volume" | "manual_required";
  warnings: string[];
};

export type BoldReferenceReadinessResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  checked_at: string;
  candidate_count: number;
  ready_count: number;
  warning_count: number;
  blocked_count: number;
  candidates: BoldReferenceCandidate[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** rs-fMRI QC Planning Report types */
export type RsfmriQcPlanningReportArtifact = {
  kind: "json" | "markdown";
  path: string;
  exists: boolean;
  size_bytes?: number | null;
};

export type RsfmriQcPlanningReportResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  generated_at: string;
  report_dir: string;
  json_path: string;
  markdown_path: string;
  artifacts: RsfmriQcPlanningReportArtifact[];
  bold_reference_status: string;
  motion_qc_status: string;
  motion_metrics_status?: string | null;
  motion_metrics_parsed_count?: number;
  motion_metrics_fd_available_count?: number;
  motion_metrics_artifacts?: RsfmriQcPlanningReportArtifact[];
  bold_candidate_count: number;
  motion_candidate_count: number;
  ready_candidate_count: number;
  warning_count: number;
  blocked_count: number;
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
  report_markdown?: string | null;
};

/** Motion metrics draft types */
export type MotionMetricsSubjectSummary = {
  subject_id?: string | null;
  session_id?: string | null;
  bold_path?: string | null;
  source_path: string;
  source_type: "spm_rp_txt" | "confounds_tsv" | "unknown";
  parsed: boolean;
  row_count: number;
  has_fd: boolean;
  volume_count_from_motion_rows?: number | null;
  max_abs_translation_mm?: number | null;
  mean_abs_translation_mm?: number | null;
  max_abs_rotation_rad?: number | null;
  mean_abs_rotation_rad?: number | null;
  fd_mean?: number | null;
  fd_max?: number | null;
  fd_over_0_2_count?: number | null;
  fd_over_0_5_count?: number | null;
  fd_over_0_2_fraction?: number | null;
  fd_over_0_5_fraction?: number | null;
  qc_flags: string[];
  warnings: string[];
};

export type MotionMetricsDraftArtifact = {
  kind: "json" | "markdown";
  path: string;
  exists: boolean;
  size_bytes?: number | null;
};

export type MotionMetricsDraftResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  generated_at: string;
  report_dir: string;
  json_path: string;
  markdown_path: string;
  artifacts: MotionMetricsDraftArtifact[];
  candidate_count: number;
  parsed_count: number;
  fd_available_count: number;
  summaries: MotionMetricsSubjectSummary[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
  report_markdown?: string | null;
};

/** SPM realign dry-run types */
export type SpmRealignPredictedOutput = {
  kind: "realigned_bold" | "mean_bold" | "motion_params" | "stdout_log" | "stderr_log" | "provenance_json" | "node_state_json";
  path: string;
  exists: boolean;
  would_overwrite: boolean;
  warning?: string | null;
};

export type SpmRealignInputPreview = {
  subject_id?: string | null;
  session_id?: string | null;
  bold_path: string;
  relative_path?: string | null;
  volume_count?: number | null;
  reference_strategy?: string | null;
  valid_for_realign: boolean;
  warnings: string[];
  predicted_outputs: SpmRealignPredictedOutput[];
};

export type SpmRealignDryRunResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  dry_run: boolean;
  checked_at: string;
  node_id: string;
  params: Record<string, unknown>;
  param_warnings: string[];
  param_errors: string[];
  input_count: number;
  ready_input_count: number;
  inputs: SpmRealignInputPreview[];
  output_root_preview?: string | null;
  environment_status?: string | null;
  approval_required: boolean;
  audit_required: boolean;
  execution_enabled: boolean;
  safe_allowlist_enabled: boolean;
  blocking_issues: string[];
  warnings: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** SPM realign wrapper skeleton types */
export type SpmRealignProvenancePreview = {
  command_template_id: string;
  node_id: string;
  dry_run_only: boolean;
  project_id: string;
  params: Record<string, unknown>;
  input_count: number;
  predicted_output_count: number;
  environment_status?: string | null;
  approval_required: boolean;
  audit_required: boolean;
  execution_enabled: boolean;
  safe_allowlist_enabled: boolean;
  warnings: string[];
};

export type SpmRealignOutputManifestItem = {
  kind: string;
  path: string;
  relative_path?: string | null;
  exists: boolean;
  size_bytes?: number | null;
  checksum_sha256?: string | null;
  modified_at?: string | null;
  required: boolean;
  verified: boolean;
  warnings: string[];
};

export type SpmRealignOutputManifest = {
  project_id: string;
  run_id: string;
  node_id: string;
  subject_id?: string | null;
  session_id?: string | null;
  output_root: string;
  items: SpmRealignOutputManifestItem[];
  missing_required_count: number;
  verified_count: number;
  warnings: string[];
  errors: string[];
};

export type SpmRealignWrapperSkeletonResponse = {
  ok: boolean;
  project_id: string;
  status: "ready" | "warning" | "blocked" | "unknown";
  generated_at: string;
  node_id: string;
  command_template_id: string;
  dry_run: SpmRealignDryRunResponse | null;
  matlab_batch_preview: string;
  provenance_preview: SpmRealignProvenancePreview;
  output_manifests?: SpmRealignOutputManifest[];
  manifest_summary?: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** NIfTI QC Snapshot types */
export type NiftiQcStatus = "ready" | "warning" | "blocked" | "unknown";

export type NiftiImageQcRecord = {
  image_id: string;
  path: string;
  relative_path?: string | null;
  subject_id?: string | null;
  session_id?: string | null;
  modality?: string | null;
  suffix?: string | null;
  exists: boolean;
  readable: boolean;
  dimensions: number[];
  ndim?: number | null;
  volume_count?: number | null;
  voxel_spacing: number[];
  dtype?: string | null;
  orientation?: string | null;
  affine_determinant?: number | null;
  intensity_min?: number | null;
  intensity_max?: number | null;
  intensity_mean?: number | null;
  intensity_std?: number | null;
  zero_fraction?: number | null;
  nan_count: number;
  warnings: string[];
};

export type NiftiQcSnapshotResponse = {
  ok: boolean;
  project_id: string;
  status: NiftiQcStatus;
  checked_at: string;
  image_count: number;
  readable_count: number;
  unreadable_count: number;
  four_d_count: number;
  warning_count: number;
  images: NiftiImageQcRecord[];
  warnings: string[];
  errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
};

/** NIfTI slice thumbnail types */
export type NiftiThumbnailView = "axial" | "coronal" | "sagittal";

export type NiftiSliceThumbnail = {
  view: NiftiThumbnailView;
  width: number;
  height: number;
  slice_index: number;
  volume_index?: number | null;
  png_base64: string;
  intensity_min?: number | null;
  intensity_max?: number | null;
  warnings: string[];
};

export type NiftiThumbnailResponse = {
  ok: boolean;
  project_id: string;
  image_id: string;
  path: string;
  dimensions: number[];
  volume_count?: number | null;
  selected_volume_index?: number | null;
  thumbnails: NiftiSliceThumbnail[];
  warnings: string[];
  errors: string[];
  safety_flags: Record<string, boolean>;
};

/** QC Dashboard Report types */
export type QcDashboardModuleStatus = "ready" | "warning" | "blocked" | "unknown" | "not_run";

export type QcDashboardModuleSummary = {
  module_id: string;
  name: string;
  status: QcDashboardModuleStatus;
  ok: boolean;
  score?: number | null;
  summary: string;
  key_metrics: Record<string, unknown>;
  warnings: string[];
  errors: string[];
  next_actions: string[];
};

export type QcDashboardReportArtifact = {
  kind: "json" | "markdown";
  path: string;
  exists: boolean;
  size_bytes?: number | null;
};

export type QcDashboardReportResponse = {
  ok: boolean;
  project_id: string;
  status: QcDashboardModuleStatus;
  generated_at: string;
  report_dir: string;
  json_path: string;
  markdown_path: string;
  artifacts: QcDashboardReportArtifact[];
  modules: QcDashboardModuleSummary[];
  ready_count: number;
  warning_count: number;
  blocked_count: number;
  unknown_count: number;
  overall_warnings: string[];
  overall_errors: string[];
  next_actions: string[];
  safety_flags: Record<string, boolean>;
  report_markdown?: string | null;
  cache?: QcDashboardCacheSummary;
};

/** QC Dashboard cache types */
export type QcDashboardCacheMode = "prefer" | "refresh" | "off";
export type QcDashboardCacheStatus = "hit" | "miss" | "stale" | "disabled" | "error";

export type QcDashboardModuleCacheRecord = {
  module_id: string;
  status: QcDashboardCacheStatus;
  cache_key?: string | null;
  fingerprint?: string | null;
  module_version?: string | null;
  generated_at?: string | null;
  artifact_path?: string | null;
  hit: boolean;
  stale: boolean;
  warnings: string[];
  errors: string[];
};

export type QcDashboardCacheSummary = {
  mode: QcDashboardCacheMode;
  hit: boolean;
  fingerprint?: string | null;
  module_hits: Record<string, boolean>;
  module_records: QcDashboardModuleCacheRecord[];
  cache_warnings: string[];
  cache_errors: string[];
};

/** QC Dashboard fingerprint debug types */
export type RawdataFingerprintType = {
  ok: boolean;
  roots: string[];
  exists_count: number;
  missing_roots: string[];
  file_count: number;
  total_size_bytes: number;
  newest_mtime?: number | null;
  newest_mtime_iso?: string | null;
  relative_path_hash?: string | null;
  fingerprint?: string | null;
  truncated: boolean;
  max_files: number;
  warnings: string[];
  errors: string[];
};

export type QcDashboardFingerprintResponse = {
  ok: boolean;
  project_id: string;
  fingerprint: RawdataFingerprintType;
  roots: string[];
  warnings: string[];
  errors: string[];
  safety_flags: Record<string, boolean>;
};

/** Phase 3 run-state timeline types */
export type RunStateTimelineEvent = {
  timestamp?: string | null;
  state: string;
  source: string;
  message?: string | null;
  node_id?: string | null;
  metadata: Record<string, unknown>;
};

export type NodeStateTimelineRecord = {
  node_id: string;
  state: string;
  terminal: boolean;
  retry_eligible: boolean;
  reuse_eligible: boolean;
  warnings: string[];
  errors: string[];
  metadata: Record<string, unknown>;
};

export type ProjectRunStateTimelineResponse = {
  ok: boolean;
  project_id: string;
  run_id: string;
  current_run_state: string;
  terminal: boolean;
  retry_eligible: boolean;
  resume_eligible: boolean;
  events: RunStateTimelineEvent[];
  nodes: NodeStateTimelineRecord[];
  warnings: string[];
  errors: string[];
};
