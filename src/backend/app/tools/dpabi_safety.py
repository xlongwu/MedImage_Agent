"""DPABI safety gate -- prevent dangerous DPABI/DPARSF calls."""
from __future__ import annotations

FORBIDDEN_FUNCTIONS = {
    "DPARSF_run",
    "DPARSFA_run",
    "DPABI_run",
    "dpabi_gui",
}

FORBIDDEN_PATTERNS = [
    "DPARSF",
    "DPARSFA",
]

ALLOWED_FUNCTIONS = {
    "y_Smooth", "rest_Smooth",
    "y_Filter", "rest_Filter",
    "y_RegressOutImgCovariates",
    "y_alff_falff",
    "y_Reho",
    "y_ROItseries",
    "y_FC",
}


def check_dpabi_call(function_name: str) -> tuple[bool, str | None]:
    """Returns (allowed, rejection_reason)."""
    if function_name in FORBIDDEN_FUNCTIONS:
        return False, f"FORBIDDEN: {function_name} is blocked by safety policy"
    for pattern in FORBIDDEN_PATTERNS:
        if pattern.lower() in function_name.lower():
            return False, f"FORBIDDEN: {function_name} matches blocked pattern '{pattern}'"
    return True, None


def list_allowed_functions() -> list[str]:
    """Return sorted list of allowlisted DPABI functions."""
    return sorted(ALLOWED_FUNCTIONS)
