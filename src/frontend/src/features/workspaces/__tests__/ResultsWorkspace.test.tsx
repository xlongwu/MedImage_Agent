import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ResultsWorkspace } from "../ResultsWorkspace";

vi.mock("../../../components/ArtifactBrowser", () => ({
  ArtifactBrowser: () => <div data-testid="artifact-browser">Artifact browser</div>,
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
  it("shows an artifact workflow overview without claiming loaded artifacts", () => {
    renderWorkspace();

    expect(screen.getByRole("heading", { name: "Artifact evidence boundary" })).toBeInTheDocument();
    expect(screen.getByLabelText("Artifact evidence states")).toHaveTextContent("Planned");
    expect(screen.getByLabelText("Artifact evidence states")).toHaveTextContent("Planned only");
    expect(screen.getByLabelText("Artifact evidence states")).toHaveTextContent(
      "Backend evidence required",
    );
    expect(screen.getByRole("table", { name: "Artifact handoff index" })).toHaveTextContent(
      "Artifact rows appear only after the Artifact Browser loads the backend index",
    );
    expect(screen.getByRole("table", { name: "Artifact state boundaries" })).toHaveTextContent(
      "Planned output",
    );
    expect(screen.getByRole("table", { name: "Artifact state boundaries" })).toHaveTextContent(
      "Missing provenance",
    );
    expect(screen.getByLabelText("Results artifact workflow")).toHaveTextContent(
      "Preview supported artifact",
    );
    expect(screen.getByLabelText("Results artifact workflow")).toHaveTextContent(
      "Check provenance",
    );
    expect(screen.getByRole("heading", { name: "Provenance checks" })).toBeInTheDocument();
    expect(screen.getByLabelText("Results module shortcuts")).toHaveTextContent(
      "Package Validation",
    );
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
