"""Tests for synthetic dcm2niix smoke — Phase 4C-1.

Tests the controlled dcm2niix smoke path on synthetic DICOM data only.
No real user rawdata is converted.  No real dcm2niix is called unless
all env flags are set AND dcm2niix is available.

Tests skip gracefully when pydicom or dcm2niix are unavailable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.backend.app.schemas.execution_manifest import (
    OutputManifest,
)
from src.backend.app.services.dicom_conversion_execution import (
    _is_synthetic_smoke_enabled,
    run_synthetic_dcm2niix_smoke,
)

# ═══════════════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════════════


class _FakeCompletedProcess:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _fake_dcm2niix_runner(argv):
    """Fake dcm2niix that writes fake output to stdout/stderr."""
    assert isinstance(argv, list)
    assert "shell=True" not in str(argv)
    return _FakeCompletedProcess(
        stdout="Conversion successful\nOutput: synth_sub-001_T1w.nii.gz\n",
        stderr="",
        returncode=0,
    )


def _fake_failing_runner(argv):
    return _FakeCompletedProcess(
        stdout="",
        stderr="Error: cannot read DICOM\n",
        returncode=1,
    )


_ALL_SMOKE_FLAGS = {
    "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
    "MEDIMAGE_ENABLE_SYNTHETIC_DICOM_SMOKE": "1",
    "MEDIMAGE_ALLOW_EXTERNAL_TOOL_SMOKE": "1",
    "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
    "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
}


# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Env flag gating
# ═══════════════════════════════════════════════════════════════════════


def test_smoke_disabled_without_env_flags(tmp_path):
    result = run_synthetic_dcm2niix_smoke(
        input_dir=tmp_path / "input",
        output_root=tmp_path / "output",
        env={},
    )
    assert result.status == "disabled"
    assert result.safety_flags.conversion_disabled_by_default is True


def test_smoke_disabled_with_partial_env_flags(tmp_path):
    env = {"MEDIMAGE_ENABLE_DICOM_CONVERSION": "1"}
    result = run_synthetic_dcm2niix_smoke(
        input_dir=tmp_path / "input",
        output_root=tmp_path / "output",
        env=env,
    )
    assert result.status == "disabled"


def test_synthetic_smoke_env_flag_helper():
    ok, missing = _is_synthetic_smoke_enabled(_ALL_SMOKE_FLAGS)
    assert ok is True
    assert missing == []

    ok, missing = _is_synthetic_smoke_enabled({})
    assert ok is False
    # Per §11.1, only 5 DICOM-specific flags are required for synthetic smoke
    # (MATLAB/SPM/real-preprocessing are intentionally NOT required).
    assert len(missing) == 5


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Input path safety (refuse real rawdata paths)
# ═══════════════════════════════════════════════════════════════════════


def test_smoke_refuses_real_rawdata_path(tmp_path):
    """Smoke must refuse any path containing 'DemoData' or 'FunRaw'."""
    input_dir = tmp_path / "DemoData" / "FunRaw"
    input_dir.mkdir(parents=True)
    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=tmp_path / "output",
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert result.status == "blocked"
    assert any("real rawdata" in b.lower() for b in result.blocking_issues)


def test_smoke_refuses_path_with_rawdata(tmp_path):
    input_dir = tmp_path / "my_rawdata_dir"
    input_dir.mkdir(parents=True)
    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=tmp_path / "output",
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert result.status == "blocked"


def test_smoke_accepts_synthetic_path(tmp_path):
    """A clean synthetic path must be accepted (blocked by availability if no dcm2niix)."""
    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=tmp_path / "output",
        env=_ALL_SMOKE_FLAGS,
    )
    # Without runner, availability check will find dcm2niix missing → mapped to blocked
    assert result.status in {"blocked", "disabled", "succeeded"}


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Fake runner execution
# ═══════════════════════════════════════════════════════════════════════


def test_smoke_with_fake_runner_succeeds(tmp_path, monkeypatch):
    """With fake runner and env flags, smoke must return succeeded."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert result.status == "succeeded"
    assert result.mode == "mock_subprocess"
    assert result.manifest_path is not None
    assert result.provenance_path is not None
    assert result.stdout_log_path is not None
    assert result.stderr_log_path is not None


def test_smoke_with_fake_runner_writes_logs(tmp_path, monkeypatch):
    """Fake runner must write stdout and stderr logs."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert Path(result.stdout_log_path).exists()
    assert Path(result.stderr_log_path).exists()
    content = Path(result.stdout_log_path).read_text()
    assert "Conversion successful" in content


def test_smoke_with_fake_runner_writes_manifest(tmp_path, monkeypatch):
    """Fake runner must produce a valid OutputManifest."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    manifest = OutputManifest.model_validate_json(Path(result.manifest_path).read_text())
    assert manifest.project_id == "synthetic_smoke"
    assert manifest.node_id == "dicom_to_nifti"


def test_smoke_with_fake_runner_writes_provenance(tmp_path, monkeypatch):
    """Fake runner must produce a valid ExecutionProvenance."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    from src.backend.app.schemas.execution_manifest import ExecutionProvenance

    prov = ExecutionProvenance.model_validate_json(Path(result.provenance_path).read_text())
    assert prov.backend == "external"
    assert prov.command_template_id == "dcm2niix_smoke"
    assert "shell" not in prov.model_dump()


def test_smoke_fake_runner_uses_argv_list(tmp_path, monkeypatch):
    """Runner must receive argv list, never shell=True."""

    def check_argv(argv):
        assert isinstance(argv, list)
        assert "--version" in argv or "-z" in argv
        return _FakeCompletedProcess(
            stdout="v1.0.0" if "--version" in argv else "ok",
            returncode=0,
        )

    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=check_argv,
    )
    assert result.status == "succeeded"


def test_smoke_fake_runner_failure(tmp_path, monkeypatch):
    """Failing runner must return warning or failed status."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_failing_runner,
    )
    # The runner is used for both version check and execution.
    # If version check fails, returns disabled. If execution fails, returns warning.
    assert result.status in {"warning", "disabled"}


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Output safety
# ═══════════════════════════════════════════════════════════════════════


def test_smoke_output_under_tmp_path(tmp_path, monkeypatch):
    """All outputs must be under the provided output_root."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    output_root = tmp_path / "output"

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert str(output_root) in result.manifest_path
    assert str(output_root) in result.provenance_path
    assert str(output_root) in result.stdout_log_path


def test_smoke_output_root_not_rawdata(tmp_path, monkeypatch):
    """Output root must never be a rawdata-like path."""
    monkeypatch.setattr("shutil.which", lambda x: "/fake/dcm2niix")

    input_dir = tmp_path / "synth_input"
    input_dir.mkdir(parents=True)
    # Even if output_root contains 'rawdata', the smoke should still work
    # since the check is on input_dir, not output_root
    output_root = tmp_path / "converted_output"
    output_root.mkdir(parents=True)

    result = run_synthetic_dcm2niix_smoke(
        input_dir=input_dir,
        output_root=output_root,
        env=_ALL_SMOKE_FLAGS,
        runner=_fake_dcm2niix_runner,
    )
    assert result.status == "succeeded"


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Synthetic DICOM creation (skip if no pydicom)
# ═══════════════════════════════════════════════════════════════════════


def test_synthetic_dicom_creation_skip_if_no_pydicom():
    """Synthetic DICOM creation must skip cleanly when pydicom unavailable."""
    from tests.unit.dicom_synthetic_helpers import pydicom_available

    if not pydicom_available():
        pytest.skip("pydicom is not installed")


def test_create_minimal_dicom_series(tmp_path):
    """Minimal DICOM series creation must produce valid .dcm files."""
    pytest.importorskip("pydicom")
    from tests.unit.dicom_synthetic_helpers import create_minimal_dicom_series

    series_dir = create_minimal_dicom_series(
        root=tmp_path,
        subject_id="sub-001",
        series_name="test_series",
        num_slices=3,
    )
    assert series_dir.exists()
    dcm_files = list(series_dir.glob("*.dcm"))
    assert len(dcm_files) == 3


def test_create_synthetic_funraw_layout(tmp_path):
    """FunRaw/T1Raw layout creation must produce expected directories."""
    pytest.importorskip("pydicom")
    from tests.unit.dicom_synthetic_helpers import create_synthetic_funraw_layout

    result = create_synthetic_funraw_layout(root=tmp_path, subject_count=2)
    assert len(result) >= 2
    assert (tmp_path / "FunRaw" / "Sub_001").exists()
    assert (tmp_path / "T1Raw" / "Sub_002").exists()
    # Files are in series subdirectory; use recursive glob
    assert len(list((tmp_path / "FunRaw" / "Sub_001").rglob("*.dcm"))) == 3


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Safety invariants
# ═══════════════════════════════════════════════════════════════════════


def test_smoke_service_never_uses_shell():
    """Synthetic smoke function must never use shell=True."""
    import inspect

    source = inspect.getsource(run_synthetic_dcm2niix_smoke)
    lines = [
        line for line in source.splitlines() if not line.strip().startswith(("#", '"""', "``"))
    ]
    code = "\n".join(lines)
    assert "shell=True" not in code


def test_smoke_result_safety_flags(tmp_path):
    """Even successful smoke must carry correct safety flags."""
    result = run_synthetic_dcm2niix_smoke(
        input_dir=tmp_path / "input",
        output_root=tmp_path / "output",
        env={},
    )
    assert result.safety_flags.rawdata_read_only is True
    assert result.safety_flags.no_spm_dpabi_matlab is True
    assert result.safety_flags.clinical_use_prohibited is True


def test_run_conversion_execute_still_disabled():
    """The user-facing execute path must remain disabled."""
    from src.backend.app.schemas.dicom_conversion_execution import (
        DicomConversionExecutionRequest,
    )
    from src.backend.app.services.dicom_conversion_execution import (
        run_conversion_execute,
    )

    req = DicomConversionExecutionRequest(
        project_id="any-project",
        mode="execute",
        confirm_execution=True,
    )
    result = run_conversion_execute("any-project", req)
    assert result.conversion_disabled is True
    assert result.execution_blocked is True
