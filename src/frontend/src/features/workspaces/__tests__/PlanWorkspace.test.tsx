import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import type { ComponentProps } from "react";
import { describe, expect, it, vi } from "vitest";

import type { ProjectDetail } from "../../../lib/types/project";
import type { PresetPlanDraft } from "../../../types";
import { PlanWorkspace } from "../PlanWorkspace";

vi.mock("../../../components/PlanReviewConsole", () => ({
  default: () => <div data-testid="plan-review-console">Technical plan tools</div>,
}));

function project(overrides: Partial<ProjectDetail> = {}): ProjectDetail {
  return {
    id: "project-1",
    name: "Demo Project",
    study_id: "study-1",
    modality: "rs-fMRI",
    created_date: "2026-06-24",
    subjects_count: 4,
    current_pipeline_id: "not-selected",
    sequences: ["bold"],
    scans_count: 24,
    total_size: "128 MB",
    current_model_id: "model-1",
    metadata: {
      project_config_path: "work/projects/demo/project_config.yaml",
      dataset_index_path: "work/projects/demo/dataset_index.json",
      rawdata_dir: "work/projects/demo/rawdata",
      project_dir: "work/projects/demo",
    },
    ...overrides,
  };
}

function draft(overrides: Partial<PresetPlanDraft> = {}): PresetPlanDraft {
  return {
    preset_id: "preset-rsfmri",
    project_id: "project-1",
    goal: "Create a reviewed rs-fMRI preprocessing plan",
    source: "pipeline_preset",
    plan: {
      pipeline_id: "rsfmri_preprocessing",
      nodes: [
        {
          id: "load_bids",
          name: "Load BIDS inputs",
          description: "Read registered BIDS/NIfTI inputs.",
          backend: "bids_loader",
          inputs: ["dataset_index.json"],
          outputs: ["validated_input_manifest.json"],
          params: { strict_bids: true },
        },
        {
          id: "spm_realign",
          name: "Motion correction",
          description: "Prepare realignment through reviewed backend gates.",
          depends_on: ["load_bids"],
          backend: "spm",
          inputs: ["validated_input_manifest.json"],
          outputs: ["realignment_dry_run.json"],
          params: { quality: 0.9, dry_run_only: true },
        },
      ],
    },
    validation: {
      ok: true,
      errors: [],
      warnings: [],
      approval_required_nodes: ["spm_realign"],
      high_risk_nodes: ["spm_realign"],
      unknown_nodes: [],
    },
    next_actions: ["Review approval-required nodes", "Run dry-run before execution"],
    warnings: [],
    ...overrides,
  };
}

function renderWorkspace(overrides: Partial<ComponentProps<typeof PlanWorkspace>> = {}) {
  const onOpenDataConversion = vi.fn();
  const onOpenEnvironment = vi.fn();
  const onSelectedNodeChange = vi.fn();
  const selectedProject = project();

  render(
    <PlanWorkspace
      baseUrl="http://localhost"
      projectId="project-1"
      selectedProject={selectedProject}
      projectConfigPath={selectedProject.metadata?.project_config_path}
      datasetIndexPath={selectedProject.metadata?.dataset_index_path}
      rawdataDir={selectedProject.metadata?.rawdata_dir}
      projectDir={selectedProject.metadata?.project_dir}
      initialPresetDraft={null}
      onSelectedNodeChange={onSelectedNodeChange}
      onOpenDataConversion={onOpenDataConversion}
      onOpenEnvironment={onOpenEnvironment}
      {...overrides}
    />,
  );

  return { onOpenDataConversion, onOpenEnvironment, onSelectedNodeChange };
}

describe("PlanWorkspace", () => {
  it("requires a project before planning", () => {
    const { onOpenDataConversion } = renderWorkspace({
      projectId: null,
      selectedProject: null,
      projectConfigPath: undefined,
    });

    expect(screen.getByText("Select a project before planning")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open Data & Conversion" }));
    expect(onOpenDataConversion).toHaveBeenCalledTimes(1);
  });

  it("routes missing project config to environment settings", () => {
    const { onOpenEnvironment } = renderWorkspace({
      selectedProject: project({ metadata: {} }),
      projectConfigPath: undefined,
    });

    expect(screen.getByText("Project config required")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Open Settings / Environment" }));
    expect(onOpenEnvironment).toHaveBeenCalledTimes(1);
  });

  it("shows a plan outline and node steps without opening technical tools by default", () => {
    renderWorkspace({ initialPresetDraft: draft() });

    expect(screen.getByRole("heading", { name: "Plan outline" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Pipeline graph" })).toBeInTheDocument();
    const steps = screen.getByRole("list", { name: "Plan pipeline steps" });
    expect(within(steps).getByText("Load BIDS inputs")).toBeInTheDocument();
    expect(within(steps).getByText("Motion correction")).toBeInTheDocument();
    expect(within(steps).getByText("High risk")).toBeInTheDocument();
    expect(screen.getByLabelText("Plan inspector")).toHaveTextContent("dataset_index.json");
    expect(screen.getByLabelText("Plan state machine")).toHaveTextContent("Needs Review");
    expect(screen.getByLabelText("Plan state machine")).toHaveTextContent("Dry-run Passed");
    expect(screen.queryByTestId("plan-review-console")).not.toBeInTheDocument();
  });

  it("does not mark approval, dry-run, or execution readiness as reached without backend evidence", () => {
    renderWorkspace({ initialPresetDraft: draft() });

    const stateMachine = screen.getByLabelText("Plan state machine");

    expect(within(stateMachine).getByLabelText("Approved: backend evidence required")).toBeInTheDocument();
    expect(within(stateMachine).getByLabelText("Dry-run Passed: locked")).toBeInTheDocument();
    expect(within(stateMachine).getByLabelText("Ready to Execute: locked")).toBeInTheDocument();
    expect(screen.getByLabelText("Plan review facts")).toHaveTextContent("Approval evidence");
    expect(screen.getByLabelText("Plan review facts")).toHaveTextContent("Backend evidence required");
  });

  it("shows later plan gates only when backend evidence is present", () => {
    renderWorkspace({
      initialPresetDraft: draft({
        validation: {
          ok: true,
          errors: [],
          warnings: [],
          approval_required_nodes: [],
          high_risk_nodes: [],
          unknown_nodes: [],
          approval_passed: true,
          dry_run_passed: true,
          ready_to_execute: true,
        },
      }),
    });

    const stateMachine = screen.getByLabelText("Plan state machine");

    expect(within(stateMachine).getByLabelText("Approved: completed")).toBeInTheDocument();
    expect(within(stateMachine).getByLabelText("Dry-run Passed: completed")).toBeInTheDocument();
    expect(within(stateMachine).getByLabelText("Ready to Execute: completed")).toBeInTheDocument();
    expect(within(stateMachine).getByLabelText("Executed: backend evidence required")).toBeInTheDocument();
  });

  it("updates the inspector and shared selection context when a pipeline node is selected", async () => {
    const { onSelectedNodeChange } = renderWorkspace({ initialPresetDraft: draft() });

    fireEvent.click(screen.getByRole("button", { name: "Inspect Motion correction" }));

    const inspector = screen.getByLabelText("Plan inspector");
    expect(inspector).toHaveTextContent("Motion correction");
    expect(inspector).toHaveTextContent("validated_input_manifest.json");
    expect(inspector).toHaveTextContent("realignment_dry_run.json");
    expect(inspector).toHaveTextContent("dry_run_only");
    expect(inspector).toHaveTextContent("High-risk or approval-sensitive node");
    await waitFor(() =>
      expect(onSelectedNodeChange).toHaveBeenLastCalledWith(
        expect.objectContaining({
          backend: "spm",
          id: "spm_realign",
          name: "Motion correction",
          risk: "High risk",
        }),
      ),
    );
  });

  it("opens technical plan tools without duplicating run history", () => {
    renderWorkspace({ initialPresetDraft: draft() });

    fireEvent.click(screen.getByRole("button", { name: "Open technical plan tools" }));

    expect(screen.getByTestId("plan-review-console")).toBeInTheDocument();
    expect(screen.queryByTestId("project-runs-panel")).not.toBeInTheDocument();
  });
});
