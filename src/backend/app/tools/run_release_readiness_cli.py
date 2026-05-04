from __future__ import annotations

import json
import sys

from src.backend.app.tools.release_readiness import build_release_readiness


def main() -> int:
    result = build_release_readiness()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
