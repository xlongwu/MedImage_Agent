"use client";
import { useCallback, useState } from "react";
import type { FormEvent } from "react";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { ProjectDetail } from "../../lib/types/project";
import type { DatasetSummary } from "../../lib/types/dataset";
import type { ModelStatus } from "../../lib/types/model";
import type { ChatMessage } from "../../lib/types/assistant";
import { sendAssistantMessage } from "../../lib/api";
import { fallbackChat } from "../../lib/mockData";

export interface ToolsDrawerController {
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  executionMode: ExecutionMode;
  setExecutionMode: (mode: ExecutionMode) => void;
  externalSmokeApprovedRun: boolean;
  setExternalSmokeApprovedRun: (v: boolean) => void;
  externalSmokeApprovedBy: string;
  setExternalSmokeApprovedBy: (v: string) => void;
  assistantMessages: ChatMessage[];
  assistantInput: string;
  setAssistantInput: (v: string) => void;
  assistantLoading: boolean;
  assistantError: string;
  pipelineLoading: boolean;
  handleAssistantSubmit: (e: FormEvent) => Promise<void>;
  handleNewChat: () => void;
  handleQuickAction: (action: string) => void;
}

export function useToolsDrawerController(
  setMode: (mode: "dashboard" | "advanced" | "planner") => void,
  handleUploadData: () => Promise<void>,
  handleRunPipeline: () => Promise<void>,
  handleViewResults: () => Promise<void>,
  pipelineLoading: boolean,
): ToolsDrawerController {
  const [isOpen, setIsOpen] = useState(false);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("simulated");
  const [externalSmokeApprovedRun, setExternalSmokeApprovedRun] = useState(false);
  const [externalSmokeApprovedBy, setExternalSmokeApprovedBy] = useState("");
  const [assistantMessages, setAssistantMessages] = useState<ChatMessage[]>(fallbackChat);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantLoading, setAssistantLoading] = useState(false);
  const [assistantError, setAssistantError] = useState("");

  const handleAssistantSubmit = useCallback(
    async (e: FormEvent) => {
      e.preventDefault();
      const message = assistantInput.trim();
      if (!message) return;
      setAssistantInput("");
      setAssistantError("");
      setAssistantLoading(true);
      setAssistantMessages((current) => [...current, { role: "user", text: message }]);
      try {
        const response = await sendAssistantMessage({ project_id: "", message });
        setAssistantMessages((current) => [
          ...current,
          { role: "assistant", text: response.reply },
        ]);
      } catch (err) {
        const friendly = err instanceof Error ? err.message : String(err);
        setAssistantError(friendly);
        setAssistantMessages((current) => [
          ...current,
          {
            role: "assistant",
            text: "I could not reach the local assistant endpoint. Please retry after the backend reconnects.",
          },
        ]);
      } finally {
        setAssistantLoading(false);
      }
    },
    [assistantInput],
  );

  const handleNewChat = useCallback(() => {
    setAssistantMessages(fallbackChat);
  }, []);

  const handleQuickAction = useCallback(
    (action: string) => {
      if (action === "new-pipeline") {
        // Pipeline builder is planned; current version keeps audited presets only.
      } else if (action === "upload-data") {
        void handleUploadData();
      } else if (action === "run-pipeline") {
        void handleRunPipeline();
      } else if (action === "view-results") {
        void handleViewResults();
      }
    },
    [handleUploadData, handleRunPipeline, handleViewResults],
  );

  return {
    isOpen,
    setIsOpen,
    executionMode,
    setExecutionMode,
    externalSmokeApprovedRun,
    setExternalSmokeApprovedRun,
    externalSmokeApprovedBy,
    setExternalSmokeApprovedBy,
    assistantMessages,
    assistantInput,
    setAssistantInput,
    assistantLoading,
    assistantError,
    pipelineLoading,
    handleAssistantSubmit,
    handleNewChat,
    handleQuickAction,
  };
}
