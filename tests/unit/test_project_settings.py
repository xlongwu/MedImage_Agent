"""Tests for ProjectSettings — unified project config loader."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from src.backend.app.config import ProjectSettings
from src.backend.app.config.settings import RuntimeSettings, SafetySettings, ThirdPartySettings


# ── Helpers ──

def _write_yaml(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ── Happy path: load from real YAML files ──

def test_load_from_dataset_yaml():
    """Load from the full project_config_dataset.yaml and verify all fields."""
    settings = ProjectSettings.from_yaml("examples/project_config_dataset.yaml")

    assert isinstance(settings, ProjectSettings)
    assert isinstance(settings.runtime, RuntimeSettings)
    assert isinstance(settings.third_party, ThirdPartySettings)
    assert isinstance(settings.safety, SafetySettings)

    # Runtime
    assert settings.runtime.work_dir == "./work"
    assert settings.runtime.log_dir == "./logs"
    assert settings.runtime.derivatives_dir == "./derivatives"
    assert settings.runtime.report_dir == "./reports"
    assert settings.runtime.matlab_command == "matlab"

    # Third-party
    assert settings.third_party.spm_dir == "./third_party/spm12"
    assert settings.third_party.dpabi_dir == "./third_party/DPABI_V8.2_240510"

    # Safety
    assert settings.safety.rawdata_readonly is True
    assert settings.safety.allow_overwrite_derivatives is False
    assert settings.safety.require_confirmation is True

    # Source path
    assert "project_config_dataset.yaml" in settings.source_path


def test_load_from_mvp_yaml():
    """Load from the smaller project_config.yaml (missing derivatives_dir)."""
    settings = ProjectSettings.from_yaml("examples/project_config.yaml")

    # Optional fields use defaults
    assert settings.runtime.derivatives_dir == "./derivatives"
    assert settings.runtime.report_dir == "./reports"

    # Critical fields present
    assert settings.runtime.work_dir == "./work"
    assert settings.runtime.log_dir == "./logs"
    assert settings.third_party.spm_dir == "./third_party/spm12"


# ── Error handling ──

def test_file_not_found():
    with pytest.raises(FileNotFoundError, match="Project config file not found"):
        ProjectSettings.from_yaml("nonexistent/config.yaml")


def test_invalid_yaml_syntax(tmp_path):
    """Malformed YAML should raise ValueError, not yaml.YAMLError."""
    p = _write_yaml(tmp_path / "bad.yaml", "runtime: [unclosed\n  work_dir: ./work\n")
    with pytest.raises(ValueError, match="Invalid YAML"):
        ProjectSettings.from_yaml(p)


def test_yaml_is_not_dict(tmp_path):
    """YAML that parses to a list or scalar should raise ValueError."""
    p = _write_yaml(tmp_path / "list.yaml", "- item1\n- item2\n")
    with pytest.raises(ValueError, match="must be a mapping"):
        ProjectSettings.from_yaml(p)

    p2 = _write_yaml(tmp_path / "string.yaml", "just a string\n")
    with pytest.raises(ValueError, match="must be a mapping"):
        ProjectSettings.from_yaml(p2)


def test_missing_critical_runtime_work_dir(tmp_path):
    p = _write_yaml(
        tmp_path / "no_work_dir.yaml",
        "runtime:\n  log_dir: ./logs\nthird_party:\n  spm_dir: ./spm\n  dpabi_dir: ./dpabi\n",
    )
    with pytest.raises(ValueError, match="Missing required field 'runtime.work_dir'"):
        ProjectSettings.from_yaml(p)


def test_missing_critical_runtime_log_dir(tmp_path):
    p = _write_yaml(
        tmp_path / "no_log_dir.yaml",
        "runtime:\n  work_dir: ./work\nthird_party:\n  spm_dir: ./spm\n  dpabi_dir: ./dpabi\n",
    )
    with pytest.raises(ValueError, match="Missing required field 'runtime.log_dir'"):
        ProjectSettings.from_yaml(p)


def test_missing_critical_spm_dir(tmp_path):
    p = _write_yaml(
        tmp_path / "no_spm_dir.yaml",
        "runtime:\n  work_dir: ./work\n  log_dir: ./logs\nthird_party:\n  dpabi_dir: ./dpabi\n",
    )
    with pytest.raises(ValueError, match="Missing required field 'third_party.spm_dir'"):
        ProjectSettings.from_yaml(p)


def test_missing_critical_dpabi_dir(tmp_path):
    p = _write_yaml(
        tmp_path / "no_dpabi_dir.yaml",
        "runtime:\n  work_dir: ./work\n  log_dir: ./logs\nthird_party:\n  spm_dir: ./spm\n",
    )
    with pytest.raises(ValueError, match="Missing required field 'third_party.dpabi_dir'"):
        ProjectSettings.from_yaml(p)


# ── Default values for optional fields ──

def test_defaults_minimal_yaml(tmp_path):
    """Only critical fields present — all optional fields use safe defaults."""
    p = _write_yaml(
        tmp_path / "minimal.yaml",
        "runtime:\n  work_dir: ./work\n  log_dir: ./logs\n"
        "third_party:\n  spm_dir: ./spm\n  dpabi_dir: ./dpabi\n",
    )
    settings = ProjectSettings.from_yaml(p)

    assert settings.runtime.derivatives_dir == "./derivatives"
    assert settings.runtime.report_dir == "./reports"
    assert settings.runtime.matlab_command == "matlab"
    assert settings.safety.rawdata_readonly is True
    assert settings.safety.allow_overwrite_derivatives is False
    assert settings.safety.require_confirmation is True


def test_safety_require_confirmation_compat(tmp_path):
    """Both require_confirmation and require_confirmation_for_matlab_run should work."""
    # New-style naming
    p1 = _write_yaml(
        tmp_path / "new_style.yaml",
        "runtime:\n  work_dir: ./w\n  log_dir: ./l\n"
        "third_party:\n  spm_dir: ./s\n  dpabi_dir: ./d\n"
        "safety:\n  require_confirmation: false\n",
    )
    s1 = ProjectSettings.from_yaml(p1)
    assert s1.safety.require_confirmation is False

    # Old-style naming (from existing project_config YAMLs)
    p2 = _write_yaml(
        tmp_path / "old_style.yaml",
        "runtime:\n  work_dir: ./w\n  log_dir: ./l\n"
        "third_party:\n  spm_dir: ./s\n  dpabi_dir: ./d\n"
        "safety:\n  require_confirmation_for_matlab_run: false\n",
    )
    s2 = ProjectSettings.from_yaml(p2)
    assert s2.safety.require_confirmation is False

    # Neither present → default True
    p3 = _write_yaml(
        tmp_path / "none.yaml",
        "runtime:\n  work_dir: ./w\n  log_dir: ./l\n"
        "third_party:\n  spm_dir: ./s\n  dpabi_dir: ./d\n",
    )
    s3 = ProjectSettings.from_yaml(p3)
    assert s3.safety.require_confirmation is True


# ── Source path ──

def test_source_path_recorded(tmp_path):
    p = _write_yaml(
        tmp_path / "src.yaml",
        "runtime:\n  work_dir: ./w\n  log_dir: ./l\n"
        "third_party:\n  spm_dir: ./s\n  dpabi_dir: ./d\n",
    )
    settings = ProjectSettings.from_yaml(p)
    assert str(p.resolve()) in settings.source_path or p.name in settings.source_path


# ── No side effects ──

def test_does_not_write_files(tmp_path):
    """Loading config must not create or modify any files."""
    # Create a clean config YAML
    p = _write_yaml(
        tmp_path / "cfg.yaml",
        "runtime:\n  work_dir: ./w\n  log_dir: ./l\n"
        "third_party:\n  spm_dir: ./s\n  dpabi_dir: ./d\n",
    )
    # Snapshot directory contents before loading
    before = set()
    for root, _dirs, files in os.walk(tmp_path):
        for f in files:
            before.add(str(Path(root) / f))

    ProjectSettings.from_yaml(p)

    after = set()
    for root, _dirs, files in os.walk(tmp_path):
        for f in files:
            after.add(str(Path(root) / f))

    new_files = after - before
    assert new_files == set(), f"from_yaml() wrote unexpected files: {new_files}"


# ── Integration: check with the real repo files ──

def test_load_from_repo_configs():
    """Both real config files load without error."""
    s1 = ProjectSettings.from_yaml("examples/project_config.yaml")
    s2 = ProjectSettings.from_yaml("examples/project_config_dataset.yaml")
    assert s1.runtime.work_dir is not None
    assert s2.runtime.work_dir is not None
