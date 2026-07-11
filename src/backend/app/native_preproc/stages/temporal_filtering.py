"""Native temporal filtering stage with explicit DPABI-like band semantics."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.dpabi_compat.qc_rules import validate_frequency_rule
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC


def _normalized_filter_type(filter_type: str) -> str:
    value = filter_type.lower().replace("_", "-")
    aliases = {"bandpass": "band-pass", "highpass": "high-pass", "lowpass": "low-pass", "none": "no-filter"}
    return aliases.get(value, value)


def _frequency_mask(freqs: np.ndarray, *, filter_type: str, low_hz: float | None, high_hz: float | None) -> np.ndarray:
    normalized = _normalized_filter_type(filter_type)
    if normalized == "band-pass":
        return (freqs >= float(low_hz)) & (freqs <= float(high_hz))
    if normalized == "high-pass":
        return freqs >= float(low_hz)
    if normalized == "low-pass":
        return freqs <= float(high_hz)
    if normalized == "no-filter":
        return np.ones_like(freqs, dtype=bool)
    raise ValueError(f"Unsupported filter_type: {filter_type}")


def temporal_filter_4d(
    data_4d: np.ndarray,
    *,
    tr: float,
    filter_type: str = "band-pass",
    low_hz: float | None = 0.01,
    high_hz: float | None = 0.08,
    method: str = "fft",
    order: int = 2,
) -> tuple[np.ndarray, dict[str, Any]]:
    data = np.asarray(data_4d, dtype=np.float32)
    ensure_4d(data, stage_id="temporal_filtering")
    if not np.isfinite(data).all():
        raise ValueError("input BOLD contains NaN or infinite values.")
    rule = validate_frequency_rule(filter_type=filter_type, tr=float(tr), low_hz=low_hz, high_hz=high_hz)
    if rule.errors:
        raise ValueError("; ".join(rule.errors))
    normalized = _normalized_filter_type(rule.filter_type)
    n_timepoints = int(data.shape[3])
    if normalized != "no-filter" and n_timepoints < 4:
        raise ValueError("temporal filtering requires at least 4 timepoints.")
    if normalized == "no-filter":
        return data.copy(), {
            "filter_type": normalized,
            "method": "no-filter",
            "tr": float(tr),
            "nyquist_hz": rule.nyquist_hz,
            "frequency_bin_count": int(len(np.fft.rfftfreq(n_timepoints, d=float(tr)))),
            "retained_frequency_bin_count": int(len(np.fft.rfftfreq(n_timepoints, d=float(tr)))),
            "retained_frequency_fraction": 1.0,
        }

    method_name = method.lower()
    freqs = np.fft.rfftfreq(n_timepoints, d=float(tr))
    mask = _frequency_mask(freqs, filter_type=normalized, low_hz=rule.low_hz, high_hz=rule.high_hz)
    retained = int(np.count_nonzero(mask))
    if retained == 0:
        raise ValueError("No frequency bins retained for requested temporal filter.")
    if method_name == "fft":
        spectrum = np.fft.rfft(data, axis=3)
        spectrum[..., ~mask] = 0.0
        filtered = np.fft.irfft(spectrum, n=n_timepoints, axis=3).astype(np.float32)
    elif method_name == "butterworth":
        from scipy import signal

        if normalized == "band-pass":
            wn: Any = [float(rule.low_hz) / rule.nyquist_hz, float(rule.high_hz) / rule.nyquist_hz]
            btype = "bandpass"
        elif normalized == "high-pass":
            wn = float(rule.low_hz) / rule.nyquist_hz
            btype = "highpass"
        else:
            wn = float(rule.high_hz) / rule.nyquist_hz
            btype = "lowpass"
        sos = signal.butter(int(order), wn, btype=btype, output="sos")
        flat = data.reshape((-1, n_timepoints))
        filtered = signal.sosfiltfilt(sos, flat, axis=1).reshape(data.shape).astype(np.float32)
    else:
        raise ValueError(f"Unsupported temporal filtering method: {method}")

    return filtered, {
        "filter_type": normalized,
        "method": method_name,
        "tr": float(tr),
        "nyquist_hz": rule.nyquist_hz,
        "low_hz": rule.low_hz,
        "high_hz": rule.high_hz,
        "frequency_bin_count": int(len(freqs)),
        "retained_frequency_bin_count": retained,
        "retained_frequency_fraction": float(retained / len(freqs)),
    }


def run_temporal_filtering(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    tr: float,
    filter_type: str = "band-pass",
    low_hz: float | None = 0.01,
    high_hz: float | None = 0.08,
    method: str = "fft",
    order: int = 2,
    tr_source: str = "parameter",
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = "temporal_filtering"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters = {
        "tr": float(tr),
        "tr_source": tr_source,
        "filter_type": filter_type,
        "low_hz": low_hz,
        "high_hz": high_hz,
        "method": method,
        "order": int(order),
        "regression_filtering_order": "regress_then_detrend_then_filter",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        filtered, filter_qc = temporal_filter_4d(
            image.data,
            tr=tr,
            filter_type=filter_type,
            low_hz=low_hz,
            high_hz=high_hz,
            method=method,
            order=order,
        )
        if float(np.std(image.data)) == 0.0:
            warnings.append("constant_input_signal")
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix="filtered_bold",
        )
        save_nifti(output_path, filtered, image.affine, header=image.header)
        output_ref = build_artifact_ref(output_path, artifact_type="filtered_bold", metadata=filter_qc)
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in filtered.shape],
                "timepoints_preserved": bool(filtered.shape[3] == image.data.shape[3]),
                "filter": filter_qc,
                "input_stats": finite_stats(image.data),
                "output_stats": finite_stats(filtered),
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, **filter_qc},
            status="warning" if warnings else "succeeded",
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=errors,
        )
    except Exception as exc:
        errors.append(str(exc))
        qc = NativePreprocQC(status="fail", errors=errors)
        return stage_result(
            context,
            stage_id=stage_id,
            parameters=parameters,
            status="blocked",
            capability_level="numerically_implemented",
            qc=qc,
            warnings=warnings,
            errors=errors,
        )
