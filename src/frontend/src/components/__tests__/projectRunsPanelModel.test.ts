import { describe, expect, it } from "vitest";

import {
  getArtifactPresenceState,
  summarizeRunHealth,
} from "../projectRunsPanelModel";
import type { RunArtifactRecord, RunLinkRecord } from "../../types";

function artifact(overrides: Partial<RunArtifactRecord> = {}): RunArtifactRecord {
  return {
    artifact_id: "artifact-1",
    exists: true,
    kind: "json",
    modified_at: null,
    name: "summary.json",
    path: "runs/run-001/summary.json",
    previewable: true,
    relative_path: "summary.json",
    size_bytes: 128,
    warnings: [],
    ...overrides,
  };
}

const run: RunLinkRecord = {
  audit_id: null,
  created_at: "2026-06-24T08:00:00Z",
  payload: {},
  pipeline_path: "pipelines/demo.yaml",
  project_config_path: "project.yaml",
  project_id: "project-1",
  reviewed_plan_id: "plan-1",
  run_id: "run-001",
  run_link_id: "link-1",
  status: "SUCCESS",
  summary_path: "runs/run-001/summary.json",
  task_id: null,
  updated_at: "2026-06-24T08:02:00Z",
  warnings: [],
};

describe("projectRunsPanelModel artifact presence", () => {
  it("does not call an empty artifact list present", () => {
    expect(getArtifactPresenceState([])).toEqual({
      label: "no artifact records",
      state: "none",
    });
    expect(summarizeRunHealth(run, null, [])).toMatchObject({
      artifactPresenceLabel: "no artifact records",
      artifactPresenceState: "none",
      artifactRecordsCount: 0,
      hasMissingArtifacts: false,
    });
  });

  it("distinguishes missing artifacts from present artifact records", () => {
    expect(getArtifactPresenceState([artifact({ exists: false })])).toEqual({
      label: "missing artifacts",
      state: "missing",
    });
    expect(getArtifactPresenceState([artifact()])).toEqual({
      label: "artifacts present",
      state: "present",
    });
  });
});
