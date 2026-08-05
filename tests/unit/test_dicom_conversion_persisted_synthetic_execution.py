"""Tests for synthetic persisted-package conversion execution — Phase 4F-0.

Tests the controlled dcm2niix smoke path that consumes a persisted approval
package.  No real user rawdata is converted.  All tests use fake runners
and monkeypatched env flags.
"""

from __future__ import annotations

import json
from pathlib import Path


class _FakeCompletedProcess:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _fake_runner(argv):
    assert isinstance(argv, list)
    if "--version" in argv:
        return _FakeCompletedProcess(stdout="dcm2niix v1.0.0\n", returncode=0)
    return _FakeCompletedProcess(stdout="Conversion ok\n", returncode=0)


def _fake_failing_runner(argv):
    return _FakeCompletedProcess(stderr="Error\n", returncode=1)


_ALL_FLAGS = {
    "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
    "MEDIMAGE_ALLOW_PERSISTED_SYNTHETIC_CONVERSION": "1",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
}


def _make_persisted_package(tmp_path: Path, run_id: str = "conv-test") -> str:
    """Create a synthetic persisted review package and return project_dir."""
    project_dir = str(tmp_path / "project")
    run_dir = Path(project_dir) / "conversion_runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "logs").mkdir()

    # approval_record.json — fully approved
    approval = {
        "approval_id": "test",
        "project_id": "test",
        "status": "approved",
        "approved": True,
        "approved_by": "tester",
        "mappings_reviewed": True,
        "output_root_confirmed": True,
        "output_root_under_project": True,
        "output_root_not_rawdata": True,
        "overwrite_policy": "fail_if_exists",
        "rawdata_read_only_confirmed": True,
        "command_templates_reviewed": True,
        "no_shell_string_confirmed": True,
        "dcm2niix_availability_confirmed": True,
        "env_flags_confirmed": True,
        "rollback_policy_acknowledged": True,
        "clinical_use_prohibited_acknowledged": True,
        "external_tool_acknowledgement": True,
        "risk_acknowledgement": True,
        "confirm_execution": True,
    }
    (run_dir / "approval_record.json").write_text(json.dumps(approval))
    (run_dir / "preflight_snapshot.json").write_text(json.dumps({"status": "ready"}))
    (run_dir / "mapping_snapshot.json").write_text(
        json.dumps(
            {
                "mappings": [
                    {
                        "subject_id": "sub-001",
                        "source_path": str(tmp_path / "synth_input"),
                        "modality": "func",
                    }
                ]
            }
        )
    )
    (run_dir / "command_templates.json").write_text(
        json.dumps(
            {
                "templates": [
                    {
                        "executable": "dcm2niix",
                        "compress": "y",
                        "bids_sidecar": True,
                        "input_dir": str(tmp_path / "synth_input"),
                        "output_dir": str(run_dir),
                        "filename_pattern": "test",
                    }
                ]
            }
        )
    )
    (run_dir / "planned_output_manifest.json").write_text("{}")
    (run_dir / "planned_execution_provenance.json").write_text("{}")
    (run_dir / "logs" / "stdout.log").write_text("")
    (run_dir / "logs" / "stderr.log").write_text("")
    (run_dir / "README.md").write_text("# test\n")
    return project_dir


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Disabled without env flags
# ═══════════════════════════════════════════════════════════════════════


def test_disabled_without_env_flags(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    result = run_synthetic_conversion_from_persisted_package("test", "any", env={})
    assert result.status == "disabled"
    assert result.safety_flags.conversion_disabled_by_default is True


def test_disabled_with_partial_env_flags(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    env = {"MEDIMAGE_ENABLE_DICOM_CONVERSION": "1"}
    result = run_synthetic_conversion_from_persisted_package("test", "any", env=env)
    assert result.status == "disabled"


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Missing approval package blocks
# ═══════════════════════════════════════════════════════════════════════


def test_missing_approval_record_blocks(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    project_dir = str(tmp_path / "project")
    run_dir = Path(project_dir) / "conversion_runs" / "conv-test"
    run_dir.mkdir(parents=True)
    # Don't create approval_record.json

    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package("test", "conv-test", env=env)
    assert result.status == "blocked"


def test_incomplete_approval_blocks(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    project_dir = str(tmp_path / "project")
    run_dir = Path(project_dir) / "conversion_runs" / "conv-test"
    run_dir.mkdir(parents=True)
    (run_dir / "approval_record.json").write_text(json.dumps({"approved": False}))
    (run_dir / "preflight_snapshot.json").write_text("{}")
    (run_dir / "mapping_snapshot.json").write_text("{}")
    (run_dir / "command_templates.json").write_text("{}")

    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package("test", "conv-test", env=env)
    assert result.status == "blocked"


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Real rawdata path refused
# ═══════════════════════════════════════════════════════════════════════


def test_refuses_real_rawdata_path(tmp_path):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    project_dir = _make_persisted_package(tmp_path, "conv-raw")
    # Inject a mapping with a rawdata-like source path
    run_dir = Path(project_dir) / "conversion_runs" / "conv-raw"
    (run_dir / "mapping_snapshot.json").write_text(
        json.dumps({"mappings": [{"source_path": "/data/DemoData/FunRaw/Sub_001"}]})
    )

    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package("test", "conv-raw", env=env)
    assert result.status == "blocked"
    # Blocking issues should mention rawdata or synthetic-only
    all_text = " ".join(b.lower() for b in result.blocking_issues)
    assert "rawdata" in all_text or "synthetic" in all_text or "demodata" in all_text


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Fake runner execution
# ═══════════════════════════════════════════════════════════════════════


def test_fake_runner_succeeds(tmp_path, monkeypatch):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    project_dir = _make_persisted_package(tmp_path)
    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        runner=_fake_runner,
    )
    # With fake runner + env flags, should succeed or at minimum not be blocked/disabled
    assert result.status in {"succeeded", "warning"}
    assert result.manifest_path is not None


def test_fake_runner_writes_manifest(tmp_path, monkeypatch):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    project_dir = _make_persisted_package(tmp_path)
    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        runner=_fake_runner,
    )
    assert result.status in {"succeeded", "warning"}, (
        f"status={result.status} blocking={result.blocking_issues}"
    )
    assert result.manifest_path is not None
    assert Path(result.manifest_path).exists()
    from src.backend.app.schemas.execution_manifest import OutputManifest

    manifest = OutputManifest.model_validate_json(Path(result.manifest_path).read_text())
    assert manifest.project_id == "test"


def test_fake_runner_writes_provenance(tmp_path, monkeypatch):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    project_dir = _make_persisted_package(tmp_path)
    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        runner=_fake_runner,
    )
    assert result.status in {"succeeded", "warning"}, f"status={result.status}"
    assert result.provenance_path is not None
    assert Path(result.provenance_path).exists()
    from src.backend.app.schemas.execution_manifest import ExecutionProvenance

    prov = ExecutionProvenance.model_validate_json(Path(result.provenance_path).read_text())
    assert prov.backend == "external"


def test_fake_runner_writes_logs(tmp_path, monkeypatch):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    project_dir = _make_persisted_package(tmp_path)
    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        runner=_fake_runner,
    )
    assert result.status in {"succeeded", "warning"}, f"status={result.status}"
    assert result.stdout_log_path is not None
    assert Path(result.stdout_log_path).exists()
    assert Path(result.stderr_log_path).exists()


def test_fake_runner_uses_argv_list(tmp_path, monkeypatch):
    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    def check_argv(argv):
        assert isinstance(argv, list), f"Expected list, got {type(argv)}"
        if "--version" in argv:
            return _FakeCompletedProcess(stdout="dcm2niix v1.0.0\n", returncode=0)
        assert "dcm2niix" in argv
        return _FakeCompletedProcess(stdout="ok", returncode=0)

    project_dir = _make_persisted_package(tmp_path)
    env = {**_ALL_FLAGS, "MEDIMAGE_PROJECT_DIR": project_dir}
    result = run_synthetic_conversion_from_persisted_package(
        "test",
        "conv-test",
        env=env,
        runner=check_argv,
    )
    assert result.status in {"succeeded", "warning"}, (
        f"status={result.status} blocking={result.blocking_issues}"
    )


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Safety invariants
# ═══════════════════════════════════════════════════════════════════════


def test_no_shell_used():
    import inspect

    from src.backend.app.services.dicom_conversion_execution import (
        run_synthetic_conversion_from_persisted_package,
    )

    source = inspect.getsource(run_synthetic_conversion_from_persisted_package)
    # Check no actual subprocess imports or usage patterns
    assert "import subprocess" not in source
    assert "from subprocess" not in source


def test_user_conversion_still_disabled():
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    result = run_conversion_execute("test", DicomConversionExecutionRequest())
    assert result.conversion_disabled is True
    assert result.execution_blocked is True
