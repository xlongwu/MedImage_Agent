import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import {
  createPreprocessingRun,
  executeReviewedPreprocessingPipeline,
} from "../../../lib/api/preprocessing";
import { PreprocessingWorkspace } from "../PreprocessingWorkspace";

vi.mock("../../../lib/api/preprocessing", () => ({
  createPreprocessingRun: vi.fn(),
  executeReviewedPreprocessingPipeline: vi.fn(),
}));

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

const executeReviewedMock = vi.mocked(executeReviewedPreprocessingPipeline);
const createRunMock = vi.mocked(createPreprocessingRun);

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
  beforeEach(() => {
    executeReviewedMock.mockReset();
    createRunMock.mockReset();
  });

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

    expect(screen.getByText("Ready to create preprocessing run")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Create preprocessing run" })).toBeInTheDocument();
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

  it("creates a preprocessing run from registered converted input and opens reviewed flow", async () => {
    createRunMock.mockResolvedValue({
      ok: true,
      status: "created",
      project_id: "project-1",
      preprocessing_run_id: "pp-created",
      run_dir: "/tmp/project/preprocessing_runs/pp-created",
      preprocessing_input_dir: "/tmp/project/converted_bids",
      artifact_registry_path: "/tmp/project/preprocessing_runs/pp-created/preprocessing_artifact_registry.json",
      input_inventory: {},
      stage_count: 12,
      python_stage_count: 6,
      external_blocked_count: 4,
      planned_stage_count: 6,
      disabled_external_stage_count: 4,
      warnings: [],
      errors: [],
      blocking_issues: [],
      next_actions: [],
      safety_flags: {},
    });

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

    fireEvent.click(screen.getByRole("button", { name: "Create preprocessing run" }));

    await waitFor(() => expect(createRunMock).toHaveBeenCalledTimes(1));
    expect(createRunMock).toHaveBeenCalledWith(
      "http://localhost",
      "project-1",
      expect.objectContaining({
        confirm_use_converted_input: true,
        confirm_no_rawdata_modification: true,
        confirm_python_only_execution: true,
        confirm_no_spm_matlab: true,
      }),
    );
    expect(await screen.findByText(/Run pp-created is ready/)).toBeInTheDocument();
    expect(screen.getByLabelText("Reviewed preprocessing flow")).toHaveTextContent("pp-created");
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
        preprocessingRunId="pp-demo"
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    const stages = screen.getByRole("list", { name: "Preprocessing stages" });
    expect(within(stages).getByText("Data preparation")).toBeInTheDocument();
    expect(within(stages).getAllByText("Review").length).toBeGreaterThan(0);
    expect(screen.queryByText("Create preprocessing run")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Reviewed preprocessing flow")).toHaveTextContent("pp-demo");
    expect(screen.getByRole("button", { name: "Submit reviewed execution" })).toBeDisabled();
    expect(screen.queryByText("Run Full Preprocessing")).not.toBeInTheDocument();
  });

  it("submits reviewed execution only after explicit confirmations", async () => {
    executeReviewedMock.mockResolvedValue({
      ok: false,
      status: "blocked",
      project_id: "project-1",
      preprocessing_run_id: "pp-demo",
      execution_id: "pprev-demo",
      pipeline_profile: "fc_minimal",
      manifest_path: "reviewed_execution/manifest.json",
      artifact_registry_path: "preprocessing_artifact_registry.json",
      report_path: "",
      validation_status: "blocked",
      completed_stages: ["input_validation"],
      skipped_stages: [],
      blocked_stages: ["realignment", "functional_connectivity"],
      failed_stages: [],
      metadata_only_stages: [],
      preview_only_stages: ["functional_connectivity"],
      stage_results: [
        {
          stage_id: "input_validation",
          name: "Input inventory",
          status: "succeeded",
          enabled: true,
          optional: false,
          backend: "registry",
          node_id: "",
          started_at: "2026-06-28T00:00:00Z",
          ended_at: "2026-06-28T00:00:01Z",
          skipped_reason: "",
          blocking_issues: [],
          warnings: [],
          errors: [],
          output_artifact_ids: [],
          result: {},
        },
        {
          stage_id: "functional_connectivity",
          name: "Functional connectivity",
          status: "preview_only",
          enabled: true,
          optional: false,
          backend: "python",
          node_id: "functional_connectivity_subject",
          started_at: "2026-06-28T00:00:02Z",
          ended_at: "2026-06-28T00:00:03Z",
          skipped_reason: "",
          blocking_issues: ["Missing required input artifact: atlas"],
          warnings: [],
          errors: [],
          output_artifact_ids: ["fc-matrix-preview"],
          result: { matrix_shape: [8, 8] },
        },
      ],
      stage_statuses: [],
      approval_gate: {},
      warnings: [],
      errors: [],
      blocking_issues: ["realignment"],
      next_actions: ["Resolve blocked required stages before continuing."],
      safety_flags: {},
    });

    render(
      <PreprocessingWorkspace
        baseUrl="http://localhost"
        projectId="project-1"
        dataState="converted_bids"
        inventory={inventory()}
        hasPreprocessingRun={true}
        preprocessingRunId="pp-demo"
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    const submit = screen.getByRole("button", { name: "Submit reviewed execution" });
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByLabelText(/Rawdata stays read-only/));
    fireEvent.click(screen.getByLabelText(/Reviewed execution request/));
    fireEvent.click(screen.getByLabelText(/External-tool gates acknowledged/));
    fireEvent.click(screen.getByLabelText(/Research use only/));
    fireEvent.click(screen.getByLabelText(/No clinical use/));

    expect(submit).toBeEnabled();
    fireEvent.click(submit);

    await waitFor(() => expect(executeReviewedMock).toHaveBeenCalledTimes(1));
    expect(executeReviewedMock).toHaveBeenCalledWith(
      "http://localhost",
      "project-1",
      "pp-demo",
      expect.objectContaining({
        pipeline_profile: "fc_minimal",
        confirmations: expect.objectContaining({
          confirm_rawdata_readonly: true,
          confirm_reviewed_execution: true,
          confirm_external_tools_if_needed: true,
          confirm_research_use_only: true,
          confirm_no_clinical_use: true,
        }),
      }),
    );
    expect(screen.getByLabelText("Pipeline run dashboard")).toHaveTextContent("blocked");
    expect(screen.getByLabelText("FC results panel")).toHaveTextContent("preview_only");
    expect(screen.getByLabelText("FC results panel")).toHaveTextContent("Synthetic preview");
    expect(screen.getByLabelText("FC results panel")).toHaveTextContent("8 x 8");
    expect(screen.getByRole("link", { name: "Metadata" })).toHaveAttribute(
      "href",
      "http://localhost/api/projects/project-1/preprocessing/runs/pp-demo/artifacts/fc-matrix-preview",
    );
    expect(screen.getByRole("link", { name: "File" })).toHaveAttribute(
      "href",
      "http://localhost/api/projects/project-1/preprocessing/runs/pp-demo/artifacts/fc-matrix-preview/file",
    );
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
