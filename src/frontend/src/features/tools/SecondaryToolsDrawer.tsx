import type { FormEvent } from "react";
import type { ChatMessage } from "../../lib/types/assistant";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ProjectDetail } from "../../lib/types/project";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";
import { useToolsDrawerController } from "./useToolsDrawerController";
import { PipelineSettingsCard } from "./PipelineSettingsCard";
import { AssistantPanel } from "./AssistantPanel";

export interface SecondaryToolsDrawerProps {
  isOpen: boolean;
  onToggle: () => void;
  onSetMode: (mode: "dashboard" | "advanced" | "planner") => void;
  project: ProjectDetail;
  model: ModelStatus;
  dataset: DatasetSummary;
  executionMode: ExecutionMode;
  externalSmokeApprovedRun: boolean;
  externalSmokeApprovedBy: string;
  assistantMessages: ChatMessage[];
  assistantInput: string;
  assistantLoading: boolean;
  assistantError: string;
  pipelineLoading: boolean;
  onExecutionModeChange: (mode: ExecutionMode) => void;
  onExternalSmokeApprovedRunChange: (value: boolean) => void;
  onExternalSmokeApprovedByChange: (value: string) => void;
  onConfigure: () => void;
  onAssistantInput: (value: string) => void;
  onAssistantSubmit: (event: FormEvent) => void;
  onNewChat: () => void;
  onQuickAction: (action: string) => void;
  projectId: string | null;
}

const quickActions = [
  { title: "New Pipeline", subtitle: "Create auditable workflow", kind: "flow", action: "new-pipeline" },
  { title: "Upload Data", subtitle: "Create project from DICOM or BIDS directory", kind: "cloud", action: "upload-data" },
  { title: "Run Pipeline", subtitle: "Start analysis", kind: "play", action: "run-pipeline" },
  { title: "View Results", subtitle: "Open latest report", kind: "chart", action: "view-results" },
];

export function SecondaryToolsDrawer({
  isOpen,
  onToggle,
  onSetMode,
  project,
  model,
  dataset,
  executionMode,
  externalSmokeApprovedRun,
  externalSmokeApprovedBy,
  assistantMessages,
  assistantInput,
  assistantLoading,
  assistantError,
  pipelineLoading,
  onExecutionModeChange,
  onExternalSmokeApprovedRunChange,
  onExternalSmokeApprovedByChange,
  onConfigure,
  onAssistantInput,
  onAssistantSubmit,
  onNewChat,
  onQuickAction,
  projectId,
}: SecondaryToolsDrawerProps) {
  const drawer = useToolsDrawerController(
    onSetMode,
    async () => { await onQuickAction("upload-data"); },
    async () => { await onQuickAction("run-pipeline"); },
    async () => { await onQuickAction("view-results"); },
    pipelineLoading,
  );

  if (!isOpen) {
    return (
      <aside className="secondary-tools-drawer collapsed" aria-label="Secondary tools drawer collapsed">
        <button
          type="button"
          className="drawer-toggle-btn"
          onClick={onToggle}
          title="Open Tools Drawer"
          aria-label="Open Tools Drawer"
        >
          <span className="drawer-toggle-icon">Open</span>
          <div className="vertical-text">Tools</div>
        </button>
      </aside>
    );
  }

  return (
    <aside className="secondary-tools-drawer open" aria-label="Secondary tools drawer">
      <details open>
        <summary className="drawer-summary" onClick={(e) => { e.preventDefault(); onToggle(); }}>
          <span>Tools Drawer</span>
          <span className="drawer-summary-action">Close</span>
        </summary>
        <div className="secondary-tools-stack">
          <PipelineSettingsCard
            project={project}
            model={model}
            dataset={dataset}
            executionMode={executionMode}
            externalSmokeApprovedRun={externalSmokeApprovedRun}
            externalSmokeApprovedBy={externalSmokeApprovedBy}
            onExecutionModeChange={onExecutionModeChange}
            onExternalSmokeApprovedRunChange={onExternalSmokeApprovedRunChange}
            onExternalSmokeApprovedByChange={onExternalSmokeApprovedByChange}
            onConfigure={onConfigure}
          />

          <details className="drawer-section">
            <summary className="drawer-section-summary">Assistant</summary>
            <AssistantPanel
              messages={assistantMessages}
              input={assistantInput}
              loading={assistantLoading}
              error={assistantError}
              onInput={onAssistantInput}
              onSubmit={onAssistantSubmit}
              onNewChat={onNewChat}
            />
          </details>

          <details className="drawer-section">
            <summary className="drawer-section-summary">Legacy Actions</summary>
            <div className="quick-grid compact">
              {quickActions.map((item) => (
                <button
                  key={item.title}
                  className={`quick-action ${item.kind}`}
                  onClick={() => onQuickAction(item.action)}
                  disabled={pipelineLoading && item.action === "run-pipeline"}
                >
                  <span>{item.title.slice(0, 1)}</span>
                  <strong>{item.action === "run-pipeline" && pipelineLoading ? "Running..." : item.title}</strong>
                  <small>{item.subtitle}</small>
                </button>
              ))}
            </div>
          </details>

          <details className="drawer-section">
            <summary className="drawer-section-summary">Planning Tools</summary>
            <div className="drawer-planning-actions">
              <button
                type="button"
                className="soft-button drawer-planning-button"
                onClick={() => onSetMode("planner")}
              >
                Plan Review Console
              </button>
              <button
                type="button"
                className="soft-button drawer-planning-button"
                onClick={() => onSetMode("advanced")}
              >
                Advanced Console
              </button>
            </div>
          </details>
        </div>
      </details>
    </aside>
  );
}
