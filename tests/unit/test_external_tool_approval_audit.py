"""Tests for external-tool approval gate and audit record extensions."""

from __future__ import annotations

from src.backend.app.planner.plan_validator import validate_plan
from src.backend.app.planner.approval_gate import check_approval_gate
from src.backend.app.planner.audit_record import build_review_audit_record


def _spm_plan():
    """Return a plan with a high-risk external-tool node (spm_smooth).

    Uses spm_smooth_subject because it has manual_required=False,
    so external-tool acknowledgement checks are reachable.
    """
    return {
        "pipeline_id": "test_spm_approval",
        "nodes": [
            {
                "id": "spm_smooth_subject",
                "backend": "matlab-spm",
                "depends_on": [],
                "params": {},
            },
        ],
    }


def _valid_approval(**overrides):
    base = {
        "approved": True,
        "approved_by": "researcher",
        "approved_nodes": ["spm_smooth_subject"],
        "approved_backends": ["matlab-spm"],
        "external_tool_acknowledgement": True,
        "rawdata_read_only_confirmed": True,
        "output_directory_confirmed": True,
        "risk_acknowledgement": True,
        "overwrite_policy": "fail_if_exists",
        "subject_scope_confirmed": True,
        "review_draft_schema_version": "review-draft-v1",
    }
    base.update(overrides)
    return base


def _validation(plan):
    return validate_plan(plan).to_dict()


# ── Low-risk compatibility ───────────────────────────────────────────────────

def test_low_risk_contract_smoke_still_passes():
    """Existing contract_smoke plan should still pass without external-tool fields."""
    plan = {
        "pipeline_id": "test_smoke",
        "nodes": [{"id": "contract_smoke", "backend": "python", "depends_on": [], "params": {}}],
    }
    val = _validation(plan)
    result = check_approval_gate(
        plan, val,
        {"approved": True, "approved_nodes": ["contract_smoke"]},
    )
    assert result.execution_allowed is True
    assert result.ok is True


# ── External-tool approval field tests ───────────────────────────────────────

def test_spm_plan_blocked_when_approved_false():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(plan, val, {"approved": False})
    assert result.execution_allowed is False


def test_spm_plan_blocked_missing_external_tool_ack():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(
        plan, val,
        _valid_approval(external_tool_acknowledgement=False),
    )
    assert result.execution_allowed is False
    assert any("EXTERNAL_TOOL_ACKNOWLEDGEMENT" in e.code for e in result.errors)


def test_spm_plan_blocked_missing_rawdata_confirm():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(
        plan, val,
        _valid_approval(rawdata_read_only_confirmed=False),
    )
    assert result.execution_allowed is False
    assert any("RAWDATA_READ_ONLY_CONFIRMATION" in e.code for e in result.errors)


def test_spm_plan_blocked_missing_output_confirm():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(
        plan, val,
        _valid_approval(output_directory_confirmed=False),
    )
    assert result.execution_allowed is False


def test_spm_plan_blocked_missing_risk_ack():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(
        plan, val,
        _valid_approval(risk_acknowledgement=False),
    )
    assert result.execution_allowed is False


def test_spm_plan_blocked_missing_overwrite_policy():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(plan, val, {**{k: v for k, v in _valid_approval().items() if k != "overwrite_policy"}})
    assert result.execution_allowed is False
    assert any("OVERWRITE_POLICY" in e.code for e in result.errors)


def test_spm_plan_blocked_invalid_overwrite_policy():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(plan, val, _valid_approval(overwrite_policy="silent_overwrite"))
    assert result.execution_allowed is False


def test_spm_plan_blocked_missing_subject_scope():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(plan, val, _valid_approval(subject_scope_confirmed=False))
    assert result.execution_allowed is False


def test_spm_plan_passes_with_all_fields():
    plan = _spm_plan()
    val = _validation(plan)
    result = check_approval_gate(plan, val, _valid_approval())
    assert result.execution_allowed is True


# ── Audit record extension tests ─────────────────────────────────────────────

def test_audit_record_includes_approval_context():
    plan = _spm_plan()
    val = _validation(plan)
    approval = _valid_approval()
    record = build_review_audit_record(
        "execution_requested", plan, val, approval,
    )
    ctx = record.safety.get("approval_context")
    assert ctx is not None
    assert ctx["external_tool_acknowledgement"] is True
    assert ctx["overwrite_policy"] == "fail_if_exists"
    assert ctx["approved_nodes"] == ["spm_smooth_subject"]


def test_audit_record_no_context_for_low_risk():
    plan = {
        "pipeline_id": "test_smoke",
        "nodes": [{"id": "contract_smoke", "backend": "python", "depends_on": [], "params": {}}],
    }
    val = _validation(plan)
    record = build_review_audit_record(
        "dry_run_checked", plan, val,
        {"approved": True, "approved_nodes": ["contract_smoke"]},
    )
    assert record.safety.get("approval_context") is None
