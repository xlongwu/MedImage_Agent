import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RsfmriReportExporterPanel } from "../RsfmriReportExporterPanel";

const apiMocks = vi.hoisted(() => ({
  getLatestRsfmriReportExport: vi.fn(),
  listRsfmriReportExports: vi.fn(),
  runRsfmriReportExport: vi.fn(),
}));

vi.mock("../../lib/api/rsfmri", () => apiMocks);

beforeEach(() => {
  apiMocks.getLatestRsfmriReportExport.mockReset();
  apiMocks.listRsfmriReportExports.mockReset();
  apiMocks.runRsfmriReportExport.mockReset();
});

describe("RsfmriReportExporterPanel", () => {
  it("loads latest package evidence after a successful generation request", async () => {
    const user = userEvent.setup();
    apiMocks.runRsfmriReportExport.mockResolvedValue({ ok: true, status: "SUCCESS" });
    apiMocks.getLatestRsfmriReportExport.mockResolvedValue({
      export_id: "exp-generated",
      export_summary: {
        exported_files_total: 10,
        exported_subjects_total: 0,
      },
      manifest: {
        files: ["README.md", "index.md"],
      },
      package_dir: "reports/exp-generated",
      zip_path: "reports/exp-generated.zip",
      zip_size_bytes: 6179,
    });

    render(<RsfmriReportExporterPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Generate Report Package" }));

    expect(apiMocks.runRsfmriReportExport).toHaveBeenCalledWith(
      "http://localhost",
      expect.objectContaining({
        pipeline_path: "examples/pipeline_rsfmri_report_exporter.yaml",
      }),
    );
    expect(apiMocks.getLatestRsfmriReportExport).toHaveBeenCalledWith("http://localhost");
    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(screen.getByText("exp-generated")).toBeInTheDocument();
    expect(screen.getByText("6179")).toBeInTheDocument();
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
      zip_size_bytes: 6179,
    });

    render(<RsfmriReportExporterPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Load Latest" }));

    expect(await screen.findByText("Created")).toBeInTheDocument();
    expect(screen.getByText("exp-001")).toBeInTheDocument();
    expect(screen.getByText("6179")).toBeInTheDocument();
    expect(screen.queryByText("Validated")).not.toBeInTheDocument();
  });
});
