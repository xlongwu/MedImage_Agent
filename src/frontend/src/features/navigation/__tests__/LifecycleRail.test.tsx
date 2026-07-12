import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import { LifecycleRail } from "../LifecycleRail";
import { buildLifecycleItems } from "../workspaceModel";

describe("LifecycleRail", () => {
  it("supports horizontal keyboard focus and does not enter blocked stages", async () => {
    const user = userEvent.setup();
    const onNavigate = vi.fn();
    render(
      <I18nProvider locale="en">
        <LifecycleRail
          activeWorkspace="overview"
          items={buildLifecycleItems({
            activeWorkspace: "overview",
            dataState: "raw_dicom",
            hasPreprocessingRun: false,
          })}
          onNavigate={onNavigate}
        />
      </I18nProvider>,
    );

    const overview = screen.getByRole("button", { name: "Overview" });
    overview.focus();
    await user.keyboard("{ArrowRight}");
    expect(screen.getByRole("button", { name: "Data" })).toHaveFocus();

    await user.click(screen.getByRole("button", { name: /Preprocessing/ }));
    expect(onNavigate).not.toHaveBeenCalled();
  });
});
