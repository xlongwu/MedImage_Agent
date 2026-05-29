from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.runtime.hook_manager import run_after_plan, run_before_plan
from src.backend.app.runtime.scheduler import create_scheduler_plan
from src.backend.app.schemas.pipeline_schema import load_pipeline_yaml


def _load_project_config(path: str | Path) -> dict[str, Any]:
    """Load and validate a project config YAML file.

    Uses ProjectSettings.from_yaml() to validate critical fields (work_dir,
    log_dir, spm_dir, dpabi_dir) before returning the raw dict.  The returned
    dict is kept for backward compatibility with hook_manager, scheduler, and
    agent_runtime — they still expect plain dicts, not dataclass instances.
    """
    # ── structural validation (M1-T003) ──
    from src.backend.app.config import ProjectSettings  # noqa: E402

    ProjectSettings.from_yaml(path)  # raises on missing critical fields

    # ── return raw dict for backward compat ──
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError(
            "Missing dependency: PyYAML. Install with: pip install pyyaml"
        ) from exc

    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Project config not found: {p}")

    return yaml.safe_load(p.read_text(encoding="utf-8"))


def create_agent_plan(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> dict[str, Any]:
    project_config = _load_project_config(project_config_path)
    warnings = run_before_plan(project_config, pipeline_path)

    pipeline = load_pipeline_yaml(pipeline_path)
    runtime = project_config.get("runtime", {})
    work_dir = runtime.get("work_dir", "./work")

    out_dir = Path(work_dir) / "agent_runs" / agent_run_id
    out_dir.mkdir(parents=True, exist_ok=True)

    nodes = []
    expected_outputs: list[str] = []

    for node in pipeline.nodes:
        node_payload = {
            "id": node.id,
            "name": node.name,
            "backend": node.backend,
            "agent": node.agent,
            "parallel_level": node.parallel_level,
            "depends_on": node.depends_on,
            "outputs": node.outputs,
        }
        nodes.append(node_payload)
        expected_outputs.extend(node.outputs)

    plan = {
        "ok": True,
        "agent_run_id": agent_run_id,
        "agent": "orchestrator",
        "mode": "PLAN",
        "project_config_path": str(project_config_path),
        "pipeline_path": str(pipeline_path),
        "pipeline_id": pipeline.pipeline_id,
        "run_id": pipeline.execution.get("run_id", agent_run_id),
        "nodes_total": len(nodes),
        "nodes": nodes,
        "expected_outputs": expected_outputs,
        "requires_approval": True,
        "approved": False,
        "risk_summary": {
            "will_run_matlab": any("matlab" in node.backend for node in pipeline.nodes),
            "will_write_derivatives": any(
                "outputs/derivatives/" in output or "./derivatives/" in output
                for output in expected_outputs
            ),
            "will_modify_rawdata": False,
            "will_delete_files": False,
        },
        "warnings": warnings,
        "errors": [],
    }

    scheduler_plan = create_scheduler_plan(pipeline, project_config)
    plan["scheduler_plan"] = {
        "mode": scheduler_plan["mode"],
        "max_workers": scheduler_plan["max_workers"],
        "matlab_max_workers": scheduler_plan["matlab_max_workers"],
    }
    plan["warnings"].extend(scheduler_plan.get("warnings", []))
    plan["errors"].extend(scheduler_plan.get("errors", []))
    if not scheduler_plan.get("ok"):
        plan["ok"] = False

    warnings.extend(run_after_plan(plan))
    plan["warnings"] = warnings

    plan_path = out_dir / "plan.json"
    plan_path.write_text(
        json.dumps(plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    plan["plan_path"] = str(plan_path)

    return plan
