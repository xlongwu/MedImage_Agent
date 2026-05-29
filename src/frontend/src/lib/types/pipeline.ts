import type { TaskStatus } from "./task";

export type ExecutionMode = "simulated" | "external_smoke" | "rsfmri_python";
export type ExternalSmokeMode = "manual_package" | "approved_smoke";

export interface PipelineRunRequest {
  project_id: string;
  pipeline_id: string;
  model_id: string;
  input_sequences: string[];
  output_type: string;
  execution_mode?: ExecutionMode;
  external_smoke_mode?: ExternalSmokeMode;
  approved?: boolean;
  approved_by?: string | null;
  dpabi_function?: string;
}

export interface PipelineRunResponse {
  task_id: string;
  status: TaskStatus;
}
