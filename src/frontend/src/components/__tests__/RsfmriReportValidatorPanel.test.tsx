import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RsfmriReportValidatorPanel } from "../RsfmriReportValidatorPanel";

const apiMocks = vi.hoisted(() => ({
  getLatestRsfmriReportValidation: vi.fn(),
  listRsfmriReportValidations: vi.fn(),
  runRsfmriReportValidation: vi.fn(),
}));

vi.mock("../../lib/api/legacy", () => apiMocks);

beforeEach(() => {
  apiMocks.getLatestRsfmriReportValidation.mockReset();
  apiMocks.listRsfmriReportValidations.mockReset();
  apiMocks.runRsfmriReportValidation.mockReset();
});

describe("RsfmriReportValidatorPanel", () => {
  it("loads latest validation evidence after a successful validation request", async () => {
    const user = userEvent.setup();
    apiMocks.runRsfmriReportValidation.mockResolvedValue({ ok: true, status: "SUCCESS" });
    apiMocks.getLatestRsfmriReportValidation.mockResolvedValue({
      validation_result: {
        validation_status: "WARNING",
        stats: {
          checksum_mismatch_total: 0,
          missing_files_total: 0,
          safety_violations_total: 0,
          zip_test_ok: true,
        },
        warnings: ["Using latest: rsfmri_export_20260706_220533"],
      },
      validation_report: "Validation completed with warnings.",
    });

    render(<RsfmriReportValidatorPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Validate Latest Package" }));

    expect(apiMocks.runRsfmriReportValidation).toHaveBeenCalledWith(
      "http://localhost",
      expect.objectContaining({
        pipeline_path: "examples/pipeline_rsfmri_report_validator.yaml",
      }),
    );
    expect(apiMocks.getLatestRsfmriReportValidation).toHaveBeenCalledWith("http://localhost");
    expect(await screen.findByText("Validated")).toBeInTheDocument();
    expect(screen.getByText("WARNING")).toBeInTheDocument();
    expect(screen.getByText("true")).toBeInTheDocument();
  });

  it("marks validation as validated only with pass status, zero issue counts, and ZIP test not false", async () => {
    const user = userEvent.setup();
    apiMocks.getLatestRsfmriReportValidation.mockResolvedValue({
      validation_result: {
        validation_status: "passed",
        stats: {
          checksum_mismatch_total: 0,
          missing_files_total: 0,
          safety_violations_total: 0,
          zip_test_ok: true,
        },
      },
    });

    render(<RsfmriReportValidatorPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Load Latest Validation" }));

    expect(await screen.findByText("Validated")).toBeInTheDocument();
    expect(screen.getByText(/zero mismatch/i)).toBeInTheDocument();
  });

  it("marks missing, mismatch, safety, or ZIP failures as validation failed", async () => {
    const user = userEvent.setup();
    apiMocks.getLatestRsfmriReportValidation.mockResolvedValue({
      validation_result: {
        validation_status: "passed",
        stats: {
          checksum_mismatch_total: 1,
          missing_files_total: 0,
          safety_violations_total: 0,
          zip_test_ok: false,
        },
      },
    });

    render(<RsfmriReportValidatorPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Load Latest Validation" }));

    expect(await screen.findByText("Validation failed")).toBeInTheDocument();
    expect(screen.queryByText("Validated")).not.toBeInTheDocument();
  });

  it("marks warning-only validation as validated when failure counts are zero", async () => {
    const user = userEvent.setup();
    apiMocks.getLatestRsfmriReportValidation.mockResolvedValue({
      validation_result: {
        validation_status: "WARNING",
        stats: {
          checksum_mismatch_total: 0,
          missing_files_total: 0,
          safety_violations_total: 0,
          zip_test_ok: true,
        },
        warnings: ["Using latest: rsfmri_export_20260706_220533"],
      },
    });

    render(<RsfmriReportValidatorPanel baseUrl="http://localhost" />);

    await user.click(screen.getByRole("button", { name: "Load Latest Validation" }));

    expect(await screen.findByText("Validated")).toBeInTheDocument();
    expect(screen.getByText(/completed with warnings/i)).toBeInTheDocument();
  });
});
