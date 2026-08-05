"""Tests for agent_plan using ProjectSettings validation (M1-T005a).

All tests use tmp_path to avoid polluting real outputs/work.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from src.backend.app.runtime.agent_plan import _load_project_config, create_agent_plan

# ── Helpers ──


def _write_project_config(
    tmp_path: Path,
    runtime_work_dir: str | None = None,
    runtime_log_dir: str | None = None,
    spm_dir: str | None = "./third_party/spm12",
    dpabi_dir: str | None = "./third_party/DPABI",
    **extra_runtime,
) -> Path:
    """Write a minimal valid project_config.yaml into tmp_path.

    Returns the path to the written file.
    """
    runtime: dict = {}
    if runtime_work_dir is not None:
        runtime["work_dir"] = runtime_work_dir
    if runtime_log_dir is not None:
        runtime["log_dir"] = runtime_log_dir
    runtime.update(extra_runtime)

    data: dict = {
        "project": {"name": "test", "root_dir": "."},
        "third_party": {},
        "runtime": runtime,
        "safety": {"rawdata_readonly": True},
    }
    if spm_dir is not None:
        data["third_party"]["spm_dir"] = spm_dir
    if dpabi_dir is not None:
        data["third_party"]["dpabi_dir"] = dpabi_dir

    p = tmp_path / "project_config.yaml"
    p.write_text(yaml.safe_dump(data), encoding="utf-8")
    return p


def _write_minimal_pipeline(tmp_path: Path, run_id: str = "run_test") -> Path:
    """Write a minimal pipeline YAML with one node."""
    p = tmp_path / "pipeline.yaml"
    p.write_text(
        yaml.safe_dump(
            {
                "pipeline_id": "test_pipeline",
                "version": "0.1.0",
                "modality": "test",
                "description": "minimal pipeline for plan tests",
                "execution": {"run_id": run_id},
                "nodes": [
                    {
                        "id": "data_inspection",
                        "name": "Data Inspection",
                        "agent": "data-inspector",
                        "backend": "python",
                        "depends_on": [],
                        "inputs": [],
                        "outputs": ["./work/dataset_index/dataset_index.json"],
                        "params": {},
                        "parallel_level": "project",
                        "gpu_supported": False,
                        "cache": False,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return p


# ── Tests: _load_project_config ──


def test_load_project_config_returns_dict(tmp_path: Path):
    """_load_project_config must still return a plain dict."""
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(tmp_path / "work"), runtime_log_dir=str(tmp_path / "logs")
    )
    result = _load_project_config(cfg)
    assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
    assert result["runtime"]["work_dir"] == str(tmp_path / "work")


def test_load_project_config_validates_work_dir(tmp_path: Path):
    """Missing runtime.work_dir → ValueError (not silent default)."""
    cfg = _write_project_config(tmp_path, runtime_log_dir=str(tmp_path / "logs"))
    with pytest.raises(ValueError, match="Missing required field 'runtime.work_dir'"):
        _load_project_config(cfg)


def test_load_project_config_validates_log_dir(tmp_path: Path):
    """Missing runtime.log_dir → ValueError."""
    cfg = _write_project_config(tmp_path, runtime_work_dir=str(tmp_path / "work"))
    with pytest.raises(ValueError, match="Missing required field 'runtime.log_dir'"):
        _load_project_config(cfg)


def test_load_project_config_validates_spm_dir(tmp_path: Path):
    """Missing third_party.spm_dir → ValueError."""
    cfg = _write_project_config(
        tmp_path,
        runtime_work_dir=str(tmp_path / "work"),
        runtime_log_dir=str(tmp_path / "logs"),
        spm_dir=None,
    )
    with pytest.raises(ValueError, match="Missing required field 'third_party.spm_dir'"):
        _load_project_config(cfg)


def test_load_project_config_validates_dpabi_dir(tmp_path: Path):
    """Missing third_party.dpabi_dir → ValueError."""
    cfg = _write_project_config(
        tmp_path,
        runtime_work_dir=str(tmp_path / "work"),
        runtime_log_dir=str(tmp_path / "logs"),
        dpabi_dir=None,
    )
    with pytest.raises(ValueError, match="Missing required field 'third_party.dpabi_dir'"):
        _load_project_config(cfg)


def test_load_project_config_file_not_found():
    with pytest.raises(FileNotFoundError, match="Project config file not found"):
        _load_project_config("nonexistent_dir/config.yaml")


# ── Tests: create_agent_plan ──

PLAN_KEY_FIELDS = [
    "ok",
    "agent_run_id",
    "agent",
    "mode",
    "project_config_path",
    "pipeline_path",
    "pipeline_id",
    "run_id",
    "nodes_total",
    "nodes",
    "expected_outputs",
    "requires_approval",
    "approved",
    "risk_summary",
    "scheduler_plan",
    "warnings",
    "errors",
    "plan_path",
]


def test_valid_config_generates_plan(tmp_path: Path):
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(tmp_path / "work"), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_001",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    assert plan["ok"] is True
    assert plan["mode"] == "PLAN"
    assert plan["agent_run_id"] == "agent_test_001"
    assert plan["pipeline_id"] == "test_pipeline"
    assert plan["requires_approval"] is True
    assert plan["approved"] is False


def test_plan_output_has_all_key_fields(tmp_path: Path):
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(tmp_path / "work"), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_002",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    for field in PLAN_KEY_FIELDS:
        assert field in plan, f"Missing key field in plan: {field}"


def test_plan_does_not_execute_pipeline(tmp_path: Path):
    """Calling create_agent_plan must NOT execute pipeline nodes.

    Verifies:
    - Only plan.json is written (under work_dir/agent_runs/).
    - No pipeline_runs/ directory created.
    - No node state files generated.
    """
    work_dir = tmp_path / "work"
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(work_dir), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_noexec",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    # plan.json must exist
    plan_path = Path(plan["plan_path"])
    assert plan_path.is_file(), f"plan.json not written to {plan_path}"

    # pipeline_runs/ must NOT exist
    pipeline_runs_dir = work_dir / "pipeline_runs"
    assert not pipeline_runs_dir.exists(), (
        f"pipeline_runs/ should not exist after PLAN-only call, "
        f"but found: {list(pipeline_runs_dir.iterdir()) if pipeline_runs_dir.is_dir() else 'N/A'}"
    )

    # No node state files outside agent_runs/
    agent_runs_dir = work_dir / "agent_runs"
    state_files = list(work_dir.rglob("*.json"))
    for sf in state_files:
        assert str(agent_runs_dir) in str(sf), f"Unexpected file outside agent_runs/: {sf}"


def test_scheduler_plan_included(tmp_path: Path):
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(tmp_path / "work"), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_sched",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    assert "scheduler_plan" in plan
    assert "mode" in plan["scheduler_plan"]
    assert "max_workers" in plan["scheduler_plan"]


def test_risk_summary_no_matlab_for_python_pipeline(tmp_path: Path):
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(tmp_path / "work"), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_risk",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    assert plan["risk_summary"]["will_run_matlab"] is False  # python-only node
    assert plan["risk_summary"]["will_modify_rawdata"] is False


def test_plan_file_written_inside_tmp_path(tmp_path: Path):
    """plan.json must be written inside the configured work_dir, not cwd."""
    work_dir = tmp_path / "test_work"
    cfg = _write_project_config(
        tmp_path, runtime_work_dir=str(work_dir), runtime_log_dir=str(tmp_path / "logs")
    )
    pipeline = _write_minimal_pipeline(tmp_path)

    plan = create_agent_plan(
        agent_run_id="agent_test_path",
        project_config_path=str(cfg),
        pipeline_path=str(pipeline),
    )

    plan_path = Path(plan["plan_path"])
    assert str(work_dir) in str(plan_path.resolve()), (
        f"plan.json should be under {work_dir}, got {plan_path}"
    )
    assert plan_path.name == "plan.json"
