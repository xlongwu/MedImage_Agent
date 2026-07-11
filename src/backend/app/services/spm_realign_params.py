"""Parameter schema validator for the future SPM realign wrapper.

Validates params against the contract defined in
docs/预处理与科学计算/SPM/重对齐包装安全契约.md.  No MATLAB/SPM execution.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_DEFAULTS: dict[str, Any] = {
    "quality": 0.9,
    "separation_mm": 4,
    "fwhm_mm": 5,
    "register_to_mean": True,
    "estimate_reslice": True,
    "interpolation": 2,
    "wrap": [0, 0, 0],
    "weight_image": None,
}

_ALLOWED_INTERPOLATION = {0, 1, 2, 3, 4, 5, 6, 7}

_ALLOWED_KEYS = set(_DEFAULTS.keys())

# Standard pipeline params that are passed through without validation
_PASSTHROUGH_PARAMS = {
    "approved",
    "approved_by",
    "approved_nodes",
    "rejected_nodes",
    "executable",
    "dry_run_only",
    "inspectable",
    "_gpu_info",
    "_gpu_mode",
    "rawdata_dir",
    "output_dir",
    "dataset_index",
    "dataset_index_path",
    "read_nifti_metadata",
    "subject_scope",
}


def default_spm_realign_params() -> dict[str, Any]:
    """Return a copy of the default params."""
    return dict(_DEFAULTS)


def validate_spm_realign_params(
    params: dict[str, Any] | None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Validate SPM realign parameters and return canonical defaults.

    Returns (cleaned_params, warnings, errors).

    Safety rules:
      - Unknown params are rejected as errors.
      - No shell snippets or MATLAB code allowed.
      - No arbitrary absolute paths allowed.
    """
    if params is None:
        params = {}

    errors: list[str] = []
    warnings: list[str] = []
    cleaned = dict(_DEFAULTS)

    for key, value in params.items():
        # Skip standard pipeline params — they are not SPM-specific
        if key in _PASSTHROUGH_PARAMS:
            continue
        if key not in _ALLOWED_KEYS:
            errors.append(
                f"Unknown SPM realign parameter '{key}'. "
                f"Allowed SPM params: {sorted(_ALLOWED_KEYS)}"
            )
            continue

        if key == "quality":
            if not isinstance(value, (int, float)):
                errors.append("quality must be a number.")
            elif not (0 < value <= 1):
                errors.append(f"quality must be in (0, 1], got {value}.")
            else:
                cleaned["quality"] = float(value)

        elif key == "separation_mm":
            if not isinstance(value, (int, float)):
                errors.append("separation_mm must be a number.")
            elif value <= 0:
                errors.append(f"separation_mm must be positive, got {value}.")
            else:
                cleaned["separation_mm"] = float(value)

        elif key == "fwhm_mm":
            if not isinstance(value, (int, float)):
                errors.append("fwhm_mm must be a number.")
            elif value < 0:
                errors.append(f"fwhm_mm must be non-negative, got {value}.")
            else:
                cleaned["fwhm_mm"] = float(value)

        elif key in ("register_to_mean", "estimate_reslice"):
            if not isinstance(value, bool):
                errors.append(f"{key} must be a boolean.")
            else:
                cleaned[key] = value

        elif key == "interpolation":
            if not isinstance(value, int):
                errors.append("interpolation must be an integer.")
            elif value not in _ALLOWED_INTERPOLATION:
                errors.append(
                    f"interpolation must be one of {sorted(_ALLOWED_INTERPOLATION)}, "
                    f"got {value}."
                )
            else:
                cleaned["interpolation"] = value

        elif key == "wrap":
            if not isinstance(value, list) or len(value) != 3:
                errors.append("wrap must be a list of exactly 3 integers (0 or 1).")
            elif not all(isinstance(v, int) and v in (0, 1) for v in value):
                errors.append("wrap values must be 0 or 1.")
            else:
                cleaned["wrap"] = [int(v) for v in value]

        elif key == "weight_image":
            if value is None:
                cleaned["weight_image"] = None
            elif isinstance(value, str):
                path_str = value.strip()
                if not path_str:
                    cleaned["weight_image"] = None
                elif Path(path_str).is_absolute():
                    errors.append(
                        "weight_image must not be an absolute path. "
                        "Use a relative path within project outputs."
                    )
                elif ".." in path_str or path_str.startswith("/") or "\\" in path_str:
                    errors.append(
                        "weight_image must be a safe relative path without traversal."
                    )
                else:
                    cleaned["weight_image"] = path_str
            else:
                errors.append("weight_image must be null or a relative path string.")

    return cleaned, warnings, errors
