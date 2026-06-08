"""Path-based FunRaw / T1Raw DICOM layout detector.

Detects DPABI/SPM-style rawdata layouts where functional and anatomical
DICOM files are organized under FunRaw/ and T1Raw/ parent folders with
Subject_xxx subdirectories.

Read-only — never modifies files, never executes external tools.
Does not require pydicom.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

_DICOM_EXTENSIONS: set[str] = {".dcm", ".ima"}
_NIFTI_EXTENSIONS: set[str] = {".nii", ".nii.gz"}

FUNRAW_NAMES: set[str] = {"funraw", "func", "functional", "bold", "fmri", "rest"}
T1RAW_NAMES: set[str] = {"t1raw", "t1", "anat", "anatomical", "struct", "structural", "t1w", "mprage"}


def _is_dicom_file(path: Path) -> bool:
    """Check if a file is a DICOM file by extension or extensionless."""
    if path.suffix.lower() in _DICOM_EXTENSIONS:
        return True
    # extensionless files are common in DICOMDIR datasets
    if not path.suffix:
        return path.is_file()
    return False


def _count_files(
    root: Path,
    *,
    dicom: bool = True,
    nifti: bool = False,
) -> tuple[int, int]:
    """Count DICOM and/or NIfTI files recursively under *root*."""
    dicom_count = 0
    nifti_count = 0
    try:
        for child in root.rglob("*"):
            if not child.is_file():
                continue
            if dicom and _is_dicom_file(child):
                dicom_count += 1
            elif nifti and "".join(child.suffixes).lower() in _NIFTI_EXTENSIONS:
                nifti_count += 1
    except (OSError, PermissionError):
        pass
    return dicom_count, nifti_count


def _normalize_subject_id(name: str) -> str:
    """Map Sub_001 / Subject_001 / sub_001 → sub-001 (BIDS-style)."""
    name = name.strip().lower()
    # Replace underscores with hyphens, strip any trailing separator
    name = name.replace("_", "-")
    # Remove any prefix like "subject-" or "subj-"
    for prefix in ("subject-", "subj-"):
        if name.startswith(prefix):
            name = name[len(prefix):]
    # Ensure starts with "sub-"
    if not name.startswith("sub-"):
        name = "sub-" + name
    return name


def detect_funraw_t1raw_layout(rawdata_dir: str | Path) -> dict[str, Any]:
    """Detect DPABI/SPM-style FunRaw / T1Raw DICOM layout.

    Returns a dict with keys:
      layout_type, has_funraw, has_t1raw, subject_ids, subject_count,
      dicom_file_count, nifti_file_count, series_count,
      per_subject_modality (list of {subject_id, modality, root_name,
      file_count, suggested_suffix, suggested_modality_dir})

    Returns layout_type="" if layout is not detected.
    """
    root = Path(rawdata_dir).expanduser().resolve()
    if not root.is_dir():
        return {"layout_type": "", "has_funraw": False, "has_t1raw": False,
                "subject_ids": [], "subject_count": 0, "dicom_file_count": 0,
                "nifti_file_count": 0, "series_count": 0,
                "per_subject_modality": []}

    children = {d.name.lower(): d for d in root.iterdir() if d.is_dir()}

    funraw_dir = None
    t1raw_dir = None
    for child_name, child_path in children.items():
        if child_name in FUNRAW_NAMES:
            funraw_dir = child_path
        elif child_name in T1RAW_NAMES:
            t1raw_dir = child_path

    if not funraw_dir and not t1raw_dir:
        return {"layout_type": "", "has_funraw": False, "has_t1raw": False,
                "subject_ids": [], "subject_count": 0, "dicom_file_count": 0,
                "nifti_file_count": 0, "series_count": 0,
                "per_subject_modality": []}

    has_funraw = funraw_dir is not None
    has_t1raw = t1raw_dir is not None

    per_subject: list[dict[str, Any]] = []
    all_subject_ids: list[str] = []
    seen_subjects: set[str] = set()
    total_dicom = 0
    total_nifti = 0

    for modality_dir, root_name, suggested_suffix, suggested_modality_dir in [
        (funraw_dir, "FunRaw", "bold", "func"),
        (t1raw_dir, "T1Raw", "T1w", "anat"),
    ]:
        if modality_dir is None:
            continue

        try:
            sub_dirs = sorted(
                [d for d in modality_dir.iterdir() if d.is_dir()],
                key=lambda d: d.name.lower(),
            )
        except (OSError, PermissionError):
            continue

        for sub_dir in sub_dirs:
            raw_name = sub_dir.name
            normalized_id = _normalize_subject_id(raw_name)
            dicom_count, nifti_count = _count_files(sub_dir, dicom=True, nifti=True)
            total_dicom += dicom_count
            total_nifti += nifti_count

            per_subject.append({
                "subject_id": normalized_id,
                "raw_subject_name": raw_name,
                "modality": root_name,
                "root_name": root_name,
                "file_count": dicom_count,
                "nifti_count": nifti_count,
                "suggested_suffix": suggested_suffix,
                "suggested_modality_dir": suggested_modality_dir,
            })

            if normalized_id not in seen_subjects:
                seen_subjects.add(normalized_id)
                all_subject_ids.append(normalized_id)

    return {
        "layout_type": "funraw_t1raw" if (has_funraw or has_t1raw) else "",
        "has_funraw": has_funraw,
        "has_t1raw": has_t1raw,
        "subject_ids": all_subject_ids,
        "subject_count": len(all_subject_ids),
        "dicom_file_count": total_dicom,
        "nifti_file_count": total_nifti,
        "series_count": len(per_subject),
        "per_subject_modality": per_subject,
    }
