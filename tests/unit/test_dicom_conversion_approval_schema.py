"""Tests for DICOM conversion approval schema — Phase 4D.

Tests all approval models, checklist builder, gate decision evaluator,
and safety invariants.  No subprocess, no file writes, no dcm2niix
execution, no SPM/DPABI/MATLAB.
"""

from __future__ import annotations

from src.backend.app.schemas.dicom_conversion_approval import (
    DicomConversionApprovalRecord,
    DicomConversionGateDecision,
    build_conversion_approval_checklist,
    evaluate_conversion_approval_gate,
    is_conversion_approval_complete,
    is_safe_overwrite_policy,
    requires_new_run_directory,
)


def _make_approved_record() -> DicomConversionApprovalRecord:
    """Build a fully approved record with all 17 fields satisfied."""
    return DicomConversionApprovalRecord(
        approval_id="test-approval",
        project_id="test-project",
        status="approved",
        approved=True,
        approved_by="researcher",
        approved_at="2026-06-08T12:00:00Z",
        mapping_ids=["map-001"],
        mappings_reviewed=True,
        output_root="/safe/output",
        output_root_confirmed=True,
        output_root_under_project=True,
        output_root_not_rawdata=True,
        overwrite_policy="fail_if_exists",
        rawdata_read_only_confirmed=True,
        command_templates_reviewed=True,
        no_shell_string_confirmed=True,
        dcm2niix_availability_confirmed=True,
        dcm2niix_version="v1.0.0",
        env_flags_confirmed=True,
        rollback_policy_acknowledged=True,
        clinical_use_prohibited_acknowledged=True,
        external_tool_acknowledgement=True,
        risk_acknowledgement=True,
        confirm_execution=True,
    )


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Missing / incomplete approval
# ═══════════════════════════════════════════════════════════════════════


def test_missing_approval_record_is_incomplete():
    record = DicomConversionApprovalRecord()
    assert is_conversion_approval_complete(record) is False


def test_missing_output_root_confirmation_blocked():
    record = _make_approved_record()
    record.output_root_confirmed = False
    assert is_conversion_approval_complete(record) is False
    decision = evaluate_conversion_approval_gate(record, preflight_ok=True)
    assert decision.status == "incomplete"
    assert "output_root_confirmed" in decision.missing_fields


def test_missing_rawdata_read_only_blocked():
    record = _make_approved_record()
    record.rawdata_read_only_confirmed = False
    assert is_conversion_approval_complete(record) is False


def test_missing_command_template_review_blocked():
    record = _make_approved_record()
    record.command_templates_reviewed = False
    assert is_conversion_approval_complete(record) is False


def test_missing_no_shell_acknowledgement_blocked():
    record = _make_approved_record()
    record.no_shell_string_confirmed = False
    assert is_conversion_approval_complete(record) is False


def test_missing_dcm2niix_availability_blocked():
    record = _make_approved_record()
    record.dcm2niix_availability_confirmed = False
    assert is_conversion_approval_complete(record) is False


def test_missing_env_flags_blocked():
    record = _make_approved_record()
    record.env_flags_confirmed = False
    assert is_conversion_approval_complete(record) is False


def test_missing_rollback_acknowledgement_blocked():
    record = _make_approved_record()
    record.rollback_policy_acknowledged = False
    assert is_conversion_approval_complete(record) is False


def test_missing_clinical_prohibition_blocked():
    record = _make_approved_record()
    record.clinical_use_prohibited_acknowledged = False
    assert is_conversion_approval_complete(record) is False


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Unsafe output root
# ═══════════════════════════════════════════════════════════════════════


def test_output_root_not_under_project_blocked():
    record = _make_approved_record()
    record.output_root_under_project = False
    decision = evaluate_conversion_approval_gate(record, preflight_ok=True)
    assert decision.status == "blocked"
    assert any("output root" in b.lower() for b in decision.blocking_issues)


def test_output_root_under_rawdata_blocked():
    record = _make_approved_record()
    record.output_root_not_rawdata = False
    decision = evaluate_conversion_approval_gate(record, preflight_ok=True)
    assert decision.status == "blocked"


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Approved record returns approved decision
# ═══════════════════════════════════════════════════════════════════════


def test_approved_record_returns_approved():
    record = _make_approved_record()
    assert is_conversion_approval_complete(record) is True
    decision = evaluate_conversion_approval_gate(record, preflight_ok=True)
    assert decision.status == "approved"
    assert decision.ready_for_execution is True


def test_approved_record_without_preflight_blocked():
    record = _make_approved_record()
    decision = evaluate_conversion_approval_gate(record, preflight_ok=False)
    assert decision.status == "blocked"
    assert any("preflight" in b.lower() for b in decision.blocking_issues)


def test_not_approved_record_is_rejected():
    record = _make_approved_record()
    record.approved = False
    decision = evaluate_conversion_approval_gate(record, preflight_ok=True)
    assert decision.status == "rejected"


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Approval decision never executes dcm2niix
# ═══════════════════════════════════════════════════════════════════════


def test_gate_decision_is_pure_function():
    """Gate decision must not import or call subprocess or dcm2niix."""
    import inspect

    source = inspect.getsource(evaluate_conversion_approval_gate)
    # Only check for actual import/usage patterns, not docstring content
    assert "import subprocess" not in source
    assert "from subprocess" not in source
    assert "subprocess.run" not in source
    assert "subprocess.call" not in source
    assert "subprocess.Popen" not in source
    assert "shell=True" not in source


def test_approval_schema_has_no_subprocess():
    import src.backend.app.schemas.dicom_conversion_approval as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
    assert "from subprocess" not in content


def test_approval_schema_has_no_spm_dpabi_matlab():
    import src.backend.app.schemas.dicom_conversion_approval as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import spm" not in content.lower()
    assert "import matlab" not in content.lower()
    assert "import dpabi" not in content.lower()


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Checklist builder
# ═══════════════════════════════════════════════════════════════════════


def test_checklist_empty_record():
    record = DicomConversionApprovalRecord()
    checklist = build_conversion_approval_checklist(record)
    assert checklist.total_count == 17
    # overwrite_policy defaults to "fail_if_exists" which counts as checked
    assert checklist.checked_count == 1
    assert checklist.all_checked is False


def test_checklist_fully_approved():
    record = _make_approved_record()
    checklist = build_conversion_approval_checklist(record)
    assert checklist.total_count == 17
    assert checklist.checked_count == 17
    assert checklist.all_checked is True


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Policy helpers
# ═══════════════════════════════════════════════════════════════════════


def test_requires_new_run_directory():
    assert requires_new_run_directory("write_new_run_directory") is True
    assert requires_new_run_directory("fail_if_exists") is False
    assert requires_new_run_directory("overwrite_derivatives_only") is False


def test_is_safe_overwrite_policy():
    assert is_safe_overwrite_policy("fail_if_exists") is True
    assert is_safe_overwrite_policy("write_new_run_directory") is True
    assert is_safe_overwrite_policy("overwrite_derivatives_only") is False


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Model defaults
# ═══════════════════════════════════════════════════════════════════════


def test_approval_record_defaults_to_missing():
    record = DicomConversionApprovalRecord()
    assert record.status == "missing"
    assert record.approved is False


def test_gate_decision_defaults_to_blocked():
    decision = DicomConversionGateDecision()
    assert decision.status == "blocked"
    assert decision.ready_for_execution is False


def test_approval_record_has_all_17_fields():
    record = _make_approved_record()
    d = record.model_dump()
    required = {
        "approved",
        "approved_by",
        "mappings_reviewed",
        "output_root_confirmed",
        "output_root_under_project",
        "output_root_not_rawdata",
        "rawdata_read_only_confirmed",
        "command_templates_reviewed",
        "no_shell_string_confirmed",
        "dcm2niix_availability_confirmed",
        "env_flags_confirmed",
        "overwrite_policy",
        "rollback_policy_acknowledged",
        "clinical_use_prohibited_acknowledged",
        "external_tool_acknowledgement",
        "risk_acknowledgement",
        "confirm_execution",
    }
    for field in required:
        assert field in d, f"Missing required field: {field}"
