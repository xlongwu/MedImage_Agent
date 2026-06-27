import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import { ProjectOverviewHeader } from "../ProjectOverviewHeader";

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

describe("ProjectOverviewHeader", () => {
  it("combines raw DICOM project context with one primary conversion action", async () => {
    const user = userEvent.setup();
    const primary = vi.fn();
    const secondary = vi.fn();

    render(
      <ProjectOverviewHeader
        hasPreprocessingRun={false}
        inventory={inventory()}
        onPrimaryAction={primary}
        onSecondaryAction={secondary}
      />,
    );

    expect(screen.getByRole("heading", { name: "Demo Project" })).toBeInTheDocument();
    expect(screen.getByLabelText("Project inventory metrics")).toHaveTextContent("Raw DICOM");
    expect(screen.getByText("1,200")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Generate conversion dry-run" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Generate conversion dry-run" }));
    await user.click(screen.getByRole("button", { name: "Review conversion readiness" }));

    expect(primary).toHaveBeenCalledTimes(1);
    expect(secondary).toHaveBeenCalledTimes(1);
  });

  it("uses preprocessing action text for converted BIDS/NIfTI projects", () => {
    render(
      <ProjectOverviewHeader
        hasPreprocessingRun={true}
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
        onPrimaryAction={vi.fn()}
        onSecondaryAction={vi.fn()}
      />,
    );

    expect(
      screen.getByRole("button", { name: "Check preprocessing validation" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review QC report status" })).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
  });

  it("requires mixed projects to review conversion state before preprocessing", () => {
    render(
      <ProjectOverviewHeader
        hasPreprocessingRun={false}
        inventory={inventory({
          dataState: "mixed",
          dataStateLabel: "Mixed",
          convertedSubjects: 2,
          niftiFileCount: 12,
          hasRawDicom: true,
          hasConvertedData: true,
        })}
        onPrimaryAction={vi.fn()}
        onSecondaryAction={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Review conversion state" })).toBeInTheDocument();
    expect(screen.getByText(/Raw DICOM and converted outputs coexist/i)).toBeInTheDocument();
  });

  it("does not show a secondary pseudo-action for empty projects", () => {
    render(
      <ProjectOverviewHeader
        hasPreprocessingRun={false}
        inventory={inventory({
          dataState: "empty",
          dataStateLabel: "Empty project",
          rawDicomCandidates: 0,
          dicomSeriesCount: 0,
          dicomFileCount: 0,
          hasRawDicom: false,
          hasConvertedData: false,
        })}
        onPrimaryAction={vi.fn()}
        onSecondaryAction={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Import dataset" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Check environment health" }),
    ).not.toBeInTheDocument();
  });
});
