from __future__ import annotations

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.release_readiness import build_release_readiness


def main() -> int:
    result = build_release_readiness()
    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
