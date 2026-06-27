import { useEffect, useMemo, useState, type ReactNode } from "react";

import PlanReviewConsole from "../../components/PlanReviewConsole";
import { TechnicalModuleSection } from "../../components/domain/TechnicalModuleSection";
import { Badge, Button, Card, EmptyState } from "../../components/ui";
import { evidenceLabel } from "../../lib/evidence";
import type { ProjectDetail } from "../../lib/types/project";
import type { PlanNodeSelection } from "../../lib/workspaceSelection";
import type { PresetPlanDraft } from "../../types";
import { WorkspaceHeader } from "../dashboard/DashboardChrome";
import styles from "./PlanWorkspace.module.css";
import layoutStyles from "./WorkspaceLayout.module.css";

export interface PlanWorkspaceProps {
  baseUrl: string;
  projectId: string | null;
  selectedProject: ProjectDetail | null;
  projectConfigPath?: string;
  datasetIndexPath?: string | null;
  rawdataDir?: string;
  projectDir?: string | null;
  initialPresetDraft?: PresetPlanDraft | null;
  onSelectedNodeChange?: (node: PlanNodeSelection | null) => void;
  onOpenDataConversion: () => void;
  onOpenEnvironment: () => void;
}

type PlanStatus = "needs-project" | "needs-config" | "draft" | "needs-review" | "validated";
type StepState = "current" | "completed" | "available" | "attention" | "pending-evidence" | "locked";

type NormalizedPlanNode = {
  backend: string;
  id: string;
  name: string;
  detail: string;
  dependsOn: string;
  inputs: string[];
  outputs: string[];
  parameters: Array<{ key: string; value: string }>;
  riskReason: string;
  risk: "high" | "approval" | "unknown" | "normal";
};

type ReviewStep = {
  description: string;
  label: string;
  state: StepState;
};

export function PlanWorkspace({
  projectId,
  selectedProject,
  projectConfigPath,
  datasetIndexPath,
  rawdataDir,
  initialPresetDraft,
  onSelectedNodeChange,
  onOpenDataConversion,
  onOpenEnvironment,
}: PlanWorkspaceProps) {
  const [showTechnicalPlanTools, setShowTechnicalPlanTools] = useState(false);
  const plan = initialPresetDraft?.plan ?? null;
  const validation = initialPresetDraft?.validation ?? {};
  const nodes = useMemo(() => normalizePlanNodes(plan, validation), [plan, validation]);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(nodes[0]?.id ?? null);
  const status = derivePlanStatus(projectId, selectedProject, projectConfigPath, initialPresetDraft);
  const summary = summarizePlan(status, initialPresetDraft, nodes.length, validation);
  const hasProjectContext = Boolean(projectId && selectedProject);
  const validationIssues = countValidationIssues(validation);
  const nextActions = initialPresetDraft?.next_actions ?? [];
  const reviewSteps = planReviewSteps(status, validation);
  const gateEvidence = summarizeGateEvidence(validation);
  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? nodes[0] ?? null;

  useEffect(() => {
    setSelectedNodeId((current) => {
      if (current && nodes.some((node) => node.id === current)) return current;
      return nodes[0]?.id ?? null;
    });
  }, [nodes]);

  useEffect(() => {
    onSelectedNodeChange?.(
      selectedNode
        ? {
            backend: selectedNode.backend,
            detail: selectedNode.detail,
            id: selectedNode.id,
            name: selectedNode.name,
            risk: riskLabel(selectedNode.risk),
          }
        : null,
    );
  }, [onSelectedNodeChange, selectedNode]);

  return (
    <div className={layoutStyles.stack}>
      <WorkspaceHeader
        title="Plan"
        subtitle="Review the planned workflow before dry-run, approval, or deterministic execution."
        status={summary.badge}
      />

      {!hasProjectContext ? (
        <EmptyState
          title="Select a project before planning"
          description="Plan review is project-scoped so input paths, data state, and audit records stay attached to the selected research workspace."
          action={<Button onClick={onOpenDataConversion}>Open Data &amp; Conversion</Button>}
        />
      ) : !projectConfigPath ? (
        <EmptyState
          title="Project config required"
          description="The selected project is missing metadata.project_config_path. Review the environment and project registration before generating a plan."
          action={<Button onClick={onOpenEnvironment}>Open Settings / Environment</Button>}
        />
      ) : null}

      <section className={styles.planGrid} aria-label="Plan workspace overview">
        <Card className={styles.outlineCard} tone="muted">
          <div className={styles.cardHeader}>
            <div>
              <h3>Plan outline</h3>
              <p>Plain-language review before opening the technical console.</p>
            </div>
            <Badge tone={summary.tone}>{summary.badge}</Badge>
          </div>
          <dl className={styles.outlineList}>
            <div>
              <dt>Goal</dt>
              <dd>{initialPresetDraft?.goal || "No draft goal loaded yet"}</dd>
            </div>
            <div>
              <dt>Data scope</dt>
              <dd>
                {selectedProject
                  ? `${selectedProject.name} · ${selectedProject.subjects_count} subject(s)`
                  : "Select project"}
              </dd>
            </div>
            <div>
              <dt>Nodes</dt>
              <dd>{nodes.length ? `${nodes.length} planned node(s)` : "No node list available"}</dd>
            </div>
            <div>
              <dt>Validation</dt>
              <dd>{summary.validationText}</dd>
            </div>
          </dl>
          {nextActions.length ? (
            <div className={styles.nextActions} aria-label="Plan next actions">
              <strong>Next actions</strong>
              <ul>
                {nextActions.slice(0, 4).map((action) => (
                  <li key={action}>{action}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </Card>

        <Card className={styles.graphCard}>
          <div className={styles.cardHeader}>
            <div>
              <h3>Pipeline graph</h3>
              <p>Ordered node cards with review focus and risk markers.</p>
            </div>
          </div>
          {nodes.length ? (
            <ol className={styles.nodeList} aria-label="Plan pipeline steps">
              {nodes.map((node, index) => (
                <li
                  className={styles.nodeItem}
                  data-risk={node.risk}
                  data-selected={node.id === selectedNode?.id ? "true" : "false"}
                  key={`${node.id}-${index}`}
                >
                  <button
                    type="button"
                    className={styles.nodeSelectButton}
                    onClick={() => setSelectedNodeId(node.id)}
                    aria-label={`Inspect ${node.name}`}
                  >
                    <span className={styles.nodeIndex}>{index + 1}</span>
                  </button>
                  <div className={styles.nodeBody}>
                    <div className={styles.nodeTitleRow}>
                      <strong>{node.name}</strong>
                      <Badge tone={riskTone(node.risk)} size="sm">
                        {riskLabel(node.risk)}
                      </Badge>
                    </div>
                    <p>{node.detail}</p>
                    <div className={styles.nodeMetaRow}>
                      <span>Depends on: {node.dependsOn}</span>
                      <span>Backend: {node.backend}</span>
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          ) : (
            <EmptyState
              title="No plan draft loaded"
              description="Generate or load a reviewed draft in the technical plan tools. The plan will remain review-only until backend validation and approval gates pass."
              action={
                <Button variant="secondary" onClick={() => setShowTechnicalPlanTools(true)}>
                  Open technical plan tools
                </Button>
              }
            />
          )}
        </Card>

        <Card className={styles.inspectorCard} aria-label="Plan inspector">
          <div className={styles.cardHeader}>
            <div>
              <h3>Inspector</h3>
              <p>Inputs, parameters, risk, and outputs for the selected node.</p>
            </div>
          </div>
          <NodeInspector node={selectedNode} />
          <div className={styles.machineHeader}>
            <strong>Plan state machine</strong>
            <span>Backend gates remain authoritative.</span>
          </div>
          <ol className={styles.stateList} aria-label="Plan state machine">
            {reviewSteps.map((step) => (
              <li
                aria-label={`${step.label}: ${stepLabel(step.state)}`}
                className={styles.stateItem}
                data-state={step.state}
                key={step.label}
              >
                <span>
                  <strong>{step.label}</strong>
                  <small>{step.description}</small>
                </span>
                <Badge tone={stepTone(step.state)} size="sm">
                  {stepLabel(step.state)}
                </Badge>
              </li>
            ))}
          </ol>
          <div className={styles.reviewFacts} aria-label="Plan review facts">
            <div>
              <span>Validation issues</span>
              <strong>{validationIssues}</strong>
            </div>
            <div>
              <span>Project config</span>
              <strong>{projectConfigPath ? "Registered" : "Missing"}</strong>
            </div>
            <div>
              <span>Execution</span>
              <strong>Backend gated</strong>
            </div>
            <div>
              <span>Approval evidence</span>
              <strong>{gateEvidence.approval}</strong>
            </div>
            <div>
              <span>Dry-run evidence</span>
              <strong>{gateEvidence.dryRun}</strong>
            </div>
            <div>
              <span>Ready evidence</span>
              <strong>{gateEvidence.ready}</strong>
            </div>
          </div>
        </Card>
      </section>

      <section className={styles.reviewBar} aria-label="Plan review bar">
        <div>
          <strong>{summary.title}</strong>
          <p>{summary.description}</p>
        </div>
        <div className={styles.reviewBarActions}>
          <Button variant="ghost" onClick={onOpenEnvironment}>
            Review environment
          </Button>
          <Button variant="primary" onClick={() => setShowTechnicalPlanTools((value) => !value)}>
            {showTechnicalPlanTools ? "Hide technical plan tools" : "Open technical plan tools"}
          </Button>
        </div>
      </section>

      <TechnicalModuleSection
        ariaLabel="Technical plan tools"
        bodyVisible={showTechnicalPlanTools}
        className={styles.advancedSection}
        description="JSON editing, approval checks, dry-run checks, and reviewed execution remain secondary to the review workspace."
        evidenceLevel="backend_required"
        helperText={
          showTechnicalPlanTools
            ? "Technical tools are open for review."
            : "Use the review bar to open the technical console when needed."
        }
        safetyNote="Plan tools stay review-only until backend validation, approval, and dry-run gates pass."
        status={showTechnicalPlanTools ? "Open" : "On demand"}
        statusTone="info"
        title="Technical plan tools"
      >
        <>
          <PlanReviewConsole
            selectedProjectId={projectId}
            selectedProject={selectedProject}
            projectConfigPath={projectConfigPath}
            datasetIndexPath={datasetIndexPath}
            rawdataDir={rawdataDir}
            initialPresetDraft={initialPresetDraft}
          />
        </>
      </TechnicalModuleSection>
    </div>
  );
}

function derivePlanStatus(
  projectId: string | null,
  selectedProject: ProjectDetail | null,
  projectConfigPath: string | undefined,
  draft: PresetPlanDraft | null | undefined,
): PlanStatus {
  if (!projectId || !selectedProject) return "needs-project";
  if (!projectConfigPath) return "needs-config";
  if (!draft?.plan) return "draft";
  if (draft.validation?.ok === true) return "validated";
  return "needs-review";
}

function summarizePlan(
  status: PlanStatus,
  draft: PresetPlanDraft | null | undefined,
  nodeCount: number,
  validation: Record<string, unknown>,
): {
  badge: string;
  description: string;
  title: string;
  tone: "neutral" | "info" | "success" | "warning" | "danger";
  validationText: string;
} {
  const issueCount = countValidationIssues(validation);
  const validationText =
    draft?.validation?.ok === true
      ? issueCount
        ? `${issueCount} issue(s) to review`
        : "Validation metadata present"
      : draft
        ? "Review required"
        : "No validation yet";

  if (status === "needs-project") {
    return {
      badge: "Needs project",
      description: "Planning is waiting for an active project context.",
      title: "Project context required",
      tone: "warning",
      validationText,
    };
  }
  if (status === "needs-config") {
    return {
      badge: "Needs config",
      description: "Project metadata is missing the config path used by reviewed planning.",
      title: "Project config is missing",
      tone: "warning",
      validationText,
    };
  }
  if (status === "validated") {
    return {
      badge: "Validated draft",
      description: `${nodeCount} node(s) are ready for human review before approval or dry-run.`,
      title: "Draft is ready for review",
      tone: "success",
      validationText,
    };
  }
  if (status === "needs-review") {
    return {
      badge: "Needs review",
      description: "A draft exists, but review issues or missing validation metadata need attention.",
      title: "Review the draft before approval",
      tone: "info",
      validationText,
    };
  }
  return {
    badge: "Draft",
    description: "Generate or load a draft in the technical plan tools; execution remains locked.",
    title: "Draft has not been generated",
    tone: "neutral",
    validationText,
  };
}

function normalizePlanNodes(
  plan: Record<string, unknown> | null,
  validation: Record<string, unknown>,
): NormalizedPlanNode[] {
  const rawNodes = Array.isArray(plan?.nodes) ? plan.nodes : [];
  const highRiskNodes = stringSet(validation.high_risk_nodes);
  const approvalNodes = stringSet(validation.approval_required_nodes);
  const unknownNodes = stringSet(validation.unknown_nodes);

  return rawNodes.map((rawNode, index) => {
    const node = isRecord(rawNode) ? rawNode : {};
    const id = String(node.id ?? node.node_id ?? `node-${index + 1}`);
    const name = String(node.name ?? node.label ?? id);
    const detail = String(node.description ?? node.type ?? node.operation ?? "Pipeline node");
    const backend = String(node.backend ?? node.runner ?? node.type ?? "registered runner");
    const dependsOn = Array.isArray(node.depends_on)
      ? node.depends_on.map(String).join(", ") || "None"
      : "None";
    const inputs = stringArray(node.inputs);
    const outputs = stringArray(node.outputs);
    const parameters = normalizeParameters(node.params ?? node.parameters);
    const risk = highRiskNodes.has(id)
      ? "high"
      : approvalNodes.has(id)
        ? "approval"
        : unknownNodes.has(id)
          ? "unknown"
          : "normal";
    const riskReason =
      risk === "high"
        ? "High-risk or approval-sensitive node flagged by backend validation."
        : risk === "approval"
          ? "Human approval is required before this node can execute."
          : risk === "unknown"
            ? "Node is not fully recognized by the current validation result."
            : "Cataloged node with no special risk marker in the current draft.";

    return { backend, id, inputs, name, outputs, parameters, detail, dependsOn, riskReason, risk };
  });
}

function planReviewSteps(status: PlanStatus, validation: Record<string, unknown>): ReviewStep[] {
  const hasContext = status !== "needs-project" && status !== "needs-config";
  const hasDraft = status === "validated" || status === "needs-review";
  const issueCount = countValidationIssues(validation);
  const validationOk = validation.ok === true;
  const approved = approvalEvidenceSignal(validation);
  const dryRunPassed = booleanSignal(validation, ["dry_run_passed", "dry_run_ok", "dry_run_completed"]);
  const readyToExecute = booleanSignal(validation, ["ready_to_execute", "execution_ready"]);
  const executed = booleanSignal(validation, ["executed", "execution_succeeded"]);

  return [
    {
      label: "Draft",
      description: hasDraft ? "Draft loaded" : "Generate or load draft",
      state: hasContext ? (hasDraft ? "completed" : "current") : "locked",
    },
    {
      label: "Validated",
      description: validationOk ? "Validator passed" : "Validator pending",
      state: validationOk ? "completed" : hasDraft ? "attention" : "locked",
    },
    {
      label: "Needs Review",
      description: issueCount ? `${issueCount} issue(s)` : "Human review required",
      state: hasDraft && !approved ? "current" : approved ? "completed" : "locked",
    },
    {
      label: "Approved",
      description: approved ? "Approval gate passed" : "Awaiting approval gate",
      state: approved ? "completed" : hasDraft ? "pending-evidence" : "locked",
    },
    {
      label: "Dry-run Passed",
      description: dryRunPassed
        ? "Backend dry-run evidence present"
        : approved
          ? "Pending backend dry-run evidence"
          : "Dry-run not passed",
      state: dryRunPassed ? "completed" : approved ? "pending-evidence" : "locked",
    },
    {
      label: "Ready to Execute",
      description: readyToExecute
        ? "Backend readiness evidence present"
        : dryRunPassed
          ? "Pending backend readiness evidence"
          : "Execution locked",
      state: readyToExecute ? "completed" : dryRunPassed ? "pending-evidence" : "locked",
    },
    {
      label: "Executed",
      description: executed
        ? "Persisted execution record present"
        : readyToExecute
          ? "Pending persisted execution record"
          : "No execution recorded",
      state: executed ? "completed" : readyToExecute ? "pending-evidence" : "locked",
    },
  ];
}

function summarizeGateEvidence(validation: Record<string, unknown>): {
  approval: string;
  dryRun: string;
  ready: string;
} {
  return {
    approval: approvalEvidenceSignal(validation) ? "Created" : evidenceLabel("backend_required"),
    dryRun: booleanSignal(validation, ["dry_run_passed", "dry_run_ok", "dry_run_completed"])
      ? "Created"
      : evidenceLabel("backend_required"),
    ready: booleanSignal(validation, ["ready_to_execute", "execution_ready"])
      ? "Created"
      : evidenceLabel("backend_required"),
  };
}

function countValidationIssues(validation: Record<string, unknown>): number {
  return arrayCount(validation.errors) + arrayCount(validation.warnings);
}

function arrayCount(value: unknown): number {
  return Array.isArray(value) ? value.length : 0;
}

function stringSet(value: unknown): Set<string> {
  return new Set(Array.isArray(value) ? value.map(String) : []);
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value) ? value.map(String).filter(Boolean) : [];
}

function normalizeParameters(value: unknown): Array<{ key: string; value: string }> {
  if (!value || typeof value !== "object" || Array.isArray(value)) return [];
  return Object.entries(value as Record<string, unknown>)
    .slice(0, 8)
    .map(([key, entry]) => ({ key, value: stringifyValue(entry) }));
}

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined || value === "") return "not set";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  try {
    return JSON.stringify(value);
  } catch {
    return "complex value";
  }
}

function approvalEvidenceSignal(record: Record<string, unknown>): boolean {
  return booleanSignal(record, ["approved", "approval_passed", "approval_gate_passed", "approval_result"]);
}

function booleanSignal(record: Record<string, unknown>, keys: string[]): boolean {
  for (const key of keys) {
    const value = record[key];
    if (value === true) return true;
    if (value && typeof value === "object" && !Array.isArray(value)) {
      const nested = value as Record<string, unknown>;
      if (
        nested.approved === true ||
        nested.ok === true ||
        nested.passed === true ||
        nested.execution_allowed === true
      ) {
        return true;
      }
    }
  }
  return false;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value && typeof value === "object" && !Array.isArray(value));
}

function riskLabel(risk: NormalizedPlanNode["risk"]): string {
  if (risk === "high") return "High risk";
  if (risk === "approval") return "Approval";
  if (risk === "unknown") return "Unknown";
  return "Cataloged";
}

function riskTone(
  risk: NormalizedPlanNode["risk"],
): "neutral" | "info" | "success" | "warning" | "danger" {
  if (risk === "high") return "danger";
  if (risk === "approval") return "warning";
  if (risk === "unknown") return "info";
  return "success";
}

function stepTone(state: StepState): "neutral" | "info" | "success" | "warning" {
  if (state === "completed") return "success";
  if (state === "current") return "info";
  if (state === "attention" || state === "pending-evidence" || state === "locked") return "warning";
  return "neutral";
}

function stepLabel(state: StepState): string {
  if (state === "pending-evidence") return evidenceLabel("backend_required").toLowerCase();
  return state;
}

function NodeInspector({ node }: { node: NormalizedPlanNode | null }) {
  if (!node) {
    return (
      <EmptyState
        title="No node selected"
        description="Load a draft to inspect node inputs, parameters, risk, and outputs."
      />
    );
  }

  return (
    <div className={styles.nodeInspector}>
      <div className={styles.inspectorTitle}>
        <strong>{node.name}</strong>
        <Badge tone={riskTone(node.risk)} size="sm">
          {riskLabel(node.risk)}
        </Badge>
      </div>
      <p>{node.detail}</p>
      <InspectorSection title="Inputs" emptyText="Inputs are inferred during backend validation.">
        {node.inputs.map((input) => (
          <li key={input}>{input}</li>
        ))}
      </InspectorSection>
      <InspectorSection title="Parameters" emptyText="No high-level parameters were provided.">
        {node.parameters.map((parameter) => (
          <li key={parameter.key}>
            <strong>{parameter.key}</strong>
            <span>{parameter.value}</span>
          </li>
        ))}
      </InspectorSection>
      <InspectorSection title="Risk" emptyText="">
        <li>{node.riskReason}</li>
      </InspectorSection>
      <InspectorSection title="Outputs" emptyText="Outputs are planned by the registered runner.">
        {node.outputs.map((output) => (
          <li key={output}>{output}</li>
        ))}
      </InspectorSection>
    </div>
  );
}

function InspectorSection({
  children,
  emptyText,
  title,
}: {
  children: ReactNode;
  emptyText: string;
  title: string;
}) {
  const items = Array.isArray(children) ? children.filter(Boolean) : children ? [children] : [];
  return (
    <section className={styles.inspectorSection}>
      <h4>{title}</h4>
      {items.length ? <ul>{items}</ul> : <p>{emptyText}</p>}
    </section>
  );
}
