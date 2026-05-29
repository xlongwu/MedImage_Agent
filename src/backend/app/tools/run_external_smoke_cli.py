from __future__ import annotations

import argparse
import json

from src.backend.app.tools.external_smoke import run_external_smoke


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate or run audited SPM/DPABI external smoke checks.")
    parser.add_argument("--target", choices=["spm", "dpabi", "all"], default="all")
    parser.add_argument("--mode", choices=["preflight", "manual_package", "approved_smoke"], default="manual_package")
    parser.add_argument("--config", default="examples/project_config.yaml")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--approved-by", default="local-user")
    parser.add_argument("--dpabi-function", default="y_Smooth")
    args = parser.parse_args()

    try:
        result = run_external_smoke(
            target=args.target,
            mode=args.mode,
            config_path=args.config,
            approve=args.approve,
            approved_by=args.approved_by,
            dpabi_function=args.dpabi_function,
        )
    except Exception as exc:
        result = {
            "ok": False,
            "target": args.target,
            "mode": args.mode,
            "checks": [],
            "external_tool_results": [],
            "artifacts": {},
            "warnings": [],
            "errors": [str(exc)],
            "next_actions": ["Fix the configuration or environment and rerun the smoke command."],
        }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
