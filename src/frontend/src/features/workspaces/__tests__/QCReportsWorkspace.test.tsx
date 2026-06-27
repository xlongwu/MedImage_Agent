import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { QCReportsWorkspace } from "../QCReportsWorkspace";

vi.mock("../../../components/QcDashboardSummaryPanel", () => ({
  default: () => <div data-testid="qc-dashboard-summary-panel">QC dashboard summary panel</div>,
}));

vi.mock("../../../components/NiftiQcSnapshotPanel", () => ({
  default: () => <div data-testid="nifti-qc-snapshot-panel">NIfTI QC snapshot panel</div>,
}));

vi.mock("../../../components/BoldReferenceReadinessPanel", () => ({
  default: () => (
    <div data-testid="bold-reference-readiness-panel">BOLD reference readiness panel</div>
  ),
}));

vi.mock("../../../components/MotionQcReadinessPanel", () => ({
  default: () => <div data-testid="motion-qc-readiness-panel">Motion QC readiness panel</div>,
}));

vi.mock("../../../components/MotionMetricsDraftPanel", () => ({
  default: () => <div data-testid="motion-metrics-draft-panel">Motion metrics draft panel</div>,
}));

vi.mock("../../../components/RsfmriQcPlanningReportPanel", () => ({
  default: () => (
    <div data-testid="rsfmri-qc-planning-report-panel">rs-fMRI QC planning report panel</div>
  ),
}));

vi.mock("../../../components/RsfmriNuisanceRegressionPanel", () => ({
  RsfmriNuisanceRegressionPanel: () => (
    <div data-testid="nuisance-regression-panel">Nuisance regression panel</div>
  ),
}));

vi.mock("../../../components/RsfmriTemporalFilteringPanel", () => ({
  RsfmriTemporalFilteringPanel: () => (
    <div data-testid="temporal-filtering-panel">Temporal filtering panel</div>
  ),
}));

vi.mock("../../../components/RsfmriMotionQcPanel", () => ({
  RsfmriMotionQcPanel: () => <div data-testid="motion-qc-panel">Motion QC panel</div>,
}));

vi.mock("../../../components/RsfmriAlffFalffPanel", () => ({
  RsfmriAlffFalffPanel: () => <div data-testid="alff-falff-panel">ALFF fALFF panel</div>,
}));

vi.mock("../../../components/RsfmriRehoPanel", () => ({
  RsfmriRehoPanel: () => <div data-testid="reho-panel">ReHo panel</div>,
}));

vi.mock("../../../components/RsfmriFunctionalConnectivityPanel", () => ({
  RsfmriFunctionalConnectivityPanel: () => (
    <div data-testid="functional-connectivity-panel">Functional connectivity panel</div>
  ),
}));

function renderWorkspace(projectId: string | null = "project-1") {
  render(<QCReportsWorkspace baseUrl="http://localhost" projectId={projectId} />);
}

describe("QCReportsWorkspace", () => {
  it("shows a unified QC dashboard before detailed modules", () => {
    renderWorkspace();

    expect(
      screen.getByRole("heading", { name: "Evidence-first QC dashboard" }),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("QC summary states")).toHaveTextContent("Evidence");
    expect(screen.getByLabelText("QC summary states")).toHaveTextContent("No pass/fail decision");
    expect(screen.getByRole("table", { name: "Subject-level QC status" })).toHaveTextContent(
      "Subject rows appear only after dashboard reports",
    );
    expect(screen.getByLabelText("QC outlier focus areas")).toHaveTextContent("Motion outliers");
    expect(screen.getByLabelText("Image comparison artifact gate")).toHaveTextContent(
      "No comparison artifact is available",
    );
    expect(screen.getByLabelText("Image comparison artifact states")).toHaveTextContent(
      "Partial artifact",
    );
    expect(screen.queryByRole("button", { name: "Sync slices" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Opacity locked" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Before / after" })).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "QC chart contract" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Visualization contract" })).toBeInTheDocument();
    expect(screen.getByLabelText("QC visualization requirements")).toHaveTextContent("Unit");
    expect(screen.getByLabelText("QC visualization requirements")).toHaveTextContent("Threshold");
    expect(screen.getByLabelText("QC visualization requirements")).toHaveTextContent("Data range");
    expect(screen.getByLabelText("QC visualization requirements")).toHaveTextContent("Drill-down");
    expect(screen.getByLabelText("Detailed QC modules")).toBeInTheDocument();
    expect(screen.getByLabelText("Derived metric modules")).toHaveTextContent("On demand");
    expect(screen.queryByTestId("alff-falff-panel")).not.toBeInTheDocument();
  });

  it("keeps the existing detailed QC panels available for selected projects", () => {
    renderWorkspace();

    expect(screen.getByTestId("qc-dashboard-summary-panel")).toBeInTheDocument();
    expect(screen.getByTestId("nifti-qc-snapshot-panel")).toBeInTheDocument();
    expect(screen.getByTestId("bold-reference-readiness-panel")).toBeInTheDocument();
    expect(screen.getByTestId("motion-qc-readiness-panel")).toBeInTheDocument();
    expect(screen.getByTestId("motion-metrics-draft-panel")).toBeInTheDocument();
    expect(screen.getByTestId("rsfmri-qc-planning-report-panel")).toBeInTheDocument();
  });

  it("does not render detailed QC modules until a project is selected", () => {
    renderWorkspace(null);

    expect(screen.getByText("Select a project before QC review")).toBeInTheDocument();
    expect(screen.getByText("QC modules are waiting for project context")).toBeInTheDocument();
    expect(screen.queryByTestId("qc-dashboard-summary-panel")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Subject-level QC status" }),
    ).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open derived modules" })).toBeDisabled();
  });

  it("opens migrated derived metric modules on demand", () => {
    renderWorkspace();

    expect(screen.queryByTestId("nuisance-regression-panel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open derived modules" }));

    expect(screen.getByTestId("nuisance-regression-panel")).toBeInTheDocument();
    expect(screen.getByTestId("temporal-filtering-panel")).toBeInTheDocument();
    expect(screen.getByTestId("motion-qc-panel")).toBeInTheDocument();
    expect(screen.getByTestId("alff-falff-panel")).toBeInTheDocument();
    expect(screen.getByTestId("reho-panel")).toBeInTheDocument();
    expect(screen.getByTestId("functional-connectivity-panel")).toBeInTheDocument();
  });
});
