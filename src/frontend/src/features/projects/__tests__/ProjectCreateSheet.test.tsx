import type { ComponentProps } from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import { ProjectCreateSheet } from "../ProjectCreateSheet";

function renderSheet(
  overrides: Partial<ComponentProps<typeof ProjectCreateSheet>> = {},
  locale: "en" | "zh-CN" = "en",
) {
  const onCreate = vi.fn().mockResolvedValue({ project_id: "project-2" });
  const onOpenChange = vi.fn();
  const onSelectDirectory = vi.fn().mockResolvedValue("D:\\study\\rawdata");

  render(
    <I18nProvider locale={locale}>
      <ProjectCreateSheet
        error=""
        loading={false}
        onCreate={onCreate}
        onOpenChange={onOpenChange}
        onSelectDirectory={onSelectDirectory}
        open={true}
        {...overrides}
      />
    </I18nProvider>,
  );

  return { onCreate, onOpenChange, onSelectDirectory };
}

describe("ProjectCreateSheet", () => {
  it("creates a project through the three-step sheet", async () => {
    const user = userEvent.setup();
    const { onCreate, onOpenChange, onSelectDirectory } = renderSheet();

    expect(screen.getByRole("dialog", { name: "Create research project" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: "Select directory" }));

    expect(onSelectDirectory).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("D:\\study\\rawdata")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Continue" }));
    expect(screen.getByText("Reference existing files")).toBeInTheDocument();
    expect(screen.getByText("Required; backend determines project data state")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Source data is referenced read-only; no conversion or preprocessing is executed",
      ),
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith("D:\\study\\rawdata", { projectName: "rawdata" }),
    );
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it("blocks review until a directory is selected", async () => {
    const user = userEvent.setup();
    renderSheet({ onSelectDirectory: vi.fn().mockResolvedValue(null) });

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByRole("alert")).toHaveTextContent("Select a local data directory");
    expect(screen.queryByText("Reference existing files")).not.toBeInTheDocument();
  });

  it("keeps BIDS focus as review copy while creating through backend inspection", async () => {
    const user = userEvent.setup();
    const { onCreate } = renderSheet({
      onSelectDirectory: vi.fn().mockResolvedValue("D:\\study\\bids"),
    });

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: /BIDS or derivatives/i }));

    expect(screen.getByText(/backend inspection remains authoritative/i)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Select directory" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText("BIDS or derivatives")).toBeInTheDocument();
    expect(screen.getByText("Required; backend determines project data state")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() =>
      expect(onCreate).toHaveBeenCalledWith("D:\\study\\bids", { projectName: "bids" }),
    );
  });

  it("keeps the sheet open when backend creation does not return a project", async () => {
    const user = userEvent.setup();
    const onCreate = vi.fn().mockResolvedValue(null);
    const onOpenChange = vi.fn();

    renderSheet({ onCreate, onOpenChange });

    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: "Select directory" }));
    await user.click(screen.getByRole("button", { name: "Continue" }));
    await user.click(screen.getByRole("button", { name: "Create project" }));

    await waitFor(() => expect(onCreate).toHaveBeenCalledTimes(1));
    expect(onOpenChange).not.toHaveBeenCalledWith(false);
    expect(screen.getByRole("dialog", { name: "Create research project" })).toBeInTheDocument();
  });

  it("renders the complete project creation flow in Chinese", async () => {
    const user = userEvent.setup();
    renderSheet({}, "zh-CN");

    expect(screen.getByRole("dialog", { name: "创建研究项目" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "继续" }));
    expect(screen.getByText("检查重点")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /原始 DICOM/ })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "选择目录" })).toBeInTheDocument();
  });
});
