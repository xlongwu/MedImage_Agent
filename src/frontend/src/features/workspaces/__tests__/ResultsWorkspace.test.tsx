import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import { ResultsWorkspace } from "../ResultsWorkspace";

vi.mock("../../../components/ArtifactBrowser", () => ({
  ArtifactBrowser: ({ projectId }: { projectId?: string | null }) => (
    <div data-testid="artifact-browser">Artifact browser {projectId}</div>
  ),
}));

vi.mock("../../../components/ReportViewer", () => ({
  ReportViewer: () => <div data-testid="report-viewer">Report viewer</div>,
}));

vi.mock("../../../components/RsfmriGroupSummaryPanel", () => ({
  RsfmriGroupSummaryPanel: () => (
    <div data-testid="rsfmri-group-summary-panel">Group summary panel</div>
  ),
}));

vi.mock("../../../components/RsfmriReportExporterPanel", () => ({
  RsfmriReportExporterPanel: () => <div data-testid="rsfmri-report-exporter">Report exporter</div>,
}));

vi.mock("../../../components/RsfmriReportValidatorPanel", () => ({
  RsfmriReportValidatorPanel: () => (
    <div data-testid="rsfmri-report-validator">Report validator</div>
  ),
}));

function renderWorkspace(projectId: string | null = "project-1") {
  render(<ResultsWorkspace baseUrl="http://localhost" projectId={projectId} />);
}

describe("ResultsWorkspace", () => {
  it("renders project-scoped result gates in simplified Chinese", () => {
    render(
      <I18nProvider locale="zh-CN">
        <ResultsWorkspace baseUrl="http://localhost" projectId={null} />
      </I18nProvider>,
    );

    expect(screen.getByText("检查结果前请选择项目")).toBeInTheDocument();
    expect(screen.getByLabelText("产物与报告模块")).toHaveTextContent("结果模块正在等待项目上下文");
    expect(screen.getByRole("button", { name: "打开报告模块" })).toBeDisabled();
  });

  it("shows the artifact browser beside an explicit empty viewer without claiming artifacts", () => {
    renderWorkspace();

    expect(
      screen.getByRole("region", { name: "Artifact browser and image viewer" }),
    ).toHaveTextContent("Artifact browser project-1");
    expect(screen.getByText("No preview selected")).toBeInTheDocument();
    expect(screen.queryByText("FC Matrix (12x12)")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Migrated report modules")).toHaveTextContent("Unavailable");
    expect(screen.queryByTestId("report-viewer")).not.toBeInTheDocument();
  });

  it("keeps the real artifact browser available and disables legacy report actions", () => {
    renderWorkspace();

    expect(screen.getByTestId("artifact-browser")).toBeInTheDocument();
    expect(screen.getByTestId("artifact-browser")).toHaveTextContent("project-1");
    expect(screen.queryByTestId("rsfmri-report-exporter")).not.toBeInTheDocument();
    expect(screen.queryByTestId("rsfmri-report-validator")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Artifact and report modules")).toHaveTextContent(
      "Legacy report export, validation, and group-summary actions are unavailable",
    );
  });

  it("does not expose report controls backed by rejected legacy endpoints", () => {
    renderWorkspace();

    expect(screen.getByRole("button", { name: "Open report modules" })).toBeDisabled();
    expect(screen.queryByTestId("rsfmri-group-summary-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("report-viewer")).not.toBeInTheDocument();
  });

  it("does not render result modules until a project is selected", () => {
    renderWorkspace(null);

    expect(screen.getByText("Select a project before reviewing results")).toBeInTheDocument();
    expect(screen.getByText("Result modules are waiting for project context")).toBeInTheDocument();
    expect(screen.queryByTestId("artifact-browser")).not.toBeInTheDocument();
    expect(screen.queryByRole("table", { name: "Artifact handoff index" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open report modules" })).toBeDisabled();
  });
});
