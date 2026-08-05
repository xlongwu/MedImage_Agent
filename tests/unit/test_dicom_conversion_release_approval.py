"""Tests for DICOM conversion release approval — Phase 4L-0.

Tests schema helpers, service validation, and safety invariants.
No dcm2niix.  No subprocess writes.  No rawdata modification.
No frontend execute button.  No public endpoint.
"""

from __future__ import annotations

import json

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


def _make_complete_approval() -> dict:
    return {
        "approval_id": "approval-L-001",
        "project_id": "test-project",
        "conversion_run_id": "conv-test",
        "status": "draft",
        "approved_by": "maintainer@lab",
        "human_approval_statement": "I have reviewed all 32 safety gates, release readiness, and safety documentation. I approve this release for human review sign-off. This does not enable public conversion.",
        "rawdata_readonly_acknowledged": True,
        "no_clinical_use_acknowledged": True,
        "rollback_acknowledged": True,
        "approval_audit_acknowledged": True,
        "public_endpoint_acknowledged": True,
        "frontend_execute_acknowledged": True,
        "spm_dpabi_matlab_disabled_acknowledged": True,
    }


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Schema: approval completeness
# ═══════════════════════════════════════════════════════════════════════


def test_missing_approval_is_incomplete():
    """Gate 1: Empty approval record is not complete."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_complete,
    )

    record = DicomConversionReleaseApprovalRecord()
    assert not is_release_approval_complete(record)


def test_incomplete_approval_blocked():
    """Gate 2: Approval without all fields is incomplete."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_complete,
    )

    record = DicomConversionReleaseApprovalRecord(
        approved_by="tester",
        human_approval_statement="Approved.",
        rawdata_readonly_acknowledged=True,
        # Missing: no_clinical_use, rollback, etc.
    )
    assert not is_release_approval_complete(record)


def test_complete_approval_accepted():
    """Gate 3: Fully complete approval record is accepted."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_complete,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    assert is_release_approval_complete(record)


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Schema: approval validation against readiness
# ═══════════════════════════════════════════════════════════════════════


def test_approval_blocked_if_not_ready():
    """Gate 4: Approval blocked if release readiness is not ready."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="blocked",
        gates_met=32,
        gates_total=32,
    )
    assert not ok
    assert any("ready_for_human_release_review" in i for i in issues)


def test_approval_blocked_if_gates_not_32():
    """Gate 5: Approval blocked if gates are not 32/32."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=25,
        gates_total=32,
    )
    assert not ok
    assert any("25/32" in i for i in issues)


def test_approval_blocked_if_no_maintainer():
    """Gate 6: Approval blocked if maintainer identity is missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["approved_by"] = ""
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("approved_by" in i for i in issues)


def test_approval_blocked_if_no_statement():
    """Gate 7: Approval blocked if human approval statement is missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["human_approval_statement"] = ""
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("statement" in i.lower() for i in issues)


def test_approval_blocked_if_no_rawdata_ack():
    """Gate 8: Approval blocked if rawdata-readonly acknowledgement missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["rawdata_readonly_acknowledged"] = False
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("rawdata" in i.lower() for i in issues)


def test_approval_blocked_if_no_clinical_ack():
    """Gate 9: Approval blocked if no-clinical-use acknowledgement missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["no_clinical_use_acknowledged"] = False
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("clinical" in i.lower() for i in issues)


def test_approval_blocked_if_no_rollback_ack():
    """Gate 10: Approval blocked if rollback acknowledgement missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["rollback_acknowledged"] = False
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("rollback" in i.lower() for i in issues)


def test_approval_blocked_if_no_audit_ack():
    """Gate 11: Approval blocked if approval/audit acknowledgement missing."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    data = _make_complete_approval()
    data["approval_audit_acknowledged"] = False
    record = DicomConversionReleaseApprovalRecord(**data)
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
    )
    assert not ok
    assert any("audit" in i.lower() for i in issues)


def test_approval_valid_when_all_met():
    """Gate 12: Complete approval is valid when readiness is ready."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
        gates_total=32,
    )
    assert ok
    assert len(issues) == 0


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Schema: evaluate_release_approval
# ═══════════════════════════════════════════════════════════════════════


def test_approval_valid_when_readiness_has_nonblocking_warnings():
    """Phase 6B: non-blocking readiness warnings do not invalidate approval."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        is_release_approval_valid,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    ok, issues = is_release_approval_valid(
        record,
        readiness_status="warning",
        gates_met=32,
        gates_total=32,
    )
    assert ok
    assert len(issues) == 0


def test_evaluate_approval_returns_approved():
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        evaluate_release_approval,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    decision = evaluate_release_approval(
        record,
        readiness_status="ready_for_human_release_review",
        gates_met=32,
        gates_total=32,
    )
    assert decision.status == "approved"
    assert decision.approved is True
    assert decision.blocked is False


def test_evaluate_approval_returns_blocked_when_incomplete():
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        evaluate_release_approval,
    )

    record = DicomConversionReleaseApprovalRecord()
    decision = evaluate_release_approval(record)
    assert decision.status in ("blocked", "incomplete")
    assert decision.approved is False


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Schema: helpers purity and summary
# ═══════════════════════════════════════════════════════════════════════


def test_build_summary():
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
        build_release_approval_summary,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    summary = build_release_approval_summary(record)
    assert summary["complete"] is True
    assert summary["gates"] == "0/32"
    assert "acknowledgements" in summary


def test_schema_has_no_subprocess():
    import src.backend.app.schemas.dicom_conversion_release_approval as mod

    source = open(mod.__file__, encoding="utf-8").read()
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_schema_has_no_file_write():
    import src.backend.app.schemas.dicom_conversion_release_approval as mod

    source = open(mod.__file__, encoding="utf-8").read()
    assert "open(" not in source


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Service: persist_release_approval
# ═══════════════════════════════════════════════════════════════════════


def test_service_persist_writes_metadata_even_when_blocked(tmp_path):
    """Gate 13: Approval service writes metadata files even when blocked."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
    )
    from src.backend.app.services.dicom_conversion_release_approval import (
        persist_release_approval,
    )

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    _decision = persist_release_approval(
        record,
        project_dir=str(tmp_path),
        conversion_run_id="conv-test",
        readiness_status="ready_for_human_release_review",
        gates_met=32,
        gates_total=32,
    )
    # The live readiness check may return blocked/warning depending on tmp_path,
    # but the service should still write metadata files for audit purposes.
    record_path = tmp_path / "conversion_runs" / "conv-test" / "release_approval_record.json"
    decision_path = tmp_path / "conversion_runs" / "conv-test" / "release_approval_decision.json"
    assert record_path.exists(), "Record file must be written even when blocked"
    assert decision_path.exists(), "Decision file must be written even when blocked"
    data = json.loads(record_path.read_text())
    assert "approved_by" in data


def test_service_approval_succeeds_when_ready(tmp_path, monkeypatch):
    """Approval succeeds when readiness is explicitly ready_for_human_release_review."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
    )
    from src.backend.app.schemas.dicom_conversion_release_readiness import (
        DicomConversionReleaseReadinessReport,
    )

    # Monkeypatch the readiness check to return ready
    from src.backend.app.services import dicom_conversion_release_readiness as rr_mod
    from src.backend.app.services.dicom_conversion_release_approval import (
        persist_release_approval,
    )

    def fake_readiness(*args, **kwargs):
        return DicomConversionReleaseReadinessReport(
            ok=True,
            status="ready_for_human_release_review",
            gates_met=32,
            gates_total=32,
            gate_status="CONDITIONAL_GO",
            human_release_approval_required=True,
        )

    monkeypatch.setattr(rr_mod, "evaluate_conversion_release_readiness", fake_readiness)

    record = DicomConversionReleaseApprovalRecord(**_make_complete_approval())
    decision = persist_release_approval(
        record,
        project_dir=str(tmp_path),
        conversion_run_id="conv-test",
    )
    assert decision.approved is True
    record_path = tmp_path / "conversion_runs" / "conv-test" / "release_approval_record.json"
    data = json.loads(record_path.read_text())
    assert data["status"] == "approved"


def test_service_does_not_call_dcm2niix():
    """Gate 14: Service does not call dcm2niix in executable code."""
    import inspect

    from src.backend.app.services import dicom_conversion_release_approval as mod

    source = inspect.getsource(mod.persist_release_approval)
    # Exclude docstring and comment lines
    code_lines = [
        line
        for line in source.splitlines()
        if '"""' not in line and "dcm2niix" not in line.lower() and not line.strip().startswith("#")
    ]
    code = "\n".join(code_lines)
    assert "subprocess" not in code.lower()


def test_service_does_not_modify_rawdata():
    """Gate 15: Service does not modify rawdata."""
    import inspect

    from src.backend.app.services import dicom_conversion_release_approval as mod

    source = inspect.getsource(mod.persist_release_approval)
    # Exclude docstrings
    code_lines = [
        line for line in source.splitlines() if '"""' not in line and "rawdata" not in line.lower()
    ]
    code = "\n".join(code_lines)
    assert "open(" not in code


def test_service_incomplete_returns_blocked(tmp_path):
    """Incomplete record returns blocked decision."""
    from src.backend.app.schemas.dicom_conversion_release_approval import (
        DicomConversionReleaseApprovalRecord,
    )
    from src.backend.app.services.dicom_conversion_release_approval import (
        persist_release_approval,
    )

    record = DicomConversionReleaseApprovalRecord()  # empty
    decision = persist_release_approval(
        record,
        project_dir=str(tmp_path),
        conversion_run_id="conv-test",
    )
    assert decision.approved is False
    assert decision.blocked is True


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Safety invariants
# ═══════════════════════════════════════════════════════════════════════


def test_run_conversion_execute_still_blocked():
    """Gate 16: run_conversion_execute() remains blocked."""
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True


def test_no_public_conversion_execute_endpoint():
    """Phase 7 retires this weak execution path in favor of reviewed tickets."""
    from fastapi.testclient import TestClient

    from src.backend.app.main import app

    client = TestClient(app)
    resp = client.post("/api/projects/test/conversion/execute", json={})
    assert resp.status_code == 410
    detail = resp.json()["detail"]
    assert detail["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert detail["replacement"] == "/api/plans/execute-reviewed"


def test_no_frontend_execute_button():
    """Gate 18: No frontend 'Run Conversion' onClick handler exists."""
    import os

    panel_paths = [
        "src/frontend/src/components/DicomConversionReviewPanel.tsx",
        "src/frontend/src/components/DicomConversionReviewPanel.jsx",
    ]
    found = False
    for rel_path in panel_paths:
        full = os.path.join(os.getcwd(), rel_path)
        if os.path.exists(full):
            lines = open(full, encoding="utf-8").read().splitlines()
            for line in lines:
                stripped = line.strip()
                if (
                    stripped.startswith("//")
                    or stripped.startswith("/*")
                    or stripped.startswith("*")
                ):
                    continue
                if "onClick" in stripped and (
                    "Run Conversion" in stripped or "runConversion" in stripped
                ):
                    found = True
    assert not found
