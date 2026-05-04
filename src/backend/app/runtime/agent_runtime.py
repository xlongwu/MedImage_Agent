from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.runtime.agent_plan import _load_project_config, create_agent_plan
from src.backend.app.runtime.hook_manager import (
    run_after_execute,
    run_before_execute,
    run_on_error,
)
from src.backend.app.runtime.pipeline_executor import run_pipeline
from src.backend.app.runtime.tool_registry import assert_tool_allowed


def run_orchestrator_plan(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> dict[str, Any]:
    try:
        assert_tool_allowed("pipeline.plan", approved=True)
        return create_agent_plan(
            agent_run_id=agent_run_id,
            project_config_path=project_config_path,
            pipeline_path=pipeline_path,
        )
    except Exception as exc:
        return run_on_error(exc)


def run_orchestrator_execute(
    agent_run_id: str,
    project_config_path: str,
    pipeline_path: str,
    plan_path: str,
    approved: bool,
) -> dict[str, Any]:
    try:
        assert_tool_allowed("pipeline.execute", approved=approved)

        project_config = _load_project_config(project_config_path)
        warnings = run_before_execute(
            project_config=project_config,
            plan_path=plan_path,
            approved=approved,
        )

        plan_file = Path(plan_path)
        plan = json.loads(plan_file.read_text(encoding="utf-8"))

        if plan.get("pipeline_path") != str(pipeline_path):
            warnings.append("Pipeline path differs from plan pipeline_path.")

        summary = run_pipeline(project_config_path, pipeline_path)
        warnings.extend(run_after_execute(summary))

        runtime = project_config.get("runtime", {})
        work_dir = runtime.get("work_dir", "./work")
        out_dir = Path(work_dir) / "agent_runs" / agent_run_id
        out_dir.mkdir(parents=True, exist_ok=True)

        pipeline_summary_path = (
            Path(work_dir)
            / "pipeline_runs"
            / str(summary.get("run_id", plan.get("run_id", agent_run_id)))
            / "summary.json"
        )

        agent_summary = {
            "ok": summary.get("status") in {"SUCCESS", "PARTIAL"},
            "agent_run_id": agent_run_id,
            "agent": "orchestrator",
            "mode": "EXECUTE",
            "approved": approved,
            "plan_path": str(plan_path),
            "pipeline_id": summary.get("pipeline_id"),
            "pipeline_status": summary.get("status"),
            "pipeline_summary_path": str(pipeline_summary_path),
            "outputs": summary.get("outputs", []),
            "metrics": summary.get("metrics", {}),
            "warnings": warnings,
            "errors": summary.get("errors", []),
        }

        agent_summary_path = out_dir / "agent_summary.json"
        agent_summary_path.write_text(
            json.dumps(agent_summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        agent_summary["agent_summary_path"] = str(agent_summary_path)

        return agent_summary

    except Exception as exc:
        return run_on_error(exc)
