from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.backend.app.tools.temporal_filtering_compute import (
    compute_temporal_filter_backend,
    compute_temporal_filter_numpy,
)


def run_temporal_filtering_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    tr: float | None = None,
    low_hz: float = 0.01,
    high_hz: float = 0.08,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    """Run single-subject temporal filtering with optional GPU acceleration."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True)
    qc_dir.mkdir(parents=True, exist_ok=True)

    result_json = func_dir / "temporal_filtering_result.json"
    qc_json = qc_dir / "temporal_filtering_qc.json"
    qc_md = qc_dir / "temporal_filtering_qc.md"

    if not input_path.exists():
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Input NIfTI not found: {input_path}"], warnings)

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")
    except Exception as exc:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Failed to read input: {exc}"], warnings)

    if data.ndim != 4:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Must be 4D. Got {data.shape}"], warnings)

    _, _, _, n_time = data.shape
    if n_time < 4:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Need >= 4 timepoints, got {n_time}."], warnings)

    # Read TR from NIfTI header if not provided
    if tr is None:
        try:
            tr = float(img.header.get_zooms()[3])
        except Exception:
            tr = 2.0
            warnings.append("TR not found in header; using default 2.0s.")

    result = compute_temporal_filter_backend(
        data_4d=data,
        tr=tr,
        low_hz=low_hz,
        high_hz=high_hz,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
    )

    if not result["ok"]:
        errors.extend(result.get("errors", []))
        return _fail(subject_id, result_json, qc_json, qc_md, errors, warnings)

    filtered_4d = result["filtered_4d"]
    output_path = input_path.with_name(f"filt_{input_path.name}")
    out_img = nib.Nifti1Image(filtered_4d, affine=img.affine, header=img.header)
    nib.save(out_img, str(output_path))

    # Benchmark comparison
    benchmark = None
    if benchmark_compare_cpu_gpu and result["backend"] != "cpu-numpy":
        try:
            cpu_result = compute_temporal_filter_numpy(data, tr, low_hz, high_hz)
            if cpu_result["ok"] and cpu_result["filtered_4d"] is not None:
                diff = np.abs(filtered_4d - cpu_result["filtered_4d"])
                benchmark = {
                    "gpu_backend": result["backend"],
                    "gpu_runtime_s": result["runtime_seconds"],
                    "cpu_runtime_s": cpu_result["runtime_seconds"],
                    "speedup": round(cpu_result["runtime_seconds"] / max(result["runtime_seconds"], 0.001), 2),
                    "max_abs_diff": float(np.max(diff)),
                    "mean_abs_diff": float(np.mean(diff)),
                }
                if benchmark["max_abs_diff"] > 1e-4:
                    warnings.append(
                        f"GPU vs CPU max_abs_diff = {benchmark['max_abs_diff']:.2e} exceeds 1e-4."
                    )
        except Exception as exc:
            warnings.append(f"CPU benchmark comparison failed: {exc}")

    input_std = result.get("input_std", float(np.std(data)))
    filtered_std_val = result.get("filtered_std", float(np.std(filtered_4d)))
    finite_fraction = result.get("finite_fraction", 1.0)
    retained_bins = result.get("retained_frequency_bin_count", 0)

    status = "PASS"
    if finite_fraction < 0.95:
        status = "WARNING"
        warnings.append(f"Finite fraction {finite_fraction:.4f} below 0.95.")
    if retained_bins == 0:
        status = "FAIL"
        errors.append("No frequency bins retained; check filter band.")

    qc = {
        "ok": status != "FAIL", "node_id": "temporal_filtering_qc_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "output_nii": str(output_path),
        "input_shape": list(data.shape), "output_shape": list(filtered_4d.shape),
        "timepoints": n_time, "tr": tr,
        "low_hz": low_hz, "high_hz": high_hz,
        "retained_frequency_bin_count": retained_bins,
        "finite_fraction": finite_fraction,
        "input_intensity_std": input_std, "filtered_std": filtered_std_val,
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark, "temporal_filtering_qc_status": status,
        "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors,
    }

    output = {
        "ok": status != "FAIL", "node_id": "temporal_filtering_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "output_nii": str(output_path),
        "qc": qc,
        "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)],
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark,
        "warnings": warnings, "errors": errors,
    }

    result_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    qc_json.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qc_md, qc)
    return output


def _fail(subject_id: str, rj: Path, qj: Path, qm: Path,
          errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "temporal_filtering_qc_subject", "backend": "unknown",
          "subject_id": subject_id, "temporal_filtering_qc_status": "FAIL",
          "outputs": [str(qj), str(qm)], "warnings": w, "errors": errors}
    result = {"ok": False, "node_id": "temporal_filtering_subject", "backend": "unknown",
              "subject_id": subject_id, "outputs": [str(rj), str(qj), str(qm)],
              "warnings": w, "errors": errors}
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result


def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [
        f"# Temporal Filtering QC: {qc.get('subject_id')}", "",
        f"- OK: {qc.get('ok')}",
        f"- Status: {qc.get('temporal_filtering_qc_status')}",
        f"- Input: `{qc.get('input_nii')}`",
        f"- Output: `{qc.get('output_nii')}`",
        f"- TR: {qc.get('tr')}s, band: {qc.get('low_hz')}-{qc.get('high_hz')} Hz",
        f"- Timepoints: {qc.get('timepoints')}",
        f"- Retained bins: {qc.get('retained_frequency_bin_count')}",
        f"- Finite fraction: {qc.get('finite_fraction')}",
        f"- Input std: {qc.get('input_intensity_std')}",
        f"- Filtered std: {qc.get('filtered_std')}",
        f"- Backend: {qc.get('gpu_backend', 'unknown')}",
        f"- Runtime: {qc.get('runtime_seconds', 'N/A')}s",
        "", "## Safety Note", "",
        "Temporal filtering reads derivative files only and does not modify rawdata.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
