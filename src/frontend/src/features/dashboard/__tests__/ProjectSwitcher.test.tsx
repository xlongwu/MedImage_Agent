import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ProjectSwitcher } from "../ProjectSwitcher";
import type { ProjectSummary } from "../../../lib/types/project";

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

describe("ProjectSwitcher", () => {
  it("selects a project from the popover", async () => {
    const user = userEvent.setup();
    const onSelect = vi.fn();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={vi.fn()}
        onOpenProjects={vi.fn()}
        onSelect={onSelect}
        projects={[project("p1", "Project One"), project("p2", "Project Two")]}
        selectedProjectId="p1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /project one/i }));
    await user.click(screen.getByRole("option", { name: /project two/i }));

    expect(onSelect).toHaveBeenCalledWith("p2");
  });

  it("closes the popover with Escape and returns focus to the trigger", async () => {
    const user = userEvent.setup();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={vi.fn()}
        onOpenProjects={vi.fn()}
        onSelect={vi.fn()}
        projects={[project("p1", "Project One"), project("p2", "Project Two")]}
        selectedProjectId="p1"
      />,
    );

    const trigger = screen.getByRole("button", { name: /project one/i });

    await user.click(trigger);
    expect(screen.getByRole("listbox", { name: "Project switcher" })).toBeInTheDocument();

    await user.keyboard("{Escape}");

    expect(screen.queryByRole("listbox", { name: "Project switcher" })).not.toBeInTheDocument();
    expect(trigger).toHaveFocus();
  });

  it("keeps one anchored popover and closes it when the trigger is clicked again", async () => {
    const user = userEvent.setup();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={vi.fn()}
        onOpenProjects={vi.fn()}
        onSelect={vi.fn()}
        projects={[project("p1", "DemoData 5"), project("p2", "Project Two")]}
        selectedProjectId="p1"
      />,
    );

    const trigger = screen.getByRole("button", { name: /demodata 5/i });

    await user.click(trigger);

    const popover = screen.getByRole("listbox", { name: "Project switcher" });
    expect(screen.getAllByRole("listbox", { name: "Project switcher" })).toHaveLength(1);
    expect(popover).toHaveStyle({ left: "16px", top: "8px", width: "320px" });

    await user.click(trigger);

    expect(screen.queryByRole("listbox", { name: "Project switcher" })).not.toBeInTheDocument();
  });

  it("requires confirmation before removing a recent project listing", async () => {
    const user = userEvent.setup();
    const onDelete = vi.fn();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={onDelete}
        onOpenProjects={vi.fn()}
        onSelect={vi.fn()}
        projects={[project("p1", "Project One")]}
        selectedProjectId="p1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /project one/i }));
    await user.click(screen.getByRole("button", { name: /more actions for project one/i }));

    expect(screen.getByRole("dialog", { name: "Remove project" })).toHaveTextContent(
      "data on disk is preserved",
    );
    expect(onDelete).not.toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: "Remove" }));

    expect(onDelete).toHaveBeenCalledWith("p1", "Project One");
  });

  it("opens the existing project import flow from the switcher", async () => {
    const user = userEvent.setup();
    const onCreateProject = vi.fn();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={onCreateProject}
        onDelete={vi.fn()}
        onOpenProjects={vi.fn()}
        onSelect={vi.fn()}
        projects={[project("p1", "Project One")]}
        selectedProjectId="p1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /project one/i }));
    await user.click(screen.getByRole("button", { name: /add project/i }));

    expect(onCreateProject).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("listbox", { name: "Project switcher" })).not.toBeInTheDocument();
  });

  it("opens the full projects page from the switcher", async () => {
    const user = userEvent.setup();
    const onOpenProjects = vi.fn();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error=""
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={vi.fn()}
        onOpenProjects={onOpenProjects}
        onSelect={vi.fn()}
        projects={[project("p1", "Project One")]}
        selectedProjectId="p1"
      />,
    );

    await user.click(screen.getByRole("button", { name: /project one/i }));
    await user.click(screen.getByRole("button", { name: /view all/i }));

    expect(onOpenProjects).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("listbox", { name: "Project switcher" })).not.toBeInTheDocument();
  });

  it("shows an unavailable state without fallback project rows when loading fails", async () => {
    const user = userEvent.setup();

    render(
      <ProjectSwitcher
        deletingProjectId={null}
        error="backend offline"
        loading={false}
        onCreateProject={vi.fn()}
        onDelete={vi.fn()}
        onOpenProjects={vi.fn()}
        onSelect={vi.fn()}
        projects={[]}
        selectedProjectId=""
      />,
    );

    expect(screen.getByText("Project list unavailable")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /select project/i }));

    expect(screen.getByRole("status")).toHaveTextContent(
      "The project list could not be loaded",
    );
    expect(screen.queryByRole("option")).not.toBeInTheDocument();
  });
});
