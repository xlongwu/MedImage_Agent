"use client";
import { useCallback, useEffect, useState } from "react";
import type { FormEvent } from "react";
import type { PresetPlanDraft } from "../../types";
import {
  DEFAULT_API_BASE,
  getApiBaseUrl,
  getHealth,
  approveTask,
  generateTaskAuditPackage,
  sendAssistantMessage,
} from "../../lib/api";
import { useTasks } from "../../hooks/useTasks";
import type { TaskAuditPackage } from "../../lib/types/task";
import type { ChatMessage } from "../../lib/types/assistant";

export interface AppController {
  baseUrl: string;
  setBaseUrl: (url: string) => void;
  activeWorkflow: import("../../lib/projectWorkflow").WorkflowTab;
  setActiveWorkflow: (tab: import("../../lib/projectWorkflow").WorkflowTab) => void;
  health: boolean | null;
  apiError: string;
  setApiError: (error: string) => void;
  notice: string;
  setNotice: (notice: string) => void;
  presetPlanDraft: PresetPlanDraft | null;
  setPresetPlanDraft: (draft: PresetPlanDraft | null) => void;
  drawerOpen: boolean;
  setDrawerOpen: (open: boolean) => void;
  checkHealth: () => Promise<void>;
  handleScrollToPanel: (panelId: string) => void;
  handleApproveTask: (taskId: string, approvalName: string) => Promise<string>;
  handleGenerateAuditPackage: (taskId: string) => Promise<{ report_path: string } | null>;
  handleReconnectTaskStream: (
    taskId: string | null,
    setActiveTaskId: (id: string | null) => void,
  ) => void;
  handleAssistantSubmit: (
    projectId: string,
    input: string,
    onReply: (text: string) => void,
    onError: (err: string) => void,
  ) => Promise<void>;
}

export function useAppController(): AppController {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_BASE);
  const [activeWorkflow, setActiveWorkflow] =
    useState<import("../../lib/projectWorkflow").WorkflowTab>("data");
  const [health, setHealth] = useState<boolean | null>(null);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");
  const [presetPlanDraft, setPresetPlanDraft] = useState<PresetPlanDraft | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const tasks = useTasks();

  const checkHealth = useCallback(async () => {
    setApiError("");
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const result = await getHealth(baseUrl);
        const status = typeof result.status === "string" ? result.status.toLowerCase() : "";
        const connected = status ? status === "ok" || status === "healthy" : Boolean(result);
        setHealth(connected);
        if (!connected) {
          setApiError("Backend health check returned a non-ready status.");
        }
        return;
      } catch {
        await new Promise((resolve) => setTimeout(resolve, 450));
      }
    }
    setHealth(false);
    setApiError(
      "Backend disconnected. Start it with:\npython -m uvicorn src.backend.app.main:app --host 127.0.0.1 --port 8000",
    );
  }, [baseUrl]);

  useEffect(() => {
    let active = true;
    getApiBaseUrl()
      .then((url) => {
        if (active) setBaseUrl(url);
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    checkHealth();
  }, [checkHealth]);

  const handleScrollToPanel = useCallback((panelId: string) => {
    document.getElementById(panelId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const handleApproveTask = useCallback(
    async (taskId: string, approvalName: string) => {
      const response = await approveTask(taskId, {
        approved: true,
        approved_by: approvalName.trim(),
        safety_flags: {
          rawdata_read_only: true,
          no_dparsf_blackbox: true,
          matlab_external_execution: true,
        },
      });
      await tasks.reload();
      return response.message;
    },
    [tasks],
  );

  const handleGenerateAuditPackage = useCallback(async (taskId: string) => {
    const response = await generateTaskAuditPackage(taskId);
    return response;
  }, []);

  const handleReconnectTaskStream = useCallback(
    (taskId: string | null, setActiveTaskId: (id: string | null) => void) => {
      const nextTaskId = taskId;
      if (!nextTaskId) {
        setNotice("Select a task before reconnecting the task stream.");
        return;
      }
      setActiveTaskId(null);
      window.setTimeout(() => setActiveTaskId(nextTaskId), 0);
    },
    [setNotice],
  );

  const handleAssistantSubmit = useCallback(
    async (
      projectId: string,
      input: string,
      onReply: (text: string) => void,
      onError: (err: string) => void,
    ) => {
      if (!input.trim()) return;
      try {
        const response = await sendAssistantMessage({ project_id: projectId, message: input });
        onReply(response.reply);
      } catch (err) {
        onError(err instanceof Error ? err.message : String(err));
      }
    },
    [],
  );

  return {
    baseUrl,
    setBaseUrl,
    activeWorkflow,
    setActiveWorkflow,
    health,
    apiError,
    setApiError,
    notice,
    setNotice,
    presetPlanDraft,
    setPresetPlanDraft,
    drawerOpen,
    setDrawerOpen,
    checkHealth,
    handleScrollToPanel,
    handleApproveTask,
    handleGenerateAuditPackage,
    handleReconnectTaskStream,
    handleAssistantSubmit,
  };
}
