import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TopBar, WorkspaceSuspenseFallback } from "../DashboardChrome";

describe("TopBar", () => {
  it("shows project context and opens the inspector", async () => {
    const user = userEvent.setup();
    const openInspector = vi.fn();
    const openAssistant = vi.fn();
    render(
      <TopBar
        health={true}
        apiError=""
        onRetry={vi.fn()}
        projectName="Demo Project"
        activePageLabel="Data & Conversion"
        onOpenAssistant={openAssistant}
        onOpenInspector={openInspector}
      />,
    );

    expect(screen.getByText("MedImage Agent")).toBeInTheDocument();
    expect(screen.getByText("Demo Project")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /advanced console/i })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /open assistant/i }));
    expect(openAssistant).toHaveBeenCalled();

    await user.click(screen.getByRole("button", { name: /open inspector/i }));
    expect(openInspector).toHaveBeenCalled();
  });

  it("surfaces backend errors with retry", async () => {
    const user = userEvent.setup();
    const retry = vi.fn();
    render(
      <TopBar
        health={false}
        apiError="Backend disconnected"
        onRetry={retry}
        projectName="Demo Project"
        activePageLabel="Plan"
        onOpenAssistant={vi.fn()}
        onOpenInspector={vi.fn()}
      />,
    );

    expect(screen.getByText("Backend disconnected")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Backend offline");
    await user.click(screen.getByRole("button", { name: "Retry" }));
    expect(retry).toHaveBeenCalled();
  });

  it("copies backend health diagnostics from the error banner", async () => {
    const user = userEvent.setup();
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
    render(
      <TopBar
        health={false}
        apiError="Backend disconnected"
        onRetry={vi.fn()}
        projectName="Demo Project"
        activePageLabel="Plan"
        onOpenAssistant={vi.fn()}
        onOpenInspector={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Copy diagnostics" }));

    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Health: Backend offline"));
    expect(writeText).toHaveBeenCalledWith(expect.stringContaining("Project: Demo Project"));
    expect(screen.getByText("Diagnostics copied")).toBeInTheDocument();
  });
});

describe("WorkspaceSuspenseFallback", () => {
  it("renders a page-level skeleton fallback with status semantics", () => {
    render(<WorkspaceSuspenseFallback label="Loading workspace..." />);

    expect(screen.getByRole("status", { name: "Loading workspace..." })).toHaveTextContent(
      "Loading workspace...",
    );
    expect(screen.getByText("Loading workspace...")).toBeInTheDocument();
  });
});
