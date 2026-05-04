from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _find_function(capabilities: dict[str, Any], name: str) -> dict[str, Any] | None:
    for item in capabilities.get("functions", []):
        if item.get("name") == name:
            return item
    return None


def write_dpabi_wrapper_scaffold(
    capabilities_path: str,
    work_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    cap_path = Path(capabilities_path)
    capabilities = _read_json(cap_path)

    if not capabilities:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_scaffold",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid capabilities JSON: {cap_path}"],
        }

    out_dir = Path(work_dir) / "dpabi"
    report_out_dir = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out_dir.mkdir(parents=True, exist_ok=True)

    config_path = out_dir / "dpabi_wrapper_config_template.yaml"
    dry_run_path = out_dir / "dpabi_dry_run_plan.json"
    report_path = report_out_dir / "dpabi_capability_report.md"

    functions = capabilities.get("functions", [])
    found = [item for item in functions if item.get("exists")]
    missing = [item for item in functions if not item.get("exists")]

    dpabi_entry = _find_function(capabilities, "DPABI")
    dparsf_run = _find_function(capabilities, "DPARSF_run")
    dparsfa_run = _find_function(capabilities, "DPARSFA_run")

    config_text = f"""# DPABI Wrapper Config Template
# This is a scaffold only. It does not execute DPABI automatically.

dpabi:
  capabilities_json: "{cap_path}"
  entrypoint_found: {str(bool(dpabi_entry and dpabi_entry.get("exists"))).lower()}
  entrypoint: "DPABI"
  dry_run_only: true

input:
  rawdata_dir: "./examples/synthetic_bids/rawdata"
  dataset_index: "./work/dataset_index/dataset_index.json"

output:
  work_dir: "./work/dpabi"
  derivatives_dir: "./derivatives/dpabi"
  report_dir: "./reports/dpabi"

execution:
  mode: "dry_run"
  require_manual_review: true
  allow_gui: false
  allow_full_preprocessing: false

candidate_wrappers:
  DPARSF_run:
    available: {str(bool(dparsf_run and dparsf_run.get("exists"))).lower()}
  DPARSFA_run:
    available: {str(bool(dparsfa_run and dparsfa_run.get("exists"))).lower()}

safety:
  modify_rawdata: false
  modify_dpabi_source: false
  delete_files: false
"""
    config_path.write_text(config_text, encoding="utf-8")

    dry_run_plan = {
        "ok": True,
        "mode": "DRY_RUN",
        "capabilities_json": str(cap_path),
        "entrypoint_found": bool(dpabi_entry and dpabi_entry.get("exists")),
        "candidate_wrappers": {
            "DPARSF_run": bool(dparsf_run and dparsf_run.get("exists")),
            "DPARSFA_run": bool(dparsfa_run and dparsfa_run.get("exists")),
        },
        "steps": [
            {
                "step_id": "dpabi_001",
                "action": "validate_dpabi_path",
                "status": "planned",
            },
            {
                "step_id": "dpabi_002",
                "action": "review_wrapper_config_template",
                "status": "requires_human_review",
            },
            {
                "step_id": "dpabi_003",
                "action": "map_dataset_index_to_dpabi_expected_layout",
                "status": "future_work",
            },
            {
                "step_id": "dpabi_004",
                "action": "prepare_dpabi_batch_config",
                "status": "future_work",
            },
        ],
        "safety": {
            "full_preprocessing_executed": False,
            "rawdata_modified": False,
            "dpabi_source_modified": False,
        },
        "warnings": warnings,
        "errors": errors,
    }

    dry_run_path.write_text(
        json.dumps(dry_run_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Capability Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Capability JSON: `{cap_path}`")
    lines.append(f"- Total checked: {len(functions)}")
    lines.append(f"- Found: {len(found)}")
    lines.append(f"- Missing: {len(missing)}")
    lines.append(f"- DPABI entrypoint found: {bool(dpabi_entry and dpabi_entry.get('exists'))}")
    lines.append("")
    lines.append("## Found Functions")
    lines.append("")
    if found:
        lines.append("| Function | Category | Path |")
        lines.append("|---|---|---|")
        for item in found:
            lines.append(
                f"| {item.get('name')} | {item.get('category')} | `{item.get('which_path')}` |"
            )
    else:
        lines.append("No known DPABI functions found.")
    lines.append("")
    lines.append("## Missing Functions")
    lines.append("")
    if missing:
        for item in missing:
            lines.append(f"- {item.get('name')} ({item.get('category')})")
    else:
        lines.append("No missing functions from the candidate list.")
    lines.append("")
    lines.append("## Dry-run Plan")
    lines.append("")
    lines.append(f"- Dry-run plan: `{dry_run_path}`")
    lines.append(f"- Config template: `{config_path}`")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This step did not run full DPABI preprocessing and did not modify rawdata or DPABI source code.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_wrapper_scaffold",
        "backend": "python",
        "outputs": [str(config_path), str(dry_run_path), str(report_path)],
        "metrics": {
            "functions_total": len(functions),
            "functions_found": len(found),
            "functions_missing": len(missing),
            "dpabi_entrypoint_found": bool(dpabi_entry and dpabi_entry.get("exists")),
        },
        "warnings": warnings,
        "errors": errors,
    }
