from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.app.tools.dpabi_param_schema import (
    validate_dpabi_params,
    write_dpabi_parameter_schema,
    write_dpabi_params_review_template,
)


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def create_dpabi_run_plan(
    work_dir: str,
    report_dir: str,
    capabilities_path: str = "./work/dpabi/dpabi_capabilities.json",
    manifest_path: str = "./work/dpabi/dpabi_input_manifest.json",
    preflight_path: str = "./work/dpabi/dpabi_preflight_report.json",
    params_path: str = "./work/dpabi/dpabi_params_review.yaml",
) -> dict[str, Any]:
    warnings: list[str] = []
    blocking_errors: list[str] = []

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    schema_result = write_dpabi_parameter_schema(work_dir)

    params_file = Path(params_path)
    if not params_file.exists():
        template_result = write_dpabi_params_review_template(work_dir)
        params_path = template_result["params_path"]

    params_validation = validate_dpabi_params(params_path=params_path, work_dir=work_dir)

    capabilities = _read_json(Path(capabilities_path))
    manifest = _read_json(Path(manifest_path))
    preflight = _read_json(Path(preflight_path))

    if not capabilities:
        blocking_errors.append(f"Missing capabilities JSON: {capabilities_path}")

    if not manifest:
        blocking_errors.append(f"Missing input manifest: {manifest_path}")

    if not preflight:
        blocking_errors.append(f"Missing preflight report: {preflight_path}")

    if preflight and preflight.get("status") == "FAIL":
        blocking_errors.append("DPABI preflight status is FAIL.")

    if not params_validation.get("ok"):
        blocking_errors.extend(params_validation.get("errors", []))

    warnings.extend(params_validation.get("warnings", []))

    subjects_ready = 0
    if manifest:
        subjects_ready = int(manifest.get("subjects_ready", 0) or 0)

    if subjects_ready <= 0:
        blocking_errors.append("No subjects are ready for DPABI run plan.")

    capability_summary = capabilities.get("summary", {}) if capabilities else {}
    dpabi_entrypoint_found = bool(capability_summary.get("dpabi_entrypoint_found"))

    if not dpabi_entrypoint_found:
        warnings.append("DPABI entrypoint was not found. Future execution may be blocked.")

    status = "READY_FOR_REVIEW"
    if blocking_errors:
        status = "BLOCKED"
    elif warnings:
        status = "WARNING"

    planned_steps = [
        {
            "step_id": "dpabi_plan_001",
            "action": "review_params",
            "status": "required",
            "input": params_path,
        },
        {
            "step_id": "dpabi_plan_002",
            "action": "review_preflight",
            "status": "required",
            "input": preflight_path,
        },
        {
            "step_id": "dpabi_plan_003",
            "action": "review_subject_manifest",
            "status": "required",
            "input": manifest_path,
        },
        {
            "step_id": "dpabi_plan_004",
            "action": "future_approved_dpabi_execution",
            "status": "not_executed",
            "requires_approval": True,
        },
    ]

    run_plan = {
        "ok": status in {"READY_FOR_REVIEW", "WARNING"},
        "node_id": "dpabi_run_plan",
        "backend": "python",
        "mode": "PLAN_ONLY",
        "status": status,
        "requires_approval": True,
        "approved": False,
        "execution_allowed": False,
        "capabilities_path": capabilities_path,
        "manifest_path": manifest_path,
        "preflight_path": preflight_path,
        "params_path": params_path,
        "params_validation_path": params_validation.get("validation_path"),
        "schema_path": schema_result.get("schema_path"),
        "subjects_ready": subjects_ready,
        "dpabi_entrypoint_found": dpabi_entrypoint_found,
        "planned_steps": planned_steps,
        "blocking_errors": blocking_errors,
        "warnings": warnings,
        "errors": blocking_errors,
        "safety": {
            "full_dpabi_executed": False,
            "rawdata_modified": False,
            "dpabi_source_modified": False,
            "files_deleted": False,
        },
    }

    run_plan_path = out_dir / "dpabi_run_plan.json"
    report_path = report_out / "dpabi_run_plan_report.md"

    run_plan_path.write_text(json.dumps(run_plan, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    lines.append("# DPABI Run Plan Report")
    lines.append("")
    lines.append(f"- Status: {status}")
    lines.append(f"- Subjects ready: {subjects_ready}")
    lines.append(f"- Requires approval: {run_plan['requires_approval']}")
    lines.append(f"- Approved: {run_plan['approved']}")
    lines.append(f"- Execution allowed: {run_plan['execution_allowed']}")
    lines.append("")
    lines.append("## Inputs")
    lines.append("")
    lines.append(f"- Capabilities: `{capabilities_path}`")
    lines.append(f"- Manifest: `{manifest_path}`")
    lines.append(f"- Preflight: `{preflight_path}`")
    lines.append(f"- Params: `{params_path}`")
    lines.append("")
    lines.append("## Planned Steps")
    lines.append("")
    for step in planned_steps:
        lines.append(f"- {step['step_id']}: {step['action']} — {step['status']}")
    lines.append("")
    lines.append("## Blocking Errors")
    lines.append("")
    if blocking_errors:
        for err in blocking_errors:
            lines.append(f"- {err}")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if warnings:
        for warn in warnings:
            lines.append(f"- {warn}")
    else:
        lines.append("None.")
    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This run plan does not execute DPABI and does not modify rawdata or DPABI source code.")
    lines.append("Execution requires explicit future approval.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": run_plan["ok"],
        "node_id": "dpabi_run_plan",
        "backend": "python",
        "outputs": [str(run_plan_path), str(report_path)],
        "metrics": {
            "status": status,
            "subjects_ready": subjects_ready,
            "blocking_errors_count": len(blocking_errors),
            "warnings_count": len(warnings),
        },
        "warnings": warnings,
        "errors": blocking_errors,
        "run_plan_path": str(run_plan_path),
        "report_path": str(report_path),
    }
