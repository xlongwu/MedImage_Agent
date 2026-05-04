from __future__ import annotations

import json
import sys

from src.backend.app.runtime.error_diagnoser import diagnose_run


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run_subject_preprocess_001"

    result = diagnose_run(run_id=run_id)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
