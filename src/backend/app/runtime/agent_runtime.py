from __future__ import annotations

from typing import Any

from src.backend.app.core.exceptions import SafetyError
from src.backend.app.runtime.agent_plan import create_agent_plan
from src.backend.app.runtime.hook_manager import (
    run_on_error,
)
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
    return run_on_error(
        SafetyError(
            "EXECUTION_CONTRACT_REQUIRED: use /api/plans/execute-reviewed",
            code="EXECUTION_CONTRACT_REQUIRED",
        )
    )
