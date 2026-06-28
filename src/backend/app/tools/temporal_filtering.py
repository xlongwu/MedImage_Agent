from __future__ import annotations
import json
from pathlib import Path
from statistics import mean
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json

def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists(): return None
    try: return json.loads(path.read_text(encoding="utf-8"))
    except Exception: return None

def _find_residual_functional(subject_id: str, derivatives_dir: str) -> Path | None:
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if not func_dir.exists(): return None
    preferred = [
        func_dir / f"resid_swra{subject_id}_bold.nii",
        func_dir / f"resid_swra{subject_id}_bold.nii.gz",
        func_dir / f"resid_r{subject_id}_bold.nii",
        func_dir / f"resid_r{subject_id}_bold.nii.gz",
        func_dir / f"resid_ra{subject_id}_bold.nii",
        func_dir / f"resid_ra{subject_id}_bold.nii.gz",
    ]
    for path in preferred:
        if path.exists(): return path
    candidates = sorted(path for path in func_dir.glob("resid_*.nii*") if path.is_file())
    return candidates[0] if candidates else None

def _safe_residual_input(path: Path, subject_id: str, derivatives_dir: str) -> bool:
    func_dir = (Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func").resolve()
    try: path.resolve().relative_to(func_dir)
    except ValueError: return False
    suffixes = "".join(path.suffixes).lower()
    is_nifti = path.suffix.lower() == ".nii" or suffixes.endswith(".nii.gz")
    return path.name.startswith("resid_") and is_nifti

def _candidate_bids_sidecars(input_path: Path, subject_id: str, derivatives_dir: str) -> list[Path]:
    suffixes = "".join(input_path.suffixes).lower()
    if suffixes.endswith(".nii.gz"):
        stem = input_path.name[:-7]
    elif input_path.suffix.lower() == ".nii":
        stem = input_path.name[:-4]
    else:
        stem = input_path.stem

    candidates: list[Path] = [input_path.with_name(f"{stem}.json")]
    stripped = stem
    for prefix in ("filt_", "resid_", "swra", "swr", "ra", "r", "a"):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            candidates.append(input_path.with_name(f"{stripped}.json"))
    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    if func_dir.exists():
        candidates.extend(sorted(func_dir.glob("*bold.json")))
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique.append(candidate)
    return unique

def _resolve_tr_from_bids_sidecar(input_path: Path, subject_id: str, derivatives_dir: str) -> tuple[float | None, list[str], list[str], str | None]:
    warnings: list[str] = []; errors: list[str] = []
    for sidecar in _candidate_bids_sidecars(input_path, subject_id, derivatives_dir):
        payload = _read_json(sidecar)
        if not payload or payload.get("RepetitionTime") is None:
            continue
        try:
            parsed = float(payload["RepetitionTime"])
            if parsed <= 0:
                errors.append(f"RepetitionTime in BIDS sidecar is not positive: {sidecar}")
                return None, warnings, errors, str(sidecar)
            return parsed, warnings, errors, str(sidecar)
        except Exception:
            errors.append(f"RepetitionTime in BIDS sidecar is not numeric: {sidecar}")
            return None, warnings, errors, str(sidecar)
    return None, warnings, errors, None

def _resolve_tr(subject_id: str, derivatives_dir: str, input_path: Path, tr: float | None = None, fallback_tr: float | None = None) -> tuple[float | None, list[str], list[str], str | None]:
    warnings: list[str] = []; errors: list[str] = []
    if tr is not None:
        try:
            parsed = float(tr)
            if parsed <= 0: errors.append("TR must be positive."); return None, warnings, errors, "parameter"
            return parsed, warnings, errors, "parameter"
        except Exception: errors.append("TR parameter must be numeric."); return None, warnings, errors, "parameter"
    sidecar_tr, sidecar_warnings, sidecar_errors, sidecar_source = _resolve_tr_from_bids_sidecar(input_path, subject_id, derivatives_dir)
    warnings.extend(sidecar_warnings); errors.extend(sidecar_errors)
    if sidecar_tr is not None:
        return sidecar_tr, warnings, errors, sidecar_source
    if sidecar_errors:
        return None, warnings, errors, sidecar_source
    qc_path = Path(derivatives_dir) / "rsfmri_qc" / subject_id / "slice_timing_qc.json"
    payload = _read_json(qc_path)
    if payload and payload.get("tr") is not None:
        try:
            parsed = float(payload["tr"])
            if parsed <= 0: errors.append(f"TR from slice timing QC is not positive: {parsed}"); return None, warnings, errors, str(qc_path)
            return parsed, warnings, errors, str(qc_path)
        except Exception: errors.append("TR in slice timing QC is not numeric."); return None, warnings, errors, str(qc_path)
    if fallback_tr is not None:
        warnings.append("Using explicit fallback TR because slice timing QC TR was unavailable.")
        try:
            parsed = float(fallback_tr)
            if parsed <= 0: errors.append("fallback_tr must be positive."); return None, warnings, errors, "fallback_tr"
            return parsed, warnings, errors, "fallback_tr"
        except Exception: errors.append("fallback_tr must be numeric."); return None, warnings, errors, "fallback_tr"
    errors.append("TR is missing. Provide tr or fallback_tr, or run slice timing QC first.")
    return None, warnings, errors, None

def _write_qc_markdown(path: Path, qc: dict[str, Any]) -> None:
    lines = [f"# Temporal Filtering QC: {qc.get('subject_id')}", "", f"- OK: {qc.get('ok')}", f"- Status: {qc.get('filtering_qc_status')}", f"- Input: `{qc.get('input_nii')}`", f"- Output: `{qc.get('output_nii')}`", f"- TR: {qc.get('tr')}", f"- Band: {qc.get('low_hz')} - {qc.get('high_hz')} Hz", f"- Nyquist: {qc.get('nyquist_hz')} Hz", f"- Retained frequency bins: {qc.get('retained_frequency_bin_count')} / {qc.get('frequency_bin_count')}", f"- Finite fraction: {qc.get('finite_fraction')}", f"- Variance ratio: {qc.get('variance_ratio')}", "", "## Safety Note", "", "Temporal filtering reads derivative files only and does not modify rawdata."]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

def _failure(subject_id: str, result_json: Path, qc_json: Path, qc_md: Path, errors: list[str], warnings: list[str] | None = None) -> dict[str, Any]:
    warnings = warnings or []
    qc = {"ok": False, "node_id": "temporal_filtering_qc_subject", "backend": "python", "subject_id": subject_id, "filtering_qc_status": "FAIL", "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
    result = {"ok": False, "node_id": "python_temporal_filter_subject", "backend": "python", "subject_id": subject_id, "outputs": [str(result_json), str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
    atomic_write_json(result_json, result, schema_version=1)
    atomic_write_json(qc_json, qc, schema_version=1)
    _write_qc_markdown(qc_md, qc)
    return result

def run_python_temporal_filter_subject(
    subject_id: str, derivatives_dir: str, low_hz: float = 0.01, high_hz: float = 0.08,
    tr: float | None = None, fallback_tr: float | None = None,
) -> dict[str, Any]:
    try: import nibabel as nib; import numpy as np
    except ImportError as exc: raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    func_dir = Path(derivatives_dir) / "rsfmri_preproc" / subject_id / "func"
    qc_dir = Path(derivatives_dir) / "rsfmri_qc" / subject_id
    func_dir.mkdir(parents=True, exist_ok=True); qc_dir.mkdir(parents=True, exist_ok=True)
    result_json = func_dir / "temporal_filtering_result.json"; qc_json = qc_dir / "temporal_filtering_qc.json"; qc_md = qc_dir / "temporal_filtering_qc.md"
    warnings: list[str] = []; errors: list[str] = []

    input_path = _find_residual_functional(subject_id, derivatives_dir)
    if not input_path: return _failure(subject_id, result_json, qc_json, qc_md, [f"No residual functional input found for subject {subject_id}."])
    if not _safe_residual_input(input_path, subject_id, derivatives_dir): return _failure(subject_id, result_json, qc_json, qc_md, [f"Unsafe temporal filtering input: {input_path}"])

    resolved_tr, tr_warnings, tr_errors, tr_source = _resolve_tr(subject_id=subject_id, derivatives_dir=derivatives_dir, input_path=input_path, tr=tr, fallback_tr=fallback_tr)
    warnings.extend(tr_warnings); errors.extend(tr_errors)
    if resolved_tr is None: return _failure(subject_id, result_json, qc_json, qc_md, errors, warnings)

    try: low_hz = float(low_hz); high_hz = float(high_hz)
    except Exception: return _failure(subject_id, result_json, qc_json, qc_md, ["low_hz and high_hz must be numeric."], warnings)
    if low_hz < 0 or high_hz <= 0 or low_hz >= high_hz: return _failure(subject_id, result_json, qc_json, qc_md, [f"Invalid band-pass range: low_hz={low_hz}, high_hz={high_hz}"], warnings)

    try:
        img = nib.load(str(input_path)); data = img.get_fdata(dtype="float32")
        if data.ndim != 4: raise ValueError(f"Input NIfTI must be 4D. Shape was: {data.shape}")
        n_time = int(data.shape[3])
        if n_time < 3: raise ValueError(f"Temporal filtering requires at least 3 timepoints. Got {n_time}.")
        nyquist = 1.0 / (2.0 * resolved_tr)
        if high_hz >= nyquist: warnings.append(f"high_hz={high_hz} >= Nyquist={nyquist}. Clipping high_hz to Nyquist."); high_hz = nyquist

        freqs = np.fft.rfftfreq(n_time, d=resolved_tr)
        mask = (freqs >= low_hz) & (freqs <= high_hz)
        retained_bins = int(np.count_nonzero(mask))
        if retained_bins == 0: raise ValueError(f"No frequency bins retained for band {low_hz}-{high_hz} Hz with TR={resolved_tr} and n_time={n_time}.")

        spectrum = np.fft.rfft(data, axis=3); spectrum[..., ~mask] = 0.0
        filtered = np.fft.irfft(spectrum, n=n_time, axis=3).astype("float32")
        output_path = input_path.with_name(f"filt_{input_path.name}")
        out_img = nib.Nifti1Image(filtered, affine=img.affine, header=img.header)
        nib.save(out_img, str(output_path))

        finite_mask = np.isfinite(filtered)
        finite_fraction = float(np.count_nonzero(finite_mask) / filtered.size) if filtered.size else 0.0
        input_std_by_voxel = np.std(data, axis=3); filtered_std_by_voxel = np.std(filtered, axis=3)
        input_temporal_std_mean = float(np.mean(input_std_by_voxel)); filtered_temporal_std_mean = float(np.mean(filtered_std_by_voxel))
        variance_ratio = float(filtered_temporal_std_mean / input_temporal_std_mean) if input_temporal_std_mean > 0 else None
        status = "PASS"
        if finite_fraction < 0.95: status = "WARNING"; warnings.append(f"Filtered finite fraction {finite_fraction:.4f} below 0.95.")
        if variance_ratio is not None and variance_ratio > 1.2: status = "WARNING"; warnings.append(f"Filtered temporal std larger than input. Ratio={variance_ratio:.4f}.")

        qc = {"ok": True, "node_id": "temporal_filtering_qc_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(input_path), "output_nii": str(output_path), "input_shape": list(data.shape), "output_shape": list(filtered.shape), "tr": resolved_tr, "tr_source": tr_source, "low_hz": low_hz, "high_hz": high_hz, "nyquist_hz": nyquist, "frequency_bin_count": int(len(freqs)), "retained_frequency_bin_count": retained_bins, "retained_frequency_fraction": float(retained_bins / len(freqs)), "finite_fraction": finite_fraction, "input_temporal_std_mean": input_temporal_std_mean, "filtered_temporal_std_mean": filtered_temporal_std_mean, "variance_ratio": variance_ratio, "filtering_qc_status": status, "outputs": [str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
        result = {"ok": True, "node_id": "python_temporal_filter_subject", "backend": "python", "subject_id": subject_id, "input_nii": str(input_path), "output_nii": str(output_path), "qc": qc, "outputs": [str(output_path), str(result_json), str(qc_json), str(qc_md)], "warnings": warnings, "errors": errors}
    except Exception as exc:
        return _failure(subject_id, result_json, qc_json, qc_md, [str(exc)], warnings)

    atomic_write_json(result_json, result, schema_version=1)
    atomic_write_json(qc_json, qc, schema_version=1)
    _write_qc_markdown(qc_md, qc)
    return result

def write_temporal_filtering_dataset_report(derivatives_dir: str, report_dir: str) -> dict[str, Any]:
    derivatives = Path(derivatives_dir); report_out = Path(report_dir) / "rsfmri"; report_out.mkdir(parents=True, exist_ok=True)
    qc_paths = sorted((derivatives / "rsfmri_qc").glob("*/temporal_filtering_qc.json"))
    subjects = []; warnings: list[str] = []; errors: list[str] = []
    for path in qc_paths:
        payload = _read_json(path)
        if not payload: warnings.append(f"Invalid temporal filtering QC JSON: {path}"); continue
        subjects.append(payload)
    n = len(subjects)
    pass_count = sum(1 for s in subjects if s.get("filtering_qc_status") == "PASS")
    warning_count = sum(1 for s in subjects if s.get("filtering_qc_status") == "WARNING")
    fail_count = sum(1 for s in subjects if s.get("filtering_qc_status") == "FAIL")
    vr = [float(s["variance_ratio"]) for s in subjects if s.get("variance_ratio") is not None]
    rf = [float(s["retained_frequency_fraction"]) for s in subjects if s.get("retained_frequency_fraction") is not None]
    summary = {"ok": n > 0 and fail_count == 0, "node_id": "temporal_filtering_qc_dataset_report", "backend": "python", "subjects_total": n, "subjects_pass": pass_count, "subjects_warning": warning_count, "subjects_fail": fail_count, "mean_variance_ratio": float(mean(vr)) if vr else None, "mean_retained_frequency_fraction": float(mean(rf)) if rf else None, "subjects": subjects, "warnings": warnings, "errors": errors}
    sp = report_out / "temporal_filtering_qc_summary.json"; rp = report_out / "temporal_filtering_qc_report.md"
    atomic_write_json(sp, summary, schema_version=1)
    lines = ["# rs-fMRI Temporal Filtering QC Dataset Report", "", "## Summary", "", f"- Subjects total: {n}", f"- PASS: {pass_count}", f"- WARNING: {warning_count}", f"- FAIL: {fail_count}", f"- Mean variance ratio: {summary['mean_variance_ratio']}", f"- Mean retained frequency fraction: {summary['mean_retained_frequency_fraction']}", "", "## Subjects", "", "| Subject | Status | TR | Band Hz | Retained Bins | Variance Ratio |", "|---|---|---:|---|---:|---:|"]
    for s in subjects: lines.append(f"| {s.get('subject_id')} | {s.get('filtering_qc_status')} | {s.get('tr')} | {s.get('low_hz')}-{s.get('high_hz')} | {s.get('retained_frequency_bin_count')} | {s.get('variance_ratio')} |")
    lines += ["", "## Safety Note", "", "This report summarizes derivative temporal filtering QC outputs only. It does not modify rawdata."]
    rp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "node_id": "temporal_filtering_qc_dataset_report", "backend": "python", "outputs": [str(sp), str(rp)], "metrics": {"subjects_total": n, "subjects_pass": pass_count, "subjects_warning": warning_count, "subjects_fail": fail_count}, "warnings": warnings, "errors": errors}
