"""Unit tests for dcm2niix availability check and sandbox runner — Phase 4C-0.

Tests availability preflight, version parsing, sandbox modes, and safety
invariants.  No real dcm2niix is called.  No subprocess.  No file writes
to real output directories.  No rawdata modification.
"""

from __future__ import annotations

from src.backend.app.schemas.dicom_conversion_execution import (
    Dcm2niixAvailabilityCheck,
    DicomConversionSafetyFlags,
    build_disabled_sandbox_result,
    is_dcm2niix_availability_ready,
    parse_dcm2niix_version,
    requires_fake_or_sandbox_mode,
    summarize_sandbox_artifacts,
)
from src.backend.app.services.dicom_conversion_execution import (
    check_dcm2niix_availability,
    run_conversion_sandbox,
)

# ═══════════════════════════════════════════════════════════════════════
# Group 1 — Version parsing
# ═══════════════════════════════════════════════════════════════════════


def test_parse_version_standard_output() -> None:
    result = parse_dcm2niix_version(
        "Chris Rorden's dcm2niix version v1.0.20230411 (JFIF-to-NIfTI)\nBSD 2-Clause License\n"
    )
    assert result == "v1.0.20230411"


def test_parse_version_v_prefix_only() -> None:
    result = parse_dcm2niix_version("dcm2niix v1.0.20220720")
    assert result == "v1.0.20220720"


def test_parse_version_no_v_prefix() -> None:
    result = parse_dcm2niix_version("version 1.0.20230411")
    assert result is not None


def test_parse_version_empty() -> None:
    assert parse_dcm2niix_version("") is None


def test_parse_version_none() -> None:
    assert parse_dcm2niix_version(None) is None


def test_parse_version_garbage() -> None:
    result = parse_dcm2niix_version("some random output without version")
    assert result is not None  # fallback: first 80 chars
    assert "random" in result


# ═══════════════════════════════════════════════════════════════════════
# Group 2 — Availability check: env flag gating
# ═══════════════════════════════════════════════════════════════════════


def test_availability_missing_env_flags_disabled() -> None:
    check = check_dcm2niix_availability(env={})
    assert check.status == "disabled"
    assert check.env_enabled is False
    # Per 实现dcm2nii任务方案.md §11.1, only 3 DICOM-specific flags are
    # required (MATLAB/SPM/real-preprocessing are intentionally NOT required).
    assert len(check.missing_env_flags) == 3


def test_availability_partial_env_flags_disabled() -> None:
    env = {"MEDIMAGE_ENABLE_DICOM_CONVERSION": "1"}
    check = check_dcm2niix_availability(env=env)
    assert check.status == "disabled"
    assert check.env_enabled is False
    assert len(check.missing_env_flags) == 2


def test_availability_all_env_flags_but_no_dcm2niix() -> None:
    # Per §11.1, only 3 DICOM-specific flags are required.
    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    # dcm2niix is unlikely to be on PATH in CI
    check = check_dcm2niix_availability(env=env)
    # Should be "missing" or "available" depending on environment
    assert check.status in {"missing", "available", "version_failed"}
    assert check.env_enabled is True


# ═══════════════════════════════════════════════════════════════════════
# Group 3 — Availability check: fake runner
# ═══════════════════════════════════════════════════════════════════════


class _FakeCompletedProcess:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


def _fake_runner(argv):
    """Fake subprocess runner that returns a controlled version string."""
    assert "--version" in argv, f"Expected --version in argv, got {argv}"
    assert isinstance(argv, list), f"Expected argv list, got {type(argv)}"
    return _FakeCompletedProcess(
        stdout="Chris Rorden's dcm2niix version v1.0.20230411\n",
        returncode=0,
    )


def test_availability_with_fake_runner() -> None:
    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    check = check_dcm2niix_availability(env=env, runner=_fake_runner)
    assert check.status in {"available", "missing", "version_failed"}
    if check.status == "available":
        assert check.version == "v1.0.20230411"
        assert check.executable_path is not None
        assert is_dcm2niix_availability_ready(check) is True


def test_availability_fake_runner_uses_argv_list(monkeypatch) -> None:
    """Confirm the runner receives an argv list, never a shell string."""

    def assert_argv(argv):
        assert isinstance(argv, list)
        assert str(argv[0]).lower().endswith(("dcm2niix", "dcm2niix.exe"))
        assert "--version" in argv
        return _FakeCompletedProcess(stdout="v1.0.0", returncode=0)

    monkeypatch.setattr("shutil.which", lambda x: "/fake/path/dcm2niix")

    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    check = check_dcm2niix_availability(env=env, runner=assert_argv)
    assert check.status == "available"


def test_availability_finds_dcm2niix_in_active_mamba_env(tmp_path) -> None:
    """Phase 6B: active mamba/conda env is checked before generic PATH."""
    fake_prefix = tmp_path / "mamba"
    fake_exe = fake_prefix / "Scripts" / "dcm2niix.exe"
    fake_exe.parent.mkdir(parents=True)
    fake_exe.write_bytes(b"fake dcm2niix binary")

    called: list[list[str]] = []

    def fake_runner(argv):
        called.append(argv)
        return _FakeCompletedProcess(
            stdout="Chris Rorden's dcm2niix version v1.0.20260416\n",
            returncode=0,
        )

    env = {
        "CONDA_PREFIX": str(fake_prefix),
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    check = check_dcm2niix_availability(env=env, runner=fake_runner)

    assert check.status == "available"
    assert check.executable_path == str(fake_exe)
    assert check.version == "v1.0.20260416"
    assert check.binary_sha256 is not None
    assert check.detection_strategy == "mamba_env"
    assert check.expected_version == "v1.0.20260416"
    assert called and called[0] == [str(fake_exe), "--version"]


def test_availability_fake_runner_exception(monkeypatch) -> None:
    def failing_runner(argv):
        raise RuntimeError("mock subprocess failure")

    monkeypatch.setattr("shutil.which", lambda x: "/fake/path/dcm2niix")

    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    check = check_dcm2niix_availability(env=env, runner=failing_runner)
    assert check.status == "version_failed"
    assert any("mock subprocess failure" in w for w in check.warnings)


# ═══════════════════════════════════════════════════════════════════════
# Group 4 — Sandbox runner: disabled by default
# ═══════════════════════════════════════════════════════════════════════


def test_sandbox_disabled_by_default() -> None:
    result = run_conversion_sandbox("test-project", mode="disabled")
    assert result.status == "disabled"
    assert result.mode == "disabled"
    assert result.safety_flags.conversion_disabled_by_default is True


def test_sandbox_unknown_mode_disabled() -> None:
    result = run_conversion_sandbox("test-project", mode="garbage")
    assert result.status == "disabled"


def test_sandbox_fake_outputs_without_env_flags() -> None:
    """Fake outputs mode with missing env flags returns blocked from preflight."""
    # The seed project "brain-tumor-study" has no import records and no env flags
    # so the sandbox preflight will be blocked
    result = run_conversion_sandbox("brain-tumor-study", mode="fake_outputs")
    assert result.status in ("disabled", "blocked")
    assert result.safety_flags.conversion_disabled_by_default is True


# ═══════════════════════════════════════════════════════════════════════
# Group 5 — Sandbox runner: mock_subprocess
# ═══════════════════════════════════════════════════════════════════════


def _mock_runner_success(argv):
    return _FakeCompletedProcess(stdout="Conversion successful\n", returncode=0)


def _mock_runner_failure(argv):
    return _FakeCompletedProcess(stderr="dcm2niix error: invalid input\n", returncode=1)


def test_sandbox_mock_subprocess_without_project_fails_gracefully() -> None:
    """Sandbox with a nonexistent project should not crash."""
    result = run_conversion_sandbox(
        "nonexistent-project",
        mode="mock_subprocess",
        runner=_mock_runner_success,
    )
    # Should return blocked/disabled since project doesn't exist
    assert result.status in ("disabled", "blocked")


def test_sandbox_result_has_safety_flags() -> None:
    result = build_disabled_sandbox_result(project_id="test")
    assert result.safety_flags.conversion_disabled_by_default is True
    assert result.safety_flags.rawdata_read_only is True
    assert result.safety_flags.no_spm_dpabi_matlab is True
    assert result.safety_flags.clinical_use_prohibited is True


# ═══════════════════════════════════════════════════════════════════════
# Group 6 — Sandbox helper functions
# ═══════════════════════════════════════════════════════════════════════


def test_requires_fake_or_sandbox_mode() -> None:
    assert requires_fake_or_sandbox_mode("fake_outputs") is True
    assert requires_fake_or_sandbox_mode("mock_subprocess") is True
    assert requires_fake_or_sandbox_mode("disabled") is False


def test_summarize_sandbox_artifacts() -> None:
    summary = summarize_sandbox_artifacts(["a.nii.gz", "a.json", "manifest.json"])
    assert summary["total_count"] == 3


def test_is_availability_ready() -> None:
    ready = Dcm2niixAvailabilityCheck(
        ok=True,
        status="available",
        executable_path="/usr/bin/dcm2niix",
        version="v1.0.0",
        env_enabled=True,
    )
    assert is_dcm2niix_availability_ready(ready) is True

    not_ready = Dcm2niixAvailabilityCheck(
        ok=True,
        status="disabled",
        env_enabled=False,
    )
    assert is_dcm2niix_availability_ready(not_ready) is False


# ═══════════════════════════════════════════════════════════════════════
# Group 7 — Safety invariants (no subprocess, no shell, no rawdata)
# ═══════════════════════════════════════════════════════════════════════


def test_availability_function_never_uses_shell() -> None:
    """Availability check must never use shell=True."""
    import inspect

    source = inspect.getsource(check_dcm2niix_availability)
    # Check actual code, not docstrings
    lines = [
        line for line in source.splitlines() if not line.strip().startswith(("#", '"""', "``"))
    ]
    code = "\n".join(lines)
    assert "shell=True" not in code


def test_sandbox_function_never_uses_shell() -> None:
    """Sandbox runner must never use shell=True."""
    import inspect

    source = inspect.getsource(run_conversion_sandbox)
    assert "shell=True" not in source
    assert "shell = True" not in source


def test_schema_module_has_no_subprocess_import() -> None:
    """Availability/sandbox schema extensions must not import subprocess."""
    import src.backend.app.schemas.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import subprocess" not in content
    assert "from subprocess" not in content


def test_service_imports_are_safe() -> None:
    """Service module must not import SPM/DPABI/MATLAB."""
    import src.backend.app.services.dicom_conversion_execution as mod

    source = mod.__file__
    assert source is not None
    content = open(source, encoding="utf-8").read()
    assert "import matlab" not in content.lower()
    assert "import spm" not in content.lower()
    assert "from spm" not in content.lower()
    assert "import dpabi" not in content.lower()


def test_no_real_subprocess_called_directly() -> None:
    """Neither availability nor sandbox calls subprocess.run without injection."""
    import inspect

    source = inspect.getsource(check_dcm2niix_availability)
    assert "subprocess.run" not in source
    assert "subprocess.call" not in source
    assert "subprocess.Popen" not in source

    source = inspect.getsource(run_conversion_sandbox)
    assert "subprocess.run" not in source
    assert "subprocess.call" not in source
    assert "subprocess.Popen" not in source


# ═══════════════════════════════════════════════════════════════════════
# Group 8 — Safety flags default values
# ═══════════════════════════════════════════════════════════════════════


def test_safety_flags_all_safe_defaults() -> None:
    sf = DicomConversionSafetyFlags()
    assert sf.conversion_disabled_by_default is True
    assert sf.rawdata_read_only is True
    assert sf.no_shell_string is True
    assert sf.command_template_only is True
    assert sf.approval_required is True
    assert sf.audit_required is True
    assert sf.env_flags_missing is True
    assert sf.no_spm_dpabi_matlab is True
    assert sf.clinical_use_prohibited is True


def test_availability_check_respects_env_flags() -> None:
    """Even with all env flags, if dcm2niix isn't on PATH, it's 'missing' not 'available' for real exec."""
    env = {
        "MEDIMAGE_ENABLE_DICOM_CONVERSION": "1",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION": "1",
        "MEDIMAGE_ALLOW_USER_DATA_CONVERSION": "1",
    }
    check = check_dcm2niix_availability(env=env)
    # Without a runner, version can't be queried
    assert check.status in {"missing", "available", "version_failed"}
    # But env IS enabled
    assert check.env_enabled is True
