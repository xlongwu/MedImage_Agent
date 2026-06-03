from __future__ import annotations

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.experiment_dashboard import build_experiment_dashboard


def main() -> int:
    result = build_experiment_dashboard()
    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
