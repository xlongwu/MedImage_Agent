"""Tests for routes._load_project_config using ProjectSettings (M1-T005c).

All tests use tmp_path.  No real endpoints or MATLAB/SPM/DPABI are invoked.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.backend.app.api.routes import _load_project_config
from src.backend.app.core.exceptions import ConfigError

# ── Helpers ──


def _write_config(
    tmp_path: Path,
    *,
    work_dir: str | None = None,
    log_dir: str | None = None,
    spm_dir: str | None = "./spm",
    dpabi_dir: str | None = "./dpabi",
) -> Path:
    """Write a minimal project_config.yaml into tmp_path.

    Pass None for a critical field to omit it entirely.
    """
    runtime: dict = {"matlab_command": "matlab"}
    if work_dir is not None:
        runtime["work_dir"] = work_dir
    if log_dir is not None:
        runtime["log_dir"] = log_dir

    third_party: dict = {}
    if spm_dir is not None:
        third_party["spm_dir"] = spm_dir
    if dpabi_dir is not None:
        third_party["dpabi_dir"] = dpabi_dir

    data: dict = {
        "project": {"name": "test"},
        "runtime": runtime,
        "third_party": third_party,
        "safety": {"rawdata_readonly": True},
    }
    p = tmp_path / "project_config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


# ── Happy path ──


def test_returns_dict(tmp_path: Path):
    cfg = _write_config(tmp_path, work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"))
    result = _load_project_config(str(cfg))
    assert isinstance(result, dict)
    assert result["runtime"]["work_dir"] == str(tmp_path / "work")


# ── Missing critical fields → ConfigError(400) ──


def test_missing_work_dir_raises_http_400(tmp_path: Path):
    cfg = _write_config(tmp_path, log_dir=str(tmp_path / "logs"))
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config(str(cfg))
    assert exc_info.value.status_code == 400
    assert "work_dir" in exc_info.value.message


def test_missing_log_dir_raises_http_400(tmp_path: Path):
    cfg = _write_config(tmp_path, work_dir=str(tmp_path / "work"))
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config(str(cfg))
    assert exc_info.value.status_code == 400
    assert "log_dir" in exc_info.value.message


def test_missing_spm_dir_raises_http_400(tmp_path: Path):
    cfg = _write_config(
        tmp_path, work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), spm_dir=None
    )
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config(str(cfg))
    assert exc_info.value.status_code == 400
    assert "spm_dir" in exc_info.value.message


def test_missing_dpabi_dir_raises_http_400(tmp_path: Path):
    cfg = _write_config(
        tmp_path, work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"), dpabi_dir=None
    )
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config(str(cfg))
    assert exc_info.value.status_code == 400
    assert "dpabi_dir" in exc_info.value.message


# ── File not found → ConfigError(400) ──


def test_file_not_found_raises_http_400():
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config("nonexistent/config.yaml")
    assert exc_info.value.status_code == 400
    assert "not found" in exc_info.value.message.lower()


# ── Invalid YAML → ConfigError(400) ──


def test_invalid_yaml_raises_http_400(tmp_path: Path):
    p = tmp_path / "bad.yaml"
    p.write_text("runtime: [unclosed\n  work_dir: x\n", encoding="utf-8")
    with pytest.raises(ConfigError) as exc_info:
        _load_project_config(str(p))
    assert exc_info.value.status_code == 400


# ── No real execution ──


def test_no_real_matlab_spm_dpabi_called(tmp_path: Path):
    """_load_project_config is a pure read function — no tools invoked."""
    cfg = _write_config(tmp_path, work_dir=str(tmp_path / "work"), log_dir=str(tmp_path / "logs"))
    result = _load_project_config(str(cfg))
    assert isinstance(result, dict)
    # Verify no files were written by the load call
    # (only the config YAML itself should exist, written by _write_config)
    config_file = cfg
    all_files = list(tmp_path.rglob("*"))
    yaml_files = [f for f in all_files if f.suffix in (".yaml", ".yml")]
    assert len(yaml_files) == 1 and yaml_files[0] == config_file, (
        f"Unexpected files written: {[str(f) for f in all_files if f != config_file]}"
    )
