from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.tools.dpabi_template_instantiator import (
    instantiate_dpabi_template,
    list_dpabi_templates,
)


# Template wizard is intentionally restricted to smoothing-only for safety.
# See dpabi_safety.ALLOWED_FUNCTIONS for the full function whitelist.
ALLOWLISTED_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _wizard_dir(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "template_wizard"


def _matrix_path(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "dpabi_wrapper_compatibility_matrix.json"


def get_dpabi_template_wizard_options(work_dir: str = "./work") -> dict[str, Any]:
    templates = list_dpabi_templates(work_dir)
    matrix = _read_json(_matrix_path(work_dir))

    promotable_functions: list[str] = []
    if matrix:
        for row in matrix.get("rows", []):
            if row.get("readiness") == "PROMOTABLE_TO_TEMPLATE":
                fn = row.get("function_name")
                if fn in ALLOWLISTED_FUNCTIONS:
                    promotable_functions.append(fn)

    return {
        "ok": templates.get("ok", False),
        "templates": templates.get("templates", []),
        "functions": sorted(set(promotable_functions) or ALLOWLISTED_FUNCTIONS),
        "default_subjects": ["sub-001", "sub-002"],
        "default_fwhm": [4, 4, 4],
        "default_scheduler": {
            "mode": "local_parallel",
            "max_workers": 2,
            "matlab_max_workers": 1,
        },
        "safety": {
            "synthetic_only": True,
            "requires_approval": True,
            "approved_by_default": False,
            "full_dpabi_execution": False,
            "dparsf_run_allowed": False,
            "dparsfa_run_allowed": False,
            "dpabi_gui_allowed": False,
        },
        "warnings": templates.get("warnings", []),
        "errors": templates.get("errors", []),
    }


def validate_dpabi_template_wizard_payload(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    template_id = str(payload.get("template_id", "")).strip()
    instance_id = str(payload.get("instance_id", "")).strip()
    function_name = str(payload.get("function_name", "")).strip()
    fwhm = payload.get("fwhm", [4, 4, 4])
    subjects = payload.get("subjects", ["sub-001", "sub-002"])
    scheduler = payload.get("scheduler", {}) or {}

    if not template_id or "/" in template_id or "\\" in template_id or ".." in template_id:
        errors.append("Invalid template_id.")

    if instance_id and ("/" in instance_id or "\\" in instance_id or ".." in instance_id):
        errors.append("Invalid instance_id.")

    options = get_dpabi_template_wizard_options(work_dir)
    available_template_ids = {
        item.get("template_id") for item in options.get("templates", [])
    }

    if template_id not in available_template_ids:
        errors.append(f"Template is not available: {template_id}")

    if function_name not in ALLOWLISTED_FUNCTIONS:
        errors.append(f"Function is not allowlisted: {function_name}")

    if not isinstance(fwhm, list) or len(fwhm) != 3:
        errors.append("fwhm must be a list of length 3.")
    else:
        for value in fwhm:
            try:
                if float(value) <= 0:
                    errors.append("fwhm values must be positive.")
            except Exception:
                errors.append("fwhm values must be numeric.")

    if not isinstance(subjects, list) or not subjects:
        errors.append("subjects must be a non-empty list.")
    else:
        for subject in subjects:
            if not isinstance(subject, str) or not subject.startswith("sub-"):
                errors.append(f"Invalid synthetic subject id: {subject}")

    mode = scheduler.get("mode", "local_parallel")
    if mode not in {"sequential", "local_parallel"}:
        errors.append(f"Invalid scheduler.mode: {mode}")

    try:
        max_workers = int(scheduler.get("max_workers", 2))
    except Exception:
        max_workers = 2
        errors.append("scheduler.max_workers must be an integer.")

    try:
        matlab_max_workers = int(scheduler.get("matlab_max_workers", 1))
    except Exception:
        matlab_max_workers = 1
        errors.append("scheduler.matlab_max_workers must be an integer.")

    if max_workers < 1 or max_workers > 8:
        errors.append("scheduler.max_workers must be between 1 and 8.")

    if matlab_max_workers < 1 or matlab_max_workers > max_workers:
        errors.append("scheduler.matlab_max_workers must be between 1 and max_workers.")

    return {
        "ok": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "normalized": {
            "template_id": template_id,
            "instance_id": instance_id or None,
            "run_id": payload.get("run_id"),
            "function_name": function_name,
            "fwhm": [float(x) for x in fwhm] if isinstance(fwhm, list) and len(fwhm) == 3 else fwhm,
            "subjects": subjects,
            "scheduler": {
                "mode": mode,
                "max_workers": max_workers,
                "matlab_max_workers": matlab_max_workers,
            },
        },
    }


def preview_dpabi_template_instance(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    validation = validate_dpabi_template_wizard_payload(payload, work_dir)
    out_dir = _wizard_dir(work_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    preview_json = out_dir / "latest_preview.json"
    preview_md = out_dir / "latest_preview.md"

    if not validation.get("ok"):
        preview = {
            "ok": False,
            "mode": "PREVIEW",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
            "normalized": validation.get("normalized"),
        }
    else:
        normalized = validation["normalized"]
        preview = {
            "ok": True,
            "mode": "PREVIEW",
            "will_execute": False,
            "template_id": normalized["template_id"],
            "instance_id": normalized["instance_id"],
            "run_id": normalized["run_id"],
            "function_name": normalized["function_name"],
            "fwhm": normalized["fwhm"],
            "subjects": normalized["subjects"],
            "scheduler": normalized["scheduler"],
            "safety": {
                "requires_approval": True,
                "approved": False,
                "execution_allowed": False,
                "synthetic_only": True,
                "full_dpabi_execution": False,
                "dparsf_run_allowed": False,
                "dparsfa_run_allowed": False,
                "dpabi_gui_allowed": False,
                "rawdata_modified": False,
                "files_deleted": False,
            },
            "warnings": validation.get("warnings", []),
            "errors": [],
        }

    preview_json.write_text(
        json.dumps(preview, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Template Wizard Preview")
    lines.append("")
    lines.append(f"- OK: {preview.get('ok')}")
    lines.append(f"- Template ID: {preview.get('template_id')}")
    lines.append(f"- Instance ID: {preview.get('instance_id')}")
    lines.append(f"- Function: {preview.get('function_name')}")
    lines.append(f"- Subjects: {preview.get('subjects')}")
    lines.append(f"- Will execute: {preview.get('will_execute')}")
    lines.append("")
    lines.append("## Safety")
    lines.append("")
    lines.append("- Requires approval: true")
    lines.append("- Approved: false")
    lines.append("- Execution allowed: false")
    lines.append("- Synthetic only: true")
    lines.append("- Full DPABI execution: false")
    lines.append("- DPARSF_run allowed: false")
    lines.append("- DPARSFA_run allowed: false")
    lines.append("- DPABI GUI allowed: false")

    preview_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    preview["outputs"] = [str(preview_json), str(preview_md)]
    return preview


def create_dpabi_template_instance_from_wizard(
    payload: dict[str, Any],
    work_dir: str = "./work",
) -> dict[str, Any]:
    validation = validate_dpabi_template_wizard_payload(payload, work_dir)
    if not validation.get("ok"):
        return {
            "ok": False,
            "mode": "CREATE_INSTANCE",
            "errors": validation.get("errors", []),
            "warnings": validation.get("warnings", []),
        }

    normalized = validation["normalized"]

    result = instantiate_dpabi_template(
        template_id=normalized["template_id"],
        instance_id=normalized["instance_id"],
        run_id=normalized["run_id"],
        function_name=normalized["function_name"],
        fwhm=normalized["fwhm"],
        subjects=normalized["subjects"],
        scheduler=normalized["scheduler"],
        work_dir=work_dir,
    )

    result["mode"] = "CREATE_INSTANCE"
    result["created_by"] = "dpabi_template_wizard"
    return result
