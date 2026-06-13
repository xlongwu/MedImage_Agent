import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import {
  ProjectHeroPanel,
  ProjectList,
  ReadinessStatusStrip,
  RecommendedNextStepCard,
  WorkflowTabs,
} from "../DashboardChrome";
import type { ProjectInventory, WorkflowTab } from "../../../lib/projectWorkflow";
import type { ProjectSummary } from "../../../lib/types/project";

function inventory(overrides: Partial<ProjectInventory> = {}): ProjectInventory {
  return {
    projectName: "Demo Project",
    modality: "rs-fMRI",
    dataState: "converted_bids",
    dataStateLabel: "Converted BIDS/NIfTI",
    stateSentence: "Converted data is available.",
    rawDicomCandidates: 0,
    dicomSeriesCount: 0,
    dicomFileCount: 0,
    convertedSubjects: 2,
    niftiFileCount: 10,
    hasRawDicom: false,
    hasConvertedData: true,
    metadataOnlyNiftiInventory: false,
    ...overrides,
  };
}

function project(id: string, name: string): ProjectSummary {
  return {
    id,
    name,
    study_id: id,
    modality: "rs-fMRI",
    created_date: "2026-06-13",
    subjects_count: 1,
    current_pipeline_id: "not-selected",
  };
}

describe("WorkflowTabs", () => {
  it("renders WorkflowTabs with role=tablist", () => {
    render(<WorkflowTabs activeTab="data" onChange={vi.fn()} />);

    expect(screen.getByRole("tablist", { name: /workflow stages/i })).toBeInTheDocument();
  });

  it("renders all workflow tab buttons", () => {
    render(<WorkflowTabs activeTab="data" onChange={vi.fn()} />);

    expect(screen.getAllByRole("tab")).toHaveLength(4);
    expect(screen.getByRole("tab", { name: /data & conversion/i })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tab", { name: /preprocessing/i })).toHaveAttribute("aria-selected", "false");
  });

  it("calls onWorkflowStepChange on tab click", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<WorkflowTabs activeTab="data" onChange={handleChange} />);

    await user.click(screen.getByRole("tab", { name: /qc & reports/i }));

    expect(handleChange).toHaveBeenCalledWith("reports");
  });

  it("supports ArrowRight keyboard navigation", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<WorkflowTabs activeTab="data" onChange={handleChange} />);

    await user.tab();
    await user.keyboard("{ArrowRight}");

    expect(handleChange).toHaveBeenCalledWith("preprocessing");
  });

  it("supports End keyboard navigation", async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<WorkflowTabs activeTab="data" onChange={handleChange} />);

    screen.getByRole("tab", { name: /data & conversion/i }).focus();
    await user.keyboard("{End}");

    expect(handleChange).toHaveBeenCalledWith("environment");
  });
});

describe("ProjectList", () => {
  it("renders project list when projects are provided", () => {
    render(
      <ProjectList
        projects={[project("p1", "Project One"), project("p2", "Project Two")]}
        selectedProjectId="p1"
        loading={false}
        error=""
        deletingProjectId={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: "Project One" })).toHaveClass("selected");
    expect(screen.getByRole("button", { name: "Project Two" })).toBeInTheDocument();
  });

  it("shows loading state when projectsLoading=true", () => {
    render(
      <ProjectList
        projects={[project("p1", "Project One")]}
        selectedProjectId="p1"
        loading={true}
        error=""
        deletingProjectId={null}
        onSelect={vi.fn()}
        onDelete={vi.fn()}
      />,
    );

    expect(screen.getByText(/recent projects \(loading\)/i)).toBeInTheDocument();
  });

  it("calls selection and deletion callbacks", async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    const handleDelete = vi.fn();
    render(
      <ProjectList
        projects={[project("p1", "Project One")]}
        selectedProjectId=""
        loading={false}
        error=""
        deletingProjectId={null}
        onSelect={handleSelect}
        onDelete={handleDelete}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Project One" }));
    await user.click(screen.getByRole("button", { name: /remove project one/i }));

    expect(handleSelect).toHaveBeenCalledWith("p1");
    expect(handleDelete).toHaveBeenCalledWith("p1", "Project One");
  });
});

describe("Dashboard summary components", () => {
  it("renders ProjectHeroPanel project metadata and metrics", () => {
    render(<ProjectHeroPanel inventory={inventory()} />);

    expect(screen.getByRole("heading", { name: "Demo Project" })).toBeInTheDocument();
    expect(screen.getByText("NIfTI files")).toBeInTheDocument();
    expect(screen.getByText("10")).toBeInTheDocument();
  });

  it("renders raw DICOM recommended action", () => {
    render(
      <RecommendedNextStepCard
        inventory={inventory({ dataState: "raw_dicom", hasRawDicom: true, dataStateLabel: "Raw DICOM" })}
        hasPreprocessingRun={false}
        onPrimaryAction={vi.fn()}
        onSecondaryAction={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /generate conversion dry-run/i })).toBeInTheDocument();
    expect(screen.getByText("Persist review package")).toBeInTheDocument();
  });

  it("calls recommended action callbacks", async () => {
    const user = userEvent.setup();
    const primary = vi.fn();
    const secondary = vi.fn();
    render(
      <RecommendedNextStepCard
        inventory={inventory({ dataState: "converted_bids" })}
        hasPreprocessingRun={false}
        onPrimaryAction={primary}
        onSecondaryAction={secondary}
      />,
    );

    await user.click(screen.getByRole("button", { name: /create preprocessing run/i }));
    await user.click(screen.getByRole("button", { name: /review qc report status/i }));

    expect(primary).toHaveBeenCalled();
    expect(secondary).toHaveBeenCalled();
  });

  it("renders readiness strip statuses", () => {
    render(
      <ReadinessStatusStrip
        inventory={inventory({ dataState: "raw_dicom", rawDicomCandidates: 3 })}
        health={true}
        hasPreprocessingRun={false}
      />,
    );

    expect(screen.getByText("BIDS/NIfTI")).toBeInTheDocument();
    expect(screen.getByText("Expected before conversion")).toBeInTheDocument();
    expect(screen.getByText("Environment")).toBeInTheDocument();
  });
});
