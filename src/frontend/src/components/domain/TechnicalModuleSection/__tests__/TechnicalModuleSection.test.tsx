import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { Card, EmptyState } from "../../../ui";
import { TechnicalModuleSection } from "../TechnicalModuleSection";

describe("TechnicalModuleSection", () => {
  it("renders a collapsed technical section with safety language", () => {
    const onToggle = vi.fn();

    render(
      <TechnicalModuleSection
        ariaLabel="Derived modules"
        description="Secondary technical panels stay behind an explicit reveal action."
        helperText="Opening does not execute backend actions."
        hideActionLabel="Hide modules"
        isOpen={false}
        onToggle={onToggle}
        openLabel="Open modules"
        status="On demand"
        title="Derived modules"
      >
        <div data-testid="technical-body">Technical body</div>
      </TechnicalModuleSection>,
    );

    expect(screen.getByLabelText("Derived modules")).toHaveTextContent("On demand");
    expect(screen.queryByTestId("technical-body")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open modules" }));

    expect(onToggle).toHaveBeenCalledTimes(1);
  });

  it("keeps disabled technical modules closed and shows the disabled reason", () => {
    render(
      <TechnicalModuleSection
        actionDisabled
        ariaLabel="Report modules"
        description="Report modules require a selected project."
        disabledReason="Select a project before loading report modules."
        hideActionLabel="Hide report modules"
        isOpen={false}
        onToggle={vi.fn()}
        openLabel="Open report modules"
        status="Select project"
        statusTone="warning"
        title="Report modules"
      >
        <div data-testid="report-body">Report body</div>
      </TechnicalModuleSection>,
    );

    expect(screen.getByRole("button", { name: "Open report modules" })).toBeDisabled();
    expect(screen.getByText("Select a project before loading report modules.")).toBeInTheDocument();
    expect(screen.queryByTestId("report-body")).not.toBeInTheDocument();
  });

  it("can render status through shared evidence definitions", () => {
    render(
      <TechnicalModuleSection
        ariaLabel="Backend-owned tools"
        description="The UI can reveal tools without treating them as complete."
        evidenceLevel="backend_required"
        status="On demand"
        title="Backend-owned tools"
      />,
    );

    expect(screen.getByText("On demand")).toHaveAttribute(
      "title",
      "Backend evidence is required before this state can be treated as complete.",
    );
  });

  it("renders an always-visible body or fallback without a toggle", () => {
    const { rerender } = render(
      <TechnicalModuleSection
        ariaLabel="Artifact modules"
        bodyVisible={true}
        description="Artifact modules are visible for selected projects."
        status="Project scoped"
        title="Artifact modules"
      >
        <Card>Artifact body</Card>
      </TechnicalModuleSection>,
    );

    expect(screen.getByText("Artifact body")).toBeInTheDocument();

    rerender(
      <TechnicalModuleSection
        ariaLabel="Artifact modules"
        bodyVisible={false}
        description="Artifact modules are visible for selected projects."
        fallback={
          <EmptyState
            title="Artifact modules are waiting for project context"
            description="Select a project before loading artifacts."
          />
        }
        status="Select project"
        statusTone="warning"
        title="Artifact modules"
      >
        <Card>Artifact body</Card>
      </TechnicalModuleSection>,
    );

    expect(
      screen.getByText("Artifact modules are waiting for project context"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Artifact body")).not.toBeInTheDocument();
  });
});
