import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RunActivityBar } from "../RunActivityBar";
import type { TaskLogEntry } from "../../../lib/types/task";

function task(overrides: Partial<TaskLogEntry> = {}): TaskLogEntry {
  return {
    id: "task-1",
    run_name: "Preprocessing run",
    pipeline: "rs-fMRI preprocessing",
    dataset: "Demo",
    status: "running",
    progress: 42,
    started_at: "2026-06-24T08:00:00Z",
    duration: "2m",
    owner: "local",
    logs: ["Detected inputs", "Running motion correction"],
    ...overrides,
  };
}

describe("RunActivityBar", () => {
  it("hides when there are no active or failed runs", () => {
    const { container } = render(
      <RunActivityBar
        tasks={[task({ status: "completed", progress: 100 })]}
        selectedTaskId={null}
        onSelectTask={vi.fn()}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });

  it("shows running progress and expands the run drawer", async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(<RunActivityBar tasks={[task()]} selectedTaskId={null} onSelectTask={handleSelect} />);

    expect(screen.getByText("Running")).toBeInTheDocument();
    expect(screen.getByText("42%")).toBeInTheDocument();
    expect(screen.getByRole("status", { name: "Background run activity" })).toHaveTextContent(
      "Managed task",
    );
    expect(screen.getByRole("status", { name: "Background run activity" })).not.toHaveTextContent(
      "rs-fMRI preprocessing",
    );

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));

    const drawer = screen.getByLabelText("Run activity drawer");
    expect(drawer).toBeInTheDocument();
    expect(screen.getByLabelText("Run activity summary")).toHaveTextContent("1 running");
    expect(screen.getByLabelText("Run timeline")).toHaveTextContent("Detected inputs");
    expect(screen.getByLabelText("Run timeline")).toHaveTextContent("Running motion correction");
    expect(screen.getByLabelText("Latest run log")).toHaveTextContent("Running motion correction");

    await user.click(within(drawer).getByRole("button", { name: /preprocessing run/i }));
    expect(handleSelect).toHaveBeenCalledWith("task-1");
  });

  it("opens the full Runs workspace from the drawer", async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    const handleOpenRuns = vi.fn();

    render(
      <RunActivityBar
        tasks={[task()]}
        selectedTaskId={null}
        onSelectTask={handleSelect}
        onOpenRuns={handleOpenRuns}
      />,
    );

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));
    await user.click(screen.getByRole("button", { name: "Open Runs" }));

    expect(handleSelect).toHaveBeenCalledWith("task-1");
    expect(handleOpenRuns).toHaveBeenCalledTimes(1);
  });

  it("copies diagnostics from the expanded run drawer", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    render(<RunActivityBar tasks={[task()]} selectedTaskId={null} onSelectTask={vi.fn()} />);

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));
    await user.click(screen.getByRole("button", { name: /copy diagnostics/i }));

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('"id": "task-1"'));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining('"status": "running"'));
    expect(screen.getByText("Copied diagnostics")).toBeInTheDocument();
  });

  it("keeps failed runs visible with a clear summary", async () => {
    const user = userEvent.setup();
    render(
      <RunActivityBar
        tasks={[task({ status: "failed", progress: 64, logs: ["SPM exited with code 1"] })]}
        selectedTaskId="task-1"
        onSelectTask={vi.fn()}
      />,
    );

    expect(screen.getByText("Failed")).toBeInTheDocument();
    expect(screen.getByText(/run failed/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));

    expect(screen.getByRole("alert")).toHaveTextContent("Failed run");
    expect(screen.getByLabelText("Latest run log")).toHaveTextContent("SPM exited with code 1");
  });

  it("bounds long drawer timelines to the latest five log entries", async () => {
    const user = userEvent.setup();
    render(
      <RunActivityBar
        tasks={[
          task({
            logs: ["event 1", "event 2", "event 3", "event 4", "event 5", "event 6", "event 7"],
          }),
        ]}
        selectedTaskId={null}
        onSelectTask={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));

    const timeline = screen.getByLabelText("Run timeline");
    expect(timeline).not.toHaveTextContent("event 1");
    expect(timeline).not.toHaveTextContent("event 2");
    expect(timeline).toHaveTextContent("event 3");
    expect(timeline).toHaveTextContent("event 7");
    expect(screen.getByText("Showing latest 5 of 7")).toBeInTheDocument();
  });

  it("shows a drawer count and switches detail between multiple active runs", async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    render(
      <RunActivityBar
        tasks={[
          task(),
          task({
            id: "task-2",
            run_name: "Conversion dry-run",
            pipeline: "DICOM conversion",
            status: "pending",
            progress: 0,
            duration: "",
            logs: ["Waiting for review"],
          }),
          task({
            id: "task-3",
            run_name: "QC report",
            pipeline: "rs-fMRI QC",
            status: "failed",
            progress: 88,
            logs: ["FD summary missing"],
          }),
        ]}
        selectedTaskId={null}
        onSelectTask={handleSelect}
      />,
    );

    expect(screen.getByText("+2")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /expand run activity/i }));

    expect(screen.getByLabelText("Run activity summary")).toHaveTextContent("1 running");
    expect(screen.getByLabelText("Run activity summary")).toHaveTextContent("1 pending");
    expect(screen.getByLabelText("Run activity summary")).toHaveTextContent("1 failed");

    const drawer = screen.getByLabelText("Run activity drawer");
    await user.click(within(drawer).getByRole("button", { name: /conversion dry-run/i }));

    expect(handleSelect).toHaveBeenCalledWith("task-2");
    expect(screen.getByLabelText("Selected run detail")).toHaveTextContent("Conversion dry-run");
    expect(screen.getByLabelText("Latest run log")).toHaveTextContent("Waiting for review");
  });
});
