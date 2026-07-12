"""NIfTI QC snapshot service — read-only metadata and QC statistics.

Discovers NIfTI files from project metadata, reads headers safely
via nibabel, and summarizes lightweight QC statistics.  Never
modifies rawdata, never executes external tools.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

import src.backend.app.services.mock_store as mock_store_module

from src.backend.app.schemas.desktop import (
    NiftiImageQcRecord,
    NiftiQcSnapshotResponse,
)
from src.backend.app.services.image_preview import (
    _canonical_sequence_from_name,
    _iter_nifti_files,
    _relative_path,
    _subject_from_path,
)
from src.backend.app.services.qc_evidence_roots import collect_qc_evidence_roots

# Compatibility hook for legacy direct service callers and tests. New API
# routes pass an injected ProjectStore explicitly.
mock_store = mock_store_module.mock_store

_NIFTI_EXT = (".nii", ".nii.gz")
_MAX_PIXELS_FOR_STATS = 1_000_000
_BLOCKED_EXTENSIONS = {".par", ".rec", ".img"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_nifti(path: Path) -> bool:
    return path.is_file() and (
        path.name.endswith(".nii") or path.name.endswith(".nii.gz")
    )


def _discover_nifti(project_id: str, *, store: Any | None = None) -> list[Path]:
    """Discover NIfTI files from project metadata and image sources.

    Only uses synthetic fallback when no real project evidence roots are
    configured. Real projects with data roots but no NIfTI return an empty
    list (no synthetic pollution).
    """
    paths: list[Path] = []

    roots = collect_qc_evidence_roots(
        project_id,
        include_native_outputs=True,
        store=store,
    )
    for root in roots:
        paths.extend(_iter_nifti_files(root))

    # Only use synthetic fallback when no real project root is configured.
    if not roots:
        search_roots = [
            Path("examples/synthetic_bids/rawdata"),
        ]
        for root in search_roots:
            resolved = root.expanduser().resolve()
            if resolved.is_dir():
                for p in _iter_nifti_files(resolved):
                    if str(p) not in {str(x) for x in paths}:
                        paths.append(p)

    # Deduplicate
    seen: set[str] = set()
    result: list[Path] = []
    for p in paths:
        key = str(p.resolve())
        if key not in seen:
            seen.add(key)
            result.append(p)
    return result


def _read_stats(data: np.ndarray) -> dict[str, Any]:
    """Read intensity statistics, capped at _MAX_PIXELS_FOR_STATS."""
    total = int(np.prod(data.shape))
    if total <= _MAX_PIXELS_FOR_STATS:
        flat = np.asarray(data, dtype=np.float32).ravel()
    else:
        # Sample central region
        slices = tuple(slice(max(0, s // 4), min(s, 3 * s // 4)) for s in data.shape)
        sampled = data[slices]
        step = max(1, int(np.prod(sampled.shape)) // _MAX_PIXELS_FOR_STATS)
        flat = np.asarray(sampled, dtype=np.float32).ravel()[::step]

    flat = flat[np.isfinite(flat)]
    if flat.size == 0:
        return {
            "intensity_min": None, "intensity_max": None,
            "intensity_mean": None, "intensity_std": None,
            "zero_fraction": None, "nan_count": int(total - flat.size),
        }

    return {
        "intensity_min": float(np.min(flat)),
        "intensity_max": float(np.max(flat)),
        "intensity_mean": float(np.mean(flat)),
        "intensity_std": float(np.std(flat)),
        "zero_fraction": float(np.mean(np.abs(flat) < 1e-10)),
        "nan_count": int(total - flat.size),
    }


def build_nifti_qc_snapshot(
    project_id: str,
    *,
    store: Any | None = None,
) -> NiftiQcSnapshotResponse:
    now = _now_iso()
    paths = _discover_nifti(project_id, store=store or mock_store)
    images: list[NiftiImageQcRecord] = []
    all_warnings: list[str] = []
    errors: list[str] = []

    readable_count = 0
    unreadable_count = 0
    four_d_count = 0
    warning_count = 0

    nib_available = True
    try:
        import nibabel as nib  # noqa: F401
    except ImportError:
        nib_available = False
        all_warnings.append("nibabel is not installed; NIfTI metadata unavailable.")

    for path in paths[:200]:
        subject = _subject_from_path(path)
        modality = _canonical_sequence_from_name(path.name) or "unknown"
        record_warnings: list[str] = []

        exists = path.is_file()
        readable = False
        dimensions: list[int] = []
        ndim: int | None = None
        vol_count: int | None = None
        voxel_spacing: list[float] = []
        dtype: str | None = None
        orientation: str | None = None
        affine_det: float | None = None

        stats: dict[str, Any] = {
            "intensity_min": None, "intensity_max": None,
            "intensity_mean": None, "intensity_std": None,
            "zero_fraction": None, "nan_count": 0,
        }

        if not exists:
            record_warnings.append("File not found.")
            images.append(NiftiImageQcRecord(
                image_id=f"nifti_{len(images):04d}",
                path=str(path),
                subject_id=subject, modality=modality,
                exists=False, warnings=record_warnings,
            ))
            unreadable_count += 1
            continue

        if not nib_available:
            record_warnings.append("nibabel unavailable; skipping metadata.")
            images.append(NiftiImageQcRecord(
                image_id=f"nifti_{len(images):04d}",
                path=str(path),
                subject_id=subject, modality=modality,
                exists=True, warnings=record_warnings,
            ))
            unreadable_count += 1
            continue

        try:
            import nibabel as nib
            img = nib.load(str(path))
            shape = [int(s) for s in img.shape]
            dimensions = shape
            ndim = len(shape)
            dtype = str(img.get_data_dtype())
            voxel_spacing = [round(float(z), 4) for z in img.header.get_zooms()[:ndim]]
            orientation = " ".join(
                nib.aff2axcodes(img.affine) if hasattr(nib, "aff2axcodes") else "?"
            )
            affine_det = round(float(np.linalg.det(img.affine)), 6) if img.affine is not None else None

            if ndim >= 4:
                vol_count = shape[3]
                four_d_count += 1
            elif ndim == 3:
                vol_count = 1

            # Dimension warnings
            if ndim and ndim < 3:
                record_warnings.append(f"Image is only {ndim}D; expected at least 3D.")
            if vol_count is not None and vol_count < 3 and ndim and ndim >= 4:
                record_warnings.append(f"4D BOLD has only {vol_count} volumes; at least 3 expected.")
            if voxel_spacing:
                if any(z <= 0 for z in voxel_spacing[:3]):
                    record_warnings.append("Non-positive voxel spacing detected.")

            # Intensity stats (sampled)
            try:
                data = np.asanyarray(img.dataobj)
                stats = _read_stats(data)
                if stats["zero_fraction"] is not None and stats["zero_fraction"] > 0.95:
                    record_warnings.append(
                        f"High zero fraction: {stats['zero_fraction']:.2%}."
                    )
                if stats["nan_count"] and stats["nan_count"] > 0:
                    record_warnings.append(f"NaN values detected: {stats['nan_count']}.")
                if stats["intensity_min"] == stats["intensity_max"] and stats["intensity_max"] is not None:
                    record_warnings.append("Constant intensity; image may be empty or masked.")
            except Exception as exc:
                record_warnings.append(f"Intensity statistics unavailable: {exc}")

            readable = True
            readable_count += 1

        except Exception as exc:
            record_warnings.append(f"Failed to read NIfTI: {exc}")
            unreadable_count += 1

        images.append(NiftiImageQcRecord(
            image_id=f"nifti_{len(images):04d}",
            path=str(path),
            relative_path=_relative_path(path, Path(".")),
            subject_id=subject, session_id=None, modality=modality,
            exists=exists, readable=readable,
            dimensions=dimensions, ndim=ndim, volume_count=vol_count,
            voxel_spacing=voxel_spacing, dtype=dtype, orientation=orientation,
            affine_determinant=affine_det,
            intensity_min=stats["intensity_min"],
            intensity_max=stats["intensity_max"],
            intensity_mean=stats["intensity_mean"],
            intensity_std=stats["intensity_std"],
            zero_fraction=stats["zero_fraction"],
            nan_count=stats.get("nan_count", 0),
            warnings=record_warnings,
        ))
        warning_count += len(record_warnings)

    # Status
    if not paths:
        status = "warning"
        all_warnings.append(
            "No NIfTI (.nii / .nii.gz) files found in registered project evidence roots. "
            "If the dataset contains DICOM (.dcm) files, run Conversion Dry-Run to "
            "plan a DICOM-to-NIfTI conversion."
        )
    elif readable_count == 0:
        status = "blocked"
        errors.append("No readable NIfTI images found.")
    elif unreadable_count > 0 and readable_count == 0:
        status = "blocked"
    elif unreadable_count > 0:
        status = "warning"
    else:
        status = "ready"

    next_actions: list[str] = []
    if not paths:
        next_actions.append("Run Conversion Dry-Run to plan DICOM-to-NIfTI conversion if your dataset contains DICOM files.")
        next_actions.append("Import or configure a project with NIfTI data if direct NIfTI analysis is required.")
    if unreadable_count > 0:
        next_actions.append("Review unreadable images; they may be corrupted or not NIfTI.")
    if warning_count > 0:
        next_actions.append("Review QC warnings for image quality issues.")

    return NiftiQcSnapshotResponse(
        ok=True,  # Always ok — missing NIfTI is a warning, not a failure
        project_id=project_id,
        status=status,
        checked_at=now,
        image_count=len(images),
        readable_count=readable_count,
        unreadable_count=unreadable_count,
        four_d_count=four_d_count,
        warning_count=warning_count + len(all_warnings),
        images=images,
        warnings=all_warnings[:30],
        errors=errors[:20],
        next_actions=next_actions[:10],
        safety_flags={
            "read_only": True,
            "rawdata_not_modified": True,
            "no_preprocessing_executed": True,
            "no_external_tools_executed": True,
            "qc_snapshot_only": True,
            "clinical_use_prohibited": True,
        },
    )
