import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import { getLatestConversionDryRun, runConversionDryRun } from "../../../lib/api/dicom";
import { DataConversionWorkspace } from "../DataConversionWorkspace";

vi.mock("../../../components/BidsValidationPanel", () => ({
  default: () => <div data-testid="bids-validation-panel">BIDS validation panel</div>,
}));

vi.mock("../../../components/DataReadinessPanel", () => ({
  default: () => <div data-testid="data-readiness-panel">Data readiness panel</div>,
}));

vi.mock("../../../components/ConversionDryRunPanel", () => ({
  default: () => <div data-testid="conversion-dry-run-panel">Conversion dry-run panel</div>,
}));

vi.mock("../../../components/DicomConversionReviewPanel", () => ({
  default: () => <div data-testid="dicom-review-panel">DICOM review panel</div>,
}));

vi.mock("../../../lib/api/dicom", () => ({
  getLatestConversionDryRun: vi.fn(),
  runConversionDryRun: vi.fn(),
}));

function inventory(overrides: Partial<ProjectInventory> = {}): ProjectInventory {
  return {
    projectName: "Demo Project",
    modality: "rs-fMRI",
    dataState: "raw_dicom",
    dataStateLabel: "Raw DICOM",
    stateSentence: "Raw DICOM data detected.",
    rawDicomCandidates: 3,
    dicomSeriesCount: 9,
    dicomFileCount: 1200,
    convertedSubjects: 0,
    niftiFileCount: 0,
    hasRawDicom: true,
    hasConvertedData: false,
    metadataOnlyNiftiInventory: false,
    ...overrides,
  };
}

describe("DataConversionWorkspace", () => {
  beforeEach(() => {
    vi.mocked(getLatestConversionDryRun).mockReset();
    vi.mocked(getLatestConversionDryRun).mockResolvedValue({
      ok: false,
      project_id: "project-1",
      status: "blocked",
      dry_run: true,
      checked_at: "2026-06-25T00:00:00Z",
      target_layout: "bids",
      output_root_name: "converted_bids",
      source_summaries: [],
      mapping_preview: [],
      blocking_issues: ["No persisted dry-run review package was found; refresh is required."],
      warnings: [],
      next_actions: ["Refresh the conversion dry-run preview for the active project."],
      safety_flags: { dry_run_only: true },
    });
    vi.mocked(runConversionDryRun).mockReset();
  });

  it("prioritizes raw DICOM inventory and keeps detailed panels secondary", async () => {
    const user = userEvent.setup();
    const onSelectedDataSeriesChange = vi.fn();

    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory()}
        onSelectedDataSeriesChange={onSelectedDataSeriesChange}
      />,
    );

    expect(screen.getByRole("heading", { name: "DICOM series browser" })).toBeInTheDocument();
    expect(
      await screen.findByRole("button", { name: "Refresh dry-run preview" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/refresh is required/i)).toBeInTheDocument();
    expect(screen.getByLabelText("DICOM inventory summary")).toHaveTextContent("Refresh required");
    expect(screen.getByLabelText("Conversion readiness")).toHaveTextContent(
      "Start the no-write dry-run from the DICOM series browser",
    );
    expect(screen.getByRole("table", { name: /source group/i })).toHaveTextContent(
      "Project inventory summary",
    );
    expect(screen.getByLabelText("DICOM conversion steps")).toHaveTextContent("Source Detection");
    expect(screen.getByLabelText("DICOM conversion steps")).toHaveTextContent(
      "Approved Conversion",
    );
    expect(screen.getByLabelText("Detailed data checks")).toBeInTheDocument();
    expect(screen.getByLabelText("Detailed data checks")).toHaveTextContent(
      "Backend gates remain authoritative",
    );
    expect(screen.queryByTestId("conversion-dry-run-panel")).not.toBeInTheDocument();

    await user.click(screen.getByLabelText("Select 9 series"));
    expect(onSelectedDataSeriesChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        evidenceLevel: "metadata_only",
        series: "9 series",
        subject: "3 candidates",
      }),
    );

    await user.click(screen.getByRole("button", { name: "Open detailed checks" }));

    expect(screen.getByTestId("conversion-dry-run-panel")).toBeInTheDocument();
    expect(screen.getByTestId("dicom-review-panel")).toBeInTheDocument();
  });

  it("loads dry-run mappings into the DICOM series browser", async () => {
    const user = userEvent.setup();
    vi.mocked(runConversionDryRun).mockResolvedValue({
      ok: true,
      project_id: "project-1",
      status: "ready",
      dry_run: true,
      checked_at: "2026-06-25T00:00:00Z",
      target_layout: "bids",
      output_root_name: "rawdata",
      output_root_preview: "D:\\study\\rawdata",
      source_summaries: [
        {
          source_id: "source-1",
          source_type: "dicom",
          root: "D:\\study\\dicom",
          exists: true,
          file_count: 1200,
          subject_candidates: ["sub-01"],
          series_count: 2,
          warnings: [],
        },
      ],
      mapping_preview: [
        {
          source_path: "D:\\study\\dicom\\sub-01\\REST",
          source_series_uid: "1.2.3",
          source_type: "dicom_series",
          subject_id: "sub-01",
          session_id: "ses-01",
          modality: "func",
          suffix: "bold",
          task: "rest",
          suggested_relative_path: "sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
          confidence: "high",
          warnings: [],
        },
      ],
      blocking_issues: [],
      warnings: [],
      next_actions: ["Review mapping preview."],
      safety_flags: { dry_run_only: true },
    });

    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory()}
      />,
    );

    await user.click(await screen.findByRole("button", { name: "Refresh dry-run preview" }));

    await waitFor(() =>
      expect(runConversionDryRun).toHaveBeenCalledWith("http://localhost", "project-1"),
    );
    expect(await screen.findByText("sub-01")).toBeInTheDocument();
    expect(
      screen.getByText("sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz"),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("DICOM conversion steps")).toHaveTextContent(
      "1 suggested mapping",
    );
  });

  it("restores persisted dry-run mappings on project load", async () => {
    vi.mocked(getLatestConversionDryRun).mockResolvedValue({
      ok: true,
      project_id: "project-1",
      status: "ready",
      dry_run: true,
      checked_at: "2026-06-25T00:00:00Z",
      target_layout: "bids",
      output_root_name: "converted_bids",
      source_summaries: [],
      mapping_preview: [
        {
          source_path: "D:\\study\\dicom\\sub-01\\REST",
          source_series_uid: "1.2.3",
          source_type: "dicom_series",
          subject_id: "sub-01",
          session_id: "ses-01",
          modality: "func",
          suffix: "bold",
          task: "rest",
          suggested_relative_path: "sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
          confidence: "high",
          warnings: [],
        },
      ],
      blocking_issues: [],
      warnings: ["Restored dry-run mappings from persisted review package conv-1."],
      next_actions: ["Review restored mappings before using them as approval material."],
      safety_flags: { dry_run_only: true, restored_from_persisted_review_package: true },
    });

    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory()}
      />,
    );

    expect(await screen.findByText("sub-01")).toBeInTheDocument();
    expect(screen.getByLabelText("DICOM conversion steps")).toHaveTextContent(
      "1 suggested mapping",
    );
    expect(runConversionDryRun).not.toHaveBeenCalled();
  });

  it("shows converted inventory summary for BIDS/NIfTI projects", () => {
    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory({
          dataState: "converted_bids",
          dataStateLabel: "Converted BIDS/NIfTI",
          rawDicomCandidates: 0,
          dicomSeriesCount: 0,
          dicomFileCount: 0,
          convertedSubjects: 4,
          niftiFileCount: 24,
          hasRawDicom: false,
          hasConvertedData: true,
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Converted imaging inventory" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "Converted data readiness summary" }),
    ).toHaveTextContent("Converted subjects");
    expect(
      screen.queryByRole("heading", { name: "DICOM inventory summary" }),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("bids-validation-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("preprocessing-validation-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("qc-summary-panel")).not.toBeInTheDocument();
  });

  it("uses converted summary as the primary view when raw DICOM and registered NIfTI coexist", async () => {
    const user = userEvent.setup();

    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory({
          dataState: "mixed",
          dataStateLabel: "Mixed",
          rawDicomCandidates: 3,
          dicomSeriesCount: 6,
          dicomFileCount: 1104,
          convertedSubjects: 3,
          niftiFileCount: 6,
          hasRawDicom: true,
          hasConvertedData: true,
        })}
      />,
    );

    expect(
      screen.getByRole("heading", { name: "Converted imaging inventory" }),
    ).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "DICOM series browser" })).not.toBeInTheDocument();
    expect(screen.getByText(/DICOM conversion has completed/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Open detailed checks" }));

    expect(screen.getByTestId("conversion-dry-run-panel")).toBeInTheDocument();
    expect(screen.getByTestId("dicom-review-panel")).toBeInTheDocument();
  });

  it("shows an empty state when no imaging inventory exists", async () => {
    render(
      <DataConversionWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        inventory={inventory({
          dataState: "empty",
          dataStateLabel: "Empty project",
          rawDicomCandidates: 0,
          dicomSeriesCount: 0,
          dicomFileCount: 0,
          hasRawDicom: false,
          hasConvertedData: false,
        })}
      />,
    );

    expect(screen.getByText("No imaging inventory yet")).toBeInTheDocument();
    expect(
      screen.queryByRole("table", { name: "Raw DICOM readiness summary" }),
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("conversion-dry-run-panel")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Open detailed checks" }));

    expect(screen.getByTestId("data-readiness-panel")).toBeInTheDocument();
    expect(screen.getByTestId("bids-validation-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("conversion-dry-run-panel")).not.toBeInTheDocument();
  });
});
