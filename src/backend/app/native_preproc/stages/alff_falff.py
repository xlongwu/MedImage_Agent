"""Native ALFF/fALFF stages with DPABI-like frequency-band semantics."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any, Literal

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.compute_backend import (
    GpuComputeError,
    compute_alff_falff_gpu,
    cpu_compute_provenance,
)
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import plan_gpu_stage
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy


StandardizationMode = Literal["none", "zscore"]


def _band_mask(freqs: np.ndarray, band: tuple[float, float], *, name: str) -> np.ndarray:
    low, high = float(band[0]), float(band[1])
    if low < 0.0:
        raise ValueError(f"{name} low frequency must be non-negative.")
    if high <= low:
        raise ValueError(f"{name} high frequency must be greater than low frequency.")
    nyquist = float(freqs[-1])
    if high > nyquist:
        raise ValueError(f"{name} high frequency {high} exceeds Nyquist {nyquist}.")
    mask = (freqs >= low) & (freqs <= high)
    if not np.any(mask):
        raise ValueError(f"No FFT bins found for {name} {band}.")
    return mask


def _apply_zscore_in_mask(values: np.ndarray, selected: np.ndarray, warnings: list[str], *, metric: str) -> np.ndarray:
    output = np.zeros_like(values, dtype=np.float32)
    sample = values[selected]
    if sample.size == 0:
        warnings.append(f"{metric}_standardization_skipped_empty_mask")
        return output
    std = float(np.std(sample))
    if std <= 1e-12:
        warnings.append(f"{metric}_standardization_skipped_zero_variance")
        output[selected] = values[selected]
        return output
    output[selected] = ((sample - float(np.mean(sample))) / std).astype(np.float32)
    return output


def compute_alff_falff_maps(
    data_4d: np.ndarray,
    *,
    tr: float,
    freq_band: tuple[float, float] = (0.01, 0.08),
    denominator_band: tuple[float, float] | None = None,
    mask_3d: np.ndarray | None = None,
    standardization: StandardizationMode = "none",
    compute_policy: NativeComputePolicy | None = None,
    compute_stage_id: Literal["alff", "falff"] = "alff",
) -> tuple[np.ndarray, np.ndarray, dict[str, Any], list[str]]:
    """Compute ALFF and fALFF maps from a 4D BOLD series.

    The numerator is the mean/sum amplitude within ``freq_band``.  By default
    fALFF uses all non-DC FFT bins as the denominator; callers may provide an
    explicit denominator band when a DPABI-compatible policy requires it.
    """

    warnings: list[str] = []
    data = np.asarray(data_4d, dtype=np.float32)
    ensure_4d(data, stage_id="alff_falff")
    if not np.isfinite(data).all():
        raise ValueError("input BOLD contains NaN or infinite values.")
    if tr <= 0.0:
        raise ValueError("TR must be positive.")
    n_timepoints = int(data.shape[3])
    if n_timepoints < 4:
        raise ValueError("ALFF/fALFF requires at least 4 timepoints.")

    if mask_3d is None:
        selected = np.ones(data.shape[:3], dtype=bool)
        mask_policy = "all_voxels"
    else:
        mask = np.asarray(mask_3d, dtype=np.float32)
        if mask.shape != data.shape[:3]:
            raise ValueError(f"mask shape {mask.shape} does not match BOLD spatial shape {data.shape[:3]}.")
        selected = np.isfinite(mask) & (mask > 0.0)
        mask_policy = "mask_positive_voxels"
        if not np.any(selected):
            raise ValueError("mask contains no selected voxels.")

    freqs = np.fft.rfftfreq(n_timepoints, d=float(tr))
    numerator_mask = _band_mask(freqs, freq_band, name="ALFF numerator band")
    if denominator_band is None:
        denominator_mask = freqs > 0.0
        denominator_policy = "all_non_dc_bins"
    else:
        denominator_mask = _band_mask(freqs, denominator_band, name="fALFF denominator band") & (freqs > 0.0)
        denominator_policy = "explicit_denominator_band"
    if not np.any(denominator_mask):
        raise ValueError("No non-DC FFT bins available for fALFF denominator.")

    policy = compute_policy or NativeComputePolicy()
    plan = plan_gpu_stage(compute_stage_id, input_shape=tuple(int(item) for item in data.shape), policy=policy)
    compute_backend = "cpu-numpy"
    compute_runtime: dict[str, Any] = {}
    fallback_reason: str | None = None
    if plan.selected_backend == "blocked":
        raise ValueError("; ".join(plan.blocking_issues))
    if plan.selected_backend == "gpu":
        try:
            gpu = compute_alff_falff_gpu(
                data,
                tr=tr,
                numerator_mask=numerator_mask,
                denominator_mask=denominator_mask,
                plan=plan,
            )
        except GpuComputeError as exc:
            if plan.fallback_allowed:
                warnings.append(f"gpu_fallback:{exc}")
                fallback_reason = str(exc)
            else:
                raise ValueError(str(exc)) from exc
        else:
            compute_backend = gpu.backend
            compute_runtime = gpu.provenance()
            raw_alff = gpu.arrays["raw_alff"]
            band_sum = gpu.arrays["band_sum"]
            denominator_sum = gpu.arrays["denominator_sum"]
    if compute_backend == "cpu-numpy":
        if plan.requested_backend == "auto" and plan.limiting_factors:
            fallback_reason = ",".join(plan.limiting_factors)
            warnings.append(f"gpu_fallback:{fallback_reason}")
        started_at = perf_counter()
        demeaned = data - np.mean(data, axis=3, keepdims=True)
        amplitude = np.abs(np.fft.rfft(demeaned, axis=3)).astype(np.float32)
        band_amp = amplitude[..., numerator_mask]
        denominator_amp = amplitude[..., denominator_mask]
        raw_alff = np.mean(band_amp, axis=3).astype(np.float32)
        band_sum = np.sum(band_amp, axis=3).astype(np.float32)
        denominator_sum = np.sum(denominator_amp, axis=3).astype(np.float32)
        compute_runtime = cpu_compute_provenance(plan, started_at=started_at, fallback_reason=fallback_reason)

    alff = np.zeros(data.shape[:3], dtype=np.float32)
    alff[selected] = raw_alff[selected]
    falff = np.zeros(data.shape[:3], dtype=np.float32)
    valid_denominator = selected & (denominator_sum > 0.0)
    falff[valid_denominator] = (band_sum[valid_denominator] / denominator_sum[valid_denominator]).astype(np.float32)
    zero_denominator_count = int(np.count_nonzero(selected & ~valid_denominator))
    if zero_denominator_count:
        warnings.append("falff_zero_denominator_voxels")

    if float(np.std(data[selected, :])) <= 1e-12:
        warnings.append("constant_input_signal")

    if standardization == "zscore":
        alff = _apply_zscore_in_mask(alff, selected, warnings, metric="alff")
        falff = _apply_zscore_in_mask(falff, selected, warnings, metric="falff")
    elif standardization != "none":
        raise ValueError(f"Unsupported standardization mode: {standardization}")

    qc = {
        "tr": float(tr),
        "timepoints": n_timepoints,
        "freq_band": [float(freq_band[0]), float(freq_band[1])],
        "denominator_band": [float(denominator_band[0]), float(denominator_band[1])] if denominator_band else None,
        "denominator_policy": denominator_policy,
        "nyquist_hz": float(freqs[-1]),
        "numerator_bin_count": int(np.count_nonzero(numerator_mask)),
        "denominator_bin_count": int(np.count_nonzero(denominator_mask)),
        "mask_policy": mask_policy,
        "mask_voxel_count": int(np.count_nonzero(selected)),
        "zero_denominator_voxel_count": zero_denominator_count,
        "standardization": standardization,
        "alff_stats": finite_stats(alff),
        "falff_stats": finite_stats(falff),
        "compute": compute_runtime,
    }
    return alff, falff, qc, warnings


def _run_alff_or_falff(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    metric: Literal["alff", "falff"],
    tr: float,
    freq_band: tuple[float, float] = (0.01, 0.08),
    denominator_band: tuple[float, float] | None = None,
    mask: str | Path | None = None,
    standardization: StandardizationMode = "none",
    compute_policy: NativeComputePolicy | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    stage_id = metric
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters: dict[str, Any] = {
        "tr": float(tr),
        "freq_band": [float(freq_band[0]), float(freq_band[1])],
        "denominator_band": [float(denominator_band[0]), float(denominator_band[1])] if denominator_band else None,
        "mask_provided": bool(mask),
        "standardization": standardization,
        "implementation_note": "native_numpy_fft_clean_room_rewrite_from_existing_formula",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        image = load_nifti(input_bold)
        mask_data = load_nifti(mask).data if mask else None
        alff, falff, metric_qc, compute_warnings = compute_alff_falff_maps(
            image.data,
            tr=tr,
            freq_band=freq_band,
            denominator_band=denominator_band,
            mask_3d=mask_data,
            standardization=standardization,
            compute_policy=compute_policy,
            compute_stage_id=metric,
        )
        warnings.extend(compute_warnings)
        output_data = alff if metric == "alff" else falff
        output_type = "alff_map" if metric == "alff" else "falff_map"
        output_path = derivative_path(
            context.stage_artifact_dir(stage_id),
            image.path,
            stage_id=stage_id,
            suffix=output_type,
        )
        save_nifti(output_path, output_data, image.affine, header=image.header)
        output_ref = build_artifact_ref(output_path, artifact_type=output_type, metadata=metric_qc)
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in output_data.shape],
                "metric": metric,
                **metric_qc,
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, **metric_qc},
            status="warning" if warnings else "succeeded",
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=[output_ref],
            warnings=warnings,
            errors=errors,
            backend="gpu" if metric_qc["compute"].get("actual_backend") == "gpu-cupy" else "native_python",
        )
    except Exception as exc:
        errors.append(str(exc))
        qc = NativePreprocQC(status="fail", warnings=warnings, errors=errors)
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


def run_alff(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    tr: float,
    freq_band: tuple[float, float] = (0.01, 0.08),
    denominator_band: tuple[float, float] | None = None,
    mask: str | Path | None = None,
    standardization: StandardizationMode = "none",
    compute_policy: NativeComputePolicy | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    return _run_alff_or_falff(
        input_bold,
        output_dir,
        metric="alff",
        tr=tr,
        freq_band=freq_band,
        denominator_band=denominator_band,
        mask=mask,
        standardization=standardization,
        compute_policy=compute_policy,
        run_id=run_id,
        subject_id=subject_id,
        session_id=session_id,
    )


def run_falff(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    tr: float,
    freq_band: tuple[float, float] = (0.01, 0.08),
    denominator_band: tuple[float, float] | None = None,
    mask: str | Path | None = None,
    standardization: StandardizationMode = "none",
    compute_policy: NativeComputePolicy | None = None,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
):
    return _run_alff_or_falff(
        input_bold,
        output_dir,
        metric="falff",
        tr=tr,
        freq_band=freq_band,
        denominator_band=denominator_band,
        mask=mask,
        standardization=standardization,
        compute_policy=compute_policy,
        run_id=run_id,
        subject_id=subject_id,
        session_id=session_id,
    )
