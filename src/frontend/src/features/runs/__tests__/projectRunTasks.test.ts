import { describe, expect, it } from "vitest";
import type { RunLinkRecord } from "../../../types";

import {
  latestProjectRunTasks,
  projectRunLinksToTasks,
  projectRunToTask,
} from "../projectRunTasks";

describe("project run task mapping", () => {
  it("maps Agent Task run links into Runs workspace records", () => {
    const mapped = projectRunToTask({
      run_link_id: "link-1",
      project_id: "project-1",
      reviewed_plan_id: "reviewed-1",
      run_id: "run-1",
      task_id: null,
      pipeline_path: "project/work/run-1.yaml",
      summary_path: "project/work/pipeline_runs/run-1/summary.json",
      project_config_path: "project/project.yaml",
      audit_id: null,
      status: "PARTIAL",
      created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:01:00Z",
      warnings: ["node failed"],
      payload: { pipeline_id: "native_reho", actor: "Agent Task" },
    });

    expect(mapped.id).toBe("run-1");
    expect(mapped.pipeline).toBe("native_reho");
    expect(mapped.status).toBe("partial");
    expect(mapped.result_path).toContain("summary.json");
  });

  it("preserves the authoritative project id on the mapped run", () => {
    const projectRun = projectRunToTask({
      run_link_id: "link-1",
      project_id: "project-1",
      reviewed_plan_id: "reviewed-1",
      run_id: "run-1",
      task_id: null,
      pipeline_path: null,
      summary_path: null,
      project_config_path: "project.yaml",
      audit_id: null,
      status: "FAILED",
      created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:01:00Z",
      warnings: [],
      payload: {},
    });

    expect(projectRun.dataset).toBe("project-1");
    expect(projectRun.status).toBe("failed");
  });

  it("keeps the newest authoritative projection when the same run id is repeated", () => {
    const base: RunLinkRecord = {
      run_link_id: "link-1",
      project_id: "project-1",
      reviewed_plan_id: "reviewed-1",
      run_id: "run-1",
      task_id: "lifecycle-1",
      pipeline_path: null,
      summary_path: null,
      project_config_path: "project.yaml",
      audit_id: null,
      status: "RUNNING",
      created_at: "2026-07-19T00:00:00Z",
      updated_at: "2026-07-19T00:01:00Z",
      warnings: [],
      payload: {},
    };

    const tasks = projectRunLinksToTasks([
      { ...base, status: "RUNNING", updated_at: "2026-07-19T00:01:00Z" },
      {
        ...base,
        status: "GOAL_NOT_SATISFIED",
        summary_path: "project/work/pipeline_runs/run-1/summary.json",
        updated_at: "2026-07-19T00:02:00Z",
      },
    ]);

    expect(tasks).toHaveLength(1);
    expect(tasks[0]).toMatchObject({
      id: "run-1",
      status: "partial",
      agent_task_id: "lifecycle-1",
      reviewed_plan_id: "reviewed-1",
    });
  });

  it("shows only the newest attempt per Agent Task or reviewed plan in the workspace", () => {
    const attempts = [
      projectRunToTask({
        run_link_id: "link-new",
        project_id: "project-1",
        reviewed_plan_id: "reviewed-1",
        run_id: "run-new",
        task_id: null,
        pipeline_path: null,
        summary_path: null,
        project_config_path: "project.yaml",
        audit_id: null,
        status: "SUCCESS",
        created_at: "2026-07-19T00:02:00Z",
        updated_at: "2026-07-19T00:03:00Z",
        warnings: [],
        payload: {},
      }),
      projectRunToTask({
        run_link_id: "link-old",
        project_id: "project-1",
        reviewed_plan_id: "reviewed-1",
        run_id: "run-old",
        task_id: null,
        pipeline_path: null,
        summary_path: null,
        project_config_path: "project.yaml",
        audit_id: null,
        status: "FAILED",
        created_at: "2026-07-19T00:00:00Z",
        updated_at: "2026-07-19T00:01:00Z",
        warnings: [],
        payload: {},
      }),
    ];

    expect(latestProjectRunTasks(attempts).map((task) => task.id)).toEqual(["run-new"]);
    expect(attempts).toHaveLength(2);
  });
});
