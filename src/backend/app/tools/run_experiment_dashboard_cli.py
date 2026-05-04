from __future__ import annotations

import json

from src.backend.app.tools.experiment_dashboard import build_experiment_dashboard


def main() -> int:
    result = build_experiment_dashboard()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
