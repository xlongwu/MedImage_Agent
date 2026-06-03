from __future__ import annotations

import sys
from pathlib import Path

from src.backend.app.runtime.agent_runtime import run_orchestrator_execute
from src.backend.app.tools.cli_utils import emit_json_result


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    project_config = Path(args[0]) if len(args) > 0 else Path("examples/project_config_dataset.yaml")
    pipeline = Path(args[1]) if len(args) > 1 else Path("examples/pipeline_subject_preprocess.yaml")
    agent_run_id = args[2] if len(args) > 2 else "agent_run_001"

    plan_path = Path("outputs/work") / "agent_runs" / agent_run_id / "plan.json"

    result = run_orchestrator_execute(
        agent_run_id=agent_run_id,
        project_config_path=str(project_config),
        pipeline_path=str(pipeline),
        plan_path=str(plan_path),
        approved=approved,
    )

    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
