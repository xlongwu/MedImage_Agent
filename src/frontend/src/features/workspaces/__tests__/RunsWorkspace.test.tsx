import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import { RunsWorkspace } from "../RunsWorkspace";
import type {
  TaskDiagnostics,
  TaskEvent,
  TaskLogEntry,
  TaskStatus,
} from "../../../lib/types/task";

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

function diagnostics(overrides: Partial<TaskDiagnostics> = {}): TaskDiagnostics {
  return {
    ok: true,
    task_id: "task-1",
    status: "running",
    diagnosis: [],
    external_tool_results: [],
    logs: [],
    artifacts: {},
    approval: null,
    errors: [],
    warnings: [],
    ...overrides,
  };
}

function event(overrides: Partial<TaskEvent> = {}): TaskEvent {
  return {
    id: 1,
    task_id: "task-1",
    status: "running" as TaskStatus,
    progress: 42,
    message: "Running motion correction",
    timestamp: "2026-06-24T08:01:00Z",
    source: "websocket",
    metadata: {},
    ...overrides,
  };
}

function renderWorkspace(overrides: Partial<ComponentProps<typeof RunsWorkspace>> = {}) {
  const selectedTask = task();
  const props: ComponentProps<typeof RunsWorkspace> = {
    auditLoading: false,
    auditPackage: null,
    diagnostics: diagnostics(),
    error: "",
    events: [event()],
    eventsError: "",
    eventsLoading: false,
    loading: false,
    onApprovalNameChange: vi.fn(),
    onApprove: vi.fn(),
    onGenerateAudit: vi.fn(),
    onReconnect: vi.fn(),
    onRetryEvents: vi.fn(),
    onRetryTasks: vi.fn(),
    onSelectTask: vi.fn(),
    projectId: "project-1",
    selectedTask,
    selectedTaskId: selectedTask.id,
    streamConnected: true,
    taskApprovalName: "",
    tasks: [
      selectedTask,
      task({
        id: "task-2",
        run_name: "QC report",
        pipeline: "rs-fMRI QC",
        status: "failed",
        progress: 88,
        logs: ["FD summary missing"],
      }),
      task({
        id: "task-3",
        run_name: "Completed export",
        pipeline: "Report export",
        status: "completed",
        progress: 100,
      }),
    ],
  };

  render(<RunsWorkspace {...props} {...overrides} />);
  return { props };
}

describe("RunsWorkspace", () => {
  it("shows run history summary, table, and selected run details", async () => {
    const user = userEvent.setup();
    renderWorkspace();

    expect(screen.getByRole("heading", { name: "Runs" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Execution runs" })).toBeInTheDocument();
    expect(screen.getByText(/backend task runs only/i)).toBeInTheDocument();
    expect(screen.getByLabelText("Run history overview")).toHaveTextContent("3");
    expect(screen.getByRole("table", { name: "Project run history" })).toHaveTextContent(
      "Preprocessing run",
    );
    expect(screen.getByRole("table", { name: "Project run history" })).toHaveTextContent(
      "QC report",
    );
    expect(screen.getByRole("table", { name: "Project run history" })).toHaveTextContent("Demo");
    expect(screen.getByRole("table", { name: "Project run history" })).toHaveTextContent("2m");
    expect(screen.getByLabelText("Selected run detail")).toHaveTextContent("Preprocessing run");
    expect(screen.getByLabelText("Run facts")).toHaveTextContent("rs-fMRI preprocessing");
    expect(screen.getByLabelText("Pipeline timeline")).toHaveTextContent(
      "Running motion correction",
    );
    expect(screen.getByLabelText("Selected node inspector")).toHaveTextContent(
      "rs-fMRI preprocessing",
    );

    await user.click(screen.getByRole("radio", { name: "Logs" }));

    expect(screen.getByLabelText("Run logs")).toHaveTextContent("Running motion correction");
  });

  it("selects a run from the list", async () => {
    const user = userEvent.setup();
    const onSelectTask = vi.fn();
    renderWorkspace({ onSelectTask });

    await user.click(screen.getAllByRole("button", { name: "Open" })[1]);

    expect(onSelectTask).toHaveBeenCalledWith("task-2");
  });

  it("caps long run logs with an explicit rendering budget note", async () => {
    const user = userEvent.setup();
    const longLogs = Array.from({ length: 18 }, (_, index) => `Log line ${index + 1}`);

    renderWorkspace({
      selectedTask: task({ logs: longLogs }),
    });

    await user.click(screen.getByRole("radio", { name: "Logs" }));

    expect(screen.getByRole("status")).toHaveTextContent("Showing latest 12 of 18 log lines");
    expect(screen.queryByText("Log line 1")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Run logs")).toHaveTextContent("Log line 18");
  });

  it("filters runs by status and search text", async () => {
    const user = userEvent.setup();
    renderWorkspace();

    await user.click(screen.getByRole("radio", { name: "Failed" }));

    const table = screen.getByRole("table", { name: "Project run history" });
    expect(table).toHaveTextContent("QC report");
    expect(table).not.toHaveTextContent("Preprocessing run");

    await user.type(screen.getByLabelText("Search runs"), "motion");

    expect(table).toHaveTextContent("No runs match the current search and status filters");
  });

  it("separates empty, loading, and error-without-rows states", () => {
    renderWorkspace({
      error: "Backend unavailable",
      loading: false,
      selectedTask: null,
      selectedTaskId: null,
      tasks: [],
    });

    const table = screen.getByRole("table", { name: "Project run history" });

    expect(table).toHaveTextContent("Run history unavailable");
    expect(screen.getByText(/Backend unavailable/)).toBeInTheDocument();
    expect(table).not.toHaveTextContent("No runs match the current search");
  });

  it("keeps stale rows visible when refresh fails with existing rows", () => {
    renderWorkspace({
      error: "Refresh failed",
      loading: false,
    });

    const table = screen.getByRole("table", { name: "Project run history" });

    expect(screen.getByText(/showing last loaded rows/i)).toBeInTheDocument();
    expect(table).toHaveTextContent("Preprocessing run");
    expect(screen.getByLabelText("Run stream status")).toHaveTextContent("Run stream connected");
  });

  it("does not show stream disconnection as an error when no run is active", () => {
    renderWorkspace({
      selectedTask: task({ status: "completed", progress: 100 }),
      streamConnected: false,
      tasks: [task({ status: "completed", progress: 100 })],
    });

    expect(screen.getByLabelText("Run stream status")).toHaveTextContent("No active run stream");
    expect(screen.getByLabelText("Selected run detail")).toHaveTextContent("No active stream");
    expect(screen.queryByText("Stream disconnected")).not.toBeInTheDocument();
  });

  it("shows diagnostics, artifact, and audit detail sections", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });

    renderWorkspace({
      selectedTask: task({
        status: "failed",
        progress: 88,
        result_path: "outputs/run-1/report.json",
        logs: ["FD summary missing"],
      }),
      diagnostics: diagnostics({
        status: "failed",
        errors: ["Motion QC failed"],
        warnings: ["FD threshold exceeded"],
        diagnosis: [{ code: "motion_qc", severity: "error", message: "Mean FD above threshold" }],
        artifacts: { report: "outputs/run-1/report.json" },
      }),
      auditPackage: {
        ok: true,
        task_id: "task-1",
        generated_at: "2026-06-24T08:05:00Z",
        package_dir: "audit/task-1",
        report_path: "audit/task-1/report.md",
        json_path: "audit/task-1/report.json",
        report_text: "audit",
        artifacts: {},
        errors: [],
      },
    });

    await user.click(screen.getByRole("radio", { name: "Diagnostics" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Failed run");
    expect(screen.getByLabelText("Failed node actions")).toHaveTextContent("Failed node response");
    expect(screen.getByRole("button", { name: "Retry Allowed Step" })).toBeDisabled();

    await user.click(screen.getByRole("button", { name: "Explain Error" }));

    expect(screen.getByLabelText("Failure explanation")).toHaveTextContent("motion_qc");

    await user.click(screen.getByRole("button", { name: "Copy Diagnostics" }));

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Motion QC failed"));
    expect(screen.getByLabelText("Failed node actions")).toHaveTextContent("Diagnostics copied");
    expect(screen.getByLabelText("Run diagnostics")).toHaveTextContent("Motion QC failed");
    expect(screen.getByLabelText("Run diagnostics")).toHaveTextContent("Mean FD above threshold");

    await user.click(screen.getByRole("radio", { name: "Artifacts" }));

    expect(screen.getByLabelText("Run artifacts")).toHaveTextContent("outputs/run-1/report.json");

    await user.click(screen.getByRole("radio", { name: "Audit" }));

    expect(screen.getByLabelText("Run audit")).toHaveTextContent("audit/task-1/report.md");
    expect(screen.getByLabelText("Run audit")).toHaveTextContent("audit/task-1/report.json");
  });

  it("uses an explicit empty state when no project is selected", () => {
    renderWorkspace({
      projectId: null,
      selectedTask: null,
      selectedTaskId: null,
      tasks: [],
    });

    expect(screen.getByText("Select a project before reviewing runs")).toBeInTheDocument();
    expect(screen.getByText("Run list unavailable")).toBeInTheDocument();
    expect(screen.getByText("Select a run to inspect")).toBeInTheDocument();
  });
});
