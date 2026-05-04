from __future__ import annotations

import json
import sys
from pathlib import Path

from backend.app.tools.matlab_runner import run_matlab_check


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
    dpabi_dir = config["third_party"]["dpabi_dir"]
    work_dir = config["runtime"]["work_dir"]
    log_dir = config["runtime"]["log_dir"]

    output_json = str(Path(work_dir) / "environment_check.json")

    result = run_matlab_check(
        matlab_command=matlab_command,
        spm_dir=spm_dir,
        dpabi_dir=dpabi_dir,
        output_json=output_json,
        log_dir=log_dir,
        matlab_script_dir="./matlab",
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
