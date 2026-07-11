"""DPARSF-style parameter mapping to native preprocessing stage configs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from src.backend.app.native_preproc.dpabi_compat.pipeline_templates import DEFAULT_TIME_SERIES_POLICY


@dataclass(frozen=True)
class NativeStageConfig:
    stage_id: str
    enabled: bool
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DPARSFConversion:
    stage_configs: list[NativeStageConfig]
    warnings: list[str] = field(default_factory=list)
    unsupported_keys: list[str] = field(default_factory=list)

    def stage_map(self) -> dict[str, NativeStageConfig]:
        return {item.stage_id: item for item in self.stage_configs}


def _section(config: Mapping[str, Any], *names: str) -> Mapping[str, Any]:
    for name in names:
        value = config.get(name)
        if isinstance(value, Mapping):
            return value
    return {}


def _value(config: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in config:
            return config[name]
    return default


def _enabled(config: Mapping[str, Any], *names: str, default: bool = False) -> bool:
    value = _value(config, *names, default=default)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "enabled"}
    return bool(value)


def convert_dparsf_config(config: Mapping[str, Any]) -> DPARSFConversion:
    """Convert a small DPARSF-like config dictionary into native stage configs."""

    known_top_level = {
        "remove_first_timepoints",
        "RemoveFirstTimePoints",
        "slice_timing",
        "SliceTiming",
        "realignment",
        "Realign",
        "normalization",
        "Normalize",
        "smoothing",
        "Smooth",
        "nuisance",
        "Nuisance",
        "detrending",
        "Detrend",
        "filtering",
        "Filter",
        "alff",
        "falff",
        "reho",
        "fc",
        "functional_connectivity",
        "atlas_resampling",
        "AtlasResampling",
        "roi_timeseries",
        "ROITimeSeries",
        "group_summary",
        "GroupSummary",
        "scrubbing",
        "Scrubbing",
        "motion_threshold",
    }
    unsupported = sorted(str(key) for key in config.keys() if key not in known_top_level)
    warnings = [f"Unsupported DPARSF config key preserved as warning: {key}" for key in unsupported]

    remove_first = int(_value(config, "remove_first_timepoints", "RemoveFirstTimePoints", default=0) or 0)
    slice_timing = _section(config, "slice_timing", "SliceTiming")
    realignment = _section(config, "realignment", "Realign")
    normalization = _section(config, "normalization", "Normalize")
    smoothing = _section(config, "smoothing", "Smooth")
    nuisance = _section(config, "nuisance", "Nuisance")
    detrending = _section(config, "detrending", "Detrend")
    filtering = _section(config, "filtering", "Filter")
    atlas_resampling = _section(config, "atlas_resampling", "AtlasResampling")
    roi_timeseries = _section(config, "roi_timeseries", "ROITimeSeries")
    group_summary = _section(config, "group_summary", "GroupSummary")
    scrubbing = _section(config, "scrubbing", "Scrubbing")
    fc_enabled = _enabled(config, "fc", "functional_connectivity", default=False)

    nuisance_params = {
        "motion_model": _value(nuisance, "motion_model", "Covariates", default="friston24"),
        "include_wm": _enabled(nuisance, "include_wm", "regress_wm", default=False),
        "include_csf": _enabled(nuisance, "include_csf", "regress_csf", default=False),
        "include_global_signal": _enabled(nuisance, "include_global_signal", "regress_global_signal", default=False),
        "polynomial_order": int(_value(nuisance, "polynomial_order", "trend_order", default=1) or 0),
        "censoring_strategy": _value(
            scrubbing,
            "censoring_strategy",
            default=DEFAULT_TIME_SERIES_POLICY["censoring_strategy"],
        ),
        "scrub_threshold_mm": _value(
            scrubbing,
            "fd_threshold_mm",
            "threshold_mm",
            default=_value(config, "motion_threshold", default=None),
        ),
    }
    filter_type = _value(filtering, "filter_type", "type", default="bandpass")
    filter_params = {
        "filter_type": filter_type,
        "low_hz": _value(filtering, "low_hz", "low_freq", default=0.01),
        "high_hz": _value(filtering, "high_hz", "high_freq", default=0.08),
        "method": _value(filtering, "method", default="fft"),
        "order": int(_value(filtering, "order", default=2) or 2),
    }

    stages = [
        NativeStageConfig("dummy_scan_removal", remove_first > 0, {"remove_first": remove_first}),
        NativeStageConfig("slice_timing", _enabled(slice_timing, "enabled", "on", default=False), dict(slice_timing)),
        NativeStageConfig("realignment", _enabled(realignment, "enabled", "on", default=True), dict(realignment)),
        NativeStageConfig("normalization", _enabled(normalization, "enabled", "on", default=False), dict(normalization)),
        NativeStageConfig("smoothing", _enabled(smoothing, "enabled", "on", default=False), dict(smoothing)),
        NativeStageConfig("nuisance_regression", _enabled(nuisance, "enabled", "on", default=bool(nuisance)), nuisance_params),
        NativeStageConfig("detrending", _enabled(detrending, "enabled", "on", default=True), {"polynomial_order": int(_value(detrending, "polynomial_order", "order", default=1) or 1)}),
        NativeStageConfig("temporal_filtering", _enabled(filtering, "enabled", "on", default=bool(filtering)), filter_params),
        NativeStageConfig("alff", _enabled(config, "alff", default=False), {}),
        NativeStageConfig("falff", _enabled(config, "falff", default=False), {}),
        NativeStageConfig("reho", _enabled(config, "reho", default=False), {}),
        NativeStageConfig(
            "atlas_resampling",
            _enabled(atlas_resampling, "enabled", "on", default=fc_enabled),
            dict(atlas_resampling),
        ),
        NativeStageConfig(
            "roi_timeseries",
            _enabled(roi_timeseries, "enabled", "on", default=fc_enabled),
            dict(roi_timeseries),
        ),
        NativeStageConfig(
            "functional_connectivity",
            fc_enabled,
            {},
        ),
        NativeStageConfig(
            "group_summary",
            _enabled(group_summary, "enabled", "on", default=True),
            dict(group_summary),
        ),
    ]
    return DPARSFConversion(stage_configs=stages, warnings=warnings, unsupported_keys=unsupported)
