"""QC and parameter validation rules for DPABI-like native stages."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class FrequencyRuleResult:
    filter_type: str
    tr: float
    nyquist_hz: float
    low_hz: float | None
    high_hz: float | None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_frequency_rule(
    *,
    filter_type: str,
    tr: float,
    low_hz: float | None = None,
    high_hz: float | None = None,
) -> FrequencyRuleResult:
    """Validate TR and cutoff semantics without silently clipping to Nyquist."""

    warnings: list[str] = []
    errors: list[str] = []
    normalized = filter_type.lower().replace("_", "-")
    if normalized == "none":
        normalized = "no-filter"
    if normalized not in {"band-pass", "bandpass", "high-pass", "highpass", "low-pass", "lowpass", "no-filter"}:
        errors.append(f"Unsupported filter_type: {filter_type}")
    if tr <= 0:
        errors.append("TR must be positive.")
        nyquist = 0.0
    else:
        nyquist = 1.0 / (2.0 * float(tr))

    low = float(low_hz) if low_hz is not None else None
    high = float(high_hz) if high_hz is not None else None
    needs_low = normalized in {"band-pass", "bandpass", "high-pass", "highpass"}
    needs_high = normalized in {"band-pass", "bandpass", "low-pass", "lowpass"}
    if needs_low and (low is None or low < 0):
        errors.append("low_hz must be non-negative for high-pass or band-pass filtering.")
    if needs_high and (high is None or high <= 0):
        errors.append("high_hz must be positive for low-pass or band-pass filtering.")
    if low is not None and low >= nyquist and normalized != "no-filter":
        errors.append(f"low_hz={low} must be below Nyquist={nyquist}.")
    if high is not None and high >= nyquist and normalized != "no-filter":
        errors.append(f"high_hz={high} must be below Nyquist={nyquist}.")
    if normalized in {"band-pass", "bandpass"} and low is not None and high is not None and low >= high:
        errors.append("band-pass filtering requires low_hz < high_hz.")
    if normalized == "no-filter" and (low is not None or high is not None):
        warnings.append("Frequency cutoffs were supplied but filter_type is no-filter.")
    return FrequencyRuleResult(
        filter_type=normalized,
        tr=float(tr),
        nyquist_hz=nyquist,
        low_hz=low,
        high_hz=high,
        warnings=warnings,
        errors=errors,
    )


def rank_qc(matrix: Any) -> dict[str, Any]:
    import numpy as np

    array = np.asarray(matrix, dtype=np.float64)
    if array.ndim != 2:
        return {"rows": 0, "columns": 0, "rank": 0, "condition_number": None, "has_nan": True, "has_inf": True}
    has_nan = bool(np.isnan(array).any())
    has_inf = bool(np.isinf(array).any())
    try:
        rank = int(np.linalg.matrix_rank(array))
    except Exception:
        rank = 0
    try:
        condition_number = float(np.linalg.cond(array)) if array.size else None
    except Exception:
        condition_number = None
    return {
        "rows": int(array.shape[0]),
        "columns": int(array.shape[1]),
        "rank": rank,
        "condition_number": condition_number,
        "has_nan": has_nan,
        "has_inf": has_inf,
    }
