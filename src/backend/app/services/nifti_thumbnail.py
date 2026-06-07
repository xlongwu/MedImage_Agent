"""NIfTI slice thumbnail generator — read-only central slice preview.

Generates base64 PNG thumbnails for axial/coronal/sagittal central
slices.  Never modifies rawdata, never writes files, never calls
external tools.
"""

from __future__ import annotations

import base64
import io
from typing import Any

import numpy as np

from src.backend.app.schemas.desktop import (
    NiftiSliceThumbnail,
    NiftiThumbnailResponse,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.nifti_qc_snapshot import _discover_nifti

_MAX_SIZE = 256
_DEFAULT_SIZE = 160


def _find_image(project_id: str, image_id: str) -> Any | None:
    """Find a NIfTI path by image_id from project-discovered images."""
    paths = _discover_nifti(project_id)
    for i, path in enumerate(paths):
        if image_id == f"nifti_{i:04d}":
            return path
    return None


def _extract_slice(
    data: np.ndarray,
    view: str,
    volume_index: int | None,
) -> tuple[np.ndarray, int, int]:
    """Extract a 2D slice from 3D or 4D data.

    Returns (slice_2d, slice_index, volume_index_used).
    """
    ndim = data.ndim
    vol_idx = volume_index or 0

    if ndim >= 4:
        n_vols = data.shape[3]
        if vol_idx < 0 or vol_idx >= n_vols:
            raise ValueError(f"volume_index {vol_idx} out of range (0..{n_vols - 1})")
        vol = data[..., vol_idx]
    else:
        if volume_index is not None and volume_index > 0:
            raise ValueError(f"volume_index {volume_index} is out of range for a 3D image (0 volumes)")
        vol = data
        vol_idx = 0

    if view == "sagittal":
        axis = 0
    elif view == "coronal":
        axis = 1
    else:  # axial
        axis = 2

    slice_count = int(vol.shape[axis])
    slice_idx = slice_count // 2
    if view == "sagittal":
        img = vol[slice_idx, :, :]
    elif view == "coronal":
        img = vol[:, slice_idx, :]
    else:
        img = vol[:, :, slice_idx]

    return np.asarray(img, dtype=np.float32), slice_idx, vol_idx


def _normalize_to_png(
    img_2d: np.ndarray,
    max_size: int,
) -> tuple[str, float, float]:
    """Normalize a 2D slice to grayscale PNG base64.

    Returns (png_base64, intensity_min, intensity_max).
    """
    from PIL import Image

    data = np.nan_to_num(img_2d, nan=0.0, posinf=0.0, neginf=0.0)
    finite = data[np.isfinite(data)]

    if finite.size == 0:
        low, high = 0.0, 1.0
    else:
        low = float(np.min(finite))
        high = float(np.max(finite))
        if high <= low:
            high = low + 1.0

    normalized = np.clip((data - low) / (high - low), 0.0, 1.0)
    uint8 = (normalized * 255).astype(np.uint8)

    # Rotate for standard radiological orientation
    uint8 = np.rot90(uint8)

    h, w = uint8.shape
    scale = min(max_size / h, max_size / w)
    new_h, new_w = int(h * scale), int(w * scale)
    if new_h < 1:
        new_h = 1
    if new_w < 1:
        new_w = 1

    pil_img = Image.fromarray(uint8, mode="L")
    pil_img = pil_img.resize((new_w, new_h), Image.NEAREST)

    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii"), low, high


def build_nifti_thumbnail(
    project_id: str,
    image_id: str,
    view: str = "all",
    volume_index: int | None = None,
    size: int | None = None,
) -> NiftiThumbnailResponse:
    """Generate central slice thumbnail(s) for a project-discovered NIfTI."""
    project = mock_store.get_project(project_id)
    if project is None:
        return NiftiThumbnailResponse(
            ok=False, project_id=project_id, image_id=image_id,
            path="", errors=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    path = _find_image(project_id, image_id)
    if path is None:
        return NiftiThumbnailResponse(
            ok=False, project_id=project_id, image_id=image_id,
            path="", errors=[f"Image not found: {image_id}"],
            safety_flags=_safety_flags(),
        )

    max_size = min(size or _DEFAULT_SIZE, _MAX_SIZE)
    warnings: list[str] = []
    errors: list[str] = []

    try:
        import nibabel as nib
        img = nib.load(str(path))
        data = np.asanyarray(img.dataobj)
        dimensions = [int(s) for s in data.shape]
        volume_count = dimensions[3] if data.ndim >= 4 else None
    except Exception as exc:
        return NiftiThumbnailResponse(
            ok=False, project_id=project_id, image_id=image_id,
            path=str(path), dimensions=[],
            errors=[f"Failed to load NIfTI: {exc}"],
            safety_flags=_safety_flags(),
        )

    views_to_render = ["axial", "coronal", "sagittal"] if view == "all" else [view]
    thumbnails: list[NiftiSliceThumbnail] = []
    selected_vol: int | None = None

    for v in views_to_render:
        try:
            slice_2d, slice_idx, vol_idx = _extract_slice(data, v, volume_index)
            png_b64, lo, hi = _normalize_to_png(slice_2d, max_size)
            thumbnails.append(NiftiSliceThumbnail(
                view=v,
                width=min(max_size, int(slice_2d.shape[1] * max_size / max(slice_2d.shape) if max(slice_2d.shape) > 0 else max_size)),
                height=min(max_size, int(slice_2d.shape[0] * max_size / max(slice_2d.shape) if max(slice_2d.shape) > 0 else max_size)),
                slice_index=slice_idx,
                volume_index=vol_idx if data.ndim >= 4 else None,
                png_base64=png_b64,
                intensity_min=lo,
                intensity_max=hi,
            ))
            if selected_vol is None:
                selected_vol = vol_idx if data.ndim >= 4 else None
        except ValueError as exc:
            msg = str(exc)
            if "volume_index" in msg.lower() or "out of range" in msg.lower():
                raise  # propagate to route for 400
            errors.append(f"View {v}: {exc}")
        except Exception as exc:
            warnings.append(f"Thumbnail for {v}: {exc}")

    return NiftiThumbnailResponse(
        ok=len(thumbnails) > 0,
        project_id=project_id,
        image_id=image_id,
        path=str(path),
        dimensions=dimensions,
        volume_count=volume_count,
        selected_volume_index=selected_vol,
        thumbnails=thumbnails,
        warnings=warnings[:20],
        errors=errors[:20],
        safety_flags=_safety_flags(),
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "read_only": True,
        "rawdata_not_modified": True,
        "no_preprocessing_executed": True,
        "no_external_tools_executed": True,
        "thumbnail_only": True,
        "clinical_use_prohibited": True,
    }
