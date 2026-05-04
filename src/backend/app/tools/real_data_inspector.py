"""Real data inspector -- read-only metadata scanning for BIDS, DICOM, and NIfTI datasets."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def inspect_real_dataset(
    rawdata_path: str,
    output_dir: str = "./reports/real_data_sandbox",
    max_subjects: int = 500,
) -> dict[str, Any]:
    """Read-only inspection of a dataset. Auto-detects BIDS, DICOM, or mixed format."""
    root = Path(rawdata_path)
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Auto-try data/ prefix if path doesn't exist directly
    if not root.exists():
        alt = Path("data") / rawdata_path
        if alt.exists():
            root = alt
        if not root.exists():
            return {"ok": False, "errors": [f"Dataset path not found: {rawdata_path} (also tried data/{rawdata_path})"]}

    # --- Phase 1: Try BIDS structure (sub-*/) ---
    bids_subjects = _scan_bids(root, max_subjects)
    if bids_subjects:
        return _build_inventory(root, out, bids_subjects, "BIDS")

    # --- Phase 2: Try DICOM structure (FunRaw/Sub_*/, T1Raw/Sub_*/) ---
    dicom_subjects = _scan_dicom(root, max_subjects)
    if dicom_subjects:
        return _build_inventory(root, out, dicom_subjects, "DICOM")

    # --- Phase 3: Try flat NIfTI search ---
    nifti_subjects = _scan_nifti(root, max_subjects)
    if nifti_subjects:
        return _build_inventory(root, out, nifti_subjects, "NIfTI")

    return {"ok": False, "errors": [f"No recognizable data found in {rawdata_path}. Expected BIDS (sub-*/), DICOM (FunRaw/Sub_*/), or NIfTI files."]}


def _scan_bids(root: Path, max_subjects: int) -> list[dict[str, Any]]:
    """Scan BIDS-style: sub-*/anat/*.nii.gz, sub-*/func/*.nii.gz"""
    subjects = []
    for subj_dir in sorted(root.iterdir()):
        if not subj_dir.is_dir():
            continue
        if not (subj_dir.name.startswith("sub-") or subj_dir.name.lower().startswith("sub_")):
            continue
        if len(subjects) >= max_subjects:
            break

        entry = _make_subject_entry(subj_dir.name)
        anat_dir = subj_dir / "anat"
        func_dir = subj_dir / "func"

        if anat_dir.is_dir():
            for f in sorted(anat_dir.iterdir()):
                if f.suffix in (".nii", ".gz") or ".nii" in f.name:
                    entry["t1w"] = str(f)
                    entry.update(_read_nifti_header(f))
                    break

        if func_dir.is_dir():
            for f in sorted(func_dir.iterdir()):
                if (f.suffix in (".nii", ".gz") or ".nii" in f.name) and "bold" in f.name.lower():
                    entry["bold"] = str(f)
                    header = _read_nifti_header(f)
                    entry["tr"] = header.get("tr", entry.get("tr"))
                    entry["slice_count"] = header.get("slice_count", entry.get("slice_count"))
                    entry["shape"] = header.get("shape", entry.get("shape"))
                    break

        if entry["t1w"] or entry["bold"]:
            subjects.append(entry)
    return subjects


def _scan_dicom(root: Path, max_subjects: int) -> list[dict[str, Any]]:
    """Scan DICOM structure: FunRaw/Sub_*/*.dcm, T1Raw/Sub_*/*.dcm"""
    # Collect subject IDs from all modality directories
    all_sids: set[str] = set()
    for mod_dir_name in ["FunRaw", "T1Raw", "FuncRaw", "Func", "func", "anat"]:
        mod_dir = root / mod_dir_name
        if mod_dir.is_dir():
            for subj_dir in sorted(mod_dir.iterdir()):
                if subj_dir.is_dir():
                    all_sids.add(subj_dir.name)

    subjects = []
    for sid in sorted(all_sids):
        if len(subjects) >= max_subjects:
            break

        entry = _make_subject_entry(sid)

        # Check FunRaw first (fMRI DICOM)
        for func_name in ["FunRaw", "FuncRaw", "Func", "func"]:
            func_dir = root / func_name / sid
            if func_dir.is_dir():
                dcms = sorted(func_dir.glob("*.dcm"))
                if dcms:
                    entry["bold"] = str(func_dir)
                    header = _read_dicom_headers(dcms)
                    entry.update(header)
                    entry["bold_count"] = len(dcms)
                    entry["bold_size_mb"] = round(sum(f.stat().st_size for f in dcms) / (1024 * 1024), 1)
                    break

        # Check T1Raw (anatomical DICOM)
        for t1_name in ["T1Raw", "T1", "anat", "Anat"]:
            t1_dir = root / t1_name / sid
            if t1_dir.is_dir():
                dcms = sorted(t1_dir.glob("*.dcm"))
                if dcms:
                    entry["t1w"] = str(t1_dir)
                    entry["t1_count"] = len(dcms)
                    t1_header = _read_dicom_headers(dcms)
                    if not entry.get("matrix"):
                        entry["matrix"] = t1_header.get("matrix")
                    entry["t1_size_mb"] = round(sum(f.stat().st_size for f in dcms) / (1024 * 1024), 1)
                    break

        if entry["t1w"] or entry["bold"]:
            subjects.append(entry)
    return subjects


def _scan_nifti(root: Path, max_subjects: int) -> list[dict[str, Any]]:
    """Scan for flat NIfTI files: derivatives/*/Sub_*/"""
    subjects = []
    seen: set[str] = set()
    for nii in sorted(root.rglob("*.nii")):
        # Derive subject ID from path
        parts = nii.relative_to(root).parts
        for i, p in enumerate(parts):
            p_lower = p.lower()
            if p_lower.startswith("sub") and len(p) >= 4:
                sid = p
                if sid not in seen and len(subjects) < max_subjects:
                    seen.add(sid)
                    entry = _make_subject_entry(sid)
                    if "bold" in nii.name.lower() or "func" in str(nii).lower():
                        entry["bold"] = str(nii)
                    elif "t1" in nii.name.lower() or "anat" in str(nii).lower():
                        entry["t1w"] = str(nii)
                    if entry.get("t1w") or entry.get("bold"):
                        entry.update(_read_nifti_header(nii))
                    subjects.append(entry)
                break
    return subjects


def _read_dicom_headers(dcm_files: list[Path]) -> dict[str, Any]:
    """Read metadata from DICOM headers (no pixel data)."""
    try:
        import pydicom
    except ImportError:
        return {"modality": "DICOM", "warning": "pydicom not installed"}
    try:
        fpath = str(dcm_files[0].resolve())
        ds = pydicom.dcmread(fpath, stop_before_pixels=True)
        tr = ds.get("RepetitionTime")
        return {
            "matrix": f"{ds.get('Rows', '?')}x{ds.get('Columns', '?')}",
            "tr": float(tr) / 1000.0 if tr else None,
            "te_ms": float(ds.get("EchoTime", 0)) if ds.get("EchoTime") else None,
            "slice_thickness_mm": float(ds.get("SliceThickness", 0)) if ds.get("SliceThickness") else None,
            "field_strength_t": float(ds.get("MagneticFieldStrength", 0)) if ds.get("MagneticFieldStrength") else None,
            "manufacturer": str(ds.get("Manufacturer", "")),
            "model": str(ds.get("ManufacturerModelName", "")),
            "series_description": str(ds.get("SeriesDescription", "")),
            "modality_type": str(ds.get("Modality", "")),
            "slice_count": len(dcm_files),
        }
    except Exception as exc:
        return {"modality": "DICOM", "slice_count": len(dcm_files), "read_error": str(exc)[:200]}


def _make_subject_entry(sid: str) -> dict[str, Any]:
    return {
        "subject_id": sid,
        "t1w": None,
        "bold": None,
        "tr": None,
        "slice_count": None,
        "matrix": None,
    }


def _read_nifti_header(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError:
        return {}
    try:
        img = nib.load(str(path))
        shape = [int(x) for x in img.shape]
        zooms = [float(x) for x in img.header.get_zooms()]
        tr_val = zooms[3] if len(zooms) > 3 and zooms[3] > 0 else None
        return {
            "shape": shape,
            "voxel_size_mm": [float(x) for x in zooms[:3]],
            "tr": float(tr_val) if tr_val is not None else None,
            "slice_count": shape[2] if len(shape) > 2 else None,
        }
    except Exception:
        return {}


def _build_inventory(root: Path, out: Path, subjects: list[dict], fmt: str) -> dict[str, Any]:
    has_t1w = sum(1 for s in subjects if s.get("t1w"))
    has_bold = sum(1 for s in subjects if s.get("bold"))

    completeness = {
        "subjects_total": len(subjects),
        "has_t1w": has_t1w,
        "has_bold": has_bold,
        "t1_ratio": round(has_t1w / max(len(subjects), 1) * 100, 1),
        "bold_ratio": round(has_bold / max(len(subjects), 1) * 100, 1),
    }

    inventory = {
        "ok": True,
        "node_id": "real_data_inspector",
        "backend": "python",
        "mode": "readonly_sandbox",
        "format": fmt,
        "dataset_root": str(root),
        "subjects": subjects,
        "completeness": completeness,
        "naming_issues": [],
        "metadata_warnings": [],
        "outputs": [],
    }

    (out / "data_inventory.json").write_text(
        json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return inventory
