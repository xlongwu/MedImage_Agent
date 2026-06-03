from __future__ import annotations

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.deployment_profile import build_deployment_profile


def main() -> int:
    result = build_deployment_profile()
    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
