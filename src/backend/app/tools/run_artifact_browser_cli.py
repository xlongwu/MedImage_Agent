from __future__ import annotations

import json
import sys

from src.backend.app.tools.artifact_browser import build_artifact_index, preview_artifact


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--preview":
        if len(args) < 2:
            print(json.dumps({"ok": False, "errors": ["Missing path after --preview"]}, indent=2))
            return 2
        result = preview_artifact(args[1])
    else:
        result = build_artifact_index()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
