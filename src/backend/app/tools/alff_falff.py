from __future__ import annotations
import json
from pathlib import Path
from statistics import mean
from typing import Any

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _find_residual_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    p = func_dir / f"resid_swra{subject_id}_bold.nii"
    if p.exists(): return p
    c = sorted(func_dir.glob("resid_swr*.nii"))
    return c[0] if c else None

def _find_filtered_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    p = func_dir / f"filt_resid_swra{subject_id}_bold.nii"
    if p.exists(): return p
    c = sorted(func_dir.glob("filt_resid_swr*.nii"))
    return c[0] if c else None

def _safe_func_path(path: Path, subject_id: str, derivatives_dir: str, prefix: str) -> bool:
    func_dir = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    try: path.resolve().relative_to(func_dir)
    except ValueError: return False
    return path.name.startswith(prefix) and path.name.endswith(".nii")

def _resolve_tr_and_band(subject_id: str, derivatives_dir: str, tr: float | None, fallback_tr: float | None, low_hz: float | None, high_hz: float | None) -> tuple[dict[str, Any], list[str], list[str]]:
    w: list[str] = []; e: list[str] = []
    fq = _read_json(Path(derivatives_dir) / "rsfmri_qc" / subject_id / "temporal_filtering_qc.json")
    sq = _read_json(Path(derivatives_dir) / "rsfmri_qc" / subject_id / "slice_timing_qc.json")
    ft, ts = tr, None
    if ft is not None: ts = "parameter"
    elif fq and fq.get("tr") is not None: ft = fq.get("tr"); ts = "temporal_filtering_qc"
    elif sq and sq.get("tr") is not None: ft = sq.get("tr"); ts = "slice_timing_qc"
    elif fallback_tr is not None: ft = fallback_tr; ts = "fallback_tr"; w.append("Using fallback TR.")
    if ft is None: e.append("TR is missing.")
    else:
        try: ft = float(ft);
        except Exception: e.append("TR must be numeric.")
        if ft and ft <= 0: e.append("TR must be positive.")
    fl, fh = low_hz, high_hz
    if fl is None and fq and fq.get("low_hz") is not None: fl = fq.get("low_hz")
    if fh is None and fq and fq.get("high_hz") is not None: fh = fq.get("high_hz")
    if fl is None: fl = 0.01
    if fh is None: fh = 0.08
    try: fl = float(fl); fh = float(fh)
    except Exception: e.append("low_hz and high_hz must be numeric.")
    if fl and fh and (fl < 0 or fh <= 0 or fl >= fh): e.append(f"Invalid band: low={fl}, high={fh}")
    return {"tr": ft, "tr_source": ts, "low_hz": fl, "high_hz": fh}, w, e

def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [f"# ALFF / fALFF QC: {qc.get('subject_id')}", "", f"- OK: {qc.get('ok')}", f"- Status: {qc.get('alff_qc_status')}", f"- TR: {qc.get('tr')}", f"- Band: {qc.get('low_hz')}-{qc.get('high_hz')} Hz", f"- Retained bins: {qc.get('retained_frequency_bin_count')}", f"- ALFF mean/std: {qc.get('alff_mean')}/{qc.get('alff_std')}", f"- fALFF mean/std: {qc.get('falff_mean')}/{qc.get('falff_std')}", "", "## Safety Note", "", "ALFF/fALFF reads derivative files only and does not modify rawdata."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _fail(subject_id: str, rj: Path, qj: Path, qm: Path, errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "alff_falff_qc_subject", "backend": "python", "subject_id": subject_id, "alff_qc_status": "FAIL", "outputs": [str(qj), str(qm)], "warnings": w, "errors": errors}
    result = {"ok": False, "node_id": "python_alff_falff_subject", "backend": "python", "subject_id": subject_id, "outputs": [str(rj), str(qj), str(qm)], "warnings": w, "errors": errors}
    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result

def run_python_alff_falff_subject(subject_id: str, derivatives_dir: str, low_hz: float | None = None, high_hz: float | None = None, tr: float | None = None, fallback_tr: float | None = None) -> dict[str, Any]:
    try: import nibabel as nib; import numpy as np
    except ImportError as exc: raise RuntimeError("Missing nibabel/numpy.") from exc

    md = Path(derivatives_dir) / "rsfmri_metrics" / subject_id
    qd = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    md.mkdir(parents=True, exist_ok=True); qd.mkdir(parents=True, exist_ok=True)
    rj = md / "alff_falff_result.json"; qj = qd / "alff_falff_qc.json"; qm = qd / "alff_falff_qc.md"
    warnings: list[str] = []; errors: list[str] = []

    rp = _find_residual_functional(subject_id, derivatives_dir)
    if not rp: return _fail(subject_id, rj, qj, qm, ["No residual functional input found."])
    if not _safe_func_path(rp, subject_id, derivatives_dir, "resid_swr"): return _fail(subject_id, rj, qj, qm, [f"Unsafe residual input: {rp}"])
    fp = _find_filtered_functional(subject_id, derivatives_dir)
    if fp and not _safe_func_path(fp, subject_id, derivatives_dir, "filt_resid_swr"): return _fail(subject_id, rj, qj, qm, [f"Unsafe filtered input: {fp}"])

    params, pw, pe = _resolve_tr_and_band(subject_id, derivatives_dir, tr, fallback_tr, low_hz, high_hz)
    warnings.extend(pw); errors.extend(pe)
    if errors: return _fail(subject_id, rj, qj, qm, errors, warnings)

    ftr = float(params["tr"]); fl = float(params["low_hz"]); fh = float(params["high_hz"])

    try:
        rimg = nib.load(str(rp)); rd = rimg.get_fdata(dtype="float32")
        if rd.ndim != 4: raise ValueError(f"Residual must be 4D. Got {rd.shape}")
        if fp:
            aimg = nib.load(str(fp)); ad = aimg.get_fdata(dtype="float32"); fi = str(fp)
        else:
            ad = rd; fi = None; warnings.append("No filtered input; ALFF from residual spectrum")
        if list(ad.shape) != list(rd.shape): raise ValueError("Filtered/residual shape mismatch")

        nt = int(rd.shape[3])
        if nt < 3: raise ValueError(f"Need >=3 timepoints, got {nt}.")
        nyq = 1.0 / (2.0 * ftr)
        if fh >= nyq: warnings.append(f"high_hz clipped to Nyquist"); fh = nyq

        freqs = np.fft.rfftfreq(nt, d=ftr)
        ndc = freqs > 0
        bm = (freqs >= fl) & (freqs <= fh) & ndc
        rb = int(np.count_nonzero(bm))
        if rb == 0: raise ValueError(f"No ALFF bins retained for {fl}-{fh} Hz, TR={ftr}, nt={nt}.")

        aspec = np.fft.rfft(ad, axis=3); rspec = np.fft.rfft(rd, axis=3)
        alff = np.mean(np.abs(aspec[..., bm]), axis=3).astype("float32")
        num = np.mean(np.abs(rspec[..., bm]), axis=3)
        den = np.mean(np.abs(rspec[..., ndc]), axis=3)
        with np.errstate(divide="ignore", invalid="ignore"): falff = np.where(den > 0, num / den, 0.0).astype("float32")

        af = md / "alff.nii"; ff = md / "falff.nii"
        h3 = rimg.header.copy()
        try: h3.set_data_shape(alff.shape)
        except Exception: pass
        nib.save(nib.Nifti1Image(alff, affine=rimg.affine, header=h3), str(af))
        nib.save(nib.Nifti1Image(falff, affine=rimg.affine, header=h3), str(ff))

        aft = np.isfinite(alff); fft = np.isfinite(falff)
        aff = float(np.count_nonzero(aft) / alff.size) if alff.size else 0.0
        fff = float(np.count_nonzero(fft) / falff.size) if falff.size else 0.0
        fmn = float(np.nanmin(falff)) if falff.size else None
        fmx = float(np.nanmax(falff)) if falff.size else None

        status = "PASS"
        if aff < 0.95 or fff < 0.95: status = "WARNING"; warnings.append("Finite fraction below 0.95.")
        if fmn is not None and fmn < -1e-6: status = "WARNING"; warnings.append(f"fALFF min negative: {fmn}")
        if fmx is not None and fmx > 1.5: status = "WARNING"; warnings.append(f"fALFF max high: {fmx}")

        qc = {"ok": True, "node_id": "alff_falff_qc_subject", "backend": "python", "subject_id": subject_id, "residual_input_nii": str(rp), "filtered_input_nii": fi, "alff_file": str(af), "falff_file": str(ff), "input_shape": list(rd.shape), "filtered_shape": list(ad.shape), "output_shape": list(alff.shape), "tr": ftr, "tr_source": params.get("tr_source"), "low_hz": fl, "high_hz": fh, "nyquist_hz": nyq, "frequency_bin_count": int(len(freqs)), "retained_frequency_bin_count": rb, "alff_finite_fraction": aff, "falff_finite_fraction": fff, "alff_mean": float(np.nanmean(alff)), "alff_std": float(np.nanstd(alff)), "falff_mean": float(np.nanmean(falff)), "falff_std": float(np.nanstd(falff)), "falff_min": fmn, "falff_max": fmx, "alff_qc_status": status, "outputs": [str(qj), str(qm)], "warnings": warnings, "errors": []}
        result = {"ok": True, "node_id": "python_alff_falff_subject", "backend": "python", "subject_id": subject_id, "residual_input_nii": str(rp), "filtered_input_nii": fi, "alff_file": str(af), "falff_file": str(ff), "qc": qc, "outputs": [str(af), str(ff), str(rj), str(qj), str(qm)], "warnings": warnings, "errors": []}
    except Exception as exc:
        return _fail(subject_id, rj, qj, qm, [str(exc)], warnings)

    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc)
    return result

def write_alff_falff_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    d = Path(derivatives_dir); ro = Path(report_dir) / "rsfmri"; ro.mkdir(parents=True, exist_ok=True)
    qps = sorted((d / "rsfmri_qc").glob("*/alff_falff_qc.json"))
    subjects = []; w: list[str] = []; e: list[str] = []
    for p in qps:
        pl = _read_json(p)
        if not pl: w.append(f"Invalid: {p}"); continue
        subjects.append(pl)
    n = len(subjects)
    pc = sum(1 for s in subjects if s.get("alff_qc_status") == "PASS")
    wc = sum(1 for s in subjects if s.get("alff_qc_status") == "WARNING")
    fc = sum(1 for s in subjects if s.get("alff_qc_status") == "FAIL")
    am = [float(s["alff_mean"]) for s in subjects if s.get("alff_mean") is not None]
    fm = [float(s["falff_mean"]) for s in subjects if s.get("falff_mean") is not None]
    summary = {"ok": n > 0 and fc == 0, "node_id": "alff_falff_qc_dataset_report", "backend": "python", "subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc, "mean_alff_mean": float(mean(am)) if am else None, "mean_falff_mean": float(mean(fm)) if fm else None, "subjects": subjects, "warnings": w, "errors": e}
    sp = ro / "alff_falff_qc_summary.json"; rp = ro / "alff_falff_qc_report.md"
    sp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# rs-fMRI ALFF/fALFF QC Dataset Report", "", "## Summary", "", f"- Subjects: {n}", f"- PASS: {pc}", f"- WARNING: {wc}", f"- FAIL: {fc}", f"- Mean ALFF: {summary['mean_alff_mean']}", f"- Mean fALFF: {summary['mean_falff_mean']}", "", "## Subjects", "", "| Subject | Status | ALFF Mean | fALFF Mean | fALFF Max | Band Hz |", "|---|---|---:|---:|---:|---|"]
    for s in subjects: lines.append(f"| {s.get('subject_id')} | {s.get('alff_qc_status')} | {s.get('alff_mean')} | {s.get('falff_mean')} | {s.get('falff_max')} | {s.get('low_hz')}-{s.get('high_hz')} |")
    lines += ["", "## Safety Note", "", "This report summarizes derivative ALFF/fALFF QC outputs only. It does not modify rawdata."]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "node_id": "alff_falff_qc_dataset_report", "backend": "python", "outputs": [str(sp), str(rp)], "metrics": {"subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc}, "warnings": w, "errors": e}
