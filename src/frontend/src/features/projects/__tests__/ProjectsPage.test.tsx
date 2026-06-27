import type { ComponentProps } from "react";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProjectsPage } from "../ProjectsPage";
import type { ProjectSummary } from "../../../lib/types/project";

function project(
  id: string,
  name: string,
  overrides: Partial<ProjectSummary> = {},
): ProjectSummary {
  return {
    id,
    name,
    study_id: id.toUpperCase(),
    modality: "rs-fMRI",
    created_date: "June 13, 2026",
    subjects_count: 12,
    current_pipeline_id: "not-selected",
    ...overrides,
  };
}

function renderPage(overrides: Partial<ComponentProps<typeof ProjectsPage>> = {}) {
  const props: ComponentProps<typeof ProjectsPage> = {
    deletingProjectId: null,
    error: "",
    loading: false,
    onClose: vi.fn(),
    onCreateProject: vi.fn(),
    onDeleteProject: vi.fn(),
    onSelectProject: vi.fn(),
    projects: [
      project("p1", "Raw Study"),
      project("p2", "QC Cohort", {
        current_pipeline_id: "stroke-qc",
        modality: "MRI / DWI",
        subjects_count: 8,
      }),
    ],
    selectedProjectId: "p1",
    ...overrides,
  };

  render(<ProjectsPage {...props} />);
  return props;
}

describe("ProjectsPage", () => {
  it("renders project metrics and filters the project list", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByRole("heading", { name: "Projects" })).toBeInTheDocument();
    expect(screen.getByText("20")).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /raw study/i })).toBeInTheDocument();
    expect(screen.getByRole("cell", { name: /qc cohort/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Needs setup" }));

    expect(screen.getByRole("cell", { name: /raw study/i })).toBeInTheDocument();
    expect(screen.queryByRole("cell", { name: /qc cohort/i })).not.toBeInTheDocument();

    await user.clear(screen.getByRole("searchbox", { name: /search projects/i }));
    await user.type(screen.getByRole("searchbox", { name: /search projects/i }), "nothing");

    expect(screen.getByText("No projects match the current filters.")).toBeInTheDocument();
  });

  it("selects a project and returns to the workspace", async () => {
    const user = userEvent.setup();
    const props = renderPage();
    const row = screen.getByRole("row", { name: /qc cohort/i });

    await user.click(within(row).getByRole("button", { name: "Select" }));

    expect(props.onSelectProject).toHaveBeenCalledWith("p2");
    expect(props.onClose).toHaveBeenCalledTimes(1);
  });

  it("requires confirmation before removing a project listing", async () => {
    const user = userEvent.setup();
    const props = renderPage();
    const row = screen.getByRole("row", { name: /raw study/i });

    await user.click(within(row).getByRole("button", { name: "Remove" }));

    expect(screen.getByRole("dialog", { name: "Remove project" })).toHaveTextContent(
      "preserves data on disk",
    );
    expect(props.onDeleteProject).not.toHaveBeenCalled();

    await user.click(
      within(screen.getByRole("dialog", { name: "Remove project" })).getByRole("button", {
        name: "Remove",
      }),
    );

    expect(props.onDeleteProject).toHaveBeenCalledWith("p1", "Raw Study");
  });

  it("shows the voxel-grid empty state when no projects exist", async () => {
    const user = userEvent.setup();
    const props = renderPage({ projects: [] });

    await user.click(screen.getByRole("button", { name: /create your first research project/i }));

    expect(props.onCreateProject).toHaveBeenCalledTimes(1);
  });

  it("shows a project-list unavailable state without fallback rows after load errors", async () => {
    const user = userEvent.setup();
    const props = renderPage({ error: "backend offline", projects: [] });

    expect(screen.getByText("Project list unavailable")).toBeInTheDocument();
    expect(screen.getByText(/backend offline/i)).toBeInTheDocument();
    expect(screen.queryByRole("table")).not.toBeInTheDocument();
    expect(screen.queryByText(/raw study/i)).not.toBeInTheDocument();

    const addProjectButtons = screen.getAllByRole("button", { name: "Add project" });
    await user.click(addProjectButtons[addProjectButtons.length - 1]);

    expect(props.onCreateProject).toHaveBeenCalledTimes(1);
  });

  it("shows backend warnings above verified rows without adding fallback projects", () => {
    renderPage({
      error: "partial timeout",
      projects: [
        project("p1", "Verified Study", {
          current_pipeline_id: "custom-lab-pipeline",
        }),
      ],
    });

    expect(screen.getByRole("status")).toHaveTextContent("partial timeout");
    expect(screen.getByRole("cell", { name: /verified study/i })).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText(/not classified as a completed stage/i)).toBeInTheDocument();
    expect(screen.queryByText("Raw Study")).not.toBeInTheDocument();
    expect(screen.queryByText("QC Cohort")).not.toBeInTheDocument();
  });
});
