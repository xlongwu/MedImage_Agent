from __future__ import annotations

import json
import sys

from src.backend.app.tools.experiment_tracker import (
    build_run_index,
    compare_experiment_runs,
)


def main() -> int:
    args = sys.argv[1:]

    if "--compare" in args:
        experiment_id = "latest_comparison"
        run_ids = [arg for arg in args if arg != "--compare"]
        result = compare_experiment_runs(
            experiment_id=experiment_id,
            run_ids=run_ids,
        )
    else:
        result = build_run_index()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
