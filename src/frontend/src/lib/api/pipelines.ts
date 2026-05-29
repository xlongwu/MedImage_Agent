import { postJson } from "./client";
import type { PipelineRunRequest, PipelineRunResponse } from "../types/pipeline";

export function runPipeline(payload: PipelineRunRequest): Promise<PipelineRunResponse> {
  return postJson<PipelineRunResponse>("/api/pipelines/run", payload);
}

