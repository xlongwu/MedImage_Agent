import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { ProjectInventory } from "../../../lib/projectWorkflow";
import { I18nProvider } from "../../../i18n/I18nProvider";
import type { NativeFullPreprocResponse } from "../../../types";
import {
  createPreprocessingRun,
  executeNativeFullPreprocessing,
  executeReviewedPreprocessingPipeline,
  getLatestNativeFullPreprocessingRun,
  getNativeFullPreprocessingReport,
  getNativeFullPreprocessingValidation,
  runNativeFullPreprocessingDryRun,
} from "../../../lib/api/preprocessing";
import { PreprocessingWorkspace } from "../PreprocessingWorkspace";

vi.mock("../../../lib/api/preprocessing", () => ({
  createPreprocessingRun: vi.fn(),
  executeNativeFullPreprocessing: vi.fn(),
  executeReviewedPreprocessingPipeline: vi.fn(),
  getLatestNativeFullPreprocessingRun: vi.fn(),
  getNativeFullPreprocessingReport: vi.fn(),
  getNativeFullPreprocessingValidation: vi.fn(),
  runNativeFullPreprocessingDryRun: vi.fn(),
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
const nativeDryRunMock = vi.mocked(runNativeFullPreprocessingDryRun);
const nativeExecuteMock = vi.mocked(executeNativeFullPreprocessing);
const latestNativeRunMock = vi.mocked(getLatestNativeFullPreprocessingRun);
const nativeValidationMock = vi.mocked(getNativeFullPreprocessingValidation);
const nativeReportMock = vi.mocked(getNativeFullPreprocessingReport);

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

function nativeResponse(
  overrides: Partial<NativeFullPreprocResponse> = {},
): NativeFullPreprocResponse {
  return {
    ok: false,
    status: "blocked",
    dry_run: true,
    project_id: "project-1",
    run_id: "pp-demo",
    run_dir: "/tmp/project/preprocessing_native_runs/pp-demo",
    backend: "native_python",
    stage_graph: [],
    stage_results: [
      {
        stage_id: "functional_connectivity",
        display_name: "Functional connectivity",
        node_id: "native_preproc_functional_connectivity",
        status: "blocked",
        capability_level: "computed",
        validation_status: "synthetic_tested_reference_pending",
        backend: "native_python",
        input_artifacts: [],
        output_artifacts: [],
        warnings: [],
        errors: [],
        blocking_issues: ["Missing required input artifact: atlas"],
        validation_errors: [],
        result: {},
      },
    ],
    completed_stages: [],
    blocked_stages: ["functional_connectivity"],
    failed_stages: [],
    skipped_stages: [],
    metadata_only_stages: [],
    warning_stages: [],
    artifact_count: 0,
    manifest_path: "/tmp/project/preprocessing_native_runs/pp-demo/native_full_run_manifest.json",
    validation_report_path: "",
    final_report_path: "",
    warnings: [],
    errors: [],
    blocking_issues: ["Missing required input artifact: atlas"],
    next_actions: ["Provide a reviewed atlas."],
    safety_flags: { no_external_tools_executed: true },
    ...overrides,
  };
}

describe("PreprocessingWorkspace", () => {
  it("renders the blocked preprocessing surface in simplified Chinese", () => {
    render(
      <I18nProvider locale="zh-CN">
        <PreprocessingWorkspace
          baseUrl="http://localhost"
          projectId="project-1"
          dataState="raw_dicom"
          inventory={inventory({
            dataState: "raw_dicom",
            dataStateLabel: "Raw DICOM",
            hasRawDicom: true,
            hasConvertedData: false,
            convertedSubjects: 0,
            niftiFileCount: 0,
          })}
          hasPreprocessingRun={false}
          onOpenDataConversion={vi.fn()}
          onOpenToolsDrawer={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: "预处理已阻塞" })).toBeInTheDocument();
    expect(screen.getByLabelText("依赖链")).toHaveTextContent("转换复核");
    expect(screen.getByRole("button", { name: "返回数据与转换" })).toBeInTheDocument();
  });

  it("renders preprocessing stages and configuration modes in simplified Chinese", () => {
    render(
      <I18nProvider locale="zh-CN">
        <PreprocessingWorkspace
          baseUrl="http://localhost"
          projectId="project-1"
          dataState="converted_bids"
          inventory={inventory()}
          hasPreprocessingRun={false}
          onOpenDataConversion={vi.fn()}
          onOpenToolsDrawer={vi.fn()}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("list", { name: "预处理阶段" })).toHaveTextContent("数据准备");
    expect(screen.getByRole("list", { name: "预处理阶段" })).toHaveTextContent("干扰回归");
    expect(screen.getByLabelText("所选预处理阶段配置")).toHaveTextContent("基础");
    expect(screen.getByLabelText("所选预处理阶段配置")).toHaveTextContent("输入数据集");
    expect(screen.getByLabelText("所选预处理阶段配置")).toHaveTextContent("规划前必需");
    expect(screen.queryByText("Input dataset")).not.toBeInTheDocument();
    expect(screen.getByLabelText("预处理配置模式")).toHaveTextContent("安全");
    expect(screen.getByRole("heading", { name: "流程构建器" })).toBeInTheDocument();
    expect(screen.getByLabelText("预处理流程配置方案")).toHaveTextContent("最小功能连接");
    expect(screen.getByRole("table", { name: "已复核预处理阶段" })).toHaveTextContent("输入清单");
    expect(screen.getByRole("table", { name: "已复核预处理阶段" })).toHaveTextContent(
      "需要已登记的转换后 BIDS/NIfTI 输入",
    );
    expect(screen.getByRole("heading", { name: "受控执行门" })).toBeInTheDocument();
    expect(screen.getByLabelText("受控执行确认项")).toHaveTextContent("rawdata 保持只读");
    expect(screen.getByRole("heading", { name: "完整原生预处理" })).toBeInTheDocument();
    expect(screen.getByLabelText("完整原生流程安全确认项")).toHaveTextContent("不使用外部工具");
    expect(screen.getByRole("table", { name: "完整原生预处理阶段结果" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "DICOM 转换交接" })).toBeInTheDocument();
    expect(screen.getByText("尚未提交受控执行")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "功能连接结果" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "功能连接产物交接" })).toHaveTextContent(
      "后端登记矩阵",
    );
  });

  beforeEach(() => {
    executeReviewedMock.mockReset();
    createRunMock.mockReset();
    nativeDryRunMock.mockReset();
    nativeExecuteMock.mockReset();
    latestNativeRunMock.mockReset();
    nativeValidationMock.mockReset();
    nativeReportMock.mockReset();
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
    const onOpenRuns = vi.fn();
    createRunMock.mockResolvedValue({
      ok: true,
      status: "created",
      project_id: "project-1",
      preprocessing_run_id: "pp-created",
      run_dir: "/tmp/project/preprocessing_runs/pp-created",
      preprocessing_input_dir: "/tmp/project/converted_bids",
      artifact_registry_path:
        "/tmp/project/preprocessing_runs/pp-created/preprocessing_artifact_registry.json",
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
        onOpenRuns={onOpenRuns}
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
    fireEvent.click(screen.getByRole("button", { name: "View logs in Runs" }));
    expect(onOpenRuns).toHaveBeenCalledWith(null);
  });

  it("offers a fresh preprocessing run without overwriting prior run evidence", async () => {
    createRunMock.mockResolvedValue({
      ok: true,
      status: "created",
      project_id: "project-1",
      preprocessing_run_id: "pp-fresh",
      run_dir: "/tmp/project/preprocessing_runs/pp-fresh",
      preprocessing_input_dir: "/tmp/project/converted_bids",
      artifact_registry_path: "/tmp/project/preprocessing_runs/pp-fresh/registry.json",
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
        hasPreprocessingRun={true}
        preprocessingRunId="pp-prior"
        onOpenDataConversion={vi.fn()}
        onOpenToolsDrawer={vi.fn()}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Create new preprocessing run" }));
    await waitFor(() => expect(createRunMock).toHaveBeenCalledTimes(1));
    expect(await screen.findByText(/Run pp-fresh is ready/)).toBeInTheDocument();
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

  it("runs native full dry-run and renders blocked stage evidence", async () => {
    nativeDryRunMock.mockResolvedValue(nativeResponse());

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

    fireEvent.change(screen.getByLabelText("Template path"), {
      target: { value: "C:\\reviewed\\mni_template.nii.gz" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Run native dry-run" }));

    await waitFor(() => expect(nativeDryRunMock).toHaveBeenCalledTimes(1));
    expect(nativeDryRunMock).toHaveBeenCalledWith(
      "http://localhost",
      "project-1",
      expect.objectContaining({
        run_id: "pp-demo",
        template: "C:\\reviewed\\mni_template.nii.gz",
        stage_overrides: expect.objectContaining({
          functional_connectivity: true,
          alff: false,
          reho: false,
        }),
      }),
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "blocked",
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "Functional connectivity",
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "Missing required input artifact: atlas",
    );
  });

  it("restores the latest native full preprocessing run after reviewed-plan execution", async () => {
    latestNativeRunMock.mockResolvedValue(
      nativeResponse({
        ok: false,
        status: "partial",
        dry_run: false,
        run_id: "run-reviewed-native",
        artifact_count: 12,
        completed_stages: ["slice_timing", "functional_connectivity"],
        blocked_stages: [],
        stage_results: [
          {
            stage_id: "functional_connectivity",
            display_name: "Functional connectivity",
            node_id: "native_preproc_functional_connectivity",
            status: "succeeded",
            capability_level: "computed",
            validation_status: "synthetic_tested_reference_pending",
            backend: "native_python",
            input_artifacts: [],
            output_artifacts: [
              {
                artifact_type: "fc_matrix",
                path: "fc.tsv",
                shape: [116, 116],
              },
            ],
            warnings: [],
            errors: [],
            blocking_issues: [],
            validation_errors: [],
            result: { qc_status: "pass", qc_metrics: { roi_count: 116 } },
          },
        ],
      }),
    );

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

    await waitFor(() =>
      expect(latestNativeRunMock).toHaveBeenCalledWith("http://localhost", "project-1"),
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "run-reviewed-native",
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "partial",
    );
    expect(screen.getByLabelText("Native full run summary")).toHaveTextContent("12");
    expect(screen.queryByText("No reviewed execution submitted")).not.toBeInTheDocument();
    const nativeWorkflow = screen.getByLabelText("Native full preprocessing workflow");
    expect(within(nativeWorkflow).getByText("Functional connectivity")).toBeInTheDocument();
    expect(within(nativeWorkflow).getByText("succeeded")).toBeInTheDocument();
    const fcPanel = screen.getByLabelText("FC results panel");
    expect(fcPanel).toHaveTextContent("succeeded");
    expect(fcPanel).toHaveTextContent("116");
    expect(fcPanel).toHaveTextContent("116 x 116");
    expect(fcPanel).toHaveTextContent("fc_matrix");
    expect(fcPanel).toHaveTextContent("fc.tsv");
  });

  it("shows latest native FC blocking evidence instead of an empty waiting state", async () => {
    latestNativeRunMock.mockResolvedValue(
      nativeResponse({
        status: "partial",
        dry_run: false,
        run_id: "run-reviewed-native",
        stage_results: [
          {
            stage_id: "functional_connectivity",
            display_name: "Functional connectivity",
            node_id: "native_preproc_functional_connectivity",
            status: "blocked",
            capability_level: "computed",
            validation_status: "synthetic_tested_reference_pending",
            backend: "native_python",
            input_artifacts: [],
            output_artifacts: [],
            warnings: [],
            errors: [],
            blocking_issues: ["Missing ROI time series for FC."],
            validation_errors: [],
            result: {},
          },
        ],
      }),
    );

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

    await waitFor(() =>
      expect(latestNativeRunMock).toHaveBeenCalledWith("http://localhost", "project-1"),
    );
    const fcPanel = screen.getByLabelText("FC results panel");
    expect(fcPanel).toHaveTextContent("blocked");
    expect(fcPanel).toHaveTextContent("Missing ROI time series for FC.");
  });

  it("allows native execute from a restored latest native run without a preprocessing run id", async () => {
    latestNativeRunMock.mockResolvedValue(
      nativeResponse({
        ok: false,
        status: "partial",
        dry_run: false,
        run_id: "run-reviewed-native",
        artifact_count: 26,
        blocked_stages: ["functional_connectivity"],
      }),
    );
    nativeExecuteMock.mockResolvedValue(
      nativeResponse({
        ok: true,
        status: "succeeded",
        dry_run: false,
        run_id: "run-reviewed-native",
        artifact_count: 30,
        completed_stages: ["functional_connectivity"],
        blocked_stages: [],
      }),
    );

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

    await waitFor(() =>
      expect(latestNativeRunMock).toHaveBeenCalledWith("http://localhost", "project-1"),
    );
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "run-reviewed-native",
    );
    const execute = screen.getByRole("button", { name: "Execute native full preprocessing" });
    expect(execute).toBeDisabled();

    fireEvent.click(screen.getByLabelText(/Reviewed native execution/));
    fireEvent.click(screen.getByLabelText(/Native rawdata read-only/));
    fireEvent.click(screen.getByLabelText(/No external tools/));
    fireEvent.click(screen.getByLabelText(/Native research use only/));
    fireEvent.click(screen.getByLabelText(/Native no clinical use/));

    expect(execute).toBeEnabled();
    fireEvent.click(execute);

    await waitFor(() => expect(nativeExecuteMock).toHaveBeenCalledTimes(1));
    expect(nativeExecuteMock).toHaveBeenCalledWith(
      "http://localhost",
      "project-1",
      expect.objectContaining({
        run_id: "run-reviewed-native",
        confirmations: expect.objectContaining({
          confirm_reviewed_native_execution: true,
          confirm_rawdata_readonly: true,
          confirm_no_external_tools: true,
          confirm_research_use_only: true,
          confirm_no_clinical_use: true,
        }),
      }),
    );
  });

  it("executes native full only after native safety confirmations", async () => {
    nativeExecuteMock.mockResolvedValue(
      nativeResponse({
        ok: true,
        status: "partial",
        dry_run: false,
        completed_stages: ["input_validation"],
        blocked_stages: ["functional_connectivity"],
        artifact_count: 3,
      }),
    );

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

    const execute = screen.getByRole("button", { name: "Execute native full preprocessing" });
    expect(execute).toBeDisabled();

    fireEvent.click(screen.getByLabelText(/Reviewed native execution/));
    fireEvent.click(screen.getByLabelText(/Native rawdata read-only/));
    fireEvent.click(screen.getByLabelText(/No external tools/));
    fireEvent.click(screen.getByLabelText(/Native research use only/));
    fireEvent.click(screen.getByLabelText(/Native no clinical use/));

    expect(execute).toBeEnabled();
    fireEvent.click(execute);

    await waitFor(() => expect(nativeExecuteMock).toHaveBeenCalledTimes(1));
    expect(nativeExecuteMock).toHaveBeenCalledWith(
      "http://localhost",
      "project-1",
      expect.objectContaining({
        run_id: "pp-demo",
        confirmations: expect.objectContaining({
          confirm_reviewed_native_execution: true,
          confirm_rawdata_readonly: true,
          confirm_no_external_tools: true,
          confirm_research_use_only: true,
          confirm_no_clinical_use: true,
        }),
      }),
    );
    expect(screen.getByLabelText("Native full run summary")).toHaveTextContent("3");
    expect(screen.getByLabelText("Native full preprocessing workflow")).toHaveTextContent(
      "partial",
    );
  });

  it("refreshes native validation and report outputs after a native run exists", async () => {
    nativeDryRunMock.mockResolvedValue(
      nativeResponse({
        ok: true,
        status: "succeeded",
        dry_run: false,
        artifact_count: 8,
        validation_report_path: "/tmp/project/native/validation.json",
        final_report_path: "/tmp/project/native/report.json",
      }),
    );
    nativeValidationMock.mockResolvedValue({
      ok: true,
      status: "succeeded",
      validation_report_path: "/tmp/project/native/validation-refreshed.json",
    });
    nativeReportMock.mockResolvedValue({
      ok: true,
      status: "succeeded",
      final_report_path: "/tmp/project/native/report-refreshed.json",
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

    fireEvent.click(screen.getByRole("button", { name: "Run native dry-run" }));
    await waitFor(() => expect(nativeDryRunMock).toHaveBeenCalledTimes(1));

    fireEvent.click(screen.getByRole("button", { name: "Refresh native validation" }));
    await waitFor(() =>
      expect(nativeValidationMock).toHaveBeenCalledWith("http://localhost", "project-1", "pp-demo"),
    );

    fireEvent.click(screen.getByRole("button", { name: "Refresh native report" }));
    await waitFor(() =>
      expect(nativeReportMock).toHaveBeenCalledWith("http://localhost", "project-1", "pp-demo"),
    );
    expect(screen.getByLabelText("Native validation and report outputs")).toHaveTextContent(
      "/tmp/project/native/validation-refreshed.json",
    );
    expect(screen.getByLabelText("Native validation and report outputs")).toHaveTextContent(
      "/tmp/project/native/report-refreshed.json",
    );
  });

  it("shows native full workflow errors from API failures", async () => {
    nativeDryRunMock.mockRejectedValue(new Error("native route unavailable"));

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

    fireEvent.click(screen.getByRole("button", { name: "Run native dry-run" }));

    expect(await screen.findByText("native route unavailable")).toBeInTheDocument();
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
