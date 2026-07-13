"""Native nuisance regression stage with DPABI-like confound semantics."""
from __future__ import annotations

from pathlib import Path
from time import perf_counter
from typing import Any

import numpy as np

from src.backend.app.native_preproc.core.qc import finite_stats
from src.backend.app.native_preproc.core.compute_backend import (
    GpuComputeError,
    compute_nuisance_regression_gpu,
    cpu_compute_provenance,
)
from src.backend.app.native_preproc.dpabi_compat.regressors import (
    RegressorMatrix,
    combine_regressor_matrices,
    extract_global_signal,
    extract_mask_mean_signal,
    load_motion_regressors,
    polynomial_trends,
    read_numeric_tsv,
    scrubbing_regressors,
    write_matrix_tsv,
)
from src.backend.app.native_preproc.io.derivative_naming import derivative_path
from src.backend.app.native_preproc.io.nifti_io import ensure_4d, load_nifti, save_nifti
from src.backend.app.native_preproc.orchestrator.artifact_registry import build_artifact_ref
from src.backend.app.native_preproc.orchestrator.gpu_resource_planner import plan_gpu_stage
from src.backend.app.native_preproc.stages._common import context_from_output_dir, stage_result
from src.backend.app.schemas.native_preproc import NativePreprocQC
from src.backend.app.schemas.native_preproc_api import NativeComputePolicy


def regress_confounds(data_4d: np.ndarray, confounds: np.ndarray) -> np.ndarray:
    data = np.asarray(data_4d, dtype=np.float32)
    ensure_4d(data, stage_id="nuisance_regression")
    matrix = np.asarray(confounds, dtype=np.float32)
    if matrix.ndim != 2:
        raise ValueError("confounds must be a 2D matrix.")
    n_timepoints = int(data.shape[3])
    if n_timepoints < 3:
        raise ValueError("nuisance regression requires at least 3 timepoints.")
    if matrix.shape[0] != n_timepoints:
        raise ValueError(f"confound rows {matrix.shape[0]} do not match timepoints {n_timepoints}.")
    if matrix.shape[1] == 0:
        raise ValueError("confound matrix must contain at least one column.")
    if not np.isfinite(matrix).all():
        raise ValueError("confound matrix contains NaN or infinite values.")
    if not np.isfinite(data).all():
        raise ValueError("input BOLD contains NaN or infinite values.")

    original_shape = data.shape
    flat = data.reshape((-1, n_timepoints))
    beta = np.linalg.lstsq(matrix.astype(np.float64), flat.T.astype(np.float64), rcond=None)[0]
    predicted = matrix.astype(np.float64) @ beta
    residual = flat.astype(np.float64) - predicted.T
    return residual.reshape(original_shape).astype(np.float32)


def regress_confounds_with_backend(
    data_4d: np.ndarray,
    confounds: np.ndarray,
    *,
    compute_policy: NativeComputePolicy | None = None,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Keep design construction on CPU, optionally offloading only linalg."""
    data = np.asarray(data_4d, dtype=np.float32)
    matrix = np.asarray(confounds, dtype=np.float32)
    policy = compute_policy or NativeComputePolicy()
    plan = plan_gpu_stage("nuisance_regression", input_shape=tuple(int(item) for item in data.shape), policy=policy)
    if plan.selected_backend == "blocked":
        raise ValueError("; ".join(plan.blocking_issues))
    if plan.selected_backend == "gpu":
        try:
            gpu = compute_nuisance_regression_gpu(data, matrix, plan=plan)
        except GpuComputeError as exc:
            if not plan.fallback_allowed:
                raise ValueError(str(exc)) from exc
            started_at = perf_counter()
            residual = regress_confounds(data, matrix)
            return residual, cpu_compute_provenance(plan, started_at=started_at, fallback_reason=str(exc))
        return gpu.arrays["residual"], gpu.provenance()
    started_at = perf_counter()
    residual = regress_confounds(data, matrix)
    fallback_reason = ",".join(plan.limiting_factors) if plan.requested_backend == "auto" and plan.limiting_factors else None
    return residual, cpu_compute_provenance(plan, started_at=started_at, fallback_reason=fallback_reason)


def _load_optional_mask(path: str | Path | None) -> np.ndarray | None:
    if not path:
        return None
    return load_nifti(path).data


def _confound_parts(
    *,
    data: np.ndarray,
    motion_parameters: str | Path | None,
    motion_model: str,
    wm_mask: str | Path | None,
    csf_mask: str | Path | None,
    brain_mask: str | Path | None,
    include_wm: bool,
    include_csf: bool,
    include_global_signal: bool,
    polynomial_order: int,
    include_intercept: bool,
    fd_timeseries: str | Path | None,
    scrub_threshold_mm: float | None,
    mask_threshold: float,
) -> list[RegressorMatrix]:
    parts: list[RegressorMatrix] = [
        polynomial_trends(data.shape[3], order=polynomial_order, include_intercept=include_intercept)
    ]
    if motion_parameters:
        parts.append(load_motion_regressors(motion_parameters, model=motion_model))
    if include_wm:
        wm = _load_optional_mask(wm_mask)
        if wm is None:
            raise ValueError("include_wm=True requires wm_mask.")
        parts.append(extract_mask_mean_signal(data, wm, column_name="wm_signal", threshold=mask_threshold))
    if include_csf:
        csf = _load_optional_mask(csf_mask)
        if csf is None:
            raise ValueError("include_csf=True requires csf_mask.")
        parts.append(extract_mask_mean_signal(data, csf, column_name="csf_signal", threshold=mask_threshold))
    if include_global_signal:
        parts.append(
            extract_global_signal(
                data,
                brain_mask_3d=_load_optional_mask(brain_mask),
                threshold=mask_threshold,
            )
        )
    if fd_timeseries and scrub_threshold_mm is not None:
        fd = read_numeric_tsv(fd_timeseries, min_columns=1)[:, 0]
        parts.append(scrubbing_regressors(fd, threshold_mm=scrub_threshold_mm, n_timepoints=data.shape[3]))
    return parts


def run_nuisance_regression(
    input_bold: str | Path,
    output_dir: str | Path,
    *,
    motion_parameters: str | Path | None = None,
    motion_model: str = "friston24",
    wm_mask: str | Path | None = None,
    csf_mask: str | Path | None = None,
    brain_mask: str | Path | None = None,
    include_wm: bool = False,
    include_csf: bool = False,
    include_global_signal: bool = False,
    polynomial_order: int = 1,
    include_intercept: bool = True,
    fd_timeseries: str | Path | None = None,
    scrub_threshold_mm: float | None = None,
    censoring_strategy: str = "spike_regressors",
    mask_threshold: float = 0.5,
    run_id: str = "native_preproc_run",
    subject_id: str = "",
    session_id: str = "",
    compute_policy: NativeComputePolicy | None = None,
):
    stage_id = "nuisance_regression"
    context = context_from_output_dir(output_dir, run_id=run_id, subject_id=subject_id, session_id=session_id)
    parameters: dict[str, Any] = {
        "motion_model": motion_model,
        "include_wm": include_wm,
        "include_csf": include_csf,
        "include_global_signal": include_global_signal,
        "polynomial_order": int(polynomial_order),
        "include_intercept": include_intercept,
        "scrub_threshold_mm": scrub_threshold_mm,
        "censoring_strategy": censoring_strategy,
        "mask_threshold": float(mask_threshold),
        "regression_filtering_order": "regress_then_detrend_then_filter",
    }
    warnings: list[str] = []
    errors: list[str] = []

    try:
        if censoring_strategy not in {"spike_regressors", "spike_regressors_preserve_timepoints"}:
            raise ValueError("Only spike-regressor censoring is implemented; timepoint-dropping censoring is not supported.")
        image = load_nifti(input_bold)
        ensure_4d(image.data, stage_id=stage_id)
        parts = _confound_parts(
            data=image.data,
            motion_parameters=motion_parameters,
            motion_model=motion_model,
            wm_mask=wm_mask,
            csf_mask=csf_mask,
            brain_mask=brain_mask,
            include_wm=include_wm,
            include_csf=include_csf,
            include_global_signal=include_global_signal,
            polynomial_order=polynomial_order,
            include_intercept=include_intercept,
            fd_timeseries=fd_timeseries,
            scrub_threshold_mm=scrub_threshold_mm,
            mask_threshold=mask_threshold,
        )
        confounds = combine_regressor_matrices(*parts)
        residual, compute_provenance = regress_confounds_with_backend(
            image.data,
            confounds.values,
            compute_policy=compute_policy,
        )
        if compute_provenance.get("fallback_reason"):
            warnings.append(f"gpu_fallback:{compute_provenance['fallback_reason']}")
        qc_metrics = confounds.qc
        if qc_metrics["rank"] >= image.data.shape[3]:
            warnings.append("confound_matrix_rank_reaches_timepoints_overfit_risk")
        if float(np.std(image.data)) == 0.0:
            warnings.append("constant_input_signal")

        stage_dir = context.stage_artifact_dir(stage_id)
        residual_path = derivative_path(stage_dir, image.path, stage_id=stage_id, suffix="residual_bold")
        confounds_path = derivative_path(
            stage_dir,
            image.path,
            stage_id=stage_id,
            suffix="confounds",
            extension=".tsv",
        )
        qc_md_path = context.qc_markdown_path(stage_id)
        save_nifti(residual_path, residual, image.affine, header=image.header)
        write_matrix_tsv(confounds_path, confounds.columns, confounds.values)
        qc_md_path.parent.mkdir(parents=True, exist_ok=True)
        qc_md_path.write_text(
            "\n".join(
                [
                    "# Native Nuisance Regression QC",
                    "",
                    f"- Confound columns: {len(confounds.columns)}",
                    f"- Matrix rank: {qc_metrics['rank']}",
                    f"- Censoring strategy: {censoring_strategy}",
                    f"- Residual finite fraction: {finite_stats(residual)['finite_fraction']}",
                ]
            )
            + "\n",
            encoding="utf-8",
        )

        output_refs = [
            build_artifact_ref(residual_path, artifact_type="residual_bold", metadata={"source": "nuisance_regression"}),
            build_artifact_ref(
                confounds_path,
                artifact_type="confound_matrix",
                metadata={"columns": confounds.columns, **confounds.metadata},
            ),
            build_artifact_ref(qc_md_path, artifact_type="qc_md", metadata={"format": "markdown"}),
        ]
        status = "warning" if warnings else "succeeded"
        qc = NativePreprocQC(
            status="warning" if warnings else "pass",
            metrics={
                "input_shape": [int(value) for value in image.data.shape],
                "output_shape": [int(value) for value in residual.shape],
                "confound_matrix": qc_metrics,
                "compute": compute_provenance,
                "output_stats": finite_stats(residual),
                "timepoints_preserved": bool(residual.shape[3] == image.data.shape[3]),
            },
            warnings=warnings,
        )
        return stage_result(
            context,
            stage_id=stage_id,
            parameters={**parameters, "compute": compute_provenance},
            status=status,
            capability_level="numerically_implemented",
            qc=qc,
            output_artifacts=output_refs,
            warnings=warnings,
            errors=errors,
            backend="gpu" if compute_provenance.get("actual_backend") == "gpu-cupy" else "native_python",
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
