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
  getTask,
} from "../../lib/api";
import { useRunPipeline } from "../../hooks/useRunPipeline";
import { useTasks } from "../../hooks/useTasks";
import type { ExecutionMode } from "../../lib/types/pipeline";
import type { TaskAuditPackage } from "../../lib/types/task";
import type { ChatMessage } from "../../lib/types/assistant";

export interface AppController {
  baseUrl: string;
  setBaseUrl: (url: string) => void;
  mode: "dashboard" | "advanced" | "planner";
  setMode: (mode: "dashboard" | "advanced" | "planner") => void;
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
  pipelineLoading: boolean;
  pipelineError: string;
  handleRunPipeline: (opts: {
    projectId: string;
    pipelineId: string;
    modelId: string;
    sequences: string[];
    executionMode: ExecutionMode;
    externalSmokeApproved: boolean;
    externalSmokeApprovedBy: string;
    onTaskStarted: (taskId: string) => void;
  }) => Promise<void>;
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
  handleQuickAction: (action: string) => void;
}

export function useAppController(): AppController {
  const [baseUrl, setBaseUrl] = useState(DEFAULT_API_BASE);
  const [mode, setMode] = useState<"dashboard" | "advanced" | "planner">("dashboard");
  const [activeWorkflow, setActiveWorkflow] =
    useState<import("../../lib/projectWorkflow").WorkflowTab>("data");
  const [health, setHealth] = useState<boolean | null>(null);
  const [apiError, setApiError] = useState("");
  const [notice, setNotice] = useState("");
  const [presetPlanDraft, setPresetPlanDraft] = useState<PresetPlanDraft | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const pipeline = useRunPipeline();
  const tasks = useTasks();

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
  }, [baseUrl]);

  useEffect(() => {}, []);

  const checkHealth = useCallback(async () => {
    setApiError("");
    for (let attempt = 0; attempt < 3; attempt += 1) {
      try {
        const result = await getHealth(baseUrl);
        setHealth((result as { status?: string }).status === "ok" || !!result);
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

  const handleScrollToPanel = useCallback((panelId: string) => {
    document.getElementById(panelId)?.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  const handleRunPipeline = useCallback(
    async ({
      projectId,
      pipelineId,
      modelId,
      sequences,
      executionMode,
      externalSmokeApproved,
      externalSmokeApprovedBy,
      onTaskStarted,
    }: {
      projectId: string;
      pipelineId: string;
      modelId: string;
      sequences: string[];
      executionMode: ExecutionMode;
      externalSmokeApproved: boolean;
      externalSmokeApprovedBy: string;
      onTaskStarted: (taskId: string) => void;
    }) => {
      const approvedExternalSmoke = executionMode === "external_smoke" && externalSmokeApproved;
      if (approvedExternalSmoke && !externalSmokeApprovedBy.trim()) {
        setNotice("Approved External Smoke requires an approved-by name.");
        return;
      }
      const response = await pipeline.start({
        project_id: projectId,
        pipeline_id: pipelineId,
        model_id: modelId,
        input_sequences: sequences,
        output_type: "segmentation_metrics",
        execution_mode: executionMode,
        external_smoke_mode: approvedExternalSmoke ? "approved_smoke" : "manual_package",
        approved: approvedExternalSmoke,
        approved_by: approvedExternalSmoke ? externalSmokeApprovedBy.trim() : null,
        dpabi_function: "y_Smooth",
      });
      if (!response) {
        setNotice(pipeline.error || "Failed to start pipeline");
        return;
      }
      try {
        const detail = await getTask(response.task_id);
        tasks.upsertTask(detail);
      } catch {
        await tasks.reload();
      }
      onTaskStarted(response.task_id);
      setNotice(`Pipeline started: ${response.task_id}`);
    },
    [pipeline, tasks, setNotice],
  );

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

  const handleQuickAction = useCallback(
    (action: string) => {
      if (action === "new-pipeline") {
        setNotice("Pipeline builder is planned; current version keeps audited presets only.");
      } else if (action === "upload-data") {
        // handled by projectController in App
      } else if (action === "run-pipeline") {
        // handled by App via handleRunPipeline
      } else if (action === "view-results") {
        setNotice("Result preview is available in the latest task details.");
      }
    },
    [setNotice],
  );

  return {
    baseUrl,
    setBaseUrl,
    mode,
    setMode,
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
    pipelineLoading: pipeline.loading,
    pipelineError: pipeline.error,
    handleRunPipeline,
    handleApproveTask,
    handleGenerateAuditPackage,
    handleReconnectTaskStream,
    handleAssistantSubmit,
    handleQuickAction,
  };
}
