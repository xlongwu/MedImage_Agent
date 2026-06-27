import React, { useMemo, useRef, useState } from "react";
import {
  DEFAULT_API_BASE,
  checkApprovalGate,
  executeReviewedDryRun,
  executeReviewedPlan,
  fetchAuditRecord,
  fetchToolCatalog,
  generatePlanFromGoal,
  listProjectReviewedPlans,
  saveReviewedPlan,
  validatePlan,
} from "../lib/api/legacy";
import { describeExecuteReviewedStatus } from "../lib/executeReviewedStatus";
import {
  detectExternalToolNodes,
  isExternalToolApprovalComplete,
} from "../lib/externalToolApproval";
import type { ExecuteReviewedSeverity } from "../lib/executeReviewedStatus";
import type { ProjectDetail } from "../lib/types/project";
import type { ExecuteReviewedResponse, PresetPlanDraft, ReviewedPlanRecord } from "../types";
import styles from "./PlanReviewConsole.module.css";

function cssVars(vars: Record<string, string>): React.CSSProperties {
  return vars as React.CSSProperties;
}

type PlanData = Record<string, unknown> | null;

type Props = {
  selectedProjectId: string | null;
  selectedProject: ProjectDetail | null;
  projectConfigPath?: string;
  datasetIndexPath?: string | null;
  rawdataDir?: string;
  initialPresetDraft?: PresetPlanDraft | null;
};

type CatalogItem = {
  id: string;
  name: string;
  backend: string;
  parallel_level: string;
  description: string;
  requires_approval: boolean;
  manual_required: boolean;
  risk_level: string;
  inputs: string[];
  outputs: string[];
  tags: string[];
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function reviewedPlanIssues(plan: unknown): string[] {
  if (!isRecord(plan)) {
    return ["plan object"];
  }
  const issues: string[] = [];
  if (!isRecord(plan.project_context)) {
    issues.push("project_context");
  }
  if (typeof plan.goal !== "string" || !plan.goal.trim()) {
    issues.push("goal");
  }
  if (!Array.isArray(plan.nodes) || plan.nodes.length === 0) {
    issues.push("nodes");
  }
  if (!isRecord(plan.metadata)) {
    issues.push("metadata");
  }
  return issues;
}

function invalidReviewedPlanMessage(issues: string[]): string {
  return `Generated plan is invalid and was not persisted. Missing or empty: ${issues.join(", ")}.`;
}

function providerStatusMessage(provider: string): string {
  if (provider === "openai_compatible") {
    return "Real LLM provider selected: requires MEDIMAGE_LLM_API_KEY. If the key is missing, the backend blocks generation before any external API call.";
  }
  if (provider === "rule_based") {
    return "Rule-based provider: local deterministic planner, no external API used.";
  }
  return "Mock provider: no external API used. Generates a deterministic metadata-only reviewed-plan draft.";
}

function providerFailureMessage(provider: string, errors: string[]): string {
  if (provider === "openai_compatible" && errors.some((item) => item.includes("LLM_API_KEY_MISSING"))) {
    return "LLM provider disabled: API key not configured. MEDIMAGE_LLM_API_KEY is missing, so openai_compatible generation was blocked before any external API call. Select mock/rule_based for local deterministic planning or configure the key before using openai_compatible.";
  }
  return errors[0] || "Plan generation did not produce a valid reviewed plan.";
}

export default function PlanReviewConsole({
  selectedProjectId,
  selectedProject,
  projectConfigPath: selectedProjectConfigPath,
  datasetIndexPath,
  rawdataDir,
  initialPresetDraft,
}: Props) {
  const baseUrl = DEFAULT_API_BASE;
  const [goal, setGoal] = useState("");
  const [provider, setProvider] = useState("mock");
  const [loadedPresetBanner, setLoadedPresetBanner] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<PlanData>(null);
  const [error, setError] = useState("");

  // ── Tool Catalog ──
  const [catalogMap, setCatalogMap] = useState<Record<string, CatalogItem>>({});
  const [catalogError, setCatalogError] = useState("");

  // ── Edit + re-validate ──
  const [planJson, setPlanJson] = useState("");
  const [validateLoading, setValidateLoading] = useState(false);
  const [jsonError, setJsonError] = useState("");
  const [reValidation, setReValidation] = useState<Record<string, unknown> | null>(null);
  const [copyStatus, setCopyStatus] = useState("");

  // ── Approval Gate ──
  const [approvalApproved, setApprovalApproved] = useState(true);
  const [approvalBy, setApprovalBy] = useState("");
  const [approvalReason, setApprovalReason] = useState("");
  const [approvalNodesInput, setApprovalNodesInput] = useState("");
  const [rejectedNodesInput, setRejectedNodesInput] = useState("");
  const [approvalResult, setApprovalResult] = useState<Record<string, unknown> | null>(null);
  const [approvalLoading, setApprovalLoading] = useState(false);
  const [approvalError, setApprovalError] = useState("");

  // ── External-tool safety acknowledgements ──
  const [externalToolAcknowledgement, setExternalToolAcknowledgement] = useState(false);
  const [rawdataReadOnlyConfirmed, setRawdataReadOnlyConfirmed] = useState(false);
  const [outputDirectoryConfirmed, setOutputDirectoryConfirmed] = useState(false);
  const [riskAcknowledgement, setRiskAcknowledgement] = useState(false);
  const [subjectScopeConfirmed, setSubjectScopeConfirmed] = useState(false);
  const [overwritePolicy, setOverwritePolicy] = useState<
    "fail_if_exists" | "require_explicit_overwrite_approval"
  >("fail_if_exists");

  // ── Dry-run Execution Check ──
  const [dryRunResult, setDryRunResult] = useState<ExecuteReviewedResponse | null>(null);
  const [dryRunLoading, setDryRunLoading] = useState(false);
  const [dryRunError, setDryRunError] = useState("");
  const [persistAudit, setPersistAudit] = useState(false);

  // ── Audit detail ──
  const [auditDetail, setAuditDetail] = useState<Record<string, unknown> | null>(null);
  const [auditLoading, setAuditLoading] = useState(false);
  const [auditFetchError, setAuditFetchError] = useState("");

  // ── Reviewed Execution ──
  const [executionLoading, setExecutionLoading] = useState(false);
  const [executionResult, setExecutionResult] = useState<ExecuteReviewedResponse | null>(null);
  const [executionError, setExecutionError] = useState("");
  const [confirmExecution, setConfirmExecution] = useState(false);
  const [explicitDemoMode, setExplicitDemoMode] = useState(false);
  const [demoProjectConfigPath, setDemoProjectConfigPath] = useState(
    "examples/project_config_synthetic_smoke.yaml",
  );
  const [actorName, setActorName] = useState("frontend-user");

  // Reviewed plan history for the selected real project
  const [reviewedPlanId, setReviewedPlanId] = useState<string | null>(null);
  const [recentPlans, setRecentPlans] = useState<ReviewedPlanRecord[]>([]);
  const [planHistoryLoading, setPlanHistoryLoading] = useState(false);
  const [planHistoryError, setPlanHistoryError] = useState("");
  const [planSaveStatus, setPlanSaveStatus] = useState("");

  // ── Node detail panel ──
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  const effectiveProjectConfigPath = explicitDemoMode
    ? demoProjectConfigPath.trim()
    : (selectedProjectConfigPath?.trim() ?? "");

  // ── Detect high-risk external-tool nodes ──
  const externalToolReq = useMemo(() => {
    const plan = result?.plan ?? null;
    return detectExternalToolNodes(plan as Record<string, unknown> | null);
  }, [result]);

  // Helper: build the external-tool approval fields to merge into the approval payload
  function externalToolApprovalFields() {
    if (!externalToolReq.required) return {};
    return {
      external_tool_acknowledgement: externalToolAcknowledgement,
      rawdata_read_only_confirmed: rawdataReadOnlyConfirmed,
      output_directory_confirmed: outputDirectoryConfirmed,
      risk_acknowledgement: riskAcknowledgement,
      subject_scope_confirmed: subjectScopeConfirmed,
      overwrite_policy: overwritePolicy,
    };
  }

  const externalToolApprovalComplete = isExternalToolApprovalComplete(externalToolReq, {
    externalToolAcknowledgement,
    rawdataReadOnlyConfirmed,
    outputDirectoryConfirmed,
    riskAcknowledgement,
    subjectScopeConfirmed,
    overwritePolicy,
  });

  const effectiveProjectId = explicitDemoMode ? undefined : (selectedProjectId ?? undefined);
  const projectContextError = explicitDemoMode
    ? effectiveProjectConfigPath
      ? ""
      : "Explicit demo mode requires a project config path."
    : !selectedProjectId
      ? "Select or create a real project before generating a plan."
      : !selectedProject
        ? "Selected project details are still loading or unavailable."
        : !selectedProjectConfigPath
          ? "Selected project is missing metadata.project_config_path."
          : "";

  const lastDraftKeyRef = useRef<string | null>(null);

  React.useEffect(() => {
    setResult(null);
    setPlanJson("");
    setReValidation(null);
    setDryRunResult(null);
    setExecutionResult(null);
    setConfirmExecution(false);
    setReviewedPlanId(null);
    setRecentPlans([]);
    setPlanHistoryError("");
    setPlanSaveStatus("");
    setLoadedPresetBanner(null);
    setExternalToolAcknowledgement(false);
    setRawdataReadOnlyConfirmed(false);
    setOutputDirectoryConfirmed(false);
    setRiskAcknowledgement(false);
    setSubjectScopeConfirmed(false);
  }, [selectedProjectId, selectedProjectConfigPath, explicitDemoMode, demoProjectConfigPath]);

  // ── Load preset draft ──
  React.useEffect(() => {
    if (!initialPresetDraft) return;
    const plan = initialPresetDraft.plan;
    if (!plan || typeof plan !== "object") return;
    const draftKey = `${initialPresetDraft.project_id}:${initialPresetDraft.preset_id}:${JSON.stringify(plan).length}`;
    if (draftKey === lastDraftKeyRef.current) return;
    lastDraftKeyRef.current = draftKey;

    const planStr = JSON.stringify(plan, null, 2);
    setGoal(initialPresetDraft.goal);
    setProvider("pipeline_preset");
    setResult({
      ok: true,
      plan: plan,
      validation: initialPresetDraft.validation ?? {},
      provider: "pipeline_preset",
      warnings: initialPresetDraft.warnings ?? [],
      errors: [],
      messages: [`Loaded from pipeline preset: ${initialPresetDraft.preset_id}`],
    });
    setPlanJson(planStr);
    setReValidation((initialPresetDraft.validation ?? null) as Record<string, unknown> | null);
    setDryRunResult(null);
    setExecutionResult(null);
    setConfirmExecution(false);
    setReviewedPlanId(null);
    setPlanSaveStatus("");
    setLoadedPresetBanner(
      `Loaded preset draft: ${initialPresetDraft.preset_id}. This is a contract MVP and does not run real SPM/DPABI preprocessing yet.`,
    );
  }, [initialPresetDraft]);

  async function refreshRecentPlans(projectId = selectedProjectId) {
    if (!projectId || explicitDemoMode) {
      setRecentPlans([]);
      return;
    }
    setPlanHistoryLoading(true);
    try {
      const data = await listProjectReviewedPlans(baseUrl, projectId);
      setRecentPlans(data.reviewed_plans ?? []);
      setPlanHistoryError("");
    } catch (e) {
      setPlanHistoryError(e instanceof Error ? e.message : String(e));
    } finally {
      setPlanHistoryLoading(false);
    }
  }

  React.useEffect(() => {
    if (selectedProjectId && selectedProjectConfigPath && !explicitDemoMode) {
      void refreshRecentPlans(selectedProjectId);
    }
  }, [selectedProjectId, selectedProjectConfigPath, explicitDemoMode]);

  async function persistReviewedPlan(
    plan: Record<string, unknown>,
    validationResult: Record<string, unknown>,
  ) {
    const planIssues = reviewedPlanIssues(plan);
    if (planIssues.length > 0) {
      setReviewedPlanId(null);
      setPlanSaveStatus("");
      setPlanHistoryError(invalidReviewedPlanMessage(planIssues));
      return;
    }
    if (explicitDemoMode || !selectedProjectId || !effectiveProjectConfigPath) return;
    setPlanSaveStatus("Saving reviewed plan...");
    setPlanHistoryError("");
    try {
      const data = await saveReviewedPlan(baseUrl, selectedProjectId, {
        plan,
        project_config_path: effectiveProjectConfigPath,
        validation: validationResult,
        goal: goal.trim() || undefined,
        provider,
      });
      setReviewedPlanId(data.reviewed_plan.reviewed_plan_id);
      setPlanSaveStatus(`Saved ${data.reviewed_plan.reviewed_plan_id}`);
      await refreshRecentPlans(selectedProjectId);
    } catch (e) {
      setReviewedPlanId(null);
      setPlanSaveStatus("");
      setPlanHistoryError(
        `Plan generated but could not be persisted: ${e instanceof Error ? e.message : String(e)}`,
      );
    }
  }

  function restoreReviewedPlan(record: ReviewedPlanRecord) {
    const restoredPlan = record.payload.plan;
    const planIssues = reviewedPlanIssues(restoredPlan);
    if (planIssues.length > 0) {
      setPlanHistoryError(`Stored reviewed plan is incomplete. ${invalidReviewedPlanMessage(planIssues)}`);
      return;
    }
    const restoredValidation =
      record.payload.validation && typeof record.payload.validation === "object"
        ? record.payload.validation
        : {};
    setResult({
      ok: true,
      plan: restoredPlan,
      validation: restoredValidation,
      provider: record.payload.provider ?? "persisted",
      warnings: record.warnings,
      errors: [],
    });
    setPlanJson(JSON.stringify(restoredPlan, null, 2));
    setReValidation(restoredValidation);
    setReviewedPlanId(record.reviewed_plan_id);
    setGoal(typeof record.payload.goal === "string" ? record.payload.goal : "");
    setPlanSaveStatus(`Restored ${record.reviewed_plan_id}`);
    setPlanHistoryError("");
    setDryRunResult(null);
    setExecutionResult(null);
    setConfirmExecution(false);
  }

  // Load full catalog on mount
  React.useEffect(() => {
    fetchToolCatalog(baseUrl)
      .then((data) => {
        const map: Record<string, CatalogItem> = {};
        const items = (data?.items ?? []) as Array<Record<string, unknown>>;
        for (const item of items) {
          const id = String(item.id ?? "");
          map[id] = {
            id,
            name: String(item.name ?? id),
            backend: String(item.backend ?? "?"),
            parallel_level: String(item.parallel_level ?? "?"),
            description: String(item.description ?? ""),
            requires_approval: Boolean(item.requires_approval),
            manual_required: Boolean(item.manual_required),
            risk_level: String(item.risk_level ?? "?"),
            inputs: Array.isArray(item.inputs) ? (item.inputs as string[]) : [],
            outputs: Array.isArray(item.outputs) ? (item.outputs as string[]) : [],
            tags: Array.isArray(item.tags) ? (item.tags as string[]) : [],
          };
        }
        setCatalogMap(map);
        setCatalogError("");
      })
      .catch(() => setCatalogError("Tool Catalog unavailable — node metadata limited."));
  }, [baseUrl]);

  async function handleGenerate() {
    setError("");
    setResult(null);
    setPlanJson("");
    setReValidation(null);
    setJsonError("");
    setSelectedNodeId(null);
    if (!goal.trim()) {
      setError("Please enter a goal.");
      return;
    }
    if (projectContextError) {
      setError(projectContextError);
      return;
    }
    setLoading(true);
    try {
      const data = await generatePlanFromGoal(baseUrl, {
        goal: goal.trim(),
        provider,
        project_id: effectiveProjectId,
        project_config_path: effectiveProjectConfigPath,
      });
      setResult(data);
      const responseErrors = Array.isArray(data?.errors) ? (data.errors as string[]) : [];
      if (data?.ok !== true) {
        setError(providerFailureMessage(provider, responseErrors));
        return;
      }
      const plan = data?.plan;
      const planIssues = reviewedPlanIssues(plan);
      if (planIssues.length > 0 || !isRecord(plan)) {
        setError(invalidReviewedPlanMessage(planIssues));
        return;
      }
      setPlanJson(JSON.stringify(plan, null, 2));
      await persistReviewedPlan(
        plan,
        (data?.validation ?? {}) as Record<string, unknown>,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleRevalidate() {
    setJsonError("");
    setReValidation(null);
    let plan: Record<string, unknown>;
    try {
      plan = JSON.parse(planJson);
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : String(e));
      return;
    }
    const planIssues = reviewedPlanIssues(plan);
    if (planIssues.length > 0) {
      setJsonError(invalidReviewedPlanMessage(planIssues));
      return;
    }
    setValidateLoading(true);
    try {
      const validated = (await validatePlan(baseUrl, plan)) as Record<string, unknown>;
      setReValidation(validated);
      await persistReviewedPlan(plan, validated);
    } catch (e) {
      setJsonError(e instanceof Error ? e.message : String(e));
    } finally {
      setValidateLoading(false);
    }
  }

  // ── Derived data ──
  const validation = (reValidation ?? result?.validation ?? {}) as Record<string, unknown>;
  const riskSummary = (validation?.risk_summary ?? {}) as Record<string, unknown>;
  const plan = (result?.plan ?? {}) as Record<string, unknown>;
  const nodes = (plan?.nodes ?? []) as Array<Record<string, unknown>>;
  const errors = (result?.errors ?? []) as string[];
  const warnings = (result?.warnings ?? []) as string[];
  const valErrors = (validation?.errors ?? []) as Array<Record<string, unknown>>;
  const valWarnings = (validation?.warnings ?? []) as Array<Record<string, unknown>>;
  const approvalNodes = (validation?.approval_required_nodes ?? []) as string[];
  const highRiskNodes = (validation?.high_risk_nodes ?? []) as string[];
  const unknownNodes = (validation?.unknown_nodes ?? []) as string[];
  const topoOrder = (validation?.topological_order ?? []) as string[];
  const reValidated = reValidation !== null;

  const selectedCatalog = selectedNodeId ? catalogMap[selectedNodeId] : null;

  // Compute summary chips
  const highRiskCount = highRiskNodes.length;
  const approvalCount = approvalNodes.length;
  const unknownMetaCount = nodes.filter((n) => {
    const id = String(n.id ?? "");
    return id && !catalogMap[id];
  }).length;
  const catalogCount = Object.keys(catalogMap).length;

  function riskBadge(level: string) {
    const colors: Record<string, string> = {
      high: "#c62828",
      medium: "#e65100",
      low: "#2e7d32",
      unknown: "#999",
    };
    return (
      <span style={{ color: colors[level] || "#999", fontWeight: 700, fontSize: 12 }}>
        {level.toUpperCase()}
      </span>
    );
  }

  function getNodeDependsOnText(nodeId: string): string {
    const node = nodes.find((item) => String(item.id) === nodeId) as
      | { depends_on?: string[] }
      | undefined;
    return node?.depends_on?.length ? node.depends_on.join(", ") : "—";
  }

  function buildReviewDraft(): Record<string, unknown> | null {
    if (!result) return null;
    // Use re-validation if available, otherwise planner's validation
    const v = (reValidation ?? result?.validation ?? {}) as Record<string, unknown>;
    return {
      schema_version: "review-draft-v1",
      review_status: "draft",
      execution_allowed: false,
      generated_at: new Date().toISOString(),
      goal,
      provider,
      plan: JSON.parse(planJson || "{}"),
      validation: {
        ok: v.ok,
        errors: v.errors,
        warnings: v.warnings,
        risk_summary: v.risk_summary,
        approval_required_nodes: v.approval_required_nodes,
        high_risk_nodes: v.high_risk_nodes,
        manual_required_nodes: v.manual_required_nodes,
        unknown_nodes: v.unknown_nodes,
        topological_order: v.topological_order,
      },
      risk_summary: v.risk_summary,
      review_summary: {
        nodes_total: nodes.length,
        approval_required_nodes: approvalNodes,
        high_risk_nodes: highRiskNodes,
        manual_required_nodes: (v.manual_required_nodes ?? []) as string[],
        unknown_nodes: unknownNodes,
      },
      catalog_summary: {
        tools_total: catalogCount,
        metadata_available: !catalogError,
      },
      planner: {
        ok: result?.ok,
        messages: result?.messages,
        errors: errors,
        warnings: warnings,
      },
      safety: {
        review_only: true,
        executes_pipeline: false,
        requires_approval_before_execution: true,
      },
    };
  }

  function handleExport() {
    const draft = buildReviewDraft();
    if (!draft) return;
    const json = JSON.stringify(draft, null, 2);
    const blob = new Blob([json], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const pipelineId = String(plan?.pipeline_id ?? "plan");
    const ts = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
    a.href = url;
    a.download = `medimage_plan_review_${pipelineId}_${ts}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleCopy() {
    const draft = buildReviewDraft();
    if (!draft) return;
    const json = JSON.stringify(draft, null, 2);
    try {
      await navigator.clipboard.writeText(json);
      setCopyStatus("Copied!");
    } catch {
      setCopyStatus("Clipboard unavailable");
    }
    setTimeout(() => setCopyStatus(""), 2000);
  }

  function handleApproveAllRequired() {
    setApprovalNodesInput(approvalNodes.join(", "));
  }

  async function handleCheckApproval() {
    setApprovalError("");
    setApprovalResult(null);
    // Parse current plan JSON
    let plan: Record<string, unknown>;
    try {
      plan = JSON.parse(planJson || "{}");
    } catch {
      setApprovalError("Cannot parse current plan JSON.");
      return;
    }
    if (!validation || !Object.keys(validation).length) {
      setApprovalError("Please generate or re-validate a plan first.");
      return;
    }
    const nodes = approvalNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const rejected = rejectedNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const baseApproval = approvalApproved
      ? {
          approved: true,
          approved_by: approvalBy || "reviewer",
          reason: approvalReason || undefined,
          approved_nodes: nodes,
          rejected_nodes: rejected,
          review_draft_schema_version: "review-draft-v1",
        }
      : { approved: false };
    const approval = { ...baseApproval, ...externalToolApprovalFields() };
    setApprovalLoading(true);
    try {
      const data = await checkApprovalGate(baseUrl, { plan, validation, approval });
      setApprovalResult(data as Record<string, unknown>);
    } catch (e) {
      setApprovalError(e instanceof Error ? e.message : String(e));
    } finally {
      setApprovalLoading(false);
    }
  }

  async function handleDryRunCheck() {
    setDryRunError("");
    setDryRunResult(null);
    if (projectContextError) {
      setDryRunError(projectContextError);
      return;
    }
    let plan: Record<string, unknown>;
    try {
      plan = JSON.parse(planJson || "{}");
    } catch {
      setDryRunError("Cannot parse current plan JSON.");
      return;
    }
    const nodes = approvalNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const rejected = rejectedNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const baseApproval = approvalApproved
      ? {
          approved: true,
          approved_by: approvalBy || "reviewer",
          reason: approvalReason || undefined,
          approved_nodes: nodes,
          rejected_nodes: rejected,
          review_draft_schema_version: "review-draft-v1",
        }
      : { approved: false };
    const approval = { ...baseApproval, ...externalToolApprovalFields() };
    setDryRunLoading(true);
    try {
      const data = await executeReviewedDryRun(baseUrl, {
        plan,
        approval,
        project_id: effectiveProjectId,
        reviewed_plan_id: reviewedPlanId ?? undefined,
        project_config_path: effectiveProjectConfigPath,
        persist_audit: persistAudit,
        actor: approvalBy || undefined,
      });
      setDryRunResult(data);
    } catch (e) {
      setDryRunError(e instanceof Error ? e.message : String(e));
    } finally {
      setDryRunLoading(false);
    }
  }

  async function handleExecute() {
    setExecutionError("");
    setExecutionResult(null);
    if (projectContextError) {
      setExecutionError(projectContextError);
      return;
    }
    let plan: Record<string, unknown>;
    try {
      plan = JSON.parse(planJson || "{}");
    } catch {
      setExecutionError("Cannot parse current plan JSON.");
      return;
    }
    if (!effectiveProjectConfigPath) {
      setExecutionError("Project config path is required.");
      return;
    }
    if (!explicitDemoMode && !reviewedPlanId) {
      setExecutionError("Save or re-validate this plan before executing it.");
      return;
    }
    const nodes = approvalNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const rejected = rejectedNodesInput
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);
    const baseApproval = approvalApproved
      ? {
          approved: true,
          approved_by: approvalBy || "reviewer",
          reason: approvalReason || undefined,
          approved_nodes: nodes,
          rejected_nodes: rejected,
          review_draft_schema_version: "review-draft-v1",
        }
      : { approved: false };
    const approval = { ...baseApproval, ...externalToolApprovalFields() };
    setExecutionLoading(true);
    try {
      const data = await executeReviewedPlan(baseUrl, {
        plan,
        approval,
        project_id: effectiveProjectId,
        reviewed_plan_id: reviewedPlanId ?? undefined,
        project_config_path: effectiveProjectConfigPath,
        actor: actorName.trim() || "frontend-user",
      });
      setExecutionResult(data);
    } catch (e) {
      setExecutionError(e instanceof Error ? e.message : String(e));
    } finally {
      setExecutionLoading(false);
    }
  }

  async function handleViewAudit(auditId: string) {
    setAuditFetchError("");
    setAuditDetail(null);
    setAuditLoading(true);
    try {
      const data = await fetchAuditRecord(baseUrl, auditId);
      setAuditDetail(((data as Record<string, unknown>).record as Record<string, unknown>) || null);
    } catch (e) {
      setAuditFetchError(e instanceof Error ? e.message : String(e));
    } finally {
      setAuditLoading(false);
    }
  }

  return (
    <div className={styles.style001}>
      <h2>Technical Plan Review</h2>

      {loadedPresetBanner ? <div className={styles.style002}>{loadedPresetBanner}</div> : null}

      <div className={styles.style003}>
        <div className={styles.style004}>Project Context</div>
        <label className={styles.style005}>
          <input
            type="checkbox"
            checked={explicitDemoMode}
            onChange={(event) => setExplicitDemoMode(event.target.checked)}
          />{" "}
          Use explicit example/demo project config
        </label>
        {explicitDemoMode ? (
          <label>
            Demo project config:{" "}
            <input
              type="text"
              value={demoProjectConfigPath}
              onChange={(event) => setDemoProjectConfigPath(event.target.value)}
              className={styles.demoConfigInput}
            />
          </label>
        ) : (
          <div className={styles.style006}>
            <div>
              <b>Project:</b>{" "}
              {selectedProject ? `${selectedProject.name} (${selectedProject.id})` : "Unavailable"}
            </div>
            <div>
              <b>Config:</b> {selectedProjectConfigPath || "Unavailable"}
            </div>
            <div>
              <b>Rawdata:</b> {rawdataDir || "Unavailable"}
            </div>
            <div>
              <b>Dataset index:</b> {datasetIndexPath || "Unavailable"}
            </div>
          </div>
        )}
        {projectContextError && <div className={styles.style007}>{projectContextError}</div>}
      </div>

      {!explicitDemoMode && selectedProjectId && (
        <div className={styles.style008}>
          <div className={styles.style009}>
            <strong>Recent Plans</strong>
            <button
              onClick={() => void refreshRecentPlans()}
              disabled={planHistoryLoading}
              className={styles.compactWhiteButton}
            >
              {planHistoryLoading ? "Loading..." : "Refresh"}
            </button>
            {reviewedPlanId && <span className={styles.style010}>Active: {reviewedPlanId}</span>}
            {planSaveStatus && <span className={styles.style011}>{planSaveStatus}</span>}
          </div>
          {planHistoryError && <div className={styles.style012}>{planHistoryError}</div>}
          {recentPlans.length === 0 && !planHistoryLoading ? (
            <div className={styles.style013}>No persisted reviewed plans for this project yet.</div>
          ) : (
            <div className={styles.style014}>
              {recentPlans.slice(0, 8).map((record) => (
                <div key={record.reviewed_plan_id} className={styles.style015}>
                  <button
                    onClick={() => restoreReviewedPlan(record)}
                    className={styles.restorePlanButton}
                  >
                    Restore
                  </button>
                  <span className={styles.style016}>{record.reviewed_plan_id}</span>
                  <span>Status: {record.status}</span>
                  <span>Execution: {record.execution_status}</span>
                  <span className={styles.style017}>{record.updated_at}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── Input ── */}
      <div className={styles.style018}>
        <label className={styles.style019}>Goal</label>
        <input
          type="text"
          value={goal}
          onChange={(e) => setGoal(e.target.value)}
          placeholder="e.g. 对 rs-fMRI 数据做 realign 和 motion QC"
          className={styles.goalInput}
          onKeyDown={(e) => e.key === "Enter" && handleGenerate()}
        />
      </div>

      <div className={styles.style020}>
        <label className={styles.style021}>Provider:</label>
        <select
          value={provider}
          onChange={(e) => setProvider(e.target.value)}
          className={styles.providerSelect}
        >
          <option value="mock">mock</option>
          <option value="rule_based">rule_based</option>
          <option value="openai_compatible">openai_compatible</option>
        </select>
        <button
          onClick={handleGenerate}
          disabled={loading || Boolean(projectContextError)}
          className={styles.style022}
        >
          {loading ? "Generating..." : "Generate Plan"}
        </button>
        {/* Summary chips */}
        {result && (
          <>
            <span style={chipStyle("#e3f2fd", "#1565c0")}>📋 {nodes.length} nodes</span>
            {catalogCount > 0 && (
              <span style={chipStyle("#e8f5e9", "#2e7d32")}>📦 {catalogCount} tools</span>
            )}
            {highRiskCount > 0 && (
              <span style={chipStyle("#ffebee", "#c62828")}>⚡ {highRiskCount} high risk</span>
            )}
            {approvalCount > 0 && (
              <span style={chipStyle("#fff3e0", "#e65100")}>🔒 {approvalCount} approval</span>
            )}
            {unknownMetaCount > 0 && (
              <span style={chipStyle("#f3e5f5", "#7b1fa2")}>
                ❓ {unknownMetaCount} unknown meta
              </span>
            )}
          </>
        )}
      </div>

      {catalogError && <div className={styles.style023}>⚠️ {catalogError}</div>}

      <div className={styles.providerStatus} role="status">
        {providerStatusMessage(provider)}
      </div>

      {error && <div className={styles.style024}>{error}</div>}

      {/* ── Plan JSON Editor ── */}
      {result && (
        <div className={styles.style025}>
          <div className={styles.style026}>
            <h4 className={styles.style027}>Candidate Plan JSON</h4>
            <button
              onClick={handleRevalidate}
              disabled={validateLoading}
              className={styles.style028}
            >
              {validateLoading ? "Validating..." : "Re-validate"}
            </button>
            <button onClick={handleExport} disabled={!result} className={styles.style029}>
              Export JSON
            </button>
            <button onClick={handleCopy} disabled={!result} className={styles.style030}>
              Copy JSON
            </button>
            {copyStatus && <span className={styles.style031}>{copyStatus}</span>}
            {reValidated && <span className={styles.style032}>(using re-validation result)</span>}
          </div>
          {jsonError && <div className={styles.style033}>JSON Parse Error: {jsonError}</div>}
          <textarea
            value={planJson}
            onChange={(e) => {
              setPlanJson(e.target.value);
              setReValidation(null);
              setReviewedPlanId(null);
              setPlanSaveStatus("Plan changed; re-validate to save this revision.");
              setJsonError("");
            }}
            rows={14}
            className={styles.planTextarea}
            spellCheck={false}
          />
        </div>
      )}

      {/* ── Approval Gate ── */}
      {result && (
        <div className={styles.style034}>
          <h4 className={styles.style035}>Approval Gate Check</h4>
          <div className={styles.style036}>
            <label>
              <input
                type="checkbox"
                checked={approvalApproved}
                onChange={(e) => setApprovalApproved(e.target.checked)}
              />{" "}
              Approved
            </label>
            <label>
              Approved by:{" "}
              <input
                type="text"
                value={approvalBy}
                onChange={(e) => setApprovalBy(e.target.value)}
                placeholder="reviewer"
                className={styles.approvalByInput}
              />
            </label>
            <label className={styles.style037}>
              Approved nodes (comma-separated, or *):
              <input
                type="text"
                value={approvalNodesInput}
                onChange={(e) => setApprovalNodesInput(e.target.value)}
                placeholder="spm_realign_subject, motion_qc_subject"
                className={styles.fullCompactInput}
              />
            </label>
            <label className={styles.style038}>
              Rejected nodes:
              <input
                type="text"
                value={rejectedNodesInput}
                onChange={(e) => setRejectedNodesInput(e.target.value)}
                placeholder="optional"
                className={styles.fullCompactInput}
              />
            </label>
          </div>
          <div className={styles.style039}>
            <button
              onClick={handleCheckApproval}
              disabled={approvalLoading}
              className={styles.style040}
            >
              {approvalLoading ? "Checking..." : "Check Approval Gate"}
            </button>
            <button onClick={handleApproveAllRequired} className={styles.style041}>
              Approve all required nodes
            </button>
          </div>
          {approvalError && <div className={styles.style042}>❌ {approvalError}</div>}
          {approvalResult && (
            <div
              style={{
                padding: 8,
                background: approvalResult.execution_allowed ? "#e8f5e9" : "#ffebee",
                borderRadius: 4,
                fontSize: 13,
              }}
            >
              <div className={styles.style043}>
                {approvalResult.execution_allowed
                  ? "✅ Execution allowed by approval gate"
                  : "🚫 Execution blocked by approval gate"}
              </div>
              <div>
                Approval required: <b>{String(approvalResult.approval_required)}</b>
              </div>
              <div>
                Approved: <b>{String(approvalResult.approved)}</b>
              </div>
              {((approvalResult.missing_approval_nodes as string[]) || []).length > 0 && (
                <div className={styles.style044}>
                  Missing: {(approvalResult.missing_approval_nodes as string[]).join(", ")}
                </div>
              )}
              {((approvalResult.rejected_nodes as string[]) || []).length > 0 && (
                <div className={styles.style045}>
                  Rejected: {(approvalResult.rejected_nodes as string[]).join(", ")}
                </div>
              )}
              {((approvalResult.errors as Array<Record<string, unknown>>) || []).map((e, i) => (
                <div key={`ae-${i}`} className={styles.style046}>
                  ❌ [{String(e.code)}] {String(e.message)}
                </div>
              ))}
              {((approvalResult.warnings as Array<Record<string, unknown>>) || []).map((w, i) => (
                <div key={`aw-${i}`} className={styles.style047}>
                  ⚠️ [{String(w.code)}] {String(w.message)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── External Tool Safety Acknowledgement ── */}
      {result && externalToolReq.required && (
        <div className={styles.style048}>
          <h4 className={styles.style049}>External Tool Safety Acknowledgement</h4>
          <p className={styles.style050}>
            This plan contains high-risk external-tool nodes: {externalToolReq.nodeIds.join(", ")}.
            These acknowledgements are required before future execution.
          </p>
          <div className={styles.style051}>
            <label>
              <input
                type="checkbox"
                checked={externalToolAcknowledgement}
                onChange={(e) => setExternalToolAcknowledgement(e.target.checked)}
              />{" "}
              I understand this may call external MATLAB/SPM/DPABI tools in future execution.
            </label>
            <label>
              <input
                type="checkbox"
                checked={rawdataReadOnlyConfirmed}
                onChange={(e) => setRawdataReadOnlyConfirmed(e.target.checked)}
              />{" "}
              I confirm rawdata must remain read-only.
            </label>
            <label>
              <input
                type="checkbox"
                checked={outputDirectoryConfirmed}
                onChange={(e) => setOutputDirectoryConfirmed(e.target.checked)}
              />{" "}
              I confirm outputs must be written only to approved project/derivatives directories.
            </label>
            <label>
              <input
                type="checkbox"
                checked={riskAcknowledgement}
                onChange={(e) => setRiskAcknowledgement(e.target.checked)}
              />{" "}
              I acknowledge the risk of external-tool execution and environment-dependent results.
            </label>
            <label>
              <input
                type="checkbox"
                checked={subjectScopeConfirmed}
                onChange={(e) => setSubjectScopeConfirmed(e.target.checked)}
              />{" "}
              I confirm the subject/session scope has been reviewed.
            </label>
            <label className={styles.style052}>
              <span>Overwrite policy:</span>
              <select
                value={overwritePolicy}
                onChange={(e) =>
                  setOverwritePolicy(
                    e.target.value as "fail_if_exists" | "require_explicit_overwrite_approval",
                  )
                }
                style={{
                  padding: "3px 6px",
                  borderRadius: 3,
                  border: "1px solid #ccc",
                  fontSize: 12,
                }}
              >
                <option value="fail_if_exists">fail_if_exists</option>
                <option value="require_explicit_overwrite_approval">
                  require_explicit_overwrite_approval
                </option>
              </select>
            </label>
          </div>
          {(!externalToolAcknowledgement ||
            !rawdataReadOnlyConfirmed ||
            !outputDirectoryConfirmed ||
            !riskAcknowledgement ||
            !subjectScopeConfirmed) && (
            <div className={styles.style053}>
              All checkboxes must be checked for the approval gate to pass.
            </div>
          )}
        </div>
      )}

      {/* ── Dry-run Execution Readiness ── */}
      {result && (
        <div className={styles.style054}>
          <h4 className={styles.style055}>Dry-run Execution Readiness</h4>
          <p className={styles.style056}>
            Backend re-runs Plan Validator + Approval Gate. No pipeline is executed.
          </p>
          <button
            onClick={handleDryRunCheck}
            disabled={
              dryRunLoading ||
              Boolean(projectContextError) ||
              (externalToolReq.required && !externalToolApprovalComplete)
            }
            title={
              externalToolReq.required && !externalToolApprovalComplete
                ? "Complete the External Tool Safety Acknowledgement before dry-run."
                : ""
            }
            className={styles.style057}
          >
            {dryRunLoading ? "Checking..." : "Dry-run Execution Check"}
          </button>
          <label className={styles.style058}>
            <input
              type="checkbox"
              checked={persistAudit}
              onChange={(e) => setPersistAudit(e.target.checked)}
            />{" "}
            Persist audit record
          </label>
          {dryRunError && <div className={styles.style059}>❌ {dryRunError}</div>}
          {dryRunResult && (
            <div
              className={styles.style060}
              style={cssVars({ "--severity-bg": severityBg(dryRunResult.status) })}
            >
              <ExecuteReviewedStatusCard status={dryRunResult.status} />
              <div className={styles.style061}>
                executor_called: {String(dryRunResult.execution?.executor_called ?? "false")}
                {" | "}submitted: {String(dryRunResult.execution?.submitted ?? "false")}
                {" | "}run_id: {String(dryRunResult.execution?.run_id ?? "null")}
              </div>
              {dryRunResult.status !== "DRY_RUN_OK" && (
                <div className={styles.style062}>
                  ⚠️ No pipeline was executed. This is a dry-run check only.
                </div>
              )}
              {dryRunResult.audit?.persisted ? (
                <div className={styles.style063}>
                  <div className={styles.style064}>
                    📝 Audit: {String(dryRunResult.audit.audit_id)} (
                    {String(dryRunResult.audit.event_type)})
                  </div>
                  <div className={styles.style065}>
                    Path: {String(dryRunResult.audit.audit_path)}
                  </div>
                  <button
                    onClick={() => handleViewAudit(String(dryRunResult.audit?.audit_id))}
                    disabled={auditLoading}
                    style={{
                      marginTop: 4,
                      padding: "3px 10px",
                      fontSize: 11,
                      background: "#e0e0e0",
                      border: "1px solid #ccc",
                      borderRadius: 3,
                      cursor: "pointer",
                    }}
                  >
                    {auditLoading ? "Loading..." : "View Audit Record"}
                  </button>
                  {auditFetchError && <div className={styles.style066}>❌ {auditFetchError}</div>}
                </div>
              ) : (
                <div className={styles.style067}>📝 Audit was not persisted for this dry-run.</div>
              )}
              {auditDetail && (
                <div className={styles.style068}>
                  <div>
                    <b>audit_id:</b> {String(auditDetail.audit_id)}
                  </div>
                  <div>
                    <b>created_at:</b> {String(auditDetail.created_at)}
                  </div>
                  <div>
                    <b>event_type:</b> {String(auditDetail.event_type)}
                  </div>
                  <div>
                    <b>plan_hash:</b> {String(auditDetail.plan_hash)}
                  </div>
                  <div>
                    <b>validation_hash:</b> {String(auditDetail.validation_hash)}
                  </div>
                  <div>
                    <b>approval_hash:</b> {String(auditDetail.approval_hash ?? "—")}
                  </div>
                  <div>
                    <b>actor:</b> {String(auditDetail.actor ?? "—")}
                  </div>
                  <div>
                    <b>source:</b> {String(auditDetail.source)}
                  </div>
                  <div>
                    <b>safety.review_only:</b>{" "}
                    {String(
                      (auditDetail.safety as Record<string, unknown> | null)?.review_only ?? "—",
                    )}
                  </div>
                  <div>
                    <b>safety.executes_pipeline:</b>{" "}
                    {String(
                      (auditDetail.safety as Record<string, unknown> | null)?.executes_pipeline ??
                        "—",
                    )}
                  </div>
                  <div>
                    <b>safety.rawdata_readonly:</b>{" "}
                    {String(
                      (auditDetail.safety as Record<string, unknown> | null)?.rawdata_readonly ??
                        "—",
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Reviewed Execution ── */}
      {result && (
        <div className={styles.style069}>
          <h4 className={styles.style070}>🚀 Reviewed Execution</h4>
          <p className={styles.style071}>
            Backend gated execution only. The backend will re-run validation, approval gate, adapter
            policy, pipeline writer, audit, and safe allowlist checks.
            <br />
            SPM / DPABI / GUI / GPU nodes remain blocked.
          </p>

          <div className={styles.style072}>
            <label className={styles.style073}>
              Project config:{" "}
              <input
                type="text"
                value={effectiveProjectConfigPath}
                readOnly
                className={styles.style074}
              />
            </label>
            <label className={styles.style075}>
              Actor:{" "}
              <input
                type="text"
                value={actorName}
                onChange={(e) => setActorName(e.target.value)}
                style={{
                  width: 120,
                  padding: "3px 6px",
                  borderRadius: 3,
                  border: "1px solid #ccc",
                  fontSize: 12,
                }}
              />
            </label>
          </div>

          <div className={styles.style076}>
            <label className={styles.style077}>
              <input
                type="checkbox"
                checked={confirmExecution}
                onChange={(e) => setConfirmExecution(e.target.checked)}
              />{" "}
              I understand this will request backend gated execution for the reviewed plan.
            </label>
          </div>

          {!effectiveProjectConfigPath && (
            <div className={styles.style078}>⚠️ Project config path is required.</div>
          )}

          {dryRunResult?.status !== "DRY_RUN_OK" && (
            <div className={styles.style079}>
              ⚠️ Run Dry-run Execution Check first — status is not DRY_RUN_OK.
            </div>
          )}

          <button
            onClick={handleExecute}
            disabled={
              executionLoading ||
              dryRunResult?.status !== "DRY_RUN_OK" ||
              !confirmExecution ||
              !effectiveProjectConfigPath ||
              (!explicitDemoMode && !reviewedPlanId) ||
              Boolean(projectContextError) ||
              (externalToolReq.required && !externalToolApprovalComplete)
            }
            title={
              externalToolReq.required && !externalToolApprovalComplete
                ? "Complete the External Tool Safety Acknowledgement before execute."
                : dryRunResult?.status !== "DRY_RUN_OK"
                  ? "Run Dry-run Execution Check first"
                  : !confirmExecution
                    ? "Check the confirmation box"
                    : !effectiveProjectConfigPath
                      ? "Enter a project config path"
                      : !explicitDemoMode && !reviewedPlanId
                        ? "Save or re-validate this plan before execution"
                        : projectContextError
                          ? projectContextError
                          : ""
            }
            style={{
              padding: "8px 20px",
              background:
                dryRunResult?.status === "DRY_RUN_OK" &&
                confirmExecution &&
                effectiveProjectConfigPath &&
                (explicitDemoMode || reviewedPlanId) &&
                !projectContextError
                  ? "#c62828"
                  : "#ccc",
              color:
                dryRunResult?.status === "DRY_RUN_OK" &&
                confirmExecution &&
                effectiveProjectConfigPath &&
                (explicitDemoMode || reviewedPlanId) &&
                !projectContextError
                  ? "#fff"
                  : "#888",
              border: "none",
              borderRadius: 4,
              cursor: "pointer",
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            {executionLoading ? "Requesting..." : "Execute Reviewed Plan"}
          </button>
          <span className={styles.style080}>
            (dry_run=false, confirm_execution=true, persist_audit=true, write_pipeline_yaml=true)
          </span>

          {executionError && <div className={styles.style081}>❌ {executionError}</div>}

          {executionResult && (
            <div
              className={styles.style082}
              style={cssVars({ "--severity-bg": severityBg(executionResult.status) })}
            >
              <ExecuteReviewedStatusCard status={executionResult.status} />
              <div className={styles.style083}>
                <div>
                  Reviewed plan: <b>{String(executionResult.reviewed_plan_id ?? "null")}</b>
                </div>
                <div>
                  Run link: <b>{String(executionResult.run_link_id ?? "null")}</b>
                </div>
                <div>
                  Pipeline path: <b>{String(executionResult.pipeline_path ?? "null")}</b>
                </div>
                <div>
                  Summary path: <b>{String(executionResult.summary_path ?? "null")}</b>
                </div>
              </div>
              <div className={styles.style084}>
                executor_called:{" "}
                <b>{String(executionResult.execution?.executor_called ?? "false")}</b>
                {" | "}submitted: <b>{String(executionResult.execution?.submitted ?? "false")}</b>
                {" | "}run_id: <b>{String(executionResult.execution?.run_id ?? "null")}</b>
              </div>
              {executionResult.audit?.audit_id ? (
                <div className={styles.style085}>
                  <span className={styles.style086}>
                    📝 Audit: {executionResult.audit.audit_id}
                  </span>
                </div>
              ) : null}
              {executionResult.pipeline_yaml &&
              typeof executionResult.pipeline_yaml === "object" &&
              "path" in executionResult.pipeline_yaml ? (
                <div className={styles.style087}>
                  <span>📄 Pipeline YAML: {String(executionResult.pipeline_yaml.path)}</span>
                </div>
              ) : null}
              {(executionResult.errors ?? []).length > 0 && (
                <div className={styles.style088}>
                  Errors: {JSON.stringify(executionResult.errors)}
                </div>
              )}
              {(executionResult.warnings ?? []).length > 0 && (
                <div className={styles.style089}>
                  Warnings: {JSON.stringify(executionResult.warnings)}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ── Result ── */}
      {result && (
        <div className={styles.style090}>
          {/* Left: plan table + validation */}
          <div className={styles.style091}>
            {/* Status */}
            <div
              style={{
                padding: 12,
                borderRadius: 4,
                marginBottom: 12,
                fontSize: 14,
                background: result.ok ? "#e8f5e9" : "#fff3e0",
                color: result.ok ? "#2e7d32" : "#e65100",
              }}
            >
              <strong>
                {result.ok
                  ? "Plan generated and validated"
                  : "Plan generation did not produce a valid reviewed plan"}
              </strong>
              {result.provider && <span> — provider: {String(result.provider)}</span>}
            </div>

            {(errors.length > 0 || warnings.length > 0) && (
              <div className={styles.style092}>
                {errors.map((e, i) => (
                  <div key={`e-${i}`} className={styles.style093}>
                    ❌ {e}
                  </div>
                ))}
                {warnings.map((w, i) => (
                  <div key={`w-${i}`} className={styles.style094}>
                    ⚠️ {w}
                  </div>
                ))}
              </div>
            )}

            {/* Risk Summary */}
            <div className={styles.style095}>
              <h4 className={styles.style096}>
                Risk Summary{reValidated ? " (re-validated)" : ""}
              </h4>
              <div className={styles.style097}>
                <span>
                  Total nodes: <b>{String(riskSummary.nodes_total ?? "?")}</b>
                </span>
                <span>
                  Requires approval:{" "}
                  <b style={{ color: riskSummary.requires_approval ? "#c62828" : "#2e7d32" }}>
                    {String(riskSummary.requires_approval ?? "?")}
                  </b>
                </span>
                <span>
                  Approval count: <b>{String(riskSummary.approval_required_count ?? "?")}</b>
                </span>
                <span>
                  High risk:{" "}
                  <b
                    style={{
                      color: (Number(riskSummary.high_risk_count) || 0) > 0 ? "#c62828" : "#333",
                    }}
                  >
                    {String(riskSummary.high_risk_count ?? "?")}
                  </b>
                </span>
                <span>
                  Manual required: <b>{String(riskSummary.manual_required ?? "?")}</b>
                </span>
                <span>
                  Unknown nodes: <b>{String(riskSummary.unknown_nodes_count ?? "?")}</b>
                </span>
              </div>
              <div className={styles.style098}>
                <div>
                  🔴 <b>High risk</b> — requires careful manual review before execution
                </div>
                <div>
                  🟠 <b>Requires approval</b> — must pass approval gate before pipeline runs
                </div>
                <div>
                  🟣 <b>Uncataloged</b> — metadata not yet complete; treat as unknown risk
                </div>
              </div>
            </div>

            {/* Validation */}
            <div className={styles.style099}>
              <h4 className={styles.style100}>Validation{reValidated ? " (re-validated)" : ""}</h4>
              {valErrors.length > 0 &&
                valErrors.map((e, i) => (
                  <div key={`ve-${i}`} className={styles.style101}>
                    ❌ [{String(e.code ?? "?")}] {String(e.message ?? "")}
                  </div>
                ))}
              {valWarnings.length > 0 &&
                valWarnings.map((w, i) => (
                  <div key={`vw-${i}`} className={styles.style102}>
                    ⚠️ [{String(w.code ?? "?")}] {String(w.message ?? "")}
                  </div>
                ))}
              {approvalNodes.length > 0 && (
                <div className={styles.style103}>
                  🔒 Approval required: {approvalNodes.join(", ")}
                </div>
              )}
              {highRiskNodes.length > 0 && (
                <div className={styles.style104}>⚡ High risk: {highRiskNodes.join(", ")}</div>
              )}
              {unknownNodes.length > 0 && (
                <div className={styles.style105}>❓ Unknown: {unknownNodes.join(", ")}</div>
              )}
              {topoOrder.length > 0 && (
                <div className={styles.style106}>→ {topoOrder.join(" → ")}</div>
              )}
            </div>

            {/* Nodes table */}
            <h4 className={styles.style107}>
              Candidate Plan: {String(plan.pipeline_id ?? "?")} ({nodes.length} nodes)
            </h4>
            <table className={styles.style108}>
              <thead>
                <tr className={styles.style109}>
                  <th className={styles.style110}>#</th>
                  <th className={styles.style111}>Node ID</th>
                  <th className={styles.style112}>Name</th>
                  <th className={styles.style113}>Risk</th>
                  <th className={styles.style114}>Appr</th>
                  <th className={styles.style115}>Tags</th>
                </tr>
              </thead>
              <tbody>
                {nodes.map((node, i) => {
                  const nid = String(node.id ?? "");
                  const cat = catalogMap[nid];
                  const sel = nid === selectedNodeId;
                  return (
                    <tr
                      key={i}
                      onClick={() => setSelectedNodeId(sel ? null : nid)}
                      style={{
                        cursor: "pointer",
                        background: sel
                          ? "#e3f2fd"
                          : cat?.risk_level === "high"
                            ? "#fff5f5"
                            : "transparent",
                        borderBottom: "1px solid #eee",
                      }}
                    >
                      <td className={styles.style116}>{i + 1}</td>
                      <td className={styles.style117}>{nid}</td>
                      <td
                        style={{
                          padding: "3px 6px",
                          border: "1px solid #ddd",
                          color: cat ? "#333" : "#999",
                          fontStyle: cat ? "normal" : "italic",
                        }}
                      >
                        {cat?.name ?? <span title="Not in Tool Catalog">Unknown metadata ⚠️</span>}
                      </td>
                      <td className={styles.style118}>{cat ? riskBadge(cat.risk_level) : "—"}</td>
                      <td className={styles.style119}>{cat?.requires_approval ? "🔒" : "—"}</td>
                      <td className={styles.style120}>
                        {(cat?.tags ?? []).slice(0, 3).join(", ") || "—"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>

            {/* Depends-on detail row for selected */}
            {selectedNodeId && (
              <div className={styles.style121}>
                Depends on: {getNodeDependsOnText(selectedNodeId)}
              </div>
            )}
          </div>

          {/* Right: node detail panel */}
          <div className={styles.style122}>
            {selectedNodeId && (
              <div className={styles.style123}>
                <h4 className={styles.style124}>Node Detail</h4>
                {selectedCatalog ? (
                  <>
                    <div className={styles.style125}>
                      <b>ID:</b> {selectedCatalog.id}
                    </div>
                    <div className={styles.style126}>
                      <b>Name:</b> {selectedCatalog.name}
                    </div>
                    <div className={styles.style127}>
                      <b>Description:</b> {selectedCatalog.description || "—"}
                    </div>
                    <div className={styles.style128}>
                      <b>Backend:</b> {selectedCatalog.backend}
                    </div>
                    <div className={styles.style129}>
                      <b>Parallel:</b> {selectedCatalog.parallel_level}
                    </div>
                    <div className={styles.style130}>
                      <b>Risk:</b> {riskBadge(selectedCatalog.risk_level)}
                    </div>
                    <div className={styles.style131}>
                      <b>Approval:</b>{" "}
                      {selectedCatalog.requires_approval ? "🔒 Required" : "✅ Not required"}
                    </div>
                    <div className={styles.style132}>
                      <b>Manual:</b> {selectedCatalog.manual_required ? "👤 Required" : "—"}
                    </div>
                    <div className={styles.style133}>
                      <b>Inputs:</b> {selectedCatalog.inputs.join(", ") || "—"}
                    </div>
                    <div className={styles.style134}>
                      <b>Outputs:</b> {selectedCatalog.outputs.join(", ") || "—"}
                    </div>
                    <div>
                      <b>Tags:</b> {selectedCatalog.tags.join(", ") || "—"}
                    </div>
                  </>
                ) : (
                  <div className={styles.style135}>
                    ⚠️ Unknown node — not found in Tool Catalog.
                    <br />
                    This node cannot be validated and should not be executed.
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Execute-Reviewed Status Helpers ─────────────────────────────────────────

function severityBg(status: string | undefined): string {
  const view = describeExecuteReviewedStatus(status);
  switch (view.severity) {
    case "success":
      return "#e8f5e9";
    case "info":
      return "#e3f2fd";
    case "warning":
      return "#fff3e0";
    case "error":
      return "#ffebee";
    default:
      return "#f5f5f5";
  }
}

function severityColor(severity: ExecuteReviewedSeverity): string {
  switch (severity) {
    case "success":
      return "#2e7d32";
    case "info":
      return "#1565c0";
    case "warning":
      return "#e65100";
    case "error":
      return "#c62828";
    default:
      return "#555";
  }
}

function severityEmoji(severity: ExecuteReviewedSeverity): string {
  switch (severity) {
    case "success":
      return "✅";
    case "info":
      return "ℹ️";
    case "warning":
      return "🟠";
    case "error":
      return "🔴";
    default:
      return "ℹ️";
  }
}

/** Compact status card for dry-run and execution results. */
function ExecuteReviewedStatusCard({ status }: { status: string | undefined }) {
  const view = describeExecuteReviewedStatus(status);
  return (
    <div className={styles.style136}>
      <div
        className={styles.style137}
        style={cssVars({ "--severity-color": severityColor(view.severity) })}
      >
        {severityEmoji(view.severity)} {view.title}
      </div>
      <div className={styles.style138}>{view.explanation}</div>
      {view.nextAction && (
        <div
          className={styles.style139}
          style={cssVars({ "--severity-color": severityColor(view.severity) })}
        >
          Next: {view.nextAction}
        </div>
      )}
      {view.safetyNote && <div className={styles.style140}>ⓘ {view.safetyNote}</div>}
    </div>
  );
}

function chipStyle(bg: string, color: string): React.CSSProperties {
  return {
    padding: "3px 10px",
    background: bg,
    color,
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 600,
  };
}
