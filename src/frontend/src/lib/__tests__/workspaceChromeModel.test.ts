import { describe, expect, it } from "vitest";

import { workspaceChromePresetForLocation } from "../workspaceChromeModel";

describe("workspaceChromePresetForLocation", () => {
  it("maps core routes to stable shell presets", () => {
    expect(workspaceChromePresetForLocation({ kind: "projects" })).toBe("project-library");
    expect(
      workspaceChromePresetForLocation({
        kind: "legacy",
        projectId: "p1",
        workspace: "overview",
      }),
    ).toBe("project-dashboard");
    expect(
      workspaceChromePresetForLocation({
        kind: "legacy",
        projectId: "p1",
        workspace: "results",
      }),
    ).toBe("image-workspace");
    expect(
      workspaceChromePresetForLocation({
        kind: "project",
        projectId: "p1",
        workspace: "runs",
      }),
    ).toBe("task-workspace");
    expect(
      workspaceChromePresetForLocation({
        kind: "legacy",
        projectId: "p1",
        workspace: "plan",
      }),
    ).toBe("standard-workspace");
  });
});
