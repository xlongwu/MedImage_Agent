import { describe, expect, it } from "vitest";

import type { ProjectInventory, WorkflowTab } from "../../../lib/projectWorkflow";
import { hasRealImagePreview, shouldRenderProjectImageViewer } from "../viewerVisibility";

function inventory(overrides: Partial<ProjectInventory> = {}): ProjectInventory {
  return {
    projectName: "Demo",
    modality: "rs-fMRI",
    dataState: "raw_dicom",
    dataStateLabel: "Raw DICOM",
    stateSentence: "Raw DICOM data detected.",
    rawDicomCandidates: 2,
    dicomSeriesCount: 8,
    dicomFileCount: 1200,
    convertedSubjects: 0,
    niftiFileCount: 0,
    hasRawDicom: true,
    hasConvertedData: false,
    metadataOnlyNiftiInventory: false,
    ...overrides,
  };
}

describe("viewer visibility", () => {
  it("keeps raw and empty projects out of the first-screen image viewer", () => {
    for (const dataState of ["raw_dicom", "empty", "unknown"] as const) {
      expect(
        shouldRenderProjectImageViewer({
          activeWorkflow: "data",
          inventory: inventory({ dataState }),
        }),
      ).toBe(false);
    }
  });

  it("shows converted image context only in image-relevant workflows", () => {
    const converted = inventory({
      dataState: "converted_bids",
      dataStateLabel: "Converted BIDS/NIfTI",
      hasRawDicom: false,
      hasConvertedData: true,
      convertedSubjects: 4,
      niftiFileCount: 24,
    });

    for (const activeWorkflow of ["data", "preprocessing", "reports", "results"] as WorkflowTab[]) {
      expect(shouldRenderProjectImageViewer({ activeWorkflow, inventory: converted })).toBe(true);
    }

    for (const activeWorkflow of ["plan", "runs", "environment"] as WorkflowTab[]) {
      expect(shouldRenderProjectImageViewer({ activeWorkflow, inventory: converted })).toBe(false);
    }
  });

  it("treats only preview URLs as real medical previews", () => {
    expect(hasRealImagePreview(null)).toBe(false);
    expect(
      hasRealImagePreview({
        project_id: "project-1",
        sequence: "BOLD",
        preview_url: null,
        message: "No preview",
      }),
    ).toBe(false);
    expect(
      hasRealImagePreview({
        project_id: "project-1",
        sequence: "BOLD",
        preview_url: "/api/projects/project-1/preview.png",
        message: "Preview ready",
      }),
    ).toBe(true);
  });
});
