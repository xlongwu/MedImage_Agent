/**
 * Pure helper for detecting high-risk external-tool nodes in a plan.
 */

export type ExternalToolApprovalRequirement = {
  required: boolean;
  nodeIds: string[];
  backendIds: string[];
  reasons: string[];
};

export type NativePreprocApprovalRequirement = {
  required: boolean;
  nodeIds: string[];
};

const HIGH_RISK_BACKENDS = new Set(["matlab-spm", "dpabi", "matlab-dpabi", "matlab"]);
const HIGH_RISK_PREFIXES = new Set(["spm_", "dpabi_"]);

export function detectExternalToolNodes(
  plan: Record<string, unknown> | null | undefined,
): ExternalToolApprovalRequirement {
  if (!plan) {
    return { required: false, nodeIds: [], backendIds: [], reasons: [] };
  }

  const nodes = (plan.nodes ?? []) as Array<Record<string, unknown>>;
  if (!Array.isArray(nodes) || nodes.length === 0) {
    return { required: false, nodeIds: [], backendIds: [], reasons: [] };
  }

  const nodeIds: string[] = [];
  const backendIds: string[] = [];
  const reasons: string[] = [];

  for (const node of nodes) {
    const id = String(node.id ?? "");
    const backend = String(node.backend ?? "").toLowerCase();

    let detected = false;

    if (HIGH_RISK_BACKENDS.has(backend)) {
      nodeIds.push(id);
      if (!backendIds.includes(backend)) backendIds.push(backend);
      reasons.push(`Backend "${backend}" is a high-risk external tool.`);
      detected = true;
    }

    if (!detected) {
      for (const prefix of HIGH_RISK_PREFIXES) {
        if (id.startsWith(prefix)) {
          nodeIds.push(id);
          if (backend && !backendIds.includes(backend)) backendIds.push(backend);
          reasons.push(`Node "${id}" matches high-risk prefix "${prefix}".`);
          detected = true;
          break;
        }
      }
    }
  }

  return {
    required: nodeIds.length > 0,
    nodeIds,
    backendIds,
    reasons,
  };
}

export function detectNativePreprocNodes(
  plan: Record<string, unknown> | null | undefined,
): NativePreprocApprovalRequirement {
  if (!plan) {
    return { required: false, nodeIds: [] };
  }

  const nodes = (plan.nodes ?? []) as Array<Record<string, unknown>>;
  if (!Array.isArray(nodes) || nodes.length === 0) {
    return { required: false, nodeIds: [] };
  }

  const nodeIds = nodes
    .map((node) => String(node.id ?? ""))
    .filter((id) => id === "native_preproc_full_execute");

  return {
    required: nodeIds.length > 0,
    nodeIds,
  };
}

// ── Approval completeness check ─────────────────────────────────────────────

export type ExternalToolApprovalState = {
  externalToolAcknowledgement: boolean;
  rawdataReadOnlyConfirmed: boolean;
  outputDirectoryConfirmed: boolean;
  riskAcknowledgement: boolean;
  subjectScopeConfirmed: boolean;
  overwritePolicy: "fail_if_exists" | "require_explicit_overwrite_approval";
};

export type NativePreprocApprovalState = {
  nativePreprocessingAcknowledgement: boolean;
  noExternalToolsConfirmed: boolean;
  rawdataReadOnlyConfirmed: boolean;
  riskAcknowledgement: boolean;
  subjectScopeConfirmed: boolean;
};

const ALLOWED_OVERWRITE = new Set(["fail_if_exists", "require_explicit_overwrite_approval"]);

/**
 * Returns true if external-tool approval is complete.
 * If no high-risk nodes are required, returns true immediately.
 */
export function isExternalToolApprovalComplete(
  requirement: ExternalToolApprovalRequirement,
  state: ExternalToolApprovalState,
): boolean {
  if (!requirement.required) return true;

  return (
    state.externalToolAcknowledgement === true &&
    state.rawdataReadOnlyConfirmed === true &&
    state.outputDirectoryConfirmed === true &&
    state.riskAcknowledgement === true &&
    state.subjectScopeConfirmed === true &&
    ALLOWED_OVERWRITE.has(state.overwritePolicy)
  );
}

export function isNativePreprocApprovalComplete(
  requirement: NativePreprocApprovalRequirement,
  state: NativePreprocApprovalState,
): boolean {
  if (!requirement.required) return true;

  return (
    state.nativePreprocessingAcknowledgement === true &&
    state.noExternalToolsConfirmed === true &&
    state.rawdataReadOnlyConfirmed === true &&
    state.riskAcknowledgement === true &&
    state.subjectScopeConfirmed === true
  );
}
