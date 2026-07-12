import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { I18nProvider } from "../../../../i18n/I18nProvider";
import { EvidenceBadge } from "../EvidenceBadge";

describe("EvidenceBadge", () => {
  it("renders the shared evidence truth label and description", () => {
    render(<EvidenceBadge level="backend_required" />);

    const badge = screen.getByText("Backend evidence required");

    expect(badge).toBeInTheDocument();
    expect(badge).toHaveAttribute(
      "title",
      "Backend evidence is required before this state can be treated as complete.",
    );
  });

  it("allows local visible copy while keeping the shared evidence level", () => {
    render(<EvidenceBadge level="preview_only">Preview boundary</EvidenceBadge>);

    expect(screen.getByText("Preview boundary")).toHaveAttribute(
      "title",
      "Preview evidence exists without export, validation, or full artifact handoff.",
    );
  });

  it("localizes shared evidence truth labels and descriptions", () => {
    render(
      <I18nProvider locale="zh-CN">
        <EvidenceBadge level="metadata_only" />
      </I18nProvider>,
    );

    expect(screen.getByText("仅元数据")).toHaveAttribute(
      "title",
      "存在元数据，但持久化数值或产物证据不足。",
    );
  });
});
