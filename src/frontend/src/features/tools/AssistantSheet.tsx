import type { FormEvent } from "react";

import type { ChatMessage } from "../../lib/types/assistant";
import type { WorkspaceSelectionContext } from "../../lib/workspaceSelection";
import { Sheet } from "../../components/ui";
import { AssistantPanel } from "./AssistantPanel";
import styles from "./AssistantSheet.module.css";

export interface AssistantSheetProps {
  activePageLabel: string;
  error: string;
  input: string;
  loading: boolean;
  messages: ChatMessage[];
  open: boolean;
  projectName: string;
  selectionContext: WorkspaceSelectionContext;
  onInput: (value: string) => void;
  onNewChat: () => void;
  onOpenChange: (open: boolean) => void;
  onSubmit: (event: FormEvent) => void;
}

type PromptSuggestion = {
  kind: "Explanation" | "Summary" | "Draft";
  text: string;
};

const defaultSuggestedPrompts: PromptSuggestion[] = [
  { kind: "Explanation", text: "Explain the current workspace state" },
  { kind: "Summary", text: "Summarize the selected run evidence" },
  { kind: "Draft", text: "Draft the next safe review step" },
];

const workspacePromptMap: Record<string, PromptSuggestion[]> = {
  QC: [
    { kind: "Explanation", text: "Explain which QC evidence is still pending" },
    { kind: "Summary", text: "Summarize the QC review gaps for this project" },
    { kind: "Draft", text: "Draft a non-executing QC review checklist" },
  ],
  Results: [
    { kind: "Explanation", text: "Explain the artifact provenance boundary" },
    { kind: "Summary", text: "Summarize which result records need backend evidence" },
    { kind: "Draft", text: "Draft a handoff note for planned and created artifacts" },
  ],
  "Settings / Environment": [
    { kind: "Explanation", text: "Explain the current environment readiness boundaries" },
    { kind: "Summary", text: "Summarize safety gates that remain backend-owned" },
    { kind: "Draft", text: "Draft a safe environment review checklist" },
  ],
  Runs: [
    { kind: "Explanation", text: "Explain the selected run diagnostics" },
    { kind: "Summary", text: "Summarize run evidence without suggesting execution" },
    { kind: "Draft", text: "Draft the next reviewed run follow-up" },
  ],
  Plan: [
    { kind: "Explanation", text: "Explain the plan evidence and locked gates" },
    { kind: "Summary", text: "Summarize nodes that need review evidence" },
    { kind: "Draft", text: "Draft plan review questions for the maintainer" },
  ],
};

function getSuggestedPrompts(activePageLabel: string): PromptSuggestion[] {
  return workspacePromptMap[activePageLabel] ?? defaultSuggestedPrompts;
}

export function AssistantSheet({
  activePageLabel,
  error,
  input,
  loading,
  messages,
  onInput,
  onNewChat,
  onOpenChange,
  onSubmit,
  open,
  projectName,
  selectionContext,
}: AssistantSheetProps) {
  const suggestedPrompts = getSuggestedPrompts(activePageLabel);
  const selectedObjectText = [
    selectionContext.dataSeries
      ? `data series ${selectionContext.dataSeries.subject} / ${selectionContext.dataSeries.series}`
      : "",
    selectionContext.image.subjectId ? `subject ${selectionContext.image.subjectId}` : "",
    selectionContext.image.series ? `series ${selectionContext.image.series}` : "",
    selectionContext.planNode ? `node ${selectionContext.planNode.name}` : "",
    selectionContext.artifact ? `artifact ${selectionContext.artifact.name}` : "",
  ]
    .filter(Boolean)
    .join(" / ");

  return (
    <Sheet
      closeLabel="Close assistant"
      description="Context-aware guidance. Execution still requires explicit plan, approval, or workspace action."
      onOpenChange={onOpenChange}
      open={open}
      title="Assistant"
    >
      <div className={styles.sheetBody}>
        <section className={styles.contextPanel} aria-label="Assistant context">
          <div>
            <span>Project</span>
            <strong>{projectName || "No project selected"}</strong>
          </div>
          <div>
            <span>Workspace</span>
            <strong>{activePageLabel}</strong>
          </div>
          <div>
            <span>Run</span>
            <strong>{formatRun(selectionContext)}</strong>
          </div>
          <div>
            <span>Selection</span>
            <strong>{selectedObjectText || "No object selected"}</strong>
          </div>
          <div>
            <span>Action mode</span>
            <strong>Explain / summarize / draft</strong>
          </div>
          <div>
            <span>Provider</span>
            <strong>
              Mock provider: no external API used; real LLM disabled until API key is configured
            </strong>
          </div>
        </section>

        <section className={styles.suggestionPanel} aria-label="Assistant suggestions">
          <div className={styles.panelHeader}>
            <h3>Suggested prompts</h3>
            <p>Prompt helpers only. They do not execute actions.</p>
          </div>
          <div className={styles.promptGrid}>
            {suggestedPrompts.map((prompt) => (
              <button
                aria-label={prompt.text}
                key={prompt.text}
                type="button"
                onClick={() => onInput(prompt.text)}
              >
                <span>{prompt.kind}</span>
                <strong>{prompt.text}</strong>
              </button>
            ))}
          </div>
        </section>

        <div className={styles.actionBoundary}>
          <strong>Execution boundary</strong>
          <p>
            Assistant responses can explain, summarize, or draft plans. Running pipelines, approving
            tasks, and changing external-tool settings remain in their reviewed workspaces. Mock
            provider mode uses the local safe default and no external API. A real LLM provider stays
            disabled until an API key is configured.
          </p>
        </div>

        <AssistantPanel
          error={error}
          input={input}
          loading={loading}
          messages={messages}
          onInput={onInput}
          onNewChat={onNewChat}
          onSubmit={onSubmit}
        />
      </div>
    </Sheet>
  );
}

function formatRun(selectionContext: WorkspaceSelectionContext): string {
  if (!selectionContext.run.id) return "No run selected";
  return selectionContext.run.name ?? selectionContext.run.id;
}
