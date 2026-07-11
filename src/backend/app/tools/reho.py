from __future__ import annotations
import json
from pathlib import Path
from statistics import mean
from typing import Any

from src.backend.app.tools import reho_compute

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _find_filtered(subject_id: str, derivatives_dir: str) -> Path | None:
    d = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not d.exists(): return None
    p = d / f"filt_resid_swra{subject_id}_bold.nii"
    if p.exists(): return p
    c = sorted(d.glob("filt_resid_swr*.nii")); return c[0] if c else None

def _safe_filtered(path: Path, subject_id: str, derivatives_dir: str) -> bool:
    fd = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    try: path.resolve().relative_to(fd)
    except ValueError: return False
    return path.name.startswith("filt_resid_swr") and path.name.endswith(".nii")

def _find_gm(subject_id: str, derivatives_dir: str) -> Path | None:
    d = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "anat"
    if not d.exists(): return None
    p = d / f"c1coreg_{subject_id}_T1w.nii"
    if p.exists(): return p
    c = sorted(d.glob("c1*.nii")); return c[0] if c else None

def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [f"# ReHo QC: {qc.get('subject_id')}", "", f"- OK: {qc.get('ok')}", f"- Status: {qc.get('reho_qc_status')}", f"- Input: `{qc.get('input_nii')}`", f"- ReHo: `{qc.get('reho_file')}`", f"- Neighborhood: {qc.get('neighborhood')}", f"- Timepoints: {qc.get('timepoints')}", f"- Valid voxels: {qc.get('valid_voxel_count')}", f"- Skipped: {qc.get('skipped_voxel_count')}", f"- Finite fraction: {qc.get('finite_fraction')}", f"- ReHo mean/std: {qc.get('reho_mean')}/{qc.get('reho_std')}", "", "## Safety Note", "", "ReHo reads derivative files only and does not modify rawdata."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _fail(sid: str, rj: Path, qj: Path, qm: Path, errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "reho_qc_subject", "backend": "python", "subject_id": sid, "reho_qc_status": "FAIL", "outputs": [str(qj),str(qm)], "warnings": w, "errors": errors}
    r = {"ok": False, "node_id": "python_reho_subject", "backend": "python", "subject_id": sid, "outputs": [str(rj),str(qj),str(qm)], "warnings": w, "errors": errors}
    rj.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc); return r

def run_python_reho_subject(subject_id: str, derivatives_dir: str, neighborhood: int = 27, use_gm_mask: bool = False) -> dict[str, Any]:
    try: import nibabel as nib; import numpy as np
    except ImportError as exc: raise RuntimeError("Missing nibabel/numpy.") from exc

    md = Path(derivatives_dir) / "rsfmri_metrics" / subject_id
    qd = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    md.mkdir(parents=True, exist_ok=True); qd.mkdir(parents=True, exist_ok=True)
    rj = md / "reho_result.json"; qj = qd / "reho_qc.json"; qm = qd / "reho_qc.md"
    w: list[str] = []; e: list[str] = []

    ip = _find_filtered(subject_id, derivatives_dir)
    if not ip: return _fail(subject_id, rj, qj, qm, ["No filtered functional input found."])
    if not _safe_filtered(ip, subject_id, derivatives_dir): return _fail(subject_id, rj, qj, qm, [f"Unsafe input: {ip}"])

    try:
        nb = int(neighborhood)
        img = nib.load(str(ip)); data = img.get_fdata(dtype="float32")
        if data.ndim != 4: raise ValueError(f"Must be 4D. Got {data.shape}")
        nx, ny, nz, nt = data.shape
        if nt < 2: raise ValueError(f"Need >=2 timepoints, got {nt}.")

        gm_mask = None; gm_used = None
        if use_gm_mask:
            gp = _find_gm(subject_id, derivatives_dir)
            if gp:
                gd = nib.load(str(gp)).get_fdata(dtype="float32")
                if list(gd.shape[:3]) == [nx,ny,nz]: gm_mask = gd > 0.2; gm_used = str(gp)
                else: w.append("GM shape mismatch; ignoring mask.")
            else: w.append("GM map not found; computing on internal voxels.")

        compute = reho_compute.compute_reho_backend(
            data,
            neighborhood=nb,
            gm_mask=gm_mask,
            prefer_gpu=False,
            require_gpu=False,
        )
        w.extend(str(item) for item in compute.get("warnings", []))
        if not compute.get("ok") or compute.get("reho") is None:
            return _fail(
                subject_id,
                rj,
                qj,
                qm,
                [str(item) for item in compute.get("errors", [])] or ["ReHo computation failed."],
                w,
            )

        reho = np.asarray(compute["reho"], dtype=np.float32)
        vc = int(compute.get("valid_voxel_count", 0) or 0)
        sc = int(compute.get("skipped_voxel_count", 0) or 0)
        rf = md / "reho.nii"
        h3 = img.header.copy()
        try: h3.set_data_shape(reho.shape)
        except Exception: pass
        nib.save(nib.Nifti1Image(reho, affine=img.affine, header=h3), str(rf))

        fm = np.isfinite(reho); ff = float(np.count_nonzero(fm)/reho.size) if reho.size else 0.0
        nz = reho[reho != 0]
        if nz.size > 0: rmean, rstd, rmin, rmax = float(np.mean(nz)), float(np.std(nz)), float(np.min(nz)), float(np.max(nz))
        else: rmean = rstd = rmin = rmax = 0.0

        status = "PASS"
        if vc == 0: status = "FAIL"; e.append("No valid voxels.")
        elif ff < 0.95: status = "WARNING"; w.append("Finite fraction below 0.95.")
        elif rmin < -1e-6 or rmax > 1.000001: status = "WARNING"; w.append(f"ReHo out of [0,1]: min={rmin}, max={rmax}")

        qc = {"ok": status != "FAIL", "node_id": "reho_qc_subject", "backend": "python", "compute_backend": compute.get("backend", "cpu-numpy"), "subject_id": subject_id, "input_nii": str(ip), "reho_file": str(rf), "gm_map_used": gm_used, "input_shape": list(data.shape), "output_shape": list(reho.shape), "timepoints": int(nt), "neighborhood": nb, "neighbor_count": len(reho_compute._offsets(nb)), "boundary_strategy": "skip_boundary", "valid_voxel_count": vc, "skipped_voxel_count": sc, "finite_fraction": ff, "reho_mean": rmean, "reho_std": rstd, "reho_min": rmin, "reho_max": rmax, "reho_qc_status": status, "outputs": [str(qj),str(qm)], "warnings": w, "errors": e}
        result = {"ok": status != "FAIL", "node_id": "python_reho_subject", "backend": "python", "compute_backend": compute.get("backend", "cpu-numpy"), "subject_id": subject_id, "input_nii": str(ip), "reho_file": str(rf), "qc": qc, "outputs": [str(rf),str(rj),str(qj),str(qm)], "warnings": w, "errors": e}
    except Exception as exc:
        return _fail(subject_id, rj, qj, qm, [str(exc)], w)

    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc); return result

def write_reho_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    d = Path(derivatives_dir); ro = Path(report_dir) / "rsfmri"; ro.mkdir(parents=True, exist_ok=True)
    qps = sorted((d / "rsfmri_qc").glob("*/reho_qc.json"))
    subjects = []; w: list[str] = []; e: list[str] = []
    for p in qps:
        pl = _read_json(p)
        if not pl: w.append(f"Invalid: {p}"); continue
        subjects.append(pl)
    n = len(subjects)
    pc = sum(1 for s in subjects if s.get("reho_qc_status") == "PASS")
    wc = sum(1 for s in subjects if s.get("reho_qc_status") == "WARNING")
    fc = sum(1 for s in subjects if s.get("reho_qc_status") == "FAIL")
    rm = [float(s["reho_mean"]) for s in subjects if s.get("reho_mean") is not None]
    vc = [float(s["valid_voxel_count"]) for s in subjects if s.get("valid_voxel_count") is not None]
    summary = {"ok": n > 0 and fc == 0, "node_id": "reho_qc_dataset_report", "backend": "python", "subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc, "mean_reho_mean": float(mean(rm)) if rm else None, "mean_valid_voxel_count": float(mean(vc)) if vc else None, "subjects": subjects, "warnings": w, "errors": e}
    sp = ro / "reho_qc_summary.json"; rp = ro / "reho_qc_report.md"
    sp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# rs-fMRI ReHo QC Dataset Report", "", "## Summary", "", f"- Subjects: {n}", f"- PASS: {pc}", f"- WARNING: {wc}", f"- FAIL: {fc}", f"- Mean ReHo mean: {summary['mean_reho_mean']}", f"- Mean valid voxels: {summary['mean_valid_voxel_count']}", "", "## Subjects", "", "| Subject | Status | Nb | Valid Voxels | ReHo Mean | ReHo Max |", "|---|---|---:|---:|---:|---:|"]
    for s in subjects: lines.append(f"| {s.get('subject_id')} | {s.get('reho_qc_status')} | {s.get('neighborhood')} | {s.get('valid_voxel_count')} | {s.get('reho_mean')} | {s.get('reho_max')} |")
    lines += ["", "## Safety Note", "", "This report summarizes derivative ReHo QC outputs only. It does not modify rawdata."]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "node_id": "reho_qc_dataset_report", "backend": "python", "outputs": [str(sp),str(rp)], "metrics": {"subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc}, "warnings": w, "errors": e}
