from __future__ import annotations

import json
import sys

from backend.app.tools.validation_runner import run_validation_suite


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

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
