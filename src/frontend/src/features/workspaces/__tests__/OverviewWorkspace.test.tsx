import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { I18nProvider } from "../../../i18n/I18nProvider";
import type { ProjectInventory } from "../../../lib/projectWorkflow";
import type { ProjectDetail } from "../../../lib/types/project";
import type { TaskLogEntry } from "../../../lib/types/task";
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

const project: ProjectDetail = {
  id: "project-1",
  name: "Study A",
  study_id: "study-a",
  modality: "rs-fMRI",
  created_date: "2026-06-24",
  subjects_count: 12,
  current_pipeline_id: "pipeline-1",
  sequences: ["BOLD"],
  scans_count: 24,
  total_size: "4 GB",
  current_model_id: "model-1",
  metadata: { project_dir: "D:/projects/study-a" },
};

const completedRun: TaskLogEntry = {
  id: "run-completed",
  run_name: "Agent Task run run-completed",
  pipeline: "reviewed-plan-1",
  dataset: "project-1",
  status: "completed",
  progress: 100,
  started_at: "2026-07-26T07:48:47.978398+00:00",
  duration: "1s",
  owner: "Agent Task",
  logs: [],
};

const olderPartialRun: TaskLogEntry = {
  ...completedRun,
  id: "run-older-partial",
  run_name: "Agent Task run run-older-partial",
  status: "partial",
  started_at: "2026-07-19T07:48:47Z",
};

describe("OverviewWorkspace", () => {
  it("shows only response-derived metrics and a reachable recommended action", () => {
    render(
      <I18nProvider locale="en">
        <OverviewWorkspace
          agentTask={null}
          dataset={null}
          inventory={inventory}
          lifecycleItems={[
            { id: "overview", state: "current", blockedReason: null },
            { id: "data", state: "completed", blockedReason: null },
            { id: "plan", state: "available", blockedReason: null },
            { id: "preprocessing", state: "available", blockedReason: null },
            { id: "qc", state: "blocked", blockedReason: "Run required" },
            { id: "results", state: "blocked", blockedReason: "Run required" },
          ]}
          model={null}
          onNavigate={vi.fn()}
          onSelectedPlanNodeChange={vi.fn()}
          project={project}
          tasks={[]}
        />
      </I18nProvider>,
    );

    expect(screen.getByRole("heading", { name: "Study A" })).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Review plan" })).toBeInTheDocument();
    expect(screen.queryByText(/Estimated/i)).not.toBeInTheDocument();
  });

  it("projects a completed project run instead of recommending another plan review", () => {
    render(
      <I18nProvider locale="en">
        <OverviewWorkspace
          agentTask={null}
          dataset={null}
          inventory={inventory}
          lifecycleItems={[
            { id: "overview", state: "current", blockedReason: null },
            { id: "data", state: "completed", blockedReason: null },
            { id: "plan", state: "completed", blockedReason: null },
            { id: "preprocessing", state: "completed", blockedReason: null },
            { id: "qc", state: "available", blockedReason: null },
            { id: "results", state: "available", blockedReason: null },
          ]}
          model={null}
          onNavigate={vi.fn()}
          onSelectedPlanNodeChange={vi.fn()}
          project={project}
          tasks={[completedRun]}
        />
      </I18nProvider>,
    );

    expect(screen.getAllByText("Agent Task run run-completed")).toHaveLength(2);
    expect(screen.getByText("Review completed results")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "View results" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Review plan" })).not.toBeInTheDocument();
  });

  it("does not let an older partial history entry override the latest completed run", () => {
    render(
      <I18nProvider locale="zh-CN">
        <OverviewWorkspace
          agentTask={null}
          dataset={null}
          inventory={inventory}
          lifecycleItems={[]}
          model={null}
          onNavigate={vi.fn()}
          onSelectedPlanNodeChange={vi.fn()}
          project={project}
          tasks={[olderPartialRun, completedRun]}
        />
      </I18nProvider>,
    );

    expect(screen.getByText("查看已完成结果")).toBeInTheDocument();
    expect(screen.queryByText("检查当前运行活动")).not.toBeInTheDocument();
  });

  it("localizes stable backend placeholder values in the Chinese overview", () => {
    render(
      <I18nProvider locale="zh-CN">
        <OverviewWorkspace
          agentTask={null}
          dataset={{
            project_id: "project-1",
            subjects: 12,
            scans: 24,
            total_size: "Referenced rawdata",
            health_status: "ready",
          }}
          inventory={inventory}
          lifecycleItems={[]}
          model={{
            project_id: "project-1",
            model_name: "No model selected",
            version: "Unavailable",
            status: "Unavailable",
            dice_score: 0,
            last_trained: "",
            metrics: {},
          }}
          onNavigate={vi.fn()}
          onSelectedPlanNodeChange={vi.fn()}
          project={project}
          tasks={[completedRun]}
        />
      </I18nProvider>,
    );

    expect(screen.getByText("未选择模型")).toBeInTheDocument();
    expect(screen.getByText("引用的原始数据")).toBeInTheDocument();
    expect(screen.queryByText("No model selected")).not.toBeInTheDocument();
    expect(screen.queryByText("Referenced rawdata")).not.toBeInTheDocument();
  });
});
