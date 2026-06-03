from __future__ import annotations

import sys

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.validation_runner import run_validation_suite


def main() -> int:
    args = set(sys.argv[1:])

    include_frontend = "--frontend" in args
    include_api = "--no-api" not in args
    include_gpu_optional = "--no-gpu" not in args

    result = run_validation_suite(
        include_api=include_api,
        include_frontend=include_frontend,
        include_gpu_optional=include_gpu_optional,
    )

    return emit_json_result(result, failure_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
