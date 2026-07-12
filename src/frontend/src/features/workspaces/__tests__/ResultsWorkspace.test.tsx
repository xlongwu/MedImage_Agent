import { fireEvent, render, screen, within } from "@testing-library/react";
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
    expect(screen.getByLabelText("Migrated report modules")).toHaveTextContent("On demand");
    expect(
      within(screen.getByLabelText("Migrated report modules")).getByTitle(
        "Backend evidence is required before this state can be treated as complete.",
      ),
    ).toHaveTextContent("On demand");
    expect(screen.queryByTestId("report-viewer")).not.toBeInTheDocument();
  });

  it("keeps artifact, export, and validation modules available for selected projects", () => {
    renderWorkspace();

    expect(screen.getByTestId("artifact-browser")).toBeInTheDocument();
    expect(screen.getByTestId("artifact-browser")).toHaveTextContent("project-1");
    expect(screen.getByTestId("rsfmri-report-exporter")).toBeInTheDocument();
    expect(screen.getByTestId("rsfmri-report-validator")).toBeInTheDocument();
  });

  it("opens report modules on demand", () => {
    renderWorkspace();

    fireEvent.click(screen.getByRole("button", { name: "Open report modules" }));

    expect(screen.getByTestId("rsfmri-group-summary-panel")).toBeInTheDocument();
    expect(screen.getByTestId("report-viewer")).toBeInTheDocument();
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
