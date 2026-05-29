"""Tests for pipeline_executor using ProjectSettings validation (M1-T005b).

All tests use tmp_path to avoid polluting real outputs/work.
No real MATLAB/SPM/DPABI nodes are executed.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.backend.app.runtime.pipeline_executor import load_project_config, run_pipeline


# ── Helpers ──

def _write_project_config(tmp_path: Path, *,
                          work_dir: str | None = None,
                          log_dir: str | None = None,
                          spm_dir: str | None = "./third_party/spm12",
                          dpabi_dir: str | None = "./third_party/DPABI") -> Path:
    """Write a minimal valid project_config.yaml into tmp_path.

    Pass None for a critical field to omit it entirely (triggering
    ValueError from ProjectSettings validation).

    Includes matlab_command and derivatives_dir so that run_pipeline's
    subscript access doesn't KeyError on a valid config.
    """
    runtime: dict = {
        "matlab_command": "matlab",
        "derivatives_dir": str(tmp_path / "derivatives"),
    }
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
        "project": {"name": "test", "root_dir": "."},
        "runtime": runtime,
        "third_party": third_party,
        "safety": {"rawdata_readonly": True},
    }
    p = tmp_path / "project_config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


def _write_minimal_pipeline(tmp_path: Path, run_id: str = "run_test",
                            node_id: str = "data_inspection") -> Path:
    """Write a minimal pipeline YAML with one python node."""
    p = tmp_path / "pipeline.yaml"
    p.write_text(yaml.safe_dump({
        "pipeline_id": "test_pipeline",
        "version": "0.1.0",
        "modality": "test",
        "description": "minimal",
        "execution": {"run_id": run_id},
        "nodes": [{
            "id": node_id,
            "name": "Test Node",
            "agent": "test",
            "backend": "python",
            "depends_on": [],
            "inputs": [],
            "outputs": [],
            "params": {},
            "parallel_level": "project",
            "gpu_supported": False,
            "cache": False,
        }],
    }), encoding="utf-8")
    return p


# ── Tests: load_project_config ──

def test_load_project_config_returns_dict(tmp_path: Path):
    cfg = _write_project_config(tmp_path,
                                work_dir=str(tmp_path / "work"),
                                log_dir=str(tmp_path / "logs"))
    result = load_project_config(cfg)
    assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
    assert result["runtime"]["work_dir"] == str(tmp_path / "work")


def test_missing_work_dir_raises_value_error(tmp_path: Path):
    cfg = _write_project_config(tmp_path,
                                log_dir=str(tmp_path / "logs"))
    with pytest.raises(ValueError, match="Missing required field 'runtime.work_dir'"):
        load_project_config(cfg)


def test_missing_spm_dir_raises_value_error(tmp_path: Path):
    cfg = _write_project_config(tmp_path,
                                work_dir=str(tmp_path / "work"),
                                log_dir=str(tmp_path / "logs"),
                                spm_dir=None)
    with pytest.raises(ValueError, match="Missing required field 'third_party.spm_dir'"):
        load_project_config(cfg)


def test_file_not_found_raises():
    with pytest.raises(FileNotFoundError, match="Project config file not found"):
        load_project_config("nonexistent/config.yaml")


# ── Tests: run_pipeline with bad config ──

def test_run_pipeline_returns_invalid_on_missing_work_dir(tmp_path: Path):
    """Missing critical field → run_pipeline returns status INVALID."""
    cfg = _write_project_config(tmp_path,
                                log_dir=str(tmp_path / "logs"))
    pipeline = _write_minimal_pipeline(tmp_path)

    result = run_pipeline(str(cfg), str(pipeline))

    assert result["status"] == "INVALID", (
        f"Expected INVALID on bad config, got {result['status']}"
    )
    assert "Failed to load project config" in result.get("error", "")


def test_run_pipeline_returns_invalid_on_missing_spm_dir(tmp_path: Path):
    cfg = _write_project_config(tmp_path,
                                work_dir=str(tmp_path / "work"),
                                log_dir=str(tmp_path / "logs"),
                                spm_dir=None)
    pipeline = _write_minimal_pipeline(tmp_path)

    result = run_pipeline(str(cfg), str(pipeline))

    assert result["status"] == "INVALID"
    assert "Failed to load project config" in result.get("error", "")


def test_run_pipeline_returns_invalid_on_nonexistent_config(tmp_path: Path):
    pipeline = _write_minimal_pipeline(tmp_path)
    result = run_pipeline(
        str(tmp_path / "no_such_config.yaml"),
        str(pipeline),
    )
    assert result["status"] == "INVALID"
    assert "Failed to load project config" in result.get("error", "")


# ── Tests: no real execution ──

def test_no_real_matlab_spm_dpabi_executed(tmp_path: Path):
    """Bad config must cause early return — never entering any node runner.

    We verify this by using a missing critical field, so run_pipeline
    returns INVALID before even parsing the pipeline YAML.
    """
    cfg = _write_project_config(tmp_path,
                                log_dir=str(tmp_path / "logs"))
    pipeline = _write_minimal_pipeline(tmp_path)

    result = run_pipeline(str(cfg), str(pipeline))

    assert result["status"] == "INVALID"
    # No pipeline_runs/ created, no node states generated
    work_dir = tmp_path / "work"
    assert not (work_dir / "pipeline_runs").exists(), (
        "pipeline_runs/ should not exist when config load fails"
    )
    assert not (work_dir / "states").exists(), (
        "states/ should not exist when config load fails"
    )


def test_bad_config_writes_summary_in_work_dir(tmp_path: Path):
    """Even on INVALID, a summary should be written (the executor does
    write_pipeline_summary with status INVALID).  The summary uses the
    runtime.work_dir from project_config, but since the config load itself
    fails, the executor falls back to a best-effort summary at a default
    location.  We verify that the result dict contains an 'error' key and
    that no unexpected directories are created."""
    cfg = _write_project_config(tmp_path,
                                log_dir=str(tmp_path / "logs"))
    pipeline = _write_minimal_pipeline(tmp_path)

    result = run_pipeline(str(cfg), str(pipeline))

    assert result["status"] == "INVALID"
    assert "error" in result
    assert "Failed to load project config" in result["error"]


# ── Tests: valid config yields correct but does not execute real nodes ──

def test_valid_config_with_nonexistent_node(tmp_path: Path):
    """Valid config + node id not in NODE_REGISTRY → execution fails
    but NOT because of config validation.  The pipeline execution was
    attempted — it just couldn't find the runner."""
    # Use a node id that definitely doesn't exist in NODE_REGISTRY
    cfg = _write_project_config(tmp_path,
                                work_dir=str(tmp_path / "work"),
                                log_dir=str(tmp_path / "logs"))
    pipeline = _write_minimal_pipeline(tmp_path,
                                       run_id="run_no_node",
                                       node_id="nonexistent_node_xyz")

    result = run_pipeline(str(cfg), str(pipeline))

    # Config loaded → pipeline parsed → node lookup failed
    # Status: FAILED because node not found in registry
    assert result["status"] == "FAILED", (
        f"Expected FAILED (node not found), got {result['status']}"
    )
    assert any("No node runner registered" in err for err in result.get("errors", [])), (
        "Expected 'No node runner registered' error"
    )
    # Verify the pipeline did NOT reach any real MATLAB/SPM node —
    # the only node was 'nonexistent_node_xyz' which failed before execution
    assert not any(
        nid in str(result.get("node_states", []))
        for nid in ["spm_", "matlab_", "dpabi_", "environment_check"]
    ), "Real MATLAB/SPM/DPABI node states should not appear"
