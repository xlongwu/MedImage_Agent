from __future__ import annotations

import sys

from src.backend.app.tools.cli_utils import emit_json, emit_json_result
from src.backend.app.tools.artifact_browser import build_artifact_index, preview_artifact


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--preview":
        if len(args) < 2:
            emit_json({"ok": False, "errors": ["Missing path after --preview"]})
            return 2
        result = preview_artifact(args[1])
    else:
        result = build_artifact_index()

    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
