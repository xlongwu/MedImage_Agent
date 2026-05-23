from __future__ import annotations

import csv
import json
import time
from pathlib import Path
from typing import Any

import nibabel as nib
import numpy as np

from src.backend.app.tools.functional_connectivity_compute import (
    compute_fc_backend,
    compute_fc_numpy,
    _generate_atlas,
    _fisher_z,
)


def _write_tsv(path: Path, header: list[str], rows: list[list[float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t")
        w.writerow(header)
        w.writerows(rows)


def run_functional_connectivity_subject(
    subject_id: str,
    input_nii: str,
    derivatives_dir: str,
    roi_count: int = 4,
    atlas_path: str | None = None,
    generate_seed_map: bool = False,
    prefer_gpu: bool = True,
    require_gpu: bool = False,
    benchmark_compare_cpu_gpu: bool = True,
) -> dict[str, Any]:
    """Run single-subject functional connectivity with optional GPU acceleration."""
    t_start = time.perf_counter()
    warnings: list[str] = []
    errors: list[str] = []

    input_path = Path(input_nii)
    fcd = Path(derivatives_dir) / "rsfmri_fc" / subject_id
    qcd = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    fcd.mkdir(parents=True, exist_ok=True)
    qcd.mkdir(parents=True, exist_ok=True)

    rj = fcd / "fc_result.json"
    qj = qcd / "functional_connectivity_qc.json"
    qm = qcd / "functional_connectivity_qc.md"

    if not input_path.exists():
        return _fail(subject_id, rj, qj, qm,
                     [f"Input NIfTI not found: {input_path}"], warnings)

    try:
        img = nib.load(str(input_path))
        data = img.get_fdata(dtype="float32")
    except Exception as exc:
        return _fail(subject_id, rj, qj, qm,
                     [f"Failed to read input: {exc}"], warnings)

    if data.ndim != 4:
        return _fail(subject_id, rj, qj, qm,
                     [f"Must be 4D. Got {data.shape}"], warnings)

    nx, ny, nz, nt = data.shape

    # Load or generate atlas
    roi_defs = []
    if atlas_path:
        af = Path(atlas_path)
        if not af.exists():
            return _fail(subject_id, rj, qj, qm,
                         [f"Atlas not found: {af}"], warnings)
        try:
            ad = nib.load(str(af)).get_fdata().astype("int16")
            if list(ad.shape[:3]) != [nx, ny, nz]:
                return _fail(subject_id, rj, qj, qm,
                             ["Atlas shape mismatch."], warnings)
            labels = sorted(int(x) for x in np.unique(ad) if int(x) > 0)
            roi_defs = [{"label": l, "name": f"ROI_{l}", "strategy": "provided"} for l in labels]
        except Exception as exc:
            return _fail(subject_id, rj, qj, qm,
                         [f"Failed to read atlas: {exc}"], warnings)
    else:
        ad, roi_defs = _generate_atlas((nx, ny, nz), int(roi_count))
        af = fcd / "synthetic_roi_atlas.nii"
        h3 = img.header.copy()
        try:
            h3.set_data_shape(ad.shape)
        except Exception:
            pass
        nib.save(nib.Nifti1Image(ad.astype("int16"), affine=img.affine, header=h3), str(af))

    (fcd / "roi_definitions.json").write_text(
        json.dumps({"subject_id": subject_id, "atlas_file": str(af),
                    "roi_definitions": roi_defs, "synthetic": atlas_path is None},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    labels = [int(d["label"]) for d in roi_defs]
    names = [str(d.get("name", f"ROI_{l}")) for d, l in zip(roi_defs, labels)]

    result = compute_fc_backend(
        data_4d=data,
        atlas_3d=ad,
        generate_seed_map=generate_seed_map,
        prefer_gpu=prefer_gpu,
        require_gpu=require_gpu,
    )

    if not result["ok"]:
        errors.extend(result.get("errors", []))
        return _fail(subject_id, rj, qj, qm, errors, warnings)

    corr = result["correlation_matrix"]
    fz = result["fisher_z_matrix"]

    # Write outputs
    ttsv = fcd / "roi_timeseries.tsv"
    ctsv = fcd / "correlation_matrix.tsv"
    ftsv = fcd / "fisher_z_matrix.tsv"
    cjson = fcd / "correlation_matrix.json"
    fjson = fcd / "fisher_z_matrix.json"

    # Reconstruct ROI time-series for TSV output
    flat = data.reshape((-1, nt)).astype(np.float64)
    rts_list = []
    for label in labels:
        mask = (ad.ravel() == label)
        if np.any(mask):
            rts_list.append(np.mean(flat[mask, :], axis=0))
        else:
            rts_list.append(np.zeros(nt))
    rta = np.vstack(rts_list) if rts_list else np.zeros((0, nt))

    _write_tsv(ttsv, names, [[float(rta[ri, t]) for ri in range(len(labels))] for t in range(nt)])
    _write_tsv(ctsv, ["roi"] + names, [[names[i]] + [float(x) for x in corr[i]] for i in range(len(names))])
    _write_tsv(ftsv, ["roi"] + names, [[names[i]] + [float(x) for x in fz[i]] for i in range(len(names))])
    cjson.write_text(json.dumps({"subject_id": subject_id, "roi_names": names, "matrix": corr.tolist()}, ensure_ascii=False, indent=2), encoding="utf-8")
    fjson.write_text(json.dumps({"subject_id": subject_id, "roi_names": names, "matrix": fz.tolist()}, ensure_ascii=False, indent=2), encoding="utf-8")

    # Seed map
    scf = None
    szf = None
    sgen = False
    if generate_seed_map and result["seed_correlation_map"] is not None:
        scf = fcd / "seed_correlation_map.nii"
        szf = fcd / "seed_fisher_z_map.nii"
        mh = img.header.copy()
        try:
            mh.set_data_shape(result["seed_correlation_map"].shape)
        except Exception:
            pass
        nib.save(nib.Nifti1Image(result["seed_correlation_map"], affine=img.affine, header=mh), str(scf))
        nib.save(nib.Nifti1Image(result["seed_fisher_z_map"], affine=img.affine, header=mh), str(szf))
        sgen = True

    # Benchmark
    benchmark = None
    if benchmark_compare_cpu_gpu and result["backend"] != "cpu-numpy":
        try:
            cpu_r = compute_fc_numpy(data, ad, generate_seed_map)
            if cpu_r["ok"] and cpu_r["correlation_matrix"] is not None:
                diff = np.abs(corr - cpu_r["correlation_matrix"])
                benchmark = {
                    "gpu_backend": result["backend"],
                    "gpu_runtime_s": result["runtime_seconds"],
                    "cpu_runtime_s": cpu_r["runtime_seconds"],
                    "speedup": round(cpu_r["runtime_seconds"] / max(result["runtime_seconds"], 0.001), 2),
                    "max_abs_diff": float(np.max(diff)),
                    "mean_abs_diff": float(np.mean(diff)),
                }
        except Exception as exc:
            warnings.append(f"CPU benchmark comparison failed: {exc}")

    cff = float(np.count_nonzero(np.isfinite(corr)) / corr.size) if corr.size else 0.0
    fff = float(np.count_nonzero(np.isfinite(fz)) / fz.size) if fz.size else 0.0
    dm = float(np.mean(np.diag(corr))) if corr.size else None
    smd = float(np.max(np.abs(corr - corr.T))) if corr.size else None

    status = "PASS"
    if len(labels) == 0:
        status = "FAIL"
        errors.append("No ROIs.")
    elif cff < 1.0 or fff < 1.0:
        status = "WARNING"

    qc = {
        "ok": status != "FAIL", "node_id": "functional_connectivity_qc_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "atlas_file": str(af),
        "input_shape": list(data.shape), "atlas_shape": list(ad.shape),
        "timepoints": int(nt), "roi_count": len(labels), "roi_names": names,
        "correlation_matrix_shape": list(corr.shape),
        "correlation_finite_fraction": cff, "fisher_z_finite_fraction": fff,
        "diagonal_mean": dm, "symmetry_max_abs_diff": smd,
        "seed_map_generated": sgen,
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark, "fc_qc_status": status,
        "outputs": [str(qj), str(qm)], "warnings": warnings, "errors": errors,
    }

    outputs = [str(af), str(fcd / "roi_definitions.json"), str(ttsv), str(ctsv), str(cjson), str(ftsv), str(fjson), str(rj), str(qj), str(qm)]
    if scf:
        outputs.append(str(scf))
    if szf:
        outputs.append(str(szf))

    output = {
        "ok": status != "FAIL", "node_id": "functional_connectivity_subject",
        "backend": result["backend"], "subject_id": subject_id,
        "input_nii": str(input_path), "atlas_file": str(af),
        "roi_definitions": roi_defs, "roi_timeseries_tsv": str(ttsv),
        "correlation_matrix_tsv": str(ctsv), "correlation_matrix_json": str(cjson),
        "fisher_z_matrix_tsv": str(ftsv), "fisher_z_matrix_json": str(fjson),
        "seed_correlation_map": str(scf) if scf else None,
        "seed_fisher_z_map": str(szf) if szf else None,
        "qc": qc, "outputs": outputs,
        "gpu_backend": result["backend"], "runtime_seconds": result["runtime_seconds"],
        "benchmark": benchmark,
        "warnings": warnings, "errors": errors,
    }

    rj.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return output


def _fail(subject_id: str, rj: Path, qj: Path, qm: Path,
          errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "functional_connectivity_qc_subject", "backend": "unknown",
          "subject_id": subject_id, "fc_qc_status": "FAIL",
          "outputs": [str(qj), str(qm)], "warnings": w, "errors": errors}
    result = {"ok": False, "node_id": "functional_connectivity_subject", "backend": "unknown",
              "subject_id": subject_id, "outputs": [str(rj), str(qj), str(qm)],
              "warnings": w, "errors": errors}
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result


def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [
        f"# FC QC: {qc.get('subject_id')}", "",
        f"- OK: {qc.get('ok')}",
        f"- Status: {qc.get('fc_qc_status')}",
        f"- ROI count: {qc.get('roi_count')}",
        f"- Timepoints: {qc.get('timepoints')}",
        f"- Correlation finite: {qc.get('correlation_finite_fraction')}",
        f"- Symmetry diff: {qc.get('symmetry_max_abs_diff')}",
        f"- Seed map: {qc.get('seed_map_generated')}",
        f"- Backend: {qc.get('gpu_backend', 'unknown')}",
        f"- Runtime: {qc.get('runtime_seconds', 'N/A')}s",
        "", "## Safety Note", "",
        "FC reads derivative files only and does not modify rawdata.",
    ]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
