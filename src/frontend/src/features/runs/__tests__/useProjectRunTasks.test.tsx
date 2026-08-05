import { renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { listProjectRunLinks } from "../../../lib/api/projectRuns";
import type { RunLinkRecord } from "../../../types";
import { useProjectRunTasks } from "../useProjectRunTasks";

vi.mock("../../../lib/api/projectRuns", () => ({
  listProjectRunLinks: vi.fn(),
}));

function run(projectId: string, runId: string): RunLinkRecord {
  return {
    run_link_id: `link-${runId}`,
    project_id: projectId,
    reviewed_plan_id: "plan-1",
    run_id: runId,
    task_id: null,
    pipeline_path: null,
    summary_path: null,
    project_config_path: "project.yaml",
    audit_id: null,
    status: "COMPLETED",
    created_at: "2026-07-19T00:00:00Z",
    updated_at: "2026-07-19T00:01:00Z",
    warnings: [],
    payload: {},
  };
}

describe("useProjectRunTasks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("rejects a run list whose project ownership does not match the selection", async () => {
    vi.mocked(listProjectRunLinks).mockResolvedValue({
      ok: true,
      project_id: "project-2",
      runs: [run("project-2", "run-2")],
    });

    const { result } = renderHook(() => useProjectRunTasks("http://api", "project-1"));

    await waitFor(() => {
      expect(result.current.error).toContain("did not match the selected project");
    });
    expect(result.current.tasks).toEqual([]);
  });

  it("loads only records owned by the selected project", async () => {
    vi.mocked(listProjectRunLinks).mockResolvedValue({
      ok: true,
      project_id: "project-1",
      runs: [
        run("project-1", "run-2"),
        { ...run("project-1", "run-1"), updated_at: "2026-07-18T00:01:00Z" },
      ],
    });

    const { result } = renderHook(() => useProjectRunTasks("http://api", "project-1"));

    await waitFor(() => {
      expect(result.current.tasks).toHaveLength(1);
    });
    expect(result.current.tasks[0]).toMatchObject({
      dataset: "project-1",
      id: "run-2",
    });
    expect(result.current.historyTasks.map((task) => task.id)).toEqual(["run-2", "run-1"]);
  });
});
