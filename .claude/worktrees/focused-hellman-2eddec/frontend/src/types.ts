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
