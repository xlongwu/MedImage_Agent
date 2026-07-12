import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../i18n/I18nProvider";
import { ReportViewer } from "../ReportViewer";

const apiMocks = vi.hoisted(() => ({
  getDatasetEvaluationReport: vi.fn(),
}));

vi.mock("../../lib/api/qc", () => apiMocks);

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

  it("renders report controls and empty content in Chinese", async () => {
    const user = userEvent.setup();
    apiMocks.getDatasetEvaluationReport.mockResolvedValue({
      ok: true,
      dataset_summary: null,
      exclusion_recommendations: null,
      report_html: null,
      report_markdown: null,
      subject_qc_table: null,
    });

    render(
      <I18nProvider locale="zh-CN">
        <ReportViewer baseUrl="http://localhost" />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: "数据集报告" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "刷新报告" }));
    expect(await screen.findByText("报告响应已加载，但没有报告产物。")).toBeInTheDocument();
    expect(screen.getByText("尚未加载数据集摘要。")).toBeInTheDocument();
  });
});
