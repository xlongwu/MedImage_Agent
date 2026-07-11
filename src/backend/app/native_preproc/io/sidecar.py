"""BIDS sidecar helpers for native preprocessing."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.runtime.atomic_file import atomic_write_json


def find_bids_sidecar_for_nifti(nifti_path: str | Path) -> Path | None:
    path = Path(nifti_path)
    if path.name.endswith(".nii.gz"):
        candidate = path.with_name(path.name[:-7] + ".json")
    elif path.suffix == ".nii":
        candidate = path.with_suffix(".json")
    else:
        candidate = path.with_suffix(path.suffix + ".json")
    return candidate if candidate.exists() else None


def read_json_sidecar(path: str | Path) -> dict[str, Any]:
    sidecar_path = Path(path)
    return json.loads(sidecar_path.read_text(encoding="utf-8"))


def write_json_sidecar(path: str | Path, payload: dict[str, Any]) -> Path:
    return atomic_write_json(Path(path), payload, schema_version=1)


def read_bids_metadata(nifti_path: str | Path, sidecar_path: str | Path | None = None) -> dict[str, Any]:
    resolved = Path(sidecar_path) if sidecar_path is not None else find_bids_sidecar_for_nifti(nifti_path)
    if resolved is None:
        raise ValueError(f"BIDS sidecar JSON not found for {nifti_path}.")
    metadata = read_json_sidecar(resolved)
    metadata["_sidecar_path"] = str(resolved)
    return metadata


def require_repetition_time(metadata: dict[str, Any]) -> float:
    value = metadata.get("RepetitionTime")
    if value is None:
        raise ValueError("BIDS RepetitionTime is required.")
    tr = float(value)
    if tr <= 0:
        raise ValueError("BIDS RepetitionTime must be positive.")
    return tr


def require_slice_timing(metadata: dict[str, Any], *, nslices: int) -> list[float]:
    value = metadata.get("SliceTiming")
    if value is None:
        raise ValueError("BIDS SliceTiming is required.")
    if not isinstance(value, list):
        raise ValueError("BIDS SliceTiming must be a list.")
    slice_timing = [float(item) for item in value]
    if len(slice_timing) != nslices:
        raise ValueError(f"SliceTiming length {len(slice_timing)} does not match nslices {nslices}.")
    return slice_timing
