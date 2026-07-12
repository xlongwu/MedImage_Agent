import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import type { ProjectInventory } from "../../../lib/projectWorkflow";
import { OverviewWorkspace } from "../OverviewWorkspace";

const inventory: ProjectInventory = {
  projectName: "Study A",
  modality: "rs-fMRI",
  dataState: "converted_bids",
  dataStateLabel: "Converted BIDS",
  stateSentence: "Converted data registered.",
  rawDicomCandidates: 0,
  dicomSeriesCount: 0,
  dicomFileCount: 0,
  convertedSubjects: 12,
  niftiFileCount: 24,
  hasRawDicom: false,
  hasConvertedData: true,
  metadataOnlyNiftiInventory: false,
};

describe("OverviewWorkspace", () => {
  it("shows only response-derived metrics and a reachable recommended action", () => {
    render(
      <I18nProvider locale="en">
        <OverviewWorkspace inventory={inventory} onNavigate={vi.fn()} tasks={[]} />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: "Study A" })).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review plan" })).toBeInTheDocument();
    expect(screen.queryByText(/Estimated/i)).not.toBeInTheDocument();
  });
});
