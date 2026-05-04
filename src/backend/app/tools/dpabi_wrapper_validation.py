from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


BLOCKED_CLASSES = {"GUI_BLOCKED", "FULL_PIPELINE_BLOCKED"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _signature_by_name(signatures: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not signatures:
        return {}
    return {
        item.get("name"): item
        for item in signatures.get("functions", [])
        if item.get("name")
    }


def _sandbox_status_by_function(sandbox: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not sandbox:
        return {}

    function_name = sandbox.get("function_name")
    if not function_name:
        return {}

    return {
        function_name: {
            "tested": True,
            "passed": bool(sandbox.get("ok")),
            "errors": sandbox.get("errors", []),
            "warnings": sandbox.get("warnings", []),
        }
    }


def _subject_status_by_function(summary: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not summary:
        return {}

    out: dict[str, dict[str, Any]] = {}

    for subject in summary.get("subjects", []):
        fn = subject.get("function_name", "unknown")
        item = out.setdefault(
            fn,
            {
                "tested": True,
                "subjects_total": 0,
                "subjects_success": 0,
                "subjects_failed": 0,
            },
        )

        item["subjects_total"] += 1
        if subject.get("ok"):
            item["subjects_success"] += 1
        else:
            item["subjects_failed"] += 1

    for fn, item in out.items():
        item["passed"] = item["subjects_total"] > 0 and item["subjects_failed"] == 0

    return out


def _determine_readiness(
    exists: bool,
    safety_classification: str,
    wrapper_candidate: bool,
    sandbox_tested: bool,
    sandbox_passed: bool,
    subject_tested: bool,
    subject_passed: bool,
) -> tuple[str, str]:
    if safety_classification in BLOCKED_CLASSES:
        return "BLOCKED", "do_not_execute"

    if not exists:
        return "MISSING", "skip_until_function_available"

    if not wrapper_candidate:
        return "MANUAL_REVIEW_REQUIRED", "manual_contract_review"

    if not sandbox_tested:
        return "CONTRACT_ONLY", "run_single_function_sandbox"

    if sandbox_tested and not sandbox_passed:
        return "MANUAL_REVIEW_REQUIRED", "review_sandbox_failure"

    if sandbox_passed and not subject_tested:
        return "SANDBOX_PASSED", "run_subject_level_synthetic_test"

    if subject_tested and not subject_passed:
        return "MANUAL_REVIEW_REQUIRED", "review_subject_level_failure"

    if subject_passed:
        return "PROMOTABLE_TO_TEMPLATE", "add_to_pipeline_template_library"

    return "MANUAL_REVIEW_REQUIRED", "manual_review"


def write_dpabi_wrapper_validation_matrix(
    work_dir: str,
    report_dir: str,
    signatures_path: str = "./work/dpabi/dpabi_function_signatures.json",
    contracts_path: str = "./work/dpabi/dpabi_wrapper_contracts.json",
    sandbox_result_path: str = "./work/dpabi/single_function_sandbox/dpabi_single_function_result.json",
    subject_wrapper_summary_path: str = "./reports/dpabi/dpabi_subject_wrapper_summary.json",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    sig_path = Path(signatures_path)
    con_path = Path(contracts_path)
    sandbox_path = Path(sandbox_result_path)
    subject_path = Path(subject_wrapper_summary_path)

    signatures = _read_json(sig_path)
    contracts = _read_json(con_path)
    sandbox = _read_json(sandbox_path)
    subject_summary = _read_json(subject_path)

    if not signatures:
        warnings.append(f"Missing or invalid signatures JSON: {sig_path}")

    if not contracts:
        return {
            "ok": False,
            "node_id": "dpabi_wrapper_validation_matrix",
            "backend": "python",
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Missing or invalid wrapper contracts JSON: {con_path}"],
        }

    if not sandbox:
        warnings.append(f"Missing sandbox result: {sandbox_path}")

    if not subject_summary:
        warnings.append(f"Missing subject wrapper summary: {subject_path}")

    sig_map = _signature_by_name(signatures)
    sandbox_map = _sandbox_status_by_function(sandbox)
    subject_map = _subject_status_by_function(subject_summary)

    rows: list[dict[str, Any]] = []

    for contract in contracts.get("contracts", []):
        function_name = contract.get("function_name")
        signature = sig_map.get(function_name, {})
        sandbox_status = sandbox_map.get(function_name, {"tested": False, "passed": False})
        subject_status = subject_map.get(function_name, {"tested": False, "passed": False})

        exists = bool(contract.get("exists"))
        safety_classification = str(contract.get("safety_classification", "UNKNOWN_REVIEW_REQUIRED"))
        wrapper_candidate = bool(contract.get("wrapper_candidate"))

        readiness, recommended_next_step = _determine_readiness(
            exists=exists,
            safety_classification=safety_classification,
            wrapper_candidate=wrapper_candidate,
            sandbox_tested=bool(sandbox_status.get("tested")),
            sandbox_passed=bool(sandbox_status.get("passed")),
            subject_tested=bool(subject_status.get("tested")),
            subject_passed=bool(subject_status.get("passed")),
        )

        rows.append({
            "function_name": function_name,
            "category": contract.get("category"),
            "exists": exists,
            "which_path": contract.get("which_path"),
            "nargin": contract.get("nargin", signature.get("nargin")),
            "nargout": contract.get("nargout", signature.get("nargout")),
            "safety_classification": safety_classification,
            "wrapper_candidate": wrapper_candidate,
            "blocked_reason": contract.get("blocked_reason", ""),
            "sandbox_tested": bool(sandbox_status.get("tested")),
            "sandbox_passed": bool(sandbox_status.get("passed")),
            "subject_tested": bool(subject_status.get("tested")),
            "subject_passed": bool(subject_status.get("passed")),
            "subjects_total": subject_status.get("subjects_total"),
            "subjects_success": subject_status.get("subjects_success"),
            "subjects_failed": subject_status.get("subjects_failed"),
            "readiness": readiness,
            "recommended_next_step": recommended_next_step,
        })

    out_dir = Path(work_dir) / "dpabi"
    report_out = Path(report_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_out.mkdir(parents=True, exist_ok=True)

    json_path = out_dir / "dpabi_wrapper_compatibility_matrix.json"
    csv_path = out_dir / "dpabi_wrapper_compatibility_matrix.csv"
    report_path = report_out / "dpabi_wrapper_validation_report.md"

    payload = {
        "ok": True,
        "node_id": "dpabi_wrapper_validation_matrix",
        "backend": "python",
        "matrix_total": len(rows),
        "promotable_total": sum(1 for row in rows if row["readiness"] == "PROMOTABLE_TO_TEMPLATE"),
        "blocked_total": sum(1 for row in rows if row["readiness"] == "BLOCKED"),
        "manual_review_total": sum(1 for row in rows if row["readiness"] == "MANUAL_REVIEW_REQUIRED"),
        "rows": rows,
        "warnings": warnings,
        "errors": errors,
    }

    json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    fieldnames = [
        "function_name",
        "category",
        "exists",
        "nargin",
        "nargout",
        "safety_classification",
        "wrapper_candidate",
        "blocked_reason",
        "sandbox_tested",
        "sandbox_passed",
        "subject_tested",
        "subject_passed",
        "subjects_total",
        "subjects_success",
        "subjects_failed",
        "readiness",
        "recommended_next_step",
    ]

    with csv_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})

    lines = []
    lines.append("# DPABI Wrapper Validation Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Matrix total: {payload['matrix_total']}")
    lines.append(f"- Promotable total: {payload['promotable_total']}")
    lines.append(f"- Blocked total: {payload['blocked_total']}")
    lines.append(f"- Manual review total: {payload['manual_review_total']}")
    lines.append("")
    lines.append("## Compatibility Matrix")
    lines.append("")
    lines.append("| Function | Exists | Candidate | Sandbox | Subject | Readiness | Next Step |")
    lines.append("|---|---:|---:|---:|---:|---|---|")

    for row in rows:
        lines.append(
            f"| {row['function_name']} | {row['exists']} | {row['wrapper_candidate']} | "
            f"{row['sandbox_passed']} | {row['subject_passed']} | "
            f"{row['readiness']} | {row['recommended_next_step']} |"
        )

    lines.append("")
    lines.append("## Safety Note")
    lines.append("")
    lines.append("This validation matrix does not execute DPABI. It only summarizes existing wrapper evidence.")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "node_id": "dpabi_wrapper_validation_matrix",
        "backend": "python",
        "outputs": [str(json_path), str(csv_path), str(report_path)],
        "metrics": {
            "matrix_total": payload["matrix_total"],
            "promotable_total": payload["promotable_total"],
            "blocked_total": payload["blocked_total"],
            "manual_review_total": payload["manual_review_total"],
        },
        "warnings": warnings,
        "errors": errors,
    }
