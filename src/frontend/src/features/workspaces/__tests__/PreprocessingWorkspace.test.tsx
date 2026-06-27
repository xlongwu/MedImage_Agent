import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import { PreprocessingWorkspace } from "../PreprocessingWorkspace";

vi.mock("../../../components/AdvancedPreprocessingPipelinePanel", () => ({
  default: () => <div data-testid="preprocessing-validation-panel">Preprocessing panel</div>,
}));

vi.mock("../../../components/RsfmriSliceTimingPanel", () => ({
  RsfmriSliceTimingPanel: () => <div data-testid="slice-timing-panel">Slice timing panel</div>,
}));

vi.mock("../../../components/RsfmriStRealignMotionChainPanel", () => ({
  RsfmriStRealignMotionChainPanel: () => (
    <div data-testid="st-realign-motion-chain-panel">ST realign motion chain panel</div>
  ),
}));

vi.mock("../../../components/RsfmriCoregistrationQcPanel", () => ({
  RsfmriCoregistrationQcPanel: () => (
    <div data-testid="coregistration-qc-panel">Coregistration QC panel</div>
  ),
}));

vi.mock("../../../components/RsfmriSegmentationTissueQcPanel", () => ({
  RsfmriSegmentationTissueQcPanel: () => (
    <div data-testid="segmentation-tissue-qc-panel">Segmentation tissue QC panel</div>
  ),
}));

vi.mock("../../../components/RsfmriNormalizationQcPanel", () => ({
  RsfmriNormalizationQcPanel: () => (
    <div data-testid="normalization-qc-panel">Normalization QC panel</div>
  ),
}));

vi.mock("../../../components/RsfmriSmoothingQcPanel", () => ({
  RsfmriSmoothingQcPanel: () => <div data-testid="smoothing-qc-panel">Smoothing QC panel</div>,
}));

function inventory(overrides: Partial<ProjectInventory> = {}): ProjectInventory {
  return {
    projectName: "Demo Project",
    modality: "rs-fMRI",
    dataState: "converted_bids",
    dataStateLabel: "Converted BIDS/NIfTI",
    stateSentence: "Converted BIDS/NIfTI data is available.",
    rawDicomCandidates: 0,
    dicomSeriesCount: 0,
    dicomFileCount: 0,
    convertedSubjects: 4,
    niftiFileCount: 24,
    hasRawDicom: false,
    hasConvertedData: true,
    metadataOnlyNiftiInventory: false,
    ...overrides,
  };
}

describe("PreprocessingWorkspace", () => {
  it("keeps raw DICOM preprocessing blocked with a data conversion CTA", () => {
    const onOpenDataConversion = vi.fn();

    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="raw_dicom"
        inventory={inventory({
          dataState: "raw_dicom",
          dataStateLabel: "Raw DICOM",
          convertedSubjects: 0,
          niftiFileCount: 0,
          hasRawDicom: true,
          hasConvertedData: false,
        })}
        hasPreprocessingRun={false}
        onOpenDataConversion={onOpenDataConversion}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Preprocessing is blocked" })).toBeInTheDocument();
    expect(screen.getByLabelText("Dependency chain")).toHaveTextContent("Conversion Review");
    expect(screen.queryByRole("heading", { name: "Preprocessing stages" })).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Return to Data & Conversion" }));
    expect(onOpenDataConversion).toHaveBeenCalledTimes(1);
  });

  it("shows staged preprocessing configuration before the detailed validation panel", () => {
    const onOpenToolsDrawer = vi.fn();

    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={false}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={onOpenToolsDrawer}
      />,
    );

    expect(screen.getByText("Ready to configure preprocessing")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open setup context" }));
    expect(onOpenToolsDrawer).toHaveBeenCalledTimes(1);

    const stages = screen.getByRole("list", { name: "Preprocessing stages" });
    expect(within(stages).getByText("Data preparation")).toBeInTheDocument();
    expect(within(stages).getByText("Slice timing")).toBeInTheDocument();
    expect(within(stages).getByText("Nuisance regression")).toBeInTheDocument();
    expect(screen.getByLabelText("Preprocessing input readiness")).toHaveTextContent("4");
    expect(screen.getByLabelText("Preprocessing configuration modes")).toHaveTextContent("Safety");
    expect(screen.getByLabelText("Selected preprocessing stage configuration")).toHaveTextContent(
      "Data preparation",
    );
    expect(screen.getByLabelText("Selected preprocessing stage configuration")).toHaveTextContent(
      "Input dataset",
    );
    expect(screen.getByLabelText("Detailed preprocessing checks")).toBeInTheDocument();
    expect(
      within(screen.getByLabelText("Detailed preprocessing checks")).getByTitle(
        "Backend evidence is required before this state can be treated as complete.",
      ),
    ).toHaveTextContent("On demand");
    expect(screen.queryByTestId("preprocessing-validation-panel")).not.toBeInTheDocument();
    expect(screen.getByLabelText("SPM technical modules")).toHaveTextContent("On demand");
    expect(
      within(screen.getByLabelText("SPM technical modules")).getByTitle(
        "Backend evidence is required before this state can be treated as complete.",
      ),
    ).toHaveTextContent("On demand");
    expect(screen.queryByTestId("slice-timing-panel")).not.toBeInTheDocument();
  });

  it("switches selected preprocessing stage and advanced parameters", () => {
    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={false}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Inspect Motion correction" }));
    const config = screen.getByLabelText("Selected preprocessing stage configuration");
    expect(config).toHaveTextContent("Motion correction");
    expect(config).toHaveTextContent("FD threshold");

    fireEvent.click(within(config).getByRole("button", { name: "Advanced" }));

    expect(config).toHaveTextContent("Interpolation");
    expect(config).toHaveTextContent("4th degree B-spline");
  });

  it("opens detailed validation checks on demand for converted projects", () => {
    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={false}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("preprocessing-validation-panel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open validation checks" }));

    expect(screen.getByTestId("preprocessing-validation-panel")).toBeInTheDocument();
  });

  it("uses input-required language when converted data is not registered", () => {
    const onOpenDataConversion = vi.fn();

    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="empty"
        inventory={inventory({
          dataState: "empty",
          dataStateLabel: "Empty project",
          convertedSubjects: 0,
          niftiFileCount: 0,
          hasConvertedData: false,
        })}
        hasPreprocessingRun={false}
        onOpenDataConversion={onOpenDataConversion}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    expect(screen.getByText("Register converted outputs before preprocessing")).toBeInTheDocument();
    expect(screen.getByLabelText("Preprocessing input required")).toHaveTextContent(
      "Registered input",
    );
    expect(screen.queryByRole("list", { name: "Preprocessing stages" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open validation checks" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Open SPM modules" })).toBeDisabled();

    fireEvent.click(screen.getByRole("button", { name: "Open Data & Conversion" }));
    expect(onOpenDataConversion).toHaveBeenCalledTimes(1);
  });

  it("treats metadata-only converted inventory as input required", () => {
    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory({
          convertedSubjects: 0,
          niftiFileCount: 0,
          hasConvertedData: true,
          metadataOnlyNiftiInventory: true,
        })}
        hasPreprocessingRun={false}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("Preprocessing input required")).toHaveTextContent(
      "Converted data evidence",
    );
    expect(screen.getByLabelText("Preprocessing input required")).toHaveTextContent("Required");
    expect(screen.queryByRole("list", { name: "Preprocessing stages" })).not.toBeInTheDocument();
  });

  it("marks stages for review when a preprocessing run record exists", () => {
    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={true}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    const stages = screen.getByRole("list", { name: "Preprocessing stages" });
    expect(within(stages).getByText("Data preparation")).toBeInTheDocument();
    expect(within(stages).getAllByText("Review").length).toBeGreaterThan(0);
    expect(screen.queryByText("Create preprocessing run")).not.toBeInTheDocument();
  });

  it("opens migrated SPM technical modules on demand for converted projects", () => {
    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={false}
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    expect(screen.queryByTestId("slice-timing-panel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open SPM modules" }));

    expect(screen.getByTestId("slice-timing-panel")).toBeInTheDocument();
    expect(screen.getByTestId("st-realign-motion-chain-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coregistration-qc-panel")).toBeInTheDocument();
    expect(screen.getByTestId("segmentation-tissue-qc-panel")).toBeInTheDocument();
    expect(screen.getByTestId("normalization-qc-panel")).toBeInTheDocument();
    expect(screen.getByTestId("smoothing-qc-panel")).toBeInTheDocument();
  });
});
