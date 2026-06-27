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
