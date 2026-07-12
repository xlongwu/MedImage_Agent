import type { ProjectDataState, WorkflowLifecycleState } from "../../lib/projectWorkflow";

export type PrimaryWorkspace = "overview" | "data" | "plan" | "preprocessing" | "qc" | "results";
export type UtilityWorkspace = "runs" | "settings";
export type ProjectWorkspace = PrimaryWorkspace | UtilityWorkspace;

export type AppLocation =
  | { kind: "projects" }
  | { kind: "project"; projectId: string; workspace: ProjectWorkspace };

export type LifecycleItem = {
  id: PrimaryWorkspace;
  state: WorkflowLifecycleState;
  blockedReason: string | null;
};

export const primaryWorkspaces: PrimaryWorkspace[] = [
  "overview",
  "data",
  "plan",
  "preprocessing",
  "qc",
  "results",
];

export const utilityWorkspaces: UtilityWorkspace[] = ["runs", "settings"];

export function locationForProject(projectId: string): AppLocation {
  return { kind: "project", projectId, workspace: "overview" };
}

export function isPrimaryWorkspace(workspace: ProjectWorkspace): workspace is PrimaryWorkspace {
  return primaryWorkspaces.includes(workspace as PrimaryWorkspace);
}

export function buildLifecycleItems({
  activeWorkspace,
  dataState,
  hasPreprocessingRun,
}: {
  activeWorkspace: ProjectWorkspace;
  dataState: ProjectDataState | undefined;
  hasPreprocessingRun: boolean;
}): LifecycleItem[] {
  const converted = dataState === "converted_bids" || dataState === "mixed";
  const hasData = converted || dataState === "raw_dicom";

  return primaryWorkspaces.map((id) => {
    let state: WorkflowLifecycleState = "available";
    let blockedReason: string | null = null;

    if (id === "overview") state = activeWorkspace === id ? "current" : "available";
    if (id === "data")
      state = converted ? "completed" : activeWorkspace === id ? "current" : "available";
    if (id === "plan") {
      if (!hasData) {
        state = "blocked";
        blockedReason = "Import or register project data before reviewing a plan.";
      } else if (hasPreprocessingRun) state = "completed";
    }
    if (id === "preprocessing") {
      if (!converted) {
        state = "blocked";
        blockedReason = "Converted BIDS/NIfTI evidence is required before preprocessing.";
      } else if (hasPreprocessingRun) state = "completed";
    }
    if (id === "qc") {
      if (!hasPreprocessingRun) {
        state = "blocked";
        blockedReason = "A preprocessing run is required before QC evidence can be reviewed.";
      }
    }
    if (id === "results") {
      if (!hasPreprocessingRun) {
        state = "blocked";
        blockedReason =
          "Computed or registered run artifacts are required before results are available.";
      }
    }

    if (activeWorkspace === id && state !== "blocked" && state !== "completed") state = "current";
    return { id, state, blockedReason };
  });
}

export function canNavigateToWorkspace(
  items: LifecycleItem[],
  workspace: ProjectWorkspace,
): boolean {
  if (!isPrimaryWorkspace(workspace)) return true;
  return items.find((item) => item.id === workspace)?.state !== "blocked";
}
