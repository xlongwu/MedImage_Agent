import { getJson } from "./client";
import type { ModelStatus } from "../types/model";

export function getModelStatus(projectId: string): Promise<ModelStatus> {
  return getJson<ModelStatus>(`/api/models/status?project_id=${encodeURIComponent(projectId)}`);
}

