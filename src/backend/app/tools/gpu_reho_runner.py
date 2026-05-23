from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.backend.app.tools.reho_compute import compute_reho_backend, compute_reho_numpy


def run_reho_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    neighborhood: int = 27,
    use_gm_mask: bool = False,
    gm_mask_path: str | None = None,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    """Run single-subject ReHo computation with optional GPU acceleration."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    md = Path(derivatives_dir) / "rsfmri_metrics" / subject_id
    qd = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    md.mkdir(parents=True, exist_ok=True)
    qd.mkdir(parents=True, exist_ok=True)

    result_json = md / "reho_result.json"
    qc_json = qd / "reho_qc.json"
    qc_md = qd / "reho_qc.md"

    if not input_path.exists():
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Input NIfTI not found: {input_path}"], warnings)

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")
    except Exception as exc:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Failed to read input NIfTI: {exc}"], warnings)

    if data.ndim != 4:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Must be 4D. Got {data.shape}"], warnings)

    nx, ny, nz, nt = data.shape
    if nt < 2:
        return _fail(subject_id, result_json, qc_json, qc_md,
                     [f"Need >= 2 timepoints, got {nt}."], warnings)

    gm_mask = None
    gm_used = None
    if use_gm_mask:
        if gm_mask_path:
            try:
                gd = nib.load(gm_mask_path).get_fdata(dtype="float32")
                if list(gd.shape[:3]) == [nx, ny, nz]:
                    gm_mask = gd > 0.2
                    gm_used = gm_mask_path
                else:
                    warnings.append("GM shape mismatch; ignoring mask.")
            except Exception as exc:
                warnings.append(f"Cannot load GM mask: {exc}")

    result = compute_reho_backend(
        data_4d=data,
        neighborhood=neighborhood,
        gm_mask=gm_mask,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
    )

    if not result["ok"]:
        errors.extend(result.get("errors", []))
        return _fail(subject_id, result_json, qc_json, qc_md, errors, warnings)

    reho_map = result["reho"]

    # Save NIfTI
    rf = md / "reho.nii"
    h3 = img.header.copy()
    try:
        h3.set_data_shape(reho_map.shape)
    except Exception:
        pass
    nib.save(nib.Nifti1Image(reho_map, affine=img.affine, header=h3), str(rf))

    # Benchmark: CPU vs GPU comparison
    benchmark = None
    if benchmark_compare_cpu_gpu and result["backend"] != "cpu-numpy":
        try:
            cpu_result = compute_reho_numpy(data, neighborhood, gm_mask)
            if cpu_result["ok"] and cpu_result["reho"] is not None:
                diff = np.abs(reho_map - cpu_result["reho"])
                benchmark = {
                    "gpu_backend": result["backend"],
                    "gpu_runtime_s": result["runtime_seconds"],
                    "cpu_runtime_s": cpu_result["runtime_seconds"],
                    "speedup": round(cpu_result["runtime_seconds"] / max(result["runtime_seconds"], 0.001), 2),
                    "max_abs_diff": float(np.max(diff)),
                    "mean_abs_diff": float(np.mean(diff)),
                }
                if benchmark["max_abs_diff"] > 1e-3:
                    warnings.append(
                        f"GPU vs CPU max_abs_diff = {benchmark['max_abs_diff']:.2e} exceeds 1e-3. "
                        "Results may differ due to float32 precision or rank tie handling."
                    )
        except Exception as exc:
            warnings.append(f"CPU benchmark comparison failed: {exc}")

    # QC metrics
    fm = np.isfinite(reho_map)
    ff = float(np.count_nonzero(fm) / reho_map.size) if reho_map.size else 0.0
    nz = reho_map[reho_map != 0]
    if nz.size > 0:
        rmean, rstd, rmin, rmax = float(np.mean(nz)), float(np.std(nz)), float(np.min(nz)), float(np.max(nz))
    else:
        rmean = rstd = rmin = rmax = 0.0

    vc = result.get("valid_voxel_count", 0)
    sc = result.get("skipped_voxel_count", 0)
    status = "PASS"
    if vc == 0:
        status = "FAIL"
        errors.append("No valid voxels.")
    elif ff < 0.95:
        status = "WARNING"
        warnings.append("Finite fraction below 0.95.")
    elif rmin < -1e-6 or rmax > 1.000001:
        status = "WARNING"
        warnings.append(f"ReHo out of [0,1]: min={rmin}, max={rmax}")

    qc = {
        "ok": status != "FAIL",
        "node_id": "reho_qc_subject", "backend": result["backend"],
        "subject_id": subject_id, "input_nii": str(input_path),
        "reho_file": str(rf), "gm_map_used": gm_used,
        "input_shape": list(data.shape), "output_shape": list(reho_map.shape),
        "timepoints": int(nt), "neighborhood": neighborhood,
        "valid_voxel_count": vc, "skipped_voxel_count": sc,
        "finite_fraction": ff, "reho_mean": rmean, "reho_std": rstd,
        "reho_min": rmin, "reho_max": rmax,
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark, "reho_qc_status": status,
        "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors,
    }

    output = {
        "ok": status != "FAIL",
        "node_id": "reho_subject", "backend": result["backend"],
        "subject_id": subject_id, "input_nii": str(input_path),
        "reho_file": str(rf), "qc": qc,
        "outputs": [str(rf), str(result_json), str(qc_json), str(qc_md)],
        "gpu_backend": result["backend"],
        "runtime_seconds": result["runtime_seconds"],
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
    qc = {"ok": False, "node_id": "reho_qc_subject", "backend": "unknown",
          "subject_id": subject_id, "reho_qc_status": "FAIL",
          "outputs": [str(qj), str(qm)], "warnings": w, "errors": errors}
    result = {"ok": False, "node_id": "reho_subject", "backend": "unknown",
              "subject_id": subject_id, "outputs": [str(rj), str(qj), str(qm)],
              "warnings": w, "errors": errors}
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result


def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [
        f"# ReHo QC: {qc.get('subject_id')}", "",
        f"- OK: {qc.get('ok')}",
        f"- Status: {qc.get('reho_qc_status')}",
        f"- Input: `{qc.get('input_nii')}`",
        f"- ReHo: `{qc.get('reho_file')}`",
        f"- Neighborhood: {qc.get('neighborhood')}",
        f"- Timepoints: {qc.get('timepoints')}",
        f"- Valid voxels: {qc.get('valid_voxel_count')}",
        f"- Skipped: {qc.get('skipped_voxel_count')}",
        f"- Finite fraction: {qc.get('finite_fraction')}",
        f"- ReHo mean/std: {qc.get('reho_mean')}/{qc.get('reho_std')}",
        f"- Backend: {qc.get('gpu_backend', 'unknown')}",
        f"- Runtime: {qc.get('runtime_seconds', 'N/A')}s",
        "", "## Safety Note", "",
        "ReHo reads derivative files only and does not modify rawdata.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
