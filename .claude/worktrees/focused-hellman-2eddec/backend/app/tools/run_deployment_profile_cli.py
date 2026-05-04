from __future__ import annotations

import json
import sys

from backend.app.tools.deployment_profile import build_deployment_profile


def main() -> int:
    result = build_deployment_profile()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
