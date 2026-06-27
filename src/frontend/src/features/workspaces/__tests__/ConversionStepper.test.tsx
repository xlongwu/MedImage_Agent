import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import type { ConversionDryRunResponse } from "../../../types";
import { ConversionStepper } from "../ConversionStepper";

function inventory(overrides: Partial<ProjectInventory> = {}): ProjectInventory {
  return {
    projectName: "Demo Project",
    modality: "rs-fMRI",
    dataState: "raw_dicom",
    dataStateLabel: "Raw DICOM",
    stateSentence: "Raw DICOM data detected.",
    rawDicomCandidates: 2,
    dicomSeriesCount: 6,
    dicomFileCount: 800,
    convertedSubjects: 0,
    niftiFileCount: 0,
    hasRawDicom: true,
    hasConvertedData: false,
    metadataOnlyNiftiInventory: false,
    ...overrides,
  };
}

function dryRun(overrides: Partial<ConversionDryRunResponse> = {}): ConversionDryRunResponse {
  return {
    ok: true,
    project_id: "project-1",
    status: "ready",
    dry_run: true,
    checked_at: "2026-06-25T00:00:00Z",
    target_layout: "bids",
    output_root_name: "rawdata",
    output_root_preview: "D:\\study\\rawdata",
    source_summaries: [],
    mapping_preview: [
      {
        source_path: "D:\\study\\dicom\\sub-01\\REST",
        source_series_uid: "series-001",
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
    ...overrides,
  };
}

describe("ConversionStepper", () => {
  it("keeps dry-run preview blocked when backend returns blocking issues", () => {
    render(
      <ConversionStepper
        dryRun={dryRun({
          blocking_issues: ["Output root is outside the safe project directory."],
          status: "blocked",
        })}
        error=""
        inventory={inventory()}
      />,
    );

    const dryRunStep = screen.getByText("Dry Run Preview").closest("li");

    expect(screen.getByLabelText("Dry-run stepper status")).toHaveTextContent(
      "1 blocking issue",
    );
    expect(dryRunStep).toHaveTextContent("blocked");
    expect(dryRunStep).toHaveTextContent("Output root is outside the safe project directory.");
  });

  it("marks low-confidence mappings as current manual review, not completed", () => {
    render(
      <ConversionStepper
        dryRun={dryRun({
          mapping_preview: [
            {
              source_path: "D:\\study\\dicom\\sub-01\\REST",
              source_series_uid: "series-001",
              source_type: "dicom_series",
              subject_id: "sub-01",
              session_id: "ses-01",
              modality: "func",
              suffix: "bold",
              task: "rest",
              suggested_relative_path: "sub-01/ses-01/func/sub-01_ses-01_task-rest_bold.nii.gz",
              confidence: "manual_required",
              warnings: [],
            },
          ],
          status: "warning",
        })}
        error=""
        inventory={inventory()}
      />,
    );

    const mappingStep = screen.getByText("Series Mapping").closest("li");

    expect(mappingStep).toHaveTextContent("current");
    expect(mappingStep).toHaveTextContent("human review before approval material");
    expect(mappingStep).not.toHaveTextContent("completed");
  });

  it("keeps the dry-run action owned by the DICOM series browser", () => {
    render(
      <ConversionStepper
        dryRun={null}
        error=""
        inventory={inventory()}
      />,
    );

    expect(screen.queryByRole("button", { name: /dry-run/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Start the no-write dry-run from the DICOM series browser/i)).toBeInTheDocument();
  });
});
