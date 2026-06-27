import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ArtifactBrowser } from "../ArtifactBrowser";

const apiMocks = vi.hoisted(() => ({
  getArtifacts: vi.fn(),
  previewArtifact: vi.fn(),
  refreshArtifacts: vi.fn(),
}));

vi.mock("../../lib/api/legacy", () => apiMocks);

const artifactIndex = {
  index: {
    artifacts_total: 2,
    generated_at: "2026-06-24T08:00:00Z",
    artifacts: [
      {
        category: "qc",
        extension: ".json",
        modified_time: "2026-06-24T08:02:00Z",
        name: "motion_qc.json",
        path: "runs/run-001/sub-001/qc/motion_qc.json",
        preview_supported: true,
        preview_type: "json",
        run_id_guess: "run-001",
        size_bytes: 2048,
      },
      {
        category: "report",
        extension: ".zip",
        modified_time: "2026-06-24T08:04:00Z",
        name: "research_package.zip",
        path: "runs/run-001/reports/research_package.zip",
        preview_supported: false,
        preview_type: "metadata_only",
        run_id_guess: "run-001",
        size_bytes: 4096,
      },
    ],
  },
};

beforeEach(() => {
  apiMocks.getArtifacts.mockReset();
  apiMocks.refreshArtifacts.mockReset();
  apiMocks.previewArtifact.mockReset();
});

function renderBrowser(onSelectedArtifactChange = vi.fn()) {
  render(
    <ArtifactBrowser
      baseUrl="http://localhost"
      onSelectedArtifactChange={onSelectedArtifactChange}
    />,
  );
  return { onSelectedArtifactChange };
}

describe("ArtifactBrowser", () => {
  it("loads the backend artifact index without showing placeholder rows first", async () => {
    const user = userEvent.setup();
    apiMocks.getArtifacts.mockResolvedValue(artifactIndex);

    const { onSelectedArtifactChange } = renderBrowser();

    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent(
      "Load the backend artifact index",
    );

    await user.click(screen.getByRole("button", { name: "Load Artifacts" }));

    expect(apiMocks.getArtifacts).toHaveBeenCalledWith("http://localhost");
    expect(await screen.findByText("Index metadata loaded")).toBeInTheDocument();
    expect(await screen.findByText("motion_qc.json")).toBeInTheDocument();
    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent("run-001");
    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent("sub-001");
    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent("Preview-only");
    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent("Created");
    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent("Unsupported");
    expect(screen.getByLabelText("Artifact provenance fields")).toHaveTextContent("Validation");
  });

  it("filters artifacts and previews supported records", async () => {
    const user = userEvent.setup();
    apiMocks.getArtifacts.mockResolvedValue(artifactIndex);
    apiMocks.previewArtifact.mockResolvedValue({
      artifact: artifactIndex.index.artifacts[0],
      preview: {
        parsed: { mean_fd: 0.12 },
        preview_type: "json",
        text: "Preview text",
        truncated: false,
      },
    });

    const { onSelectedArtifactChange } = renderBrowser();

    await user.click(screen.getByRole("button", { name: "Load Artifacts" }));
    await screen.findByText("motion_qc.json");

    await user.selectOptions(screen.getByLabelText("Type"), "report");

    expect(screen.getByRole("table", { name: "Artifact index" })).toHaveTextContent(
      "research_package.zip",
    );
    expect(screen.getByRole("table", { name: "Artifact index" })).not.toHaveTextContent(
      "motion_qc.json",
    );

    await user.selectOptions(screen.getByLabelText("Type"), "qc");
    await user.click(screen.getByRole("button", { name: "Preview" }));

    expect(apiMocks.previewArtifact).toHaveBeenCalledWith(
      "http://localhost",
      "runs/run-001/sub-001/qc/motion_qc.json",
    );
    expect(await screen.findByLabelText("Preview artifact metadata")).toHaveTextContent(
      "motion_qc.json",
    );
    expect(onSelectedArtifactChange).toHaveBeenLastCalledWith(
      expect.objectContaining({
        evidenceLevel: "preview_only",
        name: "motion_qc.json",
        runId: "run-001",
        stage: "motion",
        subject: "sub-001",
      }),
    );
    expect(screen.getByText("Preview text")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Close" }));

    expect(onSelectedArtifactChange).toHaveBeenLastCalledWith(null);
  });

  it("refreshes the artifact index through the existing backend call", async () => {
    const user = userEvent.setup();
    apiMocks.refreshArtifacts.mockResolvedValue(artifactIndex);

    renderBrowser();

    await user.click(screen.getByRole("button", { name: "Refresh Index" }));

    expect(apiMocks.refreshArtifacts).toHaveBeenCalledWith("http://localhost");
    expect(await screen.findByText("research_package.zip")).toBeInTheDocument();
  });
});
