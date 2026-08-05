import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { AppShell } from "../AppShell";

describe("AppShell", () => {
  it("renders stable shell landmarks and slots", () => {
    render(
      <AppShell
        contextSidebar={<aside aria-label="Project context">Projects</aside>}
        preset="project-dashboard"
        rail={<nav aria-label="Primary navigation">Rail</nav>}
        topBar={<header>Top bar</header>}
        systemMessages={<div>Backend offline</div>}
        lifecycle={<nav aria-label="Project lifecycle">Lifecycle</nav>}
        inspector={<aside aria-label="Context inspector">Inspector</aside>}
        inspectorOpen={true}
        runActivity={<div role="status">Run active</div>}
      >
        <section>Workspace</section>
      </AppShell>,
    );

    expect(screen.getByText("Top bar")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Primary navigation" })).toBeInTheDocument();
    expect(screen.getByLabelText("Project context")).toBeInTheDocument();
    expect(screen.getByLabelText("System messages")).toHaveTextContent("Backend offline");
    expect(screen.getByRole("navigation", { name: "Project lifecycle" })).toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("Workspace");
    expect(screen.getByLabelText("Context inspector")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Run active");
  });

  it("omits optional inspector and message slots when closed", () => {
    render(
      <AppShell topBar={<header>Top bar</header>} lifecycle={<nav>Lifecycle</nav>}>
        Workspace
      </AppShell>,
    );

    expect(screen.queryByLabelText("System messages")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Context inspector")).not.toBeInTheDocument();
    expect(screen.getByRole("main")).toHaveTextContent("Workspace");
  });
});
