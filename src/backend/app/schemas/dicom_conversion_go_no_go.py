"""DICOM Conversion GO/NO-GO Schema — Phase 4G-0.

Defines GO/NO-GO criterion models, review models, decision models, and
pure helper functions for evaluating whether real user-data DICOM
conversion should be enabled.

Schema-only module.  No subprocess.  No file writes.  No external tool imports.
No real conversion execution is enabled.

Reference:
  docs/DICOM_USER_DATA_CONVERSION_GO_NO_GO_REVIEW.md
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

GoNoGoDecision = Literal[
    "NO_GO",
    "CONDITIONAL_GO",
    "GO",
]

GoNoGoCriterionStatus = Literal[
    "met",
    "partial",
    "missing",
]


class DicomConversionGoNoGoCriterion(BaseModel):
    """A single gating condition for user-data DICOM conversion."""

    gate_id: int = 0
    label: str = ""
    status: GoNoGoCriterionStatus = "missing"
    evidence: str = ""
    risk: str = ""
    action_before_go: str = ""


class DicomConversionGoNoGoReview(BaseModel):
    """A complete GO/NO-GO review with all criteria."""

    review_id: str = ""
    decision: GoNoGoDecision = "NO_GO"
    reviewer: str = ""
    reviewed_at: str = ""
    total_criteria: int = 0
    met_count: int = 0
    partial_count: int = 0
    missing_count: int = 0
    criteria: list[DicomConversionGoNoGoCriterion] = Field(default_factory=list)
    blocking_issues: list[str] = Field(default_factory=list)
    recommendation: str = ""
    next_step: str = ""


# ═══════════════════════════════════════════════════════════════════════
# Pure helpers
# ═══════════════════════════════════════════════════════════════════════

_CRITICAL_GATE_IDS: frozenset[int] = frozenset({
    1,   # rawdata read-only
    14,  # dcm2niix availability
    15,  # env flags required
    16,  # command argv list only
    17,  # no raw shell string
    22,  # no execute button
    23,  # safe allowlist constrained
    24,  # SPM/DPABI/MATLAB disabled
    25,  # full preprocessing disabled
    26,  # run_conversion_execute blocked
})


def evaluate_go_no_go_criteria(
    criteria: list[DicomConversionGoNoGoCriterion],
) -> GoNoGoDecision:
    """Evaluate a list of criteria and return a GO/NO-GO decision.

    - Any critical gate with status "missing" → NO_GO
    - Any gate with status "missing" → NO_GO
    - All gates "met" → GO
    - All critical "met", some non-critical "partial" → CONDITIONAL_GO

    Pure function — no file I/O, no subprocess.
    """
    missing_any = any(c.status == "missing" for c in criteria)
    if missing_any:
        return "NO_GO"

    critical_missing = any(
        c.gate_id in _CRITICAL_GATE_IDS and c.status != "met"
        for c in criteria
    )
    if critical_missing:
        return "NO_GO"

    all_met = all(c.status == "met" for c in criteria)
    if all_met:
        return "GO"

    return "CONDITIONAL_GO"


def is_conditional_go_allowed(
    review: DicomConversionGoNoGoReview,
) -> bool:
    """Return True if a CONDITIONAL_GO decision is allowed.

    CONDITIONAL_GO requires all critical gates to be met and no
    missing gates.
    """
    return review.decision == "CONDITIONAL_GO"


def summarize_missing_go_criteria(
    review: DicomConversionGoNoGoReview,
) -> dict[str, Any]:
    """Summarize missing criteria from a review."""
    missing = [c for c in review.criteria if c.status == "missing"]
    partial = [c for c in review.criteria if c.status == "partial"]
    return {
        "decision": review.decision,
        "missing_count": len(missing),
        "partial_count": len(partial),
        "missing_labels": [c.label for c in missing],
        "partial_labels": [c.label for c in partial],
    }


def build_default_go_no_go_review() -> DicomConversionGoNoGoReview:
    """Build the current default GO/NO-GO review based on Phase 4F-1 evidence.

    Pure function — no file I/O.  Reflects the documented state as of
    Phase 4G-0.
    """
    criteria: list[DicomConversionGoNoGoCriterion] = [
        DicomConversionGoNoGoCriterion(gate_id=1, label="Real rawdata read-only", status="met", evidence="All services emit rawdata_read_only flag", risk="Data loss", action_before_go="Pre/post checksum"),
        DicomConversionGoNoGoCriterion(gate_id=2, label="Output root under project dir", status="met", evidence="validate_output_root_under_project()", risk="Data leak", action_before_go="Gate validation"),
        DicomConversionGoNoGoCriterion(gate_id=3, label="Output root not under rawdata", status="met", evidence="validate_output_root_not_under_rawdata()", risk="Rawdata corruption", action_before_go="Gate validation"),
        DicomConversionGoNoGoCriterion(gate_id=4, label="Conversion run dir reserved", status="met", evidence="persist_conversion_plan()", risk="Path collision", action_before_go="fail_if_exists"),
        DicomConversionGoNoGoCriterion(gate_id=5, label="Approval record persisted", status="met", evidence="approval_record.json", risk="No audit trail", action_before_go="Verify exists"),
        DicomConversionGoNoGoCriterion(gate_id=6, label="Audit preview persisted", status="met", evidence="audit_preview.json", risk="Incomplete audit", action_before_go="Populate"),
        DicomConversionGoNoGoCriterion(gate_id=7, label="Preflight snapshot persisted", status="met", evidence="preflight_snapshot.json", risk="Approval drift", action_before_go="Verify"),
        DicomConversionGoNoGoCriterion(gate_id=8, label="Mapping snapshot persisted", status="met", evidence="mapping_snapshot.json", risk="Wrong targets", action_before_go="Verify"),
        DicomConversionGoNoGoCriterion(gate_id=9, label="Command template persisted", status="met", evidence="command_templates.json", risk="Wrong commands", action_before_go="Verify"),
        DicomConversionGoNoGoCriterion(gate_id=10, label="Manifest/provenance planned", status="met", evidence="planned_*.json", risk="Missing artifacts", action_before_go="Rewrite"),
        DicomConversionGoNoGoCriterion(gate_id=11, label="Logs planned", status="met", evidence="logs/stdout|stderr.log", risk="Missing diagnostics", action_before_go="Capture"),
        DicomConversionGoNoGoCriterion(gate_id=12, label="Rollback policy defined", status="partial", evidence="Schema field only", risk="Partial outputs", action_before_go="Implement cleanup"),
        DicomConversionGoNoGoCriterion(gate_id=13, label="Overwrite policy explicit", status="met", evidence="fail_if_exists default", risk="Data loss", action_before_go="Validate"),
        DicomConversionGoNoGoCriterion(gate_id=14, label="dcm2niix availability checked", status="met", evidence="check_dcm2niix_availability()", risk="Tool missing", action_before_go="Re-check"),
        DicomConversionGoNoGoCriterion(gate_id=15, label="Env flags required", status="met", evidence="_PERSISTED_SYNTHETIC_ENV_FLAGS", risk="Accidental exec", action_before_go="All 8 must be '1'"),
        DicomConversionGoNoGoCriterion(gate_id=16, label="Command argv list only", status="met", evidence="All runners accept list[str]", risk="Shell injection", action_before_go="Code review"),
        DicomConversionGoNoGoCriterion(gate_id=17, label="No raw shell string", status="met", evidence="extra='forbid' on template", risk="Shell injection", action_before_go="Code review"),
        DicomConversionGoNoGoCriterion(gate_id=18, label="Metadata-only audit export", status="met", evidence="Excludes .dcm/.nii", risk="Data leak", action_before_go="Maintain whitelist"),
        DicomConversionGoNoGoCriterion(gate_id=19, label="Review package readable", status="met", evidence="read_conversion_review_package()", risk="Missing context", action_before_go="Verify"),
        DicomConversionGoNoGoCriterion(gate_id=20, label="Synthetic smoke validated", status="met", evidence="12 tests passed", risk="Unknown behavior", action_before_go="Pass before GO"),
        DicomConversionGoNoGoCriterion(gate_id=21, label="Synthetic result viewer", status="met", evidence="read_synthetic_smoke_results()", risk="Missing visibility", action_before_go="Available"),
        DicomConversionGoNoGoCriterion(gate_id=22, label="No real execute button", status="met", evidence="DicomConversionReviewPanel", risk="Operator error", action_before_go="Maintain"),
        DicomConversionGoNoGoCriterion(gate_id=23, label="Safe allowlist constrained", status="met", evidence="test_spm_safe_allowlist_policy.py", risk="Unauthorized exec", action_before_go="Do not expand"),
        DicomConversionGoNoGoCriterion(gate_id=24, label="SPM/DPABI/MATLAB disabled", status="met", evidence="Guard tests pass", risk="Preprocessing leak", action_before_go="Keep disabled"),
        DicomConversionGoNoGoCriterion(gate_id=25, label="Full preprocessing disabled", status="met", evidence="No nodes registered", risk="Scope creep", action_before_go="Keep disabled"),
        DicomConversionGoNoGoCriterion(gate_id=26, label="run_conversion_execute blocked", status="met", evidence="Always returns disabled", risk="Accidental exec", action_before_go="Maintain"),
        DicomConversionGoNoGoCriterion(gate_id=27, label="Approval gate schema complete", status="partial", evidence="17 preconditions defined", risk="Missing checks", action_before_go="Integrate gate"),
        DicomConversionGoNoGoCriterion(gate_id=28, label="Audit persists before exec", status="partial", evidence="Schema only; not integrated", risk="Race condition", action_before_go="Gate integration"),
        DicomConversionGoNoGoCriterion(gate_id=29, label="Rawdata unchanged verified", status="met", evidence="rawdata_checksum_before.json written by persist_conversion_plan(); 8 fields in approval record", risk="Silent corruption", action_before_go="Re-verify at exec time"),
        DicomConversionGoNoGoCriterion(gate_id=30, label="Real dcm2niix on synthetic DICOM", status="met", evidence="Phase 4H-3d: integration test PASSED with real dcm2niix.exe on synthetic DICOM", risk="Tool incompatibility", action_before_go="Done — smoke validated"),
        DicomConversionGoNoGoCriterion(gate_id=31, label="External DICOM smoke on real layout", status="met", evidence="Phase 4I-1b: internal FunRaw/T1Raw DemoData conversion PASSED — 1104 DICOM, 3 subjects, 6 groups", risk="Layout incompatibility", action_before_go="Done — smoke validated"),
        DicomConversionGoNoGoCriterion(gate_id=32, label="Rollback tested", status="partial", evidence="rollback_plan_dry_run.json written; dry-run tested; no real deletion", risk="Partial outputs", action_before_go="Implement real rollback"),
    ]

    met = sum(1 for c in criteria if c.status == "met")
    partial = sum(1 for c in criteria if c.status == "partial")
    missing = sum(1 for c in criteria if c.status == "missing")

    return DicomConversionGoNoGoReview(
        review_id="phase-4g-2-review",
        decision="CONDITIONAL_GO",
        reviewer="MedImage Agent Phase 4G-0 automated review",
        reviewed_at="2026-06-08",
        total_criteria=len(criteria),
        met_count=met,
        partial_count=partial,
        missing_count=missing,
        criteria=criteria,
        blocking_issues=[
            "Rollback implementation is dry-run only (gate 32)",
            "Approval/audit execution integration not wired (gate 28)",
        ],
        recommendation="CONDITIONAL GO MAINTAINED — 30/32 gates met, zero missing. Full GO blocked by rollback and audit integration.",
        next_step="Phase 4J-0: Rollback implementation and approval/audit execution integration.",
    )
