from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_PARAMS = {
    "basic": {
        "tr": 2.0,
        "slice_timing_enabled": False,
        "realign_enabled": True,
        "normalize_enabled": True,
        "smooth_enabled": True,
        "smooth_fwhm": [6, 6, 6],
    },
    "nuisance": {
        "regress_motion": True,
        "regress_wm": False,
        "regress_csf": False,
        "regress_global_signal": False,
    },
    "filtering": {
        "bandpass_enabled": False,
        "low_freq": 0.01,
        "high_freq": 0.08,
    },
    "metrics": {
        "alff": False,
        "falff": False,
        "reho": False,
    },
    "safety": {
        "allow_full_dpabi_execution": False,
        "require_manual_review": True,
        "modify_rawdata": False,
        "delete_files": False,
    },
}


def _yaml_dump_fallback(data: dict[str, Any]) -> str:
    lines = []
    for section, values in data.items():
        lines.append(f"{section}:")
        for key, value in values.items():
            if isinstance(value, bool):
                rendered = "true" if value else "false"
            elif isinstance(value, list):
                rendered = "[" + ", ".join(str(x) for x in value) + "]"
            elif isinstance(value, str):
                rendered = f'"{value}"'
            else:
                rendered = str(value)
            lines.append(f"  {key}: {rendered}")
        lines.append("")
    return "\n".join(lines)


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def write_dpabi_parameter_schema(work_dir: str) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    schema = {
        "version": "0.1.0",
        "sections": {
            "basic": {
                "tr": {"type": "float", "min": 0.001, "required": True},
                "slice_timing_enabled": {"type": "bool"},
                "realign_enabled": {"type": "bool"},
                "normalize_enabled": {"type": "bool"},
                "smooth_enabled": {"type": "bool"},
                "smooth_fwhm": {"type": "list[float]", "length": 3},
            },
            "nuisance": {
                "regress_motion": {"type": "bool"},
                "regress_wm": {"type": "bool"},
                "regress_csf": {"type": "bool"},
                "regress_global_signal": {"type": "bool"},
            },
            "filtering": {
                "bandpass_enabled": {"type": "bool"},
                "low_freq": {"type": "float", "min": 0.0},
                "high_freq": {"type": "float", "min": 0.0},
            },
            "metrics": {
                "alff": {"type": "bool"},
                "falff": {"type": "bool"},
                "reho": {"type": "bool"},
            },
            "safety": {
                "allow_full_dpabi_execution": {"type": "bool", "default": False},
                "require_manual_review": {"type": "bool", "must_be": True},
                "modify_rawdata": {"type": "bool", "must_be": False},
                "delete_files": {"type": "bool", "must_be": False},
            },
        },
        "default_params": DEFAULT_PARAMS,
    }

    schema_path = out_dir / "dpabi_parameter_schema.json"
    schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "outputs": [str(schema_path)],
        "schema_path": str(schema_path),
        "errors": [],
        "warnings": [],
    }


def write_dpabi_params_review_template(work_dir: str) -> dict[str, Any]:
    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    params_path = out_dir / "dpabi_params_review.yaml"

    header = """# DPABI Parameter Review Template
# Human review is required before any DPABI execution.
# This file does not execute DPABI.

"""
    params_path.write_text(header + _yaml_dump_fallback(DEFAULT_PARAMS), encoding="utf-8")

    return {
        "ok": True,
        "outputs": [str(params_path)],
        "params_path": str(params_path),
        "errors": [],
        "warnings": [],
    }


def validate_dpabi_params(params_path: str, work_dir: str) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    path = Path(params_path)
    if not path.exists():
        errors.append(f"DPABI params review YAML not found: {path}")
        params = {}
    else:
        try:
            params = _load_yaml(path)
        except Exception as exc:
            errors.append(f"Failed to load params YAML: {exc}")
            params = {}

    basic = params.get("basic", {})
    filtering = params.get("filtering", {})
    safety = params.get("safety", {})

    tr = basic.get("tr")
    try:
        if tr is None or float(tr) <= 0:
            errors.append("basic.tr must be > 0.")
    except Exception:
        errors.append("basic.tr must be numeric.")

    fwhm = basic.get("smooth_fwhm")
    if not isinstance(fwhm, list) or len(fwhm) != 3:
        errors.append("basic.smooth_fwhm must be a list of length 3.")
    else:
        try:
            [float(x) for x in fwhm]
        except Exception:
            errors.append("basic.smooth_fwhm must contain numeric values.")

    low = filtering.get("low_freq", 0.01)
    high = filtering.get("high_freq", 0.08)

    try:
        low_f = float(low)
        high_f = float(high)
        if low_f < 0:
            errors.append("filtering.low_freq must be >= 0.")
        if high_f <= low_f:
            errors.append("filtering.high_freq must be greater than low_freq.")
    except Exception:
        errors.append("filtering.low_freq and high_freq must be numeric.")

    if safety.get("modify_rawdata") is not False:
        errors.append("safety.modify_rawdata must be false.")

    if safety.get("delete_files") is not False:
        errors.append("safety.delete_files must be false.")

    if safety.get("require_manual_review") is not True:
        errors.append("safety.require_manual_review must be true.")

    if safety.get("allow_full_dpabi_execution") is True:
        warnings.append(
            "allow_full_dpabi_execution=true was found. This step still does not execute DPABI; future execution must require explicit approval."
        )

    validation = {
        "ok": len(errors) == 0,
        "params_path": str(path),
        "errors": errors,
        "warnings": warnings,
        "params": params,
    }

    out_dir = Path(work_dir) / "dpabi"
    out_dir.mkdir(parents=True, exist_ok=True)

    validation_path = out_dir / "dpabi_params_validation.json"
    validation_path.write_text(json.dumps(validation, ensure_ascii=False, indent=2), encoding="utf-8")

    validation["outputs"] = [str(validation_path)]
    validation["validation_path"] = str(validation_path)
    return validation
