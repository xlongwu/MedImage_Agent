import { describe, expect, it } from "vitest";

import { buildLifecycleItems, locationForProject, utilityWorkspaces } from "../workspaceModel";

describe("workspaceModel", () => {
  it("opens every selected project at Overview", () => {
    expect(locationForProject("project-1")).toEqual({
      kind: "project",
      projectId: "project-1",
      workspace: "overview",
    });
  });

  it("keeps utility workspaces outside the lifecycle", () => {
    const items = buildLifecycleItems({
      activeWorkspace: "runs",
      dataState: "converted_bids",
      hasPreprocessingRun: true,
    });

    expect(items.map((item) => item.id)).not.toEqual(expect.arrayContaining(utilityWorkspaces));
  });

  it("blocks scientific stages without backend evidence", () => {
    const items = buildLifecycleItems({
      activeWorkspace: "overview",
      dataState: "raw_dicom",
      hasPreprocessingRun: false,
    });

    expect(items.find((item) => item.id === "preprocessing")?.state).toBe("blocked");
    expect(items.find((item) => item.id === "qc")?.state).toBe("blocked");
    expect(items.find((item) => item.id === "results")?.state).toBe("blocked");
  });
});
