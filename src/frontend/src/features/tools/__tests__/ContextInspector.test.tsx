import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ContextInspector } from "../ContextInspector";

function renderInspector(isOpen = true) {
  const onToggle = vi.fn();
  const onConfigure = vi.fn();

  render(
    <ContextInspector
      activePageLabel="QC"
      dataset={{ subjects: 2, scans: 4, health_status: "review", total_size: "1 GB" } as never}
      executionMode="simulated"
      externalSmokeApprovedBy=""
      externalSmokeApprovedRun={false}
      inventory={
        {
          dataState: "converted_bids",
          dataStateLabel: "Converted BIDS/NIfTI",
          metadataOnlyNiftiInventory: false,
          modality: "rs-fMRI",
        } as never
      }
      isOpen={isOpen}
      model={{ model_name: "Planner", version: "0.6" } as never}
      onConfigure={onConfigure}
      onToggle={onToggle}
      project={{ id: "project-1", name: "Demo Project" } as never}
      selectionContext={{
        artifact: {
          evidenceLevel: "preview_only",
          name: "motion_qc.json",
          path: "runs/run-001/sub-001/qc/motion_qc.json",
          previewType: "json",
          runId: "run-001",
          stage: "qc",
          subject: "sub-001",
        },
        dataSeries: {
          evidenceLevel: "preview_only",
          series: "series-001",
          seriesDetail: "Series UID",
          sourceKind: "mapping_preview",
          status: "high",
          subject: "sub-001",
          subjectDetail: "dicom_series",
          warnings: [],
        },
        image: {
          plane: "axial",
          series: "bold",
          source: "sub-001/func/sub-001_task-rest_bold.nii.gz",
          subjectId: "sub-001",
        },
        planNode: {
          backend: "spm",
          detail: "Prepare realignment through reviewed backend gates.",
          id: "spm_realign",
          name: "Motion correction",
          risk: "High risk",
        },
        run: {
          id: "task-1",
          name: "Preprocessing run",
          pipeline: "rs-fMRI preprocessing",
          status: "failed",
        },
      }}
    />,
  );

  return { onConfigure, onToggle };
}

describe("ContextInspector", () => {
  it("renders a focused inspector without run quick actions", () => {
    renderInspector();

    expect(screen.getByLabelText("Context inspector")).toBeInTheDocument();
    expect(
      screen.getByText("Read-only project, workspace, run, and execution context"),
    ).toBeInTheDocument();
    expect(screen.getByText("Project context")).toBeInTheDocument();
    expect(screen.getByText("Demo Project")).toBeInTheDocument();
    expect(screen.getAllByText("Converted BIDS/NIfTI").length).toBeGreaterThan(0);
    expect(screen.getByText("Workspace context")).toBeInTheDocument();
    expect(screen.getByText("QC")).toBeInTheDocument();
    expect(screen.getByText("Selected objects")).toBeInTheDocument();
    expect(screen.getByText("sub-001 / series-001")).toBeInTheDocument();
    expect(screen.getAllByText("sub-001").length).toBeGreaterThan(0);
    expect(screen.getAllByText("bold").length).toBeGreaterThan(0);
    expect(screen.getByText("Motion correction (High risk)")).toBeInTheDocument();
    expect(screen.getByText("motion_qc.json - qc")).toBeInTheDocument();
    expect(screen.getAllByText("Preprocessing run (failed)").length).toBeGreaterThan(0);
    expect(screen.getByText("Evidence drilldown")).toBeInTheDocument();
    expect(screen.getAllByText("Preview-only").length).toBeGreaterThan(0);
    expect(screen.getByText("Planned only")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Open Settings" })).toBeInTheDocument();
    expect(screen.queryByText("Pipeline settings")).not.toBeInTheDocument();
    expect(screen.queryByRole("tablist", { name: "Drawer sections" })).not.toBeInTheDocument();
    expect(screen.queryByRole("tab", { name: "Run" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /View Results/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /External Smoke/i })).not.toBeInTheDocument();
  });

  it("does not render when closed", () => {
    renderInspector(false);

    expect(screen.queryByLabelText("Context inspector")).not.toBeInTheDocument();
  });
});
