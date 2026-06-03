from __future__ import annotations

import sys
from pathlib import Path

from src.backend.app.runtime.background_review import run_background_review
from src.backend.app.tools.cli_utils import emit_json_result


def main() -> int:
    project_config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    agent_run_id = sys.argv[2] if len(sys.argv) > 2 else "agent_run_001"
    agent_summary = sys.argv[3] if len(sys.argv) > 3 else None

    result = run_background_review(
        agent_run_id=agent_run_id,
        project_config_path=str(project_config),
        agent_summary_path=agent_summary,
    )

    return emit_json_result(result, failure_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
