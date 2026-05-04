from __future__ import annotations

import json
import sys
from pathlib import Path

from src.backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    project_config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config.yaml")
    pipeline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_mvp.yaml")

    if not project_config_path.exists():
        print(f"Project config file not found: {project_config_path}")
        return 1

    if not pipeline_path.exists():
        print(f"Pipeline file not found: {pipeline_path}")
        return 1

    result = run_pipeline(
        project_config_path=project_config_path,
        pipeline_path=pipeline_path,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))

    status = result.get("status")
    if status == "SUCCESS":
        return 0
    elif status == "INVALID":
        return 1
    else:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
