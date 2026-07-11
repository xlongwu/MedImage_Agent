"""Native pipeline ordering templates derived from DPARSF semantics."""
from __future__ import annotations

NATIVE_DPARSF_TIME_SERIES_ORDER: tuple[str, ...] = (
    "dummy_scan_removal",
    "slice_timing",
    "realignment",
    "motion_qc",
    "coregistration",
    "segmentation",
    "normalization",
    "smoothing",
    "nuisance_regression",
    "detrending",
    "temporal_filtering",
)

DEFAULT_TIME_SERIES_POLICY = {
    "regression_filtering_order": "regress_then_detrend_then_filter",
    "censoring_strategy": "spike_regressors_preserve_timepoints",
    "unsupported_censoring_strategy": "drop_timepoints",
}


def default_time_series_order() -> tuple[str, ...]:
    return NATIVE_DPARSF_TIME_SERIES_ORDER
