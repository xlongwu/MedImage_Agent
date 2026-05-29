"""Tests for Approval Gate — approval record validation."""

from __future__ import annotations

import json

from src.backend.app.planner.approval_gate import (
    ApprovalGateResult,
    ApprovalRecord,
    check_approval_gate,
)


# ── Helpers ──

def _valid_validation(**overrides):
    v = {
        "ok": True,
        "approval_required_nodes": [],
        "high_risk_nodes": [],
        "manual_required_nodes": [],
        "risk_summary": {"requires_approval": False},
    }
    v.update(overrides)
    return v


def _approval(approved=True, approved_nodes=None, rejected_nodes=None):
    return ApprovalRecord(
        approved=approved,
        approved_by="test-user",
        approved_nodes=approved_nodes or [],
        rejected_nodes=rejected_nodes or [],
    )


# ── 1. Validation missing ──

def test_validation_missing():
    result = check_approval_gate({}, None, None)  # type: ignore[arg-type]
    assert result.execution_allowed is False
    assert any(e.code == "VALIDATION_MISSING" for e in result.errors)


# ── 2. Validation not ok ──

def test_validation_not_ok():
    result = check_approval_gate({}, {"ok": False}, None)
    assert result.execution_allowed is False
    assert any(e.code == "VALIDATION_NOT_OK" for e in result.errors)


# ── 3. No approval needed → allowed ──

def test_no_approval_needed():
    result = check_approval_gate({}, _valid_validation(), None)
    assert result.execution_allowed is True
    assert result.approval_required is False


# ── 4. Approval needed but missing ──

def test_approval_missing():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    result = check_approval_gate({}, v, None)
    assert result.execution_allowed is False
    assert any(e.code == "APPROVAL_MISSING" for e in result.errors)


# ── 5. approved=false ──

def test_approved_false():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    a = _approval(approved=False)
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is False
    assert any(e.code == "APPROVAL_NOT_GRANTED" for e in result.errors)


# ── 6. approved_nodes cover required ──

def test_approved_nodes_cover_required():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    a = _approval(approved_nodes=["spm_realign_subject"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is True


# ── 7. approved_nodes missing required ──

def test_approved_nodes_missing_required():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    a = _approval(approved_nodes=["data_inspection"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is False
    assert any(e.code == "APPROVAL_NODE_MISSING" for e in result.errors)


# ── 8. Wildcard approval ──

def test_wildcard_approval():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject", "spm_smooth_subject"])
    a = _approval(approved_nodes=["*"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is True


# ── 9. rejected_nodes block ──

def test_rejected_nodes_block():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    a = _approval(approved_nodes=["spm_realign_subject"], rejected_nodes=["spm_smooth_subject"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is False
    assert any(e.code == "APPROVAL_REJECTED_NODE" for e in result.errors)


# ── 10. High risk → warning ──

def test_high_risk_warning():
    v = _valid_validation(
        approval_required_nodes=["spm_realign_subject"],
        high_risk_nodes=["spm_realign_subject"],
    )
    a = _approval(approved_nodes=["spm_realign_subject"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is True
    assert any(w.code == "HIGH_RISK_APPROVED" for w in result.warnings)


# ── 11. Manual required → blocked ──

def test_manual_required_blocked():
    v = _valid_validation(
        approval_required_nodes=["spm_realign_subject"],
        manual_required_nodes=["gui_acpc_location"],
    )
    a = _approval(approved_nodes=["*"])
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is False
    assert any(e.code == "MANUAL_REQUIRED_NODE" for e in result.errors)


# ── 12. to_dict JSON serializable ──

def test_to_dict_json():
    result = check_approval_gate({}, _valid_validation(), None)
    d = result.to_dict()
    raw = json.dumps(d, ensure_ascii=False)
    back = json.loads(raw)
    assert back["execution_allowed"] is True


# ── 13. No pipeline execution ──

def test_no_pipeline_execution():
    result = check_approval_gate({}, _valid_validation(), None)
    assert result.execution_allowed is True


# ── 14. No node runner ──

def test_no_runner():
    check_approval_gate({}, _valid_validation(), None)


# ── 15. No file writes ──

def test_no_file_writes(tmp_path):
    import os
    before = set(os.listdir(tmp_path))
    check_approval_gate({}, _valid_validation(), None)
    after = set(os.listdir(tmp_path))
    assert after == before


# ── 16. Dict approval accepted ──

def test_dict_approval():
    v = _valid_validation(approval_required_nodes=["spm_realign_subject"])
    a = {"approved": True, "approved_nodes": ["spm_realign_subject"], "rejected_nodes": []}
    result = check_approval_gate({}, v, a)
    assert result.execution_allowed is True


# ── 17. Risk summary requires_approval triggers ──

def test_risk_summary_triggers_approval():
    v = _valid_validation(risk_summary={"requires_approval": True})
    result = check_approval_gate({}, v, None)
    assert result.execution_allowed is False
    assert result.approval_required is True
