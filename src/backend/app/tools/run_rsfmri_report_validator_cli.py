from __future__ import annotations

import json
import sys
from pathlib import Path

from src.backend.app.runtime.pipeline_executor import run_pipeline


def main() -> int:
    pc = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config_dataset.yaml")
    pl = (
        Path(sys.argv[2])
        if len(sys.argv) > 2
        else Path("examples/pipeline_rsfmri_report_validator.yaml")
    )
    s = run_pipeline(pc, pl)
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0 if s.get("status") == "SUCCESS" else (1 if s.get("status") == "INVALID" else 2)


if __name__ == "__main__":
    raise SystemExit(main())
