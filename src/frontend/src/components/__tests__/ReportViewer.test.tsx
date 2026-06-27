import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ReportViewer } from "../ReportViewer";

const apiMocks = vi.hoisted(() => ({
  getDatasetEvaluationReport: vi.fn(),
}));

vi.mock("../../lib/api/legacy", () => apiMocks);

beforeEach(() => {
  apiMocks.getDatasetEvaluationReport.mockReset();
});

describe("ReportViewer", () => {
  it("starts as backend-required before report evidence is loaded", () => {
    render(<ReportViewer baseUrl="http://localhost" />);

    expect(screen.getByText("Backend evidence required")).toBeInTheDocument();
    expect(screen.getByText(/No report response has been loaded/i)).toBeInTheDocument();
  });

  it("treats a summary-only report as metadata-only", async () => {
    const user = userEvent.setup();
    apiMocks.getDatasetEvaluationReport.mockResolvedValue({
      ok: true,
      dataset_summary: { subjects: 2 },
      exclusion_recommendations: null,
      report_html: null,
      report_markdown: null,
      subject_qc_table: null,
    });

    render(<ReportViewer baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Refresh report" }));

    expect(apiMocks.getDatasetEvaluationReport).toHaveBeenCalledWith("http://localhost");
    expect(await screen.findByText("Metadata only")).toBeInTheDocument();
    expect(screen.queryByText("Created")).not.toBeInTheDocument();
  });

  it("marks report content as created without claiming validation", async () => {
    const user = userEvent.setup();
    apiMocks.getDatasetEvaluationReport.mockResolvedValue({
      ok: true,
      dataset_summary: { subjects: 2 },
      exclusion_recommendations: null,
      report_html: null,
      report_markdown: "# QC report",
      subject_qc_table: null,
    });

    render(<ReportViewer baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Refresh report" }));

    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(screen.queryByText("Validated")).not.toBeInTheDocument();
  });
});
