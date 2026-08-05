"""Tests for SPM realign execution contract Pydantic schemas.

Schema-only — no MATLAB/SPM execution, no file creation.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from src.backend.app.schemas.desktop import (
    SpmRealignExecutionProvenance,
    SpmRealignExecutionRequest,
    SpmRealignExecutionResult,
    SpmRealignFailureRecord,
    SpmRealignOutputManifest,
    SpmRealignOutputManifestItem,
)

# ── Execution request tests ─────────────────────────────────────────────────


def test_request_defaults_to_disabled():
    req = SpmRealignExecutionRequest(
        project_id="p1",
        reviewed_plan_id="r1",
    )
    assert req.execution_mode == "disabled"
    assert req.command_template_id == "spm12_realign_estwrite_v1"
    assert req.overwrite_policy == "fail_if_exists"


def test_request_rejects_unknown_fields():
    """extra='forbid' means unknown fields like shell_command are rejected."""
    with pytest.raises(ValidationError):
        SpmRealignExecutionRequest(
            project_id="p1",
            reviewed_plan_id="r1",
            shell_command="matlab -batch evil",  # Intentional unknown field.
        )


def test_request_rejects_matlab_script_field():
    with pytest.raises(ValidationError):
        SpmRealignExecutionRequest(
            project_id="p1",
            reviewed_plan_id="r1",
            matlab_script="evil()",  # Intentional unknown field.
        )


# ── Output manifest tests ───────────────────────────────────────────────────


def test_output_manifest_item_supports_all_kinds():
    for kind in (
        "realigned_bold",
        "mean_bold",
        "motion_params",
        "stdout_log",
        "stderr_log",
        "provenance_json",
        "node_state_json",
        "batch_file",
    ):
        item = SpmRealignOutputManifestItem(kind=kind, path="/out/file.nii")
        assert item.kind == kind


def test_output_manifest_counts_missing():
    manifest = SpmRealignOutputManifest(
        project_id="p1",
        run_id="r1",
        output_root="/out",
        items=[
            SpmRealignOutputManifestItem(
                kind="realigned_bold", path="/out/a.nii", required=True, verified=True
            ),
            SpmRealignOutputManifestItem(
                kind="mean_bold", path="/out/b.nii", required=True, verified=False
            ),
            SpmRealignOutputManifestItem(
                kind="motion_params", path="/out/c.txt", required=True, verified=False
            ),
        ],
        missing_required_count=2,
        verified_count=1,
    )
    assert len([i for i in manifest.items if i.required and not i.verified]) == 2
    assert manifest.missing_required_count == 2
    assert manifest.verified_count == 1


# ── Provenance tests ────────────────────────────────────────────────────────


def test_provenance_includes_all_fields():
    p = SpmRealignExecutionProvenance(
        project_id="p1",
        reviewed_plan_id="r1",
        run_id="run1",
        command_template_id="spm12_realign_estwrite_v1",
        matlab_version="R2023b",
        spm_version="12.7771",
        input_paths=["/data/sub-01/bold.nii"],
        input_checksums={"/data/sub-01/bold.nii": "abc123"},
        predicted_output_paths=["/out/rbold.nii"],
        actual_output_paths=["/out/rbold.nii"],
        return_code=0,
        stdout_log_path="/logs/stdout.log",
        stderr_log_path="/logs/stderr.log",
        batch_file_path="/batch/run.m",
        approval_context={"approved": True},
    )
    assert p.command_template_id == "spm12_realign_estwrite_v1"
    assert p.matlab_version == "R2023b"
    assert p.spm_version == "12.7771"
    assert len(p.input_paths) == 1
    assert p.approval_context["approved"] is True


# ── Failure record tests ────────────────────────────────────────────────────


def test_failure_record_all_stages():
    stages = [
        "preflight",
        "approval",
        "audit",
        "environment",
        "batch_generation",
        "execution",
        "output_verification",
        "provenance",
        "artifact_discovery",
    ]
    for stage in stages:
        f = SpmRealignFailureRecord(
            code="ERR",
            message="fail",
            stage=stage,
            retryable=True,
            next_action="fix it",
        )
        assert f.stage == stage


# ── Execution result tests ──────────────────────────────────────────────────


def test_result_defaults_executor_called_false():
    result = SpmRealignExecutionResult(
        ok=False,
        project_id="p1",
        reviewed_plan_id="r1",
        run_id="run1",
        status="not_started",
    )
    assert result.executor_called is False
    assert result.execution_mode == "disabled"


def test_result_can_represent_blocked():
    result = SpmRealignExecutionResult(
        ok=False,
        project_id="p1",
        reviewed_plan_id="r1",
        run_id="run1",
        status="blocked",
        failures=[
            SpmRealignFailureRecord(
                code="APPROVAL_REQUIRED",
                message="Approval missing",
                stage="approval",
                retryable=False,
                next_action="Complete external tool acknowledgement",
            ),
        ],
    )
    assert result.status == "blocked"
    assert len(result.failures) == 1


def test_result_can_represent_failed_output_verification():
    result = SpmRealignExecutionResult(
        ok=False,
        project_id="p1",
        reviewed_plan_id="r1",
        run_id="run1",
        status="failed",
        output_manifests=[
            SpmRealignOutputManifest(
                project_id="p1",
                run_id="run1",
                output_root="/out",
                items=[
                    SpmRealignOutputManifestItem(
                        kind="realigned_bold", path="/out/a.nii", required=True, verified=False
                    ),
                ],
                missing_required_count=1,
            ),
        ],
        failures=[
            SpmRealignFailureRecord(
                code="OUTPUT_MISSING",
                message="Expected output not found",
                stage="output_verification",
            ),
        ],
    )
    assert result.status == "failed"
    assert result.output_manifests[0].missing_required_count == 1


# ── Serialization tests ─────────────────────────────────────────────────────


def test_request_serializes_to_json_dict():
    req = SpmRealignExecutionRequest(
        project_id="p1",
        reviewed_plan_id="r1",
        subject_scope=["sub-01"],
        params={"quality": 0.9},
    )
    d = req.model_dump()
    assert d["execution_mode"] == "disabled"
    assert d["project_id"] == "p1"
    assert "shell_command" not in d


def test_no_files_created(tmp_path):
    """Schema instantiation must not create files."""
    before = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    SpmRealignExecutionRequest(project_id="p1", reviewed_plan_id="r1")
    SpmRealignExecutionResult(
        ok=False, project_id="p2", reviewed_plan_id="r2", run_id="r2", status="not_started"
    )
    after = {p.name for p in tmp_path.iterdir()} if tmp_path.exists() else set()
    assert after == before
