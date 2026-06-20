import type { WorkflowRunResult } from "../../state/workflowTypes";
import { getJson, postJson } from "./client";

export interface InventorySubject {
  tr?: number | string;
  manufacturer?: string;
  model?: string;
  matrix?: string;
  field_strength_t?: number | string;
  bold_count?: number | string;
  t1_count?: number | string;
}

export interface InventoryResult {
  ok?: boolean;
  error?: string;
  errors?: string[];
  format?: string;
  completeness?: {
    subjects_total?: number;
    has_t1w?: boolean;
    has_bold?: boolean;
    t1_ratio?: number;
  };
  summary?: {
    total_subjects?: number;
  };
  subjects?: InventorySubject[];
}

export function inspectRealDataInventory(
  baseUrl: string,
  rawdataPath: string,
): Promise<InventoryResult> {
  return postJson<InventoryResult>(
    "/api/real-data/inventory",
    { rawdata_path: rawdataPath },
    { baseUrl },
  );
}

export function getLatestQuickstartDemo(baseUrl: string): Promise<WorkflowRunResult> {
  return getJson<WorkflowRunResult>("/api/quickstart-demo/latest", { baseUrl });
}

export function runWorkflow(
  baseUrl: string,
  payload: { data_source: string; dataset_path: string },
): Promise<WorkflowRunResult> {
  return postJson<WorkflowRunResult>("/api/workflow/run", payload, { baseUrl });
}
