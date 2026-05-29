"""Approval Gate — validates approval records before pipeline execution.

The Approval Gate sits between Plan Validator and Pipeline Executor.
It checks that: validation passed, required approvals are granted,
no nodes are rejected, and manual/GUI nodes are not yet executed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ── Dataclasses ──────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ApprovalRecord:
    """A human approval record for a pipeline plan."""

    approved: bool
    approved_by: str | None = None
    approved_at: str | None = None
    reason: str | None = None
    approved_nodes: list[str] | None = None
    rejected_nodes: list[str] | None = None
    review_draft_schema_version: str | None = None


@dataclass(frozen=True)
class ApprovalGateIssue:
    """A single issue found during approval gate checking."""

    code: str
    message: str
    node_id: str | None = None
    severity: str = "error"  # "error" | "warning"


@dataclass(frozen=True)
class ApprovalGateResult:
    """Result of checking the approval gate."""

    ok: bool
    execution_allowed: bool
    approval_required: bool
    approved: bool
    missing_approval_nodes: list[str] = field(default_factory=list)
    rejected_nodes: list[str] = field(default_factory=list)
    errors: list[ApprovalGateIssue] = field(default_factory=list)
    warnings: list[ApprovalGateIssue] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "execution_allowed": self.execution_allowed,
            "approval_required": self.approval_required,
            "approved": self.approved,
            "missing_approval_nodes": self.missing_approval_nodes,
            "rejected_nodes": self.rejected_nodes,
            "errors": [
                {"code": e.code, "message": e.message,
                 "node_id": e.node_id, "severity": e.severity}
                for e in self.errors
            ],
            "warnings": [
                {"code": w.code, "message": w.message,
                 "node_id": w.node_id, "severity": w.severity}
                for w in self.warnings
            ],
        }


# ── Public API ───────────────────────────────────────────────────────────────

def check_approval_gate(
    plan: dict[str, Any],
    validation: dict[str, Any],
    approval: ApprovalRecord | dict[str, Any] | None,
) -> ApprovalGateResult:
    """Check whether a plan may proceed to execution given its validation
    and approval state.

    Args:
        plan: Pipeline plan dict (used only for node count / sanity).
        validation: PlanValidationResult.to_dict().
        approval: ApprovalRecord or dict, or None if no approval yet.

    Returns:
        ApprovalGateResult — execution_allowed=True only when all checks pass.
    """
    errors: list[ApprovalGateIssue] = []
    warnings: list[ApprovalGateIssue] = []

    # ── 1. Validation must exist and pass ──
    if not isinstance(validation, dict):
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=False, approved=False,
            errors=[ApprovalGateIssue("VALIDATION_MISSING", "Validation result is missing or not a dict.")],
        )

    if validation.get("ok") is not True:
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=False, approved=False,
            errors=[ApprovalGateIssue("VALIDATION_NOT_OK", "Plan validation did not pass.")],
        )

    # ── 2. Determine if approval is required ──
    approval_required_nodes: list[str] = list(validation.get("approval_required_nodes", []) or [])
    high_risk_nodes: list[str] = list(validation.get("high_risk_nodes", []) or [])
    manual_required_nodes: list[str] = list(validation.get("manual_required_nodes", []) or [])
    risk_summary = validation.get("risk_summary", {}) or {}
    approval_required = bool(
        approval_required_nodes
        or high_risk_nodes
        or manual_required_nodes
        or risk_summary.get("requires_approval")
    )

    # ── 3. No approval needed → green light ──
    if not approval_required:
        return ApprovalGateResult(
            ok=True, execution_allowed=True,
            approval_required=False, approved=False,
        )

    # ── 4. Approval required but no approval record ──
    if approval is None:
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=True, approved=False,
            missing_approval_nodes=list(approval_required_nodes),
            errors=[ApprovalGateIssue("APPROVAL_MISSING", "Plan requires approval but no approval record provided.")],
        )

    # Normalize approval to dict if needed
    if isinstance(approval, ApprovalRecord):
        appr_dict: dict[str, Any] = {
            "approved": approval.approved,
            "approved_nodes": approval.approved_nodes,
            "rejected_nodes": approval.rejected_nodes,
        }
    else:
        appr_dict = approval

    # ── 5. approved must be True ──
    if appr_dict.get("approved") is not True:
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=True, approved=False,
            missing_approval_nodes=list(approval_required_nodes),
            errors=[ApprovalGateIssue("APPROVAL_NOT_GRANTED", "Approval record exists but 'approved' is not true.")],
        )

    approved_nodes: list[str] = list(appr_dict.get("approved_nodes") or [])
    rejected_nodes: list[str] = list(appr_dict.get("rejected_nodes") or [])
    is_wildcard = "*" in approved_nodes

    # ── 6. rejected nodes block execution ──
    if rejected_nodes:
        errors.append(ApprovalGateIssue(
            "APPROVAL_REJECTED_NODE",
            f"Plan contains rejected nodes: {', '.join(rejected_nodes)}",
        ))
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=True, approved=True,
            rejected_nodes=rejected_nodes,
            missing_approval_nodes=list(approval_required_nodes),
            errors=errors,
        )

    # ── 7. approved_nodes must cover required nodes ──
    if not is_wildcard:
        missing = [n for n in approval_required_nodes if n not in approved_nodes]
        if missing:
            errors.append(ApprovalGateIssue(
                "APPROVAL_NODE_MISSING",
                f"Required nodes not individually approved: {', '.join(missing)}",
            ))
            return ApprovalGateResult(
                ok=False, execution_allowed=False,
                approval_required=True, approved=True,
                missing_approval_nodes=missing,
                errors=errors,
            )

    # ── 8. manual_required nodes block execution (MVP) ──
    if manual_required_nodes:
        errors.append(ApprovalGateIssue(
            "MANUAL_REQUIRED_NODE",
            f"Manual/GUI nodes not yet supported: {', '.join(manual_required_nodes)}",
        ))
        return ApprovalGateResult(
            ok=False, execution_allowed=False,
            approval_required=True, approved=True,
            missing_approval_nodes=list(approval_required_nodes),
            errors=errors,
        )

    # ── 9. high risk approved → warning ──
    if high_risk_nodes:
        warnings.append(ApprovalGateIssue(
            "HIGH_RISK_APPROVED",
            f"High-risk nodes approved: {', '.join(high_risk_nodes)}. Proceed with caution.",
            severity="warning",
        ))

    return ApprovalGateResult(
        ok=True, execution_allowed=True,
        approval_required=True, approved=True,
        missing_approval_nodes=[],
        warnings=warnings,
    )
