from __future__ import annotations

import json
from pathlib import Path
from typing import Any


GUI_ENTRYPOINTS = {"DPABI", "DPARSF", "DPARSFA"}
FULL_PIPELINE_RUNNERS = {"DPARSF_run", "DPARSFA_run"}
SAFE_IO = {"y_Read", "y_Write", "rest_readfile", "rest_writefile"}
SINGLE_FUNCTION_CANDIDATES = {
    "y_Smooth",
    "y_Filter",
    "y_RegressOutImgCovariates",
    "y_alff_falff",
    "y_Reho",
    "y_ROItseries",
    "y_FC",
    "y_Reslice",
    "y_ALFF",
    "y_fALFF",
    "y_ReHo",
    "y_CalcALFF",
    "y_CalcReHo",
    "rest_Smooth",
    "rest_RegressOutCovariates",
    "y_RegressOutImgCovariates",
    "y_bandpass",
}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _yaml_scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def _classify_function(item: dict[str, Any]) -> dict[str, Any]:
    name = item.get("name")
    exists = bool(item.get("exists"))
    nargin_value = item.get("nargin")
    nargout_value = item.get("nargout")
    probe_errors = item.get("probe_errors", []) or []

    wrapper_candidate = False
    blocked_reason = ""
    recommended_next_step = "manual_review"
    safety_classification = "UNKNOWN_REVIEW_REQUIRED"

    if not exists:
        blocked_reason = "function_missing"
        recommended_next_step = "skip"
    elif name in GUI_ENTRYPOINTS:
        safety_classification = "GUI_BLOCKED"
        blocked_reason = "gui_entrypoint_blocked"
        recommended_next_step = "do_not_wrap"
    elif name in FULL_PIPELINE_RUNNERS:
        safety_classification = "FULL_PIPELINE_BLOCKED"
        blocked_reason = "full_pipeline_runner_blocked"
        recommended_next_step = "requires_separate_approved_execution_design"
    elif name in SAFE_IO:
        safety_classification = "SAFE_IO_PROBE"
        wrapper_candidate = True
        recommended_next_step = "keep_for_io_smoke_tests"
    elif name in SINGLE_FUNCTION_CANDIDATES:
        safety_classification = "SAFE_SINGLE_FUNCTION_CANDIDATE"
        wrapper_candidate = True
        recommended_next_step = "create_sandbox_contract_test_before_subject_execution"
    elif probe_errors:
        safety_classification = "UNKNOWN_REVIEW_REQUIRED"
        blocked_reason = "signature_probe_errors"
        recommended_next_step = "manual_review"
    else:
        safety_classification = "UNKNOWN_REVIEW_REQUIRED"
        recommended_next_step = "manual_review"

    if wrapper_candidate and (nargin_value is None or nargout_value is None):
        wrapper_candidate = False
        blocked_reason = "missing_nargin_or_nargout"
        recommended_next_step = "manual_signature_review"

    return {
        "function_name": name,
        "category": item.get("category"),
        "exists": exists,
        "which_path": item.get("which_path"),
        "nargin": nargin_value,
        "nargout": nargout_value,
        "safety_classification": safety_classification,
        "wrapper_candidate": wrapper_candidate,
        "blocked_reason": blocked_reason,
        "recommended_next_step": recommended_next_step,
        "probe_errors": probe_errors,
    }


def write_dpabi_wrapper_contracts(
    signatures_path: str,
    work_dir: str,
    report_dir: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sig_path = Path(signatures_path)
    signatures = _read_json(sig_path)

    if not signatures:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_contracts",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid signatures JSON: {sig_path}"],
        }

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    contracts = [
        _classify_function(item)
        for item in signatures.get("functions", [])
    ]

    candidates = [item for item in contracts if item["wrapper_candidate"]]
    blocked = [item for item in contracts if item["blocked_reason"]]

    payload = {
        "ok": True,
        "node_id": "dpabi_wrapper_contracts",
        "backend": "python",
        "signatures_path": str(sig_path),
        "contracts_total": len(contracts),
        "wrapper_candidates": len(candidates),
        "blocked_total": len(blocked),
        "contracts": contracts,
        "warnings": warnings,
        "errors": errors,
    }

    json_path = out_dir / "dpabi_wrapper_contracts.json"
    yaml_path = out_dir / "dpabi_wrapper_contracts.yaml"
    report_path = report_out / "dpabi_signature_probe_report.md"

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    yaml_lines = []
    yaml_lines.append('version: "0.1.0"')
    yaml_lines.append("contracts:")
    for item in contracts:
        yaml_lines.append(f"  - function_name: {_yaml_scalar(item['function_name'])}")
        yaml_lines.append(f"    category: {_yaml_scalar(item['category'])}")
        yaml_lines.append(f"    exists: {_yaml_scalar(item['exists'])}")
        yaml_lines.append(f"    nargin: {_yaml_scalar(item['nargin'])}")
        yaml_lines.append(f"    nargout: {_yaml_scalar(item['nargout'])}")
        yaml_lines.append(f"    safety_classification: {_yaml_scalar(item['safety_classification'])}")
        yaml_lines.append(f"    wrapper_candidate: {_yaml_scalar(item['wrapper_candidate'])}")
        yaml_lines.append(f"    blocked_reason: {_yaml_scalar(item['blocked_reason'])}")
        yaml_lines.append(f"    recommended_next_step: {_yaml_scalar(item['recommended_next_step'])}")
    yaml_path.write_text("\n".join(yaml_lines) + "\n", encoding="utf-8")

    lines = []
    lines.append("# DPABI Signature Probe Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Signatures: `{sig_path}`")
    lines.append(f"- Contracts total: {len(contracts)}")
    lines.append(f"- Wrapper candidates: {len(candidates)}")
    lines.append(f"- Blocked total: {len(blocked)}")
    lines.append("")
    lines.append("## Wrapper Candidates")
    lines.append("")
    if candidates:
        lines.append("| Function | Category | nargin | nargout | Classification |")
        lines.append("|---|---|---:|---:|---|")
        for item in candidates:
            lines.append(
                f"| {item['function_name']} | {item['category']} | {item['nargin']} | "
                f"{item['nargout']} | {item['safety_classification']} |"
            )
    else:
        lines.append("No wrapper candidates found.")
    lines.append("")
    lines.append("## Blocked Functions")
    lines.append("")
    if blocked:
        lines.append("| Function | Category | Blocked Reason | Recommended Next Step |")
        lines.append("|---|---|---|---|")
        for item in blocked:
            lines.append(
                f"| {item['function_name']} | {item['category']} | {item['blocked_reason']} | "
                f"{item['recommended_next_step']} |"
            )
    else:
        lines.append("No blocked functions.")
    lines.append("")
    lines.append("## All Contracts")
    lines.append("")
    lines.append("```yaml")
    lines.append(yaml_path.read_text(encoding="utf-8"))
    lines.append("```")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("*Generated by MedImage Agent - DPABI Signature Probe*")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    payload["outputs"] = [str(json_path), str(yaml_path), str(report_path)]
    payload["contracts_json"] = str(json_path)
    payload["contracts_yaml"] = str(yaml_path)
    payload["report_md"] = str(report_path)

    return payload
