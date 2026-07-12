import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ImportDiagnosticsPanel from "../ImportDiagnosticsPanel";

const apiMocks = vi.hoisted(() => ({
  createImportDiagnosticsPackage: vi.fn(),
  getDatasetImportHistory: vi.fn(),
  getDicomPreflight: vi.fn(),
  getImageManifestReport: vi.fn(),
  getImageValidationReport: vi.fn(),
  getLatestImportDiagnosticsPackage: vi.fn(),
  verifyImportDiagnosticsPackage: vi.fn(),
}));

vi.mock("../../lib/api/diagnostic", () => ({
  createImportDiagnosticsPackage: apiMocks.createImportDiagnosticsPackage,
  getDatasetImportHistory: apiMocks.getDatasetImportHistory,
  getLatestImportDiagnosticsPackage: apiMocks.getLatestImportDiagnosticsPackage,
  verifyImportDiagnosticsPackage: apiMocks.verifyImportDiagnosticsPackage,
}));
vi.mock("../../lib/api/dicom", () => ({ getDicomPreflight: apiMocks.getDicomPreflight }));
vi.mock("../../lib/api/qc", () => ({
  getImageManifestReport: apiMocks.getImageManifestReport,
  getImageValidationReport: apiMocks.getImageValidationReport,
}));

describe("ImportDiagnosticsPanel", () => {
  beforeEach(() => {
    apiMocks.createImportDiagnosticsPackage.mockReset();
    apiMocks.getDatasetImportHistory.mockReset();
    apiMocks.getDicomPreflight.mockReset();
    apiMocks.getImageManifestReport.mockReset();
    apiMocks.getImageValidationReport.mockReset();
    apiMocks.getLatestImportDiagnosticsPackage.mockReset();
    apiMocks.verifyImportDiagnosticsPackage.mockReset();

    apiMocks.getImageValidationReport.mockResolvedValue({
      ok: true,
      issue_count: 0,
      issues: [],
    });
    apiMocks.getImageManifestReport.mockResolvedValue({
      ok: true,
      source_count: 1,
      warnings: [],
    });
    apiMocks.getDatasetImportHistory.mockResolvedValue({
      ok: true,
      imports: [],
    });
    apiMocks.getLatestImportDiagnosticsPackage.mockResolvedValue({
      ok: true,
      latest: null,
    });
    apiMocks.getDicomPreflight.mockResolvedValue({
      ok: true,
      dicom_file_count: 1104,
      sampled_file_count: 2000,
      series_count: 6,
      series: [],
      subjects: ["sub-001"],
      modalities: ["MR"],
      warnings: [],
      errors: [],
    });
  });

  it("loads active project id and rawdata context into diagnostics inputs", async () => {
    render(
      <ImportDiagnosticsPanel
        baseUrl="http://localhost"
        projectId="project-1"
        rawdataDir={"D:\\DemoData\\rawdata"}
      />,
    );

    expect(screen.getByLabelText("Project ID")).toHaveValue("project-1");
    expect(screen.getByLabelText("Active project context")).toHaveValue(
      "project-1 | D:\\DemoData\\rawdata",
    );
    expect(screen.getByLabelText("DICOM root")).toHaveValue("D:\\DemoData\\rawdata");

    await waitFor(() =>
      expect(apiMocks.getDicomPreflight).toHaveBeenCalledWith(
        "http://localhost",
        "project-1",
        "D:\\DemoData\\rawdata",
        2000,
      ),
    );
  });

  it("explains that zero DICOM preflight counts mean diagnostics input is missing", () => {
    render(<ImportDiagnosticsPanel baseUrl="http://localhost" />);

    expect(screen.getByText(/DICOM diagnostics input is not configured/i)).toBeInTheDocument();
    expect(
      screen.getByText(/does not mean the active project has no raw DICOM data/i),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /No DICOM series metadata loaded because diagnostics input is not configured/i,
      ),
    ).toBeInTheDocument();
  });
});
