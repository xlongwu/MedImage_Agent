import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ProjectShell } from "../ProjectShell";

describe("ProjectShell", () => {
  it("renders overview, optional viewer, and workspace landmarks", () => {
    render(
      <ProjectShell
        overview={<header>Project overview</header>}
        viewer={<aside>Viewer</aside>}
        workspaceLabel="Data workspace"
      >
        Workspace content
      </ProjectShell>,
    );

    expect(screen.getByText("Project overview")).toBeInTheDocument();
    expect(screen.getByText("Viewer")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Data workspace" })).toHaveTextContent(
      "Workspace content",
    );
  });

  it("omits the viewer slot when no viewer is supplied", () => {
    render(
      <ProjectShell overview={<header>Project overview</header>} workspaceLabel="Runs workspace">
        Runs content
      </ProjectShell>,
    );

    expect(screen.queryByText("Viewer")).not.toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Runs workspace" })).toHaveTextContent(
      "Runs content",
    );
  });
});
