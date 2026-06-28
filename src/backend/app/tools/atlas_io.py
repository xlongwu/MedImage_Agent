from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any


class AtlasValidationError(ValueError):
    """Raised when an atlas cannot be used for atlas-grounded FC."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_int_label(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _label_name(item: dict[str, Any], label: int) -> str:
    for key in ("name", "label_name", "roi_name", "region", "description"):
        value = item.get(key)
        if value not in (None, ""):
            return str(value)
    return f"ROI_{label}"


def _read_json_labels(path: Path) -> dict[int, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        rows = payload.get("labels") or payload.get("roi_definitions") or []
    else:
        rows = payload
    labels: dict[int, str] = {}
    for item in rows:
        if not isinstance(item, dict):
            continue
        label = _as_int_label(item.get("label", item.get("id", item.get("index"))))
        if label is not None and label > 0:
            labels[label] = _label_name(item, label)
    return labels


def _read_tsv_labels(path: Path) -> dict[int, str]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        labels: dict[int, str] = {}
        if not reader.fieldnames:
            return labels
        fieldnames = [field.lower() for field in reader.fieldnames]
        label_key = next(
            (reader.fieldnames[idx] for idx, name in enumerate(fieldnames) if name in {"label", "id", "index"}),
            reader.fieldnames[0],
        )
        name_key = next(
            (
                reader.fieldnames[idx]
                for idx, name in enumerate(fieldnames)
                if name in {"name", "label_name", "roi_name", "region", "description"}
            ),
            "",
        )
        for row in reader:
            label = _as_int_label(row.get(label_key))
            if label is None or label <= 0:
                continue
            labels[label] = row.get(name_key) or f"ROI_{label}"
    return labels


def load_label_table(labels_path: str | Path | None) -> dict[int, str]:
    if not labels_path:
        return {}
    path = Path(labels_path)
    if not path.exists():
        raise AtlasValidationError(f"Atlas labels file not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".json":
        return _read_json_labels(path)
    if suffix in {".tsv", ".txt", ".csv"}:
        return _read_tsv_labels(path)
    raise AtlasValidationError(f"Unsupported atlas labels format: {path}")


def load_atlas_for_bold(
    *,
    atlas_path: str | Path,
    bold_img: Any,
    labels_path: str | Path | None = None,
    affine_atol: float = 1e-4,
) -> dict[str, Any]:
    """Load and validate a 3D integer atlas for a 4D BOLD image."""
    try:
        import nibabel as nib
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: nibabel and numpy are required.") from exc

    atlas_file = Path(atlas_path)
    if not atlas_file.exists():
        raise AtlasValidationError(f"Atlas not found: {atlas_file}")

    atlas_img = nib.load(str(atlas_file))
    atlas_data = atlas_img.get_fdata()
    if atlas_data.ndim != 3:
        raise AtlasValidationError(f"Atlas must be 3D. Got shape {atlas_data.shape}.")

    bold_shape = tuple(int(value) for value in bold_img.shape[:3])
    atlas_shape = tuple(int(value) for value in atlas_data.shape)
    if atlas_shape != bold_shape:
        raise AtlasValidationError(f"Atlas shape {atlas_shape} does not match BOLD shape {bold_shape}.")

    if not np.allclose(atlas_img.affine, bold_img.affine, atol=affine_atol):
        raise AtlasValidationError("Atlas affine does not match BOLD affine.")

    finite = np.isfinite(atlas_data)
    if not bool(np.all(finite)):
        raise AtlasValidationError("Atlas contains NaN or infinite labels.")
    rounded = np.rint(atlas_data)
    if not bool(np.allclose(atlas_data, rounded)):
        raise AtlasValidationError("Atlas labels must be integer-valued.")

    atlas_int = rounded.astype("int32")
    labels = sorted(int(label) for label in np.unique(atlas_int) if int(label) > 0)
    if not labels:
        raise AtlasValidationError("Atlas contains no positive ROI labels.")

    label_names = load_label_table(labels_path)
    warnings: list[str] = []
    missing = [label for label in labels if label not in label_names]
    if missing and labels_path:
        warnings.append(f"Labels file missing {len(missing)} atlas label(s); generated fallback ROI names.")

    roi_definitions = [
        {
            "label": label,
            "name": label_names.get(label, f"ROI_{label}"),
            "strategy": "provided_atlas",
        }
        for label in labels
    ]

    labels_extra = sorted(label for label in label_names if label not in labels)
    if labels_extra:
        warnings.append(f"Labels file contains {len(labels_extra)} label(s) not present in atlas.")

    return {
        "atlas_data": atlas_int,
        "atlas_file": str(atlas_file),
        "labels_path": str(labels_path or ""),
        "roi_definitions": roi_definitions,
        "label_count": len(labels),
        "labels": labels,
        "shape": list(atlas_shape),
        "affine": atlas_img.affine.tolist(),
        "checksum": sha256_file(atlas_file),
        "warnings": warnings,
    }


__all__ = [
    "AtlasValidationError",
    "load_atlas_for_bold",
    "load_label_table",
    "sha256_file",
]
