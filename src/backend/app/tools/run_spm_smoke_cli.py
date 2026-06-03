from __future__ import annotations

import sys
from pathlib import Path

from src.backend.app.runtime.state_store import (
    determine_status_from_result,
    now_iso,
    write_node_state,
)
from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.spm_runner import run_spm_smoke_test


def main() -> int:
    try:
        import yaml
    except ImportError:
        print("Missing dependency: PyYAML. Install with: pip install pyyaml")
        return 1

    config_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("examples/project_config.yaml")

    if not config_path.exists():
        print(f"Config file not found: {config_path}")
        return 1

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))

    matlab_command = config["runtime"]["matlab_command"]
    spm_dir = config["third_party"]["spm_dir"]
    work_dir = config["runtime"]["work_dir"]
    log_dir = config["runtime"]["log_dir"]

    run_id = "run_spm_smoke_001"
    node_id = "spm_smoke_test"

    started_at = now_iso()

    result = run_spm_smoke_test(
        matlab_command=matlab_command,
        spm_dir=spm_dir,
        work_dir=work_dir,
        log_dir=log_dir,
        matlab_script_dir="./matlab",
    )

    ended_at = now_iso()
    status = determine_status_from_result(result)

    state_path = write_node_state(
        run_id=run_id,
        node_id=node_id,
        subject="project",
        status=status,
        started_at=started_at,
        ended_at=ended_at,
        result=result,
        work_dir=work_dir,
    )

    result["state_path"] = str(state_path)

    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
