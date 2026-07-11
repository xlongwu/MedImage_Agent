"""Predictable derivative naming helpers for native preprocessing."""
from __future__ import annotations

from pathlib import Path


def nifti_stem(path: str | Path) -> str:
    source = Path(path)
    if source.name.endswith(".nii.gz"):
        return source.name[:-7]
    if source.suffix == ".nii":
        return source.stem
    return source.stem


def derivative_path(
    output_dir: str | Path,
    source_path: str | Path,
    *,
    stage_id: str,
    suffix: str,
    extension: str = ".nii.gz",
) -> Path:
    safe_stage = stage_id.replace(" ", "_")
    safe_suffix = suffix.replace(" ", "_")
    return Path(output_dir) / safe_stage / f"{nifti_stem(source_path)}_desc-{safe_suffix}{extension}"
