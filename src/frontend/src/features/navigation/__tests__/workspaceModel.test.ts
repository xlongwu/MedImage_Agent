import { describe, expect, it } from "vitest";

import {
  buildLifecycleItems,
  legacyLocationForProject,
  locationForProject,
  projectWorkspaces,
  utilityWorkspaces,
} from "../workspaceModel";

describe("workspaceModel", () => {
  it("opens every selected project at the Agent workspace", () => {
    expect(locationForProject("project-1")).toEqual({
      kind: "project",
      projectId: "project-1",
      workspace: "agent",
    });
    expect(projectWorkspaces).toEqual(["agent", "runs", "settings"]);
  });

  it("keeps old lifecycle pages available only through compatibility locations", () => {
    expect(legacyLocationForProject("project-1", "preprocessing")).toEqual({
      kind: "legacy",
      projectId: "project-1",
      workspace: "preprocessing",
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
