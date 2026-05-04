from __future__ import annotations

import json
import sys
from pathlib import Path

from src.backend.app.runtime.retry_runtime import (
    dry_run_retry_plan,
    execute_retry_plan,
)


def main() -> int:
    args = sys.argv[1:]
    approved = "--approve" in args
    args = [arg for arg in args if arg != "--approve"]

    run_id = args[0] if len(args) > 0 else "run_subject_preprocess_001"
    project_config = Path(args[1]) if len(args) > 1 else Path("examples/project_config_dataset.yaml")
    retry_run_id = args[2] if len(args) > 2 else None

    if approved:
        result = execute_retry_plan(
            run_id=run_id,
            project_config_path=str(project_config),
            retry_run_id=retry_run_id,
            approved=True,
        )
    else:
        result = dry_run_retry_plan(
            run_id=run_id,
            retry_run_id=retry_run_id,
        )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
