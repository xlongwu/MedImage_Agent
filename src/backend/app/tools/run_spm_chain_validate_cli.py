"""SPM chain validation CLI — run full 6-node SPM preprocessing chain."""
from __future__ import annotations

import sys

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.spm_chain_validator import validate_spm_chain


def main() -> int:
    mode = sys.argv[1] if len(sys.argv) > 1 else "dry_run"
    approved = "--approved" in sys.argv

    result = validate_spm_chain(
        subject_id="sub-001",
        mode=mode,
        approved=approved,
        stop_on_failure=True,
    )
    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
