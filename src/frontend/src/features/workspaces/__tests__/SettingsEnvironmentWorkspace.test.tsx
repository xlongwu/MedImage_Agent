import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { SettingsEnvironmentWorkspace } from "../SettingsEnvironmentWorkspace";
import { I18nProvider } from "../../../i18n/I18nProvider";

vi.mock("../../../components/EnvironmentHealthPanel", () => ({
  default: () => <div data-testid="environment-health-panel">Environment health panel</div>,
}));

vi.mock("../../../components/SpmRealignDryRunPanel", () => ({
  default: () => <div data-testid="spm-realign-dry-run-panel">SPM realign dry-run panel</div>,
}));

vi.mock("../../../components/SpmRealignWrapperSkeletonPanel", () => ({
  default: () => (
    <div data-testid="spm-realign-wrapper-skeleton-panel">SPM wrapper skeleton panel</div>
  ),
}));

vi.mock("../../../components/RsfmriPresetPanel", () => ({
  default: () => <div data-testid="rsfmri-preset-panel">rs-fMRI preset panel</div>,
}));

vi.mock("../../../components/DesktopSettingsPanel", () => ({
  default: () => <div data-testid="desktop-settings-panel">Desktop settings panel</div>,
}));

vi.mock("../../../components/ImportDiagnosticsPanel", () => ({
  default: ({
    projectId,
    rawdataDir,
  }: {
    projectId?: string | null;
    rawdataDir?: string | null;
  }) => (
    <div data-testid="import-diagnostics-panel">
      Import diagnostics panel {projectId} {rawdataDir}
    </div>
  ),
}));

vi.mock("../../../components/ExternalSmokePanel", () => ({
  default: () => <div data-testid="external-smoke-panel">External smoke panel</div>,
}));

vi.mock("../../../components/RsfmriReleaseReadinessPanel", () => ({
  RsfmriReleaseReadinessPanel: () => (
    <div data-testid="release-readiness-panel">Release readiness panel</div>
  ),
}));

vi.mock("../../memory/MemorySettingsPanel", () => ({
  MemorySettingsPanel: () => <div data-testid="memory-settings-panel">Memory settings panel</div>,
}));

function renderWorkspace(locale: "en" | "zh-CN" = "en", advancedMode = false) {
  const onThemePreferenceChange = vi.fn();
  const onAdvancedModeChange = vi.fn();

  render(
    <I18nProvider locale={locale}>
      <SettingsEnvironmentWorkspace
        advancedMode={advancedMode}
        baseUrl="http://localhost"
        localePreference={locale}
        onLocalePreferenceChange={vi.fn()}
        onAdvancedModeChange={onAdvancedModeChange}
        onThemePreferenceChange={onThemePreferenceChange}
        projectId="project-1"
        rawdataDir={"D:\\DemoData\\rawdata"}
        themePreference="light"
        onReviewDraft={vi.fn()}
      />
    </I18nProvider>,
  );

  return { onAdvancedModeChange, onThemePreferenceChange };
}

describe("SettingsEnvironmentWorkspace", () => {
  it("shows the settings map and safety gates before technical panels", () => {
    renderWorkspace();

    expect(screen.getByRole("navigation", { name: "Settings domains" })).toHaveTextContent(
      "Diagnostics",
    );
    expect(screen.getByRole("heading", { name: "Settings map" })).toBeInTheDocument();
    expect(screen.getByTestId("memory-settings-panel")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Settings domains" })).toHaveTextContent("Safety");
    expect(screen.getByRole("heading", { name: "General and integrations" })).toBeInTheDocument();
    expect(screen.getByRole("radiogroup", { name: "Theme preference" })).toBeInTheDocument();
    expect(
      screen.getByRole("table", { name: "General and integration controls" }),
    ).toHaveTextContent("Language / theme");
    expect(
      screen.getByRole("table", { name: "General and integration controls" }),
    ).toHaveTextContent("LLM provider");
    expect(screen.getByRole("heading", { name: "Safety gates" })).toBeInTheDocument();
    expect(screen.getAllByText("Backend gated").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "Safety policy matrix" })).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Safety policy matrix" })).toHaveTextContent(
      "Rawdata read-only",
    );
    expect(screen.getByRole("table", { name: "Safety policy matrix" })).toHaveTextContent(
      "External execution",
    );
    expect(screen.queryByLabelText("Environment setup modules")).not.toBeInTheDocument();
  });

  it("routes theme preference changes through app state", () => {
    const { onThemePreferenceChange } = renderWorkspace();

    expect(screen.getByRole("radio", { name: "Light" })).toHaveAttribute("aria-checked", "true");

    fireEvent.click(screen.getByRole("radio", { name: "Dark" }));

    expect(onThemePreferenceChange).toHaveBeenCalledWith("dark");
  });

  it("keeps Advanced Mode off and warns before opt-in", () => {
    const { onAdvancedModeChange } = renderWorkspace();

    expect(screen.getByRole("radio", { name: "Off" })).toHaveAttribute("aria-checked", "true");
    expect(screen.getByText(/change scientific meaning or comparability/i)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("radio", { name: "On" }));
    expect(onAdvancedModeChange).toHaveBeenCalledWith(true);
  });

  it("keeps manual environment tools out of the standard settings path", () => {
    renderWorkspace();

    expect(screen.queryByTestId("environment-health-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("spm-realign-dry-run-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("spm-realign-wrapper-skeleton-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("rsfmri-preset-panel")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Open diagnostics modules" }),
    ).not.toBeInTheDocument();
  });

  it("reveals compatibility environment tools only in Advanced Mode", () => {
    renderWorkspace("en", true);

    expect(screen.getByText("Readiness only")).toHaveAttribute(
      "title",
      "Metadata exists without enough persisted numerical or artifact evidence.",
    );
    expect(screen.getByTestId("environment-health-panel")).toBeInTheDocument();
    expect(screen.getByTestId("spm-realign-dry-run-panel")).toBeInTheDocument();
    expect(screen.getByTestId("spm-realign-wrapper-skeleton-panel")).toBeInTheDocument();
    expect(screen.getByTestId("rsfmri-preset-panel")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open diagnostics modules" })).toBeInTheDocument();
  });

  it("loads migrated diagnostics modules only on demand", () => {
    renderWorkspace("en", true);

    expect(screen.queryByTestId("desktop-settings-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("external-smoke-panel")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Open diagnostics modules" }));

    const diagnostics = screen.getByLabelText("System diagnostics modules");
    expect(diagnostics).toBeInTheDocument();
    expect(within(diagnostics).getByText("On demand")).toHaveAttribute(
      "title",
      "Backend evidence is required before this state can be treated as complete.",
    );
    expect(screen.getByTestId("desktop-settings-panel")).toBeInTheDocument();
    expect(screen.getByTestId("import-diagnostics-panel")).toBeInTheDocument();
    expect(screen.getByTestId("import-diagnostics-panel")).toHaveTextContent("project-1");
    expect(screen.getByTestId("import-diagnostics-panel")).toHaveTextContent(
      "D:\\DemoData\\rawdata",
    );
    expect(screen.getByTestId("external-smoke-panel")).toBeInTheDocument();
    expect(screen.getByTestId("release-readiness-panel")).toBeInTheDocument();
  });

  it("renders the settings map and safety policies in Chinese", () => {
    renderWorkspace("zh-CN");

    expect(screen.getByRole("heading", { name: "设置与环境" })).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "设置域" })).toHaveTextContent("诊断");
    expect(screen.getByRole("table", { name: "设置域" })).toHaveTextContent("后端门控");
    expect(screen.getByRole("radiogroup", { name: "主题偏好" })).toHaveTextContent("深色");
    expect(screen.getByRole("table", { name: "安全策略矩阵" })).toHaveTextContent("rawdata 只读");
    expect(screen.queryByRole("button", { name: "打开诊断模块" })).not.toBeInTheDocument();
  });
});
