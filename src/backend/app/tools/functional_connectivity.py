from __future__ import annotations
import csv, json
from pathlib import Path
from statistics import mean
from typing import Any

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

def _safe_atlas(path: Path, derivatives_dir: str) -> bool:
    r = path.resolve()
    for root in [Path(derivatives_dir).resolve(), Path("outputs/work").resolve()]:
        try: r.relative_to(root); return True
        except ValueError: continue
    return False

def _write_tsv(path: Path, header: list[str], rows: list[list[float]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter="\t"); w.writerow(header); w.writerows(rows)

def _generate_atlas(shape: tuple[int,int,int], roi_count: int):
    import numpy as np
    nx, ny, nz = shape
    atlas = np.zeros(shape, dtype=np.int16)
    edges = np.linspace(0, nx, roi_count + 1).astype(int)
    defs = []
    for idx in range(roi_count):
        s, e = int(edges[idx]), int(edges[idx+1])
        if e <= s: continue
        atlas[s:e, :, :] = idx + 1
        defs.append({"label": idx+1, "name": f"ROI_{idx+1}", "strategy": "synthetic_x_chunk", "x_start": s, "x_end": e})
    return atlas, defs

def _safe_corrcoef(ts):
    import numpy as np
    arr = np.asarray(ts, dtype=np.float64); n = arr.shape[0]; corr = np.eye(n)
    for i in range(n):
        for j in range(i+1, n):
            a, b = arr[i], arr[j]
            sa, sb = float(np.std(a)), float(np.std(b))
            if sa == 0 or sb == 0: v = 0.0
            else:
                v = float(np.corrcoef(a,b)[0,1])
                if not np.isfinite(v): v = 0.0
            corr[i,j] = corr[j,i] = v
    return corr

def _fisher_z(corr):
    import numpy as np
    c = np.clip(corr, -0.999999, 0.999999); z = np.arctanh(c); np.fill_diagonal(z, 0.0); return z

def _seed_to_voxel(data, seed_ts):
    import numpy as np
    nx,ny,nz,nt = data.shape; flat = data.reshape((-1,nt)).astype(np.float64)
    seed = np.asarray(seed_ts, dtype=np.float64); ss = float(np.std(seed))
    corr = np.zeros(flat.shape[0], dtype=np.float32)
    if ss == 0: return corr.reshape((nx,ny,nz)), corr.reshape((nx,ny,nz))
    sc = seed - np.mean(seed)
    for i in range(flat.shape[0]):
        v = flat[i]; sv = float(np.std(v))
        if sv == 0: continue
        d = float((nt-1)*ss*sv)
        if d == 0: continue
        val = float(np.sum(sc*(v-np.mean(v)))/d)
        corr[i] = val if np.isfinite(val) else 0.0
    cm = corr.reshape((nx,ny,nz)); zm = np.arctanh(np.clip(cm, -0.999999, 0.999999)).astype(np.float32)
    return cm.astype(np.float32), zm

def _write_qc_md(path: Path, qc: dict[str, Any]) -> None:
    lines = [f"# FC QC: {qc.get('subject_id')}", "", f"- OK: {qc.get('ok')}", f"- Status: {qc.get('fc_qc_status')}", f"- ROI count: {qc.get('roi_count')}", f"- Timepoints: {qc.get('timepoints')}", f"- Empty ROIs: {qc.get('empty_roi_count')}", f"- Timeseries finite: {qc.get('timeseries_finite_fraction')}", f"- Correlation finite: {qc.get('correlation_finite_fraction')}", f"- Symmetry diff: {qc.get('symmetry_max_abs_diff')}", f"- Seed map: {qc.get('seed_map_generated')}", "", "## Safety Note", "", "FC reads derivative files only and does not modify rawdata."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _fail(sid: str, rj: Path, qj: Path, qm: Path, errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    w = warnings or []
    qc = {"ok": False, "node_id": "functional_connectivity_qc_subject", "backend": "python", "subject_id": sid, "fc_qc_status": "FAIL", "outputs": [str(qj),str(qm)], "warnings": w, "errors": errors}
    r = {"ok": False, "node_id": "python_functional_connectivity_subject", "backend": "python", "subject_id": sid, "outputs": [str(rj),str(qj),str(qm)], "warnings": w, "errors": errors}
    rj.write_text(json.dumps(r, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc); return r

def run_python_functional_connectivity_subject(subject_id: str, derivatives_dir: str, roi_count: int = 4, atlas_path: str | None = None, generate_seed_map: bool = False) -> dict[str, Any]:
    try: import nibabel as nib; import numpy as np
    except ImportError as exc: raise RuntimeError("Missing nibabel/numpy.") from exc

    fcd = Path(derivatives_dir) / "rsfmri_fc" / subject_id
    qcd = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    fcd.mkdir(parents=True, exist_ok=True); qcd.mkdir(parents=True, exist_ok=True)
    rj = fcd / "fc_result.json"; qj = qcd / "functional_connectivity_qc.json"; qm = qcd / "functional_connectivity_qc.md"
    w: list[str] = []; e: list[str] = []

    ip = _find_filtered(subject_id, derivatives_dir)
    if not ip: return _fail(subject_id, rj, qj, qm, ["No filtered functional input found."])
    if not _safe_filtered(ip, subject_id, derivatives_dir): return _fail(subject_id, rj, qj, qm, [f"Unsafe input: {ip}"])

    try:
        img = nib.load(str(ip)); data = img.get_fdata(dtype="float32")
        if data.ndim != 4: raise ValueError(f"Must be 4D. Got {data.shape}")
        nx, ny, nz, nt = data.shape; roi_defs = []

        if atlas_path:
            af = Path(atlas_path)
            if not af.exists(): raise ValueError(f"Atlas not found: {af}")
            if not _safe_atlas(af, derivatives_dir): raise ValueError(f"Unsafe atlas: {af}")
            ad = nib.load(str(af)).get_fdata().astype("int16")
            if list(ad.shape[:3]) != [nx,ny,nz]: raise ValueError(f"Atlas shape mismatch")
            labels = sorted(int(x) for x in np.unique(ad) if int(x) > 0)
            roi_defs = [{"label": l, "name": f"ROI_{l}", "strategy": "provided"} for l in labels]
        else:
            ad, roi_defs = _generate_atlas((nx,ny,nz), int(roi_count))
            af = fcd / "synthetic_roi_atlas.nii"
            h3 = img.header.copy()
            try: h3.set_data_shape(ad.shape)
            except Exception: pass
            nib.save(nib.Nifti1Image(ad.astype("int16"), affine=img.affine, header=h3), str(af))

        (fcd / "roi_definitions.json").write_text(json.dumps({"subject_id": subject_id, "atlas_file": str(af), "roi_definitions": roi_defs, "synthetic": atlas_path is None}, ensure_ascii=False, indent=2), encoding="utf-8")
        labels = [int(d["label"]) for d in roi_defs]; names = [str(d.get("name", f"ROI_{l}")) for d,l in zip(roi_defs, labels)]

        rts = []; rvc = {}; ec = 0
        for l in labels:
            m = ad == l; vc = int(np.count_nonzero(m)); rvc[str(l)] = vc
            if vc == 0: ec += 1; w.append(f"ROI {l} empty."); rts.append(np.zeros((nt,), dtype=np.float64))
            else: ts = np.mean(data[m, :], axis=0).astype(np.float64); rts.append(np.where(np.isfinite(ts), ts, 0.0))
        rta = np.vstack(rts) if rts else np.zeros((0, nt), dtype=np.float64)

        ttsv = fcd / "roi_timeseries.tsv"
        _write_tsv(ttsv, names, [[float(rta[ri,t]) for ri in range(len(labels))] for t in range(nt)])

        corr = _safe_corrcoef(rta); fz = _fisher_z(corr)
        ctsv = fcd / "correlation_matrix.tsv"; ftsv = fcd / "fisher_z_matrix.tsv"
        cjson = fcd / "correlation_matrix.json"; fjson = fcd / "fisher_z_matrix.json"
        _write_tsv(ctsv, ["roi"]+names, [[names[i]] + [float(x) for x in corr[i]] for i in range(len(names))])
        _write_tsv(ftsv, ["roi"]+names, [[names[i]] + [float(x) for x in fz[i]] for i in range(len(names))])
        cjson.write_text(json.dumps({"subject_id": subject_id, "roi_names": names, "matrix": corr.tolist()}, ensure_ascii=False, indent=2), encoding="utf-8")
        fjson.write_text(json.dumps({"subject_id": subject_id, "roi_names": names, "matrix": fz.tolist()}, ensure_ascii=False, indent=2), encoding="utf-8")

        scf = None; szf = None; sgen = False
        if generate_seed_map and len(labels) > 0:
            ni = [i for i,l in enumerate(labels) if rvc.get(str(l),0) > 0]
            if ni:
                si = ni[0]; cm, zm = _seed_to_voxel(data, rta[si])
                scf = fcd / "seed_correlation_map.nii"; szf = fcd / "seed_fisher_z_map.nii"
                mh = img.header.copy()
                try: mh.set_data_shape(cm.shape)
                except Exception: pass
                nib.save(nib.Nifti1Image(cm, affine=img.affine, header=mh), str(scf))
                nib.save(nib.Nifti1Image(zm, affine=img.affine, header=mh), str(szf)); sgen = True
            else: w.append("Seed map requested but no non-empty ROI.")

        tff = float(np.count_nonzero(np.isfinite(rta))/rta.size) if rta.size else 0.0
        cff = float(np.count_nonzero(np.isfinite(corr))/corr.size) if corr.size else 0.0
        fff = float(np.count_nonzero(np.isfinite(fz))/fz.size) if fz.size else 0.0
        dm = float(np.mean(np.diag(corr))) if corr.size else None
        smd = float(np.max(np.abs(corr-corr.T))) if corr.size else None

        status = "PASS"
        if len(labels) == 0: status = "FAIL"; e.append("No ROIs.")
        elif ec > 0: status = "WARNING"; w.append(f"{ec} empty ROI(s).")
        elif tff < 1.0 or cff < 1.0 or fff < 1.0: status = "WARNING"; w.append("Non-finite values detected.")
        elif dm is not None and abs(dm-1.0) > 1e-5: status = "WARNING"; w.append(f"Diagonal mean {dm} != 1.0")
        elif smd is not None and smd > 1e-6: status = "WARNING"; w.append(f"Symmetry diff {smd}")

        qc = {"ok": status != "FAIL", "node_id": "functional_connectivity_qc_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(ip), "atlas_file": str(af), "input_shape": list(data.shape), "atlas_shape": list(ad.shape), "timepoints": int(nt), "roi_count": len(labels), "roi_names": names, "roi_voxel_counts": rvc, "empty_roi_count": ec, "timeseries_finite_fraction": tff, "correlation_matrix_shape": list(corr.shape), "correlation_finite_fraction": cff, "fisher_z_finite_fraction": fff, "diagonal_mean": dm, "symmetry_max_abs_diff": smd, "seed_map_generated": sgen, "fc_qc_status": status, "outputs": [str(qj),str(qm)], "warnings": w, "errors": e}

        outputs = [str(af), str(fcd/"roi_definitions.json"), str(ttsv), str(ctsv), str(cjson), str(ftsv), str(fjson), str(rj), str(qj), str(qm)]
        if scf: outputs.append(str(scf))
        if szf: outputs.append(str(szf))

        result = {"ok": status != "FAIL", "node_id": "python_functional_connectivity_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(ip), "atlas_file": str(af), "roi_definitions": roi_defs, "roi_timeseries_tsv": str(ttsv), "correlation_matrix_tsv": str(ctsv), "correlation_matrix_json": str(cjson), "fisher_z_matrix_tsv": str(ftsv), "fisher_z_matrix_json": str(fjson), "seed_correlation_map": str(scf) if scf else None, "seed_fisher_z_map": str(szf) if szf else None, "qc": qc, "outputs": outputs, "warnings": w, "errors": e}
    except Exception as exc:
        return _fail(subject_id, rj, qj, qm, [str(exc)], w)

    rj.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    qj.write_text(json.dumps(qc, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_qc_md(qm, qc); return result

def write_functional_connectivity_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    d = Path(derivatives_dir); ro = Path(report_dir) / "rsfmri"; ro.mkdir(parents=True, exist_ok=True)
    qps = sorted((d / "rsfmri_qc").glob("*/functional_connectivity_qc.json"))
    subjects = []; w: list[str] = []; e: list[str] = []
    for p in qps:
        pl = _read_json(p)
        if not pl: w.append(f"Invalid: {p}"); continue
        subjects.append(pl)
    n = len(subjects); pc = sum(1 for s in subjects if s.get("fc_qc_status") == "PASS"); wc = sum(1 for s in subjects if s.get("fc_qc_status") == "WARNING"); fc_c = sum(1 for s in subjects if s.get("fc_qc_status") == "FAIL")
    rc = [float(s["roi_count"]) for s in subjects if s.get("roi_count") is not None]
    ec = [float(s["empty_roi_count"]) for s in subjects if s.get("empty_roi_count") is not None]
    summary = {"ok": n > 0 and fc_c == 0, "node_id": "functional_connectivity_qc_dataset_report", "backend": "python", "subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc_c, "mean_roi_count": float(mean(rc)) if rc else None, "mean_empty_roi_count": float(mean(ec)) if ec else None, "subjects": subjects, "warnings": w, "errors": e}
    sp = ro / "functional_connectivity_qc_summary.json"; rp = ro / "functional_connectivity_qc_report.md"
    sp.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# rs-fMRI FC QC Dataset Report", "", "## Summary", "", f"- Subjects: {n}", f"- PASS: {pc}", f"- WARNING: {wc}", f"- FAIL: {fc_c}", f"- Mean ROI count: {summary['mean_roi_count']}", f"- Mean empty ROIs: {summary['mean_empty_roi_count']}", "", "## Subjects", "", "| Subject | Status | ROI Count | Empty ROIs | Timepoints | Symmetry Diff |", "|---|---|---:|---:|---:|---:|"]
    for s in subjects: lines.append(f"| {s.get('subject_id')} | {s.get('fc_qc_status')} | {s.get('roi_count')} | {s.get('empty_roi_count')} | {s.get('timepoints')} | {s.get('symmetry_max_abs_diff')} |")
    lines += ["", "## Safety Note", "", "Derivative FC QC only. Does not modify rawdata."]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "node_id": "functional_connectivity_qc_dataset_report", "backend": "python", "outputs": [str(sp),str(rp)], "metrics": {"subjects_total": n, "subjects_pass": pc, "subjects_warning": wc, "subjects_fail": fc_c}, "warnings": w, "errors": e}
