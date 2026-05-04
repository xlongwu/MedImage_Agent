from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.runtime.agent_plan import _load_project_config
from backend.app.runtime.scheduler import create_scheduler_plan
from backend.app.schemas.pipeline_schema import load_pipeline_yaml


def main() -> int:
    project_config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pipeline_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("examples/pipeline_subject_preprocess_parallel.yaml")

    project_config = _load_project_config(project_config_path)
    pipeline = load_pipeline_yaml(pipeline_path)

    result = create_scheduler_plan(pipeline, project_config)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
