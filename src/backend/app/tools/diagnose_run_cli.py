from __future__ import annotations

import sys

from src.backend.app.runtime.error_diagnoser import diagnose_run
from src.backend.app.tools.cli_utils import emit_json_result


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run_subject_preprocess_001"

    result = diagnose_run(run_id=run_id)

    return emit_json_result(result, failure_code=1)


if __name__ == "__main__":
    raise SystemExit(main())
