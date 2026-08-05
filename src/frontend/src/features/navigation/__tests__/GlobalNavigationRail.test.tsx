import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import { GlobalNavigationRail } from "../GlobalNavigationRail";

describe("GlobalNavigationRail", () => {
  it("navigates through existing workspace callbacks without inventing execution actions", async () => {
    const user = userEvent.setup();
    const onOpenLegacyWorkspace = vi.fn();
    const onOpenWorkspace = vi.fn();
    render(
      <I18nProvider locale="en">
        <GlobalNavigationRail
          location={{ kind: "legacy", projectId: "project-1", workspace: "overview" }}
          onOpenLegacyWorkspace={onOpenLegacyWorkspace}
          onOpenProjects={vi.fn()}
          onOpenWorkspace={onOpenWorkspace}
          projectId="project-1"
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("button", { name: "Overview" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    await user.click(screen.getByRole("button", { name: "Results" }));
    expect(onOpenLegacyWorkspace).toHaveBeenCalledWith("project-1", "results");

    await user.click(screen.getByRole("button", { name: "Runs" }));
    expect(onOpenWorkspace).toHaveBeenCalledWith("project-1", "runs");

    expect(screen.queryByRole("button", { name: /execute/i })).not.toBeInTheDocument();
  });

  it("keeps project workspaces disabled until a project is selected", () => {
    render(
      <I18nProvider locale="en">
        <GlobalNavigationRail
          location={{ kind: "projects" }}
          onOpenLegacyWorkspace={vi.fn()}
          onOpenProjects={vi.fn()}
          onOpenWorkspace={vi.fn()}
          projectId={null}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("button", { name: "Projects" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Agent" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Results" })).toBeDisabled();
  });
});
