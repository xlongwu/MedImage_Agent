import type { PipelinePreset, PipelinePresetInstantiateResponse } from "../../types";
import { requestJson } from "./legacyCore";

export async function getPipelinePreset(baseUrl: string, presetId: string) {
  return requestJson<{ ok: boolean; preset: PipelinePreset }>(
    baseUrl,
    `/api/pipeline-presets/${encodeURIComponent(presetId)}`,
  );
}

export async function instantiatePipelinePreset(
  baseUrl: string,
  projectId: string,
  presetId: string,
  payload?: Record<string, unknown>,
) {
  return requestJson<PipelinePresetInstantiateResponse>(
    baseUrl,
    `/api/projects/${encodeURIComponent(projectId)}/pipeline-presets/${encodeURIComponent(presetId)}/instantiate`,
    { method: "POST", body: JSON.stringify(payload ?? {}) },
  );
}

export async function listPipelinePresets(baseUrl: string) {
  return requestJson<{ ok: boolean; presets: PipelinePreset[] }>(baseUrl, "/api/pipeline-presets");
}
