import type { ImagePreview } from "../../lib/types/image";
import type { ProjectInventory, WorkflowTab } from "../../lib/projectWorkflow";

const viewerWorkflows = new Set<WorkflowTab>(["data", "preprocessing", "reports", "results"]);

export function shouldRenderProjectImageViewer({
  activeWorkflow,
  inventory,
}: {
  activeWorkflow: WorkflowTab;
  inventory: ProjectInventory | null;
}): boolean {
  if (!inventory || !viewerWorkflows.has(activeWorkflow)) {
    return false;
  }

  return inventory.dataState === "converted_bids" || inventory.dataState === "mixed";
}

export function hasRealImagePreview(preview: ImagePreview | null): boolean {
  return Boolean(preview?.preview_url);
}
