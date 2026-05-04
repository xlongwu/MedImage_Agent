from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from src.backend.app.tools.alff_compute import compute_alff_backend, compute_alff_numpy
from src.backend.app.tools.gpu_utils import detect_gpu


def _compare_arrays(a: np.ndarray, b: np.ndarray) -> dict[str, float]:
    diff = np.abs(a.astype("float32") - b.astype("float32"))
    return {
        "max_abs_diff": float(np.max(diff)),
        "mean_abs_diff": float(np.mean(diff)),
    }


def run_alff_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    tr: float = 2.0,
    freq_band: list[float] | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError:
        return {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": [],
            "errors": ["Missing dependency: nibabel. Install with: pip install nibabel"],
        }

    freq_band = freq_band or [0.01, 0.08]
    band_tuple = (float(freq_band[0]), float(freq_band[1]))

    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    if not input_path.exists():
        return {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": [],
            "errors": [f"Input smoothed BOLD not found: {input_path}"],
        }

    out_dir = Path(derivatives_dir) / "gpu_alff" / subject_id / "func"
    out_dir.mkdir(parents=True, exist_ok=True)

    alff_path = out_dir / f"{subject_id}_alff.nii"
    falff_path = out_dir / f"{subject_id}_falff.nii"
    result_json = out_dir / "gpu_alff_result.json"

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")

        if data.ndim != 4:
            raise ValueError(f"Expected 4D BOLD input, got shape={data.shape}")

        gpu_info = detect_gpu()
        warnings.extend(gpu_info.get("warnings", []))

        result = compute_alff_backend(
            data=data,
            tr=tr,
            freq_band=band_tuple,
            prefer_gpu=prefer_gpu,
            require_gpu=require_gpu,
        )

        warnings.extend(result.get("warnings", []))
        errors.extend(result.get("errors", []))

        if not result.get("ok"):
            payload = {
                "ok": False,
                "node_id": "gpu_alff_subject",
                "backend": result.get("backend"),
                "subject_id": subject_id,
                "outputs": [],
                "metrics": {},
                "warnings": warnings,
                "errors": errors,
            }
            result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            return payload

        alff = result["alff"]
        falff = result["falff"]

        nib.save(nib.Nifti1Image(alff.astype("float32"), img.affine, img.header), str(alff_path))
        nib.save(nib.Nifti1Image(falff.astype("float32"), img.affine, img.header), str(falff_path))

        comparison: dict[str, Any] = {}

        if benchmark_compare_cpu_gpu and result.get("backend") == "gpu-cupy":
            cpu_alff, cpu_falff, cpu_warnings = compute_alff_numpy(data, tr, band_tuple)
            warnings.extend([f"CPU benchmark: {item}" for item in cpu_warnings])

            alff_diff = _compare_arrays(cpu_alff, alff)
            falff_diff = _compare_arrays(cpu_falff, falff)

            comparison = {
                "max_abs_diff_alff": alff_diff["max_abs_diff"],
                "mean_abs_diff_alff": alff_diff["mean_abs_diff"],
                "max_abs_diff_falff": falff_diff["max_abs_diff"],
                "mean_abs_diff_falff": falff_diff["mean_abs_diff"],
            }

        metrics = {
            "backend": result.get("backend"),
            "gpu_available": gpu_info.get("gpu_available"),
            "cupy_available": gpu_info.get("cupy_available"),
            "device_name": gpu_info.get("device_name"),
            "runtime_seconds": result.get("runtime_seconds"),
            "input_shape": list(data.shape),
            "tr": tr,
            "freq_band": list(band_tuple),
            **comparison,
        }

        payload = {
            "ok": True,
            "node_id": "gpu_alff_subject",
            "backend": result.get("backend"),
            "subject_id": subject_id,
            "input": str(input_path),
            "outputs": [str(alff_path), str(falff_path), str(result_json)],
            "metrics": metrics,
            "warnings": warnings,
            "errors": errors,
        }

        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload

    except Exception as exc:
        payload = {
            "ok": False,
            "node_id": "gpu_alff_subject",
            "backend": "python",
            "subject_id": subject_id,
            "outputs": [],
            "metrics": {},
            "warnings": warnings,
            "errors": [f"Failed to run ALFF subject: {exc}"],
        }
        result_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return payload
