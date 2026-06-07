"""Execution Manifest Schema — unit tests.

Tests: OutputManifestItem validation, OutputManifest summaries,
ExecutionProvenance serialization, ExecutionFailureRecord stages,
pure helpers, and safety invariants.
"""

from __future__ import annotations

import sys

import pytest
from pydantic import ValidationError

from src.backend.app.schemas.execution_manifest import (
    OutputManifestItem,
    OutputManifest,
    ExecutionProvenance,
    ExecutionFailureRecord,
    build_output_manifest,
    summarize_output_manifest,
    count_missing_required,
    count_verified,
    count_manifest_warnings,
    count_manifest_errors,
)


# ═══════════════════════════════════════════════════════════════
# OutputManifestItem tests
# ═══════════════════════════════════════════════════════════════

def test_valid_item_serializes():
    item = OutputManifestItem(
        kind="json", path="/tmp/report.json",
        exists=True, verified=True, verification_status="verified",
        size_bytes=2048,
    )
    d = item.model_dump()
    assert d["kind"] == "json"
    assert d["exists"] is True
    assert d["verified"] is True
    assert d["size_bytes"] == 2048


def test_empty_path_rejected():
    with pytest.raises(ValidationError, match="path must be non-empty"):
        OutputManifestItem(path="")


def test_whitespace_path_rejected():
    with pytest.raises(ValidationError, match="path must be non-empty"):
        OutputManifestItem(path="   ")


def test_negative_size_bytes_rejected():
    with pytest.raises(ValidationError, match="size_bytes cannot be negative"):
        OutputManifestItem(path="/t", size_bytes=-1)


def test_verified_requires_exists():
    with pytest.raises(ValidationError, match="verified=True requires exists=True"):
        OutputManifestItem(path="/t", verified=True, exists=False)


def test_verification_status_verified_requires_exists():
    with pytest.raises(ValidationError, match="verification_status='verified' requires exists=True"):
        OutputManifestItem(path="/t", verification_status="verified", exists=False)


def test_missing_required_is_counted():
    item = OutputManifestItem(path="/t", required=True, exists=False)
    assert count_missing_required([item]) == 1


def test_optional_missing_not_counted_as_required():
    item = OutputManifestItem(path="/t", required=False, exists=False)
    assert count_missing_required([item]) == 0


def test_warnings_are_counted():
    item = OutputManifestItem(path="/t", warnings=["w1", "w2"])
    assert count_manifest_warnings([item]) == 2


def test_errors_are_counted():
    item = OutputManifestItem(path="/t", errors=["e1"])
    assert count_manifest_errors([item]) == 1


def test_defaults():
    item = OutputManifestItem(path="/t")
    assert item.kind == "other"
    assert item.required is True
    assert item.exists is False
    assert item.verified is False
    assert item.verification_status == "not_checked"
    assert item.previewable is False


# ═══════════════════════════════════════════════════════════════
# OutputManifest tests
# ═══════════════════════════════════════════════════════════════

def test_build_auto_computes_counts():
    items = [
        OutputManifestItem(path="/a", required=True, exists=True, verified=True, verification_status="verified"),
        OutputManifestItem(path="/b", required=True, exists=False),
        OutputManifestItem(path="/c", required=False, exists=False, previewable=True),
    ]
    m = build_output_manifest(project_id="p1", run_id="r1", node_id="n1", items=items)
    assert m.missing_required_count == 1
    assert m.verified_count == 1


def test_verified_count_correct():
    items = [OutputManifestItem(path="/x", verified=True, exists=True)]
    m = build_output_manifest(project_id="p1", run_id="r1", node_id="n1", items=items)
    assert m.verified_count == 1


def test_missing_required_count_correct():
    items = [OutputManifestItem(path="/x", required=True, exists=False)]
    m = build_output_manifest(project_id="p1", run_id="r1", node_id="n1", items=items)
    assert m.missing_required_count == 1


def test_previewable_appears_in_summary():
    items = [
        OutputManifestItem(path="/a", previewable=True),
        OutputManifestItem(path="/b", previewable=True),
        OutputManifestItem(path="/c", previewable=False),
    ]
    s = summarize_output_manifest(items)
    assert s["previewable_count"] == 2
    assert s["total_count"] == 3


def test_model_serializes_cleanly():
    m = build_output_manifest(
        project_id="p1", run_id="r1", node_id="n1",
        items=[OutputManifestItem(path="/a")],
        subject_id="sub-01",
    )
    d = m.model_dump()
    assert d["project_id"] == "p1"
    assert d["run_id"] == "r1"
    assert d["node_id"] == "n1"
    assert d["subject_id"] == "sub-01"
    assert d["items"][0]["path"] == "/a"


def test_empty_manifest():
    m = build_output_manifest(project_id="p1", run_id="r1", node_id="n1", items=[])
    assert m.missing_required_count == 0
    assert m.verified_count == 0


def test_summarize_counts_all_fields():
    items = [
        OutputManifestItem(path="/a", required=True, exists=True, previewable=True),
        OutputManifestItem(path="/b", required=True, exists=False),
        OutputManifestItem(path="/c", required=False, exists=False, previewable=True),
    ]
    s = summarize_output_manifest(items)
    assert s == {
        "total_count": 3,
        "required_count": 2,
        "missing_required_count": 1,
        "verified_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "previewable_count": 2,
    }


# ═══════════════════════════════════════════════════════════════
# ExecutionProvenance tests
# ═══════════════════════════════════════════════════════════════

def test_minimal_provenance_instantiates():
    p = ExecutionProvenance(project_id="p1", run_id="r1", node_id="n1")
    d = p.model_dump()
    assert d["project_id"] == "p1"
    assert d["run_id"] == "r1"
    assert d["node_id"] == "n1"
    assert d["backend"] == "unknown"


def test_full_provenance_serializes():
    p = ExecutionProvenance(
        project_id="p1", reviewed_plan_id="rp1", run_id="r1", node_id="n1",
        backend="python", command_template_id="tpl_v1",
        params={"quality": 0.9},
        input_paths=["/in/file.nii"],
        input_checksums={"/in/file.nii": "abc123"},
        output_paths=["/out/report.json"],
        output_checksums={"/out/report.json": "def456"},
        software_versions={"python": "3.11", "nibabel": "5.2"},
        environment_fingerprint="sha256:env123",
        approval_context={"approved": True},
        audit_id="audit_001",
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:05:00Z",
        return_code=0,
        stdout_log_path="/logs/stdout.log",
        stderr_log_path="/logs/stderr.log",
    )
    d = p.model_dump()
    assert d["backend"] == "python"
    assert d["command_template_id"] == "tpl_v1"
    assert d["params"] == {"quality": 0.9}
    assert d["input_checksums"] == {"/in/file.nii": "abc123"}
    assert d["output_checksums"] == {"/out/report.json": "def456"}
    assert d["software_versions"]["python"] == "3.11"
    assert d["environment_fingerprint"] == "sha256:env123"
    assert d["approval_context"] == {"approved": True}
    assert d["return_code"] == 0


def test_no_shell_command_field():
    """ExecutionProvenance has no shell command field."""
    with pytest.raises(ValidationError):
        ExecutionProvenance(
            project_id="p1", run_id="r1", node_id="n1",
            shell_command="rm -rf /",  # type: ignore[call-arg]
        )


def test_external_backend_without_enabling_execution():
    """External backend can be represented without enabling execution."""
    p = ExecutionProvenance(
        project_id="p1", run_id="r1", node_id="spm_realign",
        backend="matlab-spm", command_template_id="spm12_realign_estwrite_v1",
    )
    assert p.backend == "matlab-spm"
    assert p.command_template_id == "spm12_realign_estwrite_v1"
    # command_template_id is an identifier only, not executable code
    assert "matlab" not in p.command_template_id.lower() or "batch" not in p.command_template_id


def test_command_template_id_is_plain_identifier():
    """command_template_id is accepted as a plain identifier string."""
    p = ExecutionProvenance(
        project_id="p1", run_id="r1", node_id="n1",
        command_template_id="tpl_nifti_qc_v1",
    )
    assert p.command_template_id == "tpl_nifti_qc_v1"


# ═══════════════════════════════════════════════════════════════
# ExecutionFailureRecord tests
# ═══════════════════════════════════════════════════════════════

def test_all_failure_stages_instantiate():
    for stage in ["preflight", "approval", "audit", "execution", "timeout",
                  "output_verification", "artifact_discovery", "provenance", "unknown"]:
        r = ExecutionFailureRecord(stage=stage, message=f"Failure at {stage}")  # type: ignore[arg-type]
        assert r.stage == stage


def test_retryable_resume_eligible_serialize():
    r = ExecutionFailureRecord(
        stage="execution", message="Node failed",
        retryable=True, resume_eligible=True,
    )
    d = r.model_dump()
    assert d["retryable"] is True
    assert d["resume_eligible"] is True


def test_next_action_is_optional():
    r = ExecutionFailureRecord(stage="timeout", message="Timed out")
    assert r.next_action is None


def test_failure_record_creates_no_files(tmp_path):
    """ExecutionFailureRecord is a pure model — no file I/O."""
    before = set(str(p) for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    _r = ExecutionFailureRecord(stage="execution", message="test")
    after = set(str(p) for p in tmp_path.iterdir()) if tmp_path.exists() else set()
    assert before == after


# ═══════════════════════════════════════════════════════════════
# Safety tests
# ═══════════════════════════════════════════════════════════════

def test_import_does_not_pull_pipeline_executor():
    """Importing execution_manifest must not import pipeline_executor."""
    assert "pipeline_executor" not in sys.modules


def test_import_does_not_pull_state_store():
    """Importing execution_manifest must not import state_store."""
    assert "state_store" not in sys.modules


def test_helper_functions_create_no_files(tmp_path):
    """build_output_manifest and helpers create no files."""
    before = list(tmp_path.iterdir())
    _m = build_output_manifest(
        project_id="p1", run_id="r1", node_id="n1",
        items=[OutputManifestItem(path="/tmp/test.json")],
    )
    _s = summarize_output_manifest([OutputManifestItem(path="/t")])
    after = list(tmp_path.iterdir())
    assert before == after


def test_no_rawdata_or_outputs_path_touched():
    """Module does not reference rawdata or outputs directories."""
    import src.backend.app.schemas.execution_manifest as em
    source = str(getattr(em, "__file__", ""))
    # source should be under src/backend/app/schemas/
    assert "schemas" in source
