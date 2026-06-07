/**
 * Pure helper for building a PresetPlanDraft from an instantiate response.
 */

import type { PipelinePresetInstantiateResponse, PresetPlanDraft } from "../types";

export function buildPresetPlanDraft(
  projectId: string,
  response: PipelinePresetInstantiateResponse,
): PresetPlanDraft {
  return {
    preset_id: response.preset_id,
    project_id: projectId,
    goal: "rs-fMRI preprocessing MVP preset",
    plan: response.plan,
    validation: response.validation ?? undefined,
    warnings: response.warnings ?? [],
    next_actions: response.next_actions ?? [],
    source: "pipeline_preset",
  };
}
