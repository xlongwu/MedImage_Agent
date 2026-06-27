import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RsfmriReportExporterPanel } from "../RsfmriReportExporterPanel";

const apiMocks = vi.hoisted(() => ({
  getLatestRsfmriReportExport: vi.fn(),
  listRsfmriReportExports: vi.fn(),
  runRsfmriReportExport: vi.fn(),
}));

vi.mock("../../lib/api/legacy", () => apiMocks);

beforeEach(() => {
  apiMocks.getLatestRsfmriReportExport.mockReset();
  apiMocks.listRsfmriReportExports.mockReset();
  apiMocks.runRsfmriReportExport.mockReset();
});

describe("RsfmriReportExporterPanel", () => {
  it("keeps a successful request as metadata-only until package evidence exists", async () => {
    const user = userEvent.setup();
    apiMocks.runRsfmriReportExport.mockResolvedValue({ ok: true, status: "accepted" });

    render(<RsfmriReportExporterPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Generate Report Package" }));

    expect(apiMocks.runRsfmriReportExport).toHaveBeenCalledWith(
      "http://localhost",
      expect.objectContaining({
        pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml",
      }),
    );
    expect(await screen.findByText("Metadata only")).toBeInTheDocument();
    expect(screen.getByText("Request complete")).toBeInTheDocument();
    expect(screen.queryByText("Validated")).not.toBeInTheDocument();
  });

  it("marks exports as created only when package fields are present", async () => {
    const user = userEvent.setup();
    apiMocks.getLatestRsfmriReportExport.mockResolvedValue({
      export_id: "exp-001",
      export_summary: {
        exported_files_total: 3,
        exported_subjects_total: 2,
      },
      manifest: {
        files: ["README.md", "index.md"],
      },
      package_dir: "reports/exp-001",
      zip_path: "reports/exp-001.zip",
    });

    render(<RsfmriReportExporterPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Load Latest" }));

    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(screen.getByText("exp-001")).toBeInTheDocument();
    expect(screen.queryByText("Validated")).not.toBeInTheDocument();
  });
});
