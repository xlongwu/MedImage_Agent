import { getJson, postJson } from "./client";
import type { DatasetImportRequest, DatasetImportResponse, DatasetSummary } from "../types/dataset";

export function getDatasetSummary(projectId: string): Promise<DatasetSummary> {
  return getJson<DatasetSummary>(
    `/api/datasets/summary?project_id=${encodeURIComponent(projectId)}`,
  );
}

export function importDataset(payload: DatasetImportRequest): Promise<DatasetImportResponse> {
  return postJson<DatasetImportResponse>("/api/datasets/import", payload);
}
