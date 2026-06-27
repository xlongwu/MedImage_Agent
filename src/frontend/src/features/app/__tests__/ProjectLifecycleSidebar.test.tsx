import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProjectLifecycleSidebar } from "../ProjectLifecycleSidebar";

describe("ProjectLifecycleSidebar", () => {
  beforeEach(() => {
    vi.stubGlobal("requestAnimationFrame", (callback: FrameRequestCallback) => {
      callback(0);
      return 1;
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("renders the project lifecycle entries and marks the active workspace", () => {
    render(
      <ProjectLifecycleSidebar
        activeTab="preprocessing"
        dataState="converted_bids"
        hasPreprocessingRun={false}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("navigation", { name: /project lifecycle/i })).toBeInTheDocument();
    expect(screen.getAllByRole("button")).toHaveLength(7);
    expect(screen.getByRole("button", { name: /preprocessing, current/i })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: /data & conversion, completed/i })).toBeEnabled();
    expect(screen.getByRole("button", { name: /results, blocked/i })).toBeDisabled();
  });

  it("opens reachable lifecycle workspaces from the side rail", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    const handleOpenWorkspace = vi.fn();
    render(
      <ProjectLifecycleSidebar
        activeTab="data"
        dataState="raw_dicom"
        onChange={handleChange}
        onOpenWorkspace={handleOpenWorkspace}
      />,
    );

    await user.click(screen.getByRole("button", { name: /plan, available/i }));

    expect(handleOpenWorkspace).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith("plan");
  });

  it("keeps prerequisite-gated workspaces locked until converted data is available", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    const handleOpenWorkspace = vi.fn();
    render(
      <ProjectLifecycleSidebar
        activeTab="data"
        dataState="raw_dicom"
        onChange={handleChange}
        onOpenWorkspace={handleOpenWorkspace}
      />,
    );

    await user.click(screen.getByRole("button", { name: /preprocessing, blocked/i }));

    expect(handleOpenWorkspace).not.toHaveBeenCalled();
    expect(handleChange).not.toHaveBeenCalled();
  });

  it("does not mark a workflow as current while the project library page is open", () => {
    render(
      <ProjectLifecycleSidebar
        activeTab="data"
        dataState="raw_dicom"
        projectsPageOpen={true}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /data & conversion, current/i })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("supports keyboard navigation and skips locked lifecycle workspaces", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    const handleOpenWorkspace = vi.fn();
    render(
      <ProjectLifecycleSidebar
        activeTab="data"
        dataState="empty"
        onChange={handleChange}
        onOpenWorkspace={handleOpenWorkspace}
      />,
    );

    screen.getByRole("button", { name: /data & conversion, current/i }).focus();
    await user.keyboard("{ArrowRight}");

    expect(handleOpenWorkspace).toHaveBeenCalledTimes(1);
    expect(handleChange).toHaveBeenCalledWith("environment");
  });

  it("skips locked stages between reachable lifecycle buttons", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(
      <ProjectLifecycleSidebar activeTab="plan" dataState="raw_dicom" onChange={handleChange} />,
    );

    screen.getByRole("button", { name: "Plan, Available" }).focus();
    await user.keyboard("{ArrowRight}");

    expect(screen.getByRole("button", { name: "Preprocessing, Blocked" })).toBeDisabled();
    expect(handleChange).toHaveBeenCalledWith("runs");
  });

  it("uses Home and End to move only to reachable lifecycle stages", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<ProjectLifecycleSidebar activeTab="data" dataState="empty" onChange={handleChange} />);

    screen.getByRole("button", { name: "Data & Conversion, Current" }).focus();
    await user.keyboard("{End}");
    await user.keyboard("{Home}");

    expect(screen.getByRole("button", { name: "Plan, Blocked" })).toBeDisabled();
    expect(handleChange).toHaveBeenNthCalledWith(1, "environment");
    expect(handleChange).toHaveBeenNthCalledWith(2, "data");
  });

  it("links lifecycle buttons to the active workspace region", () => {
    render(<ProjectLifecycleSidebar activeTab="data" dataState="raw_dicom" onChange={vi.fn()} />);

    expect(screen.getByRole("button", { name: /data & conversion, current/i })).toHaveAttribute(
      "aria-controls",
      "workflow-workspace",
    );
  });
});
