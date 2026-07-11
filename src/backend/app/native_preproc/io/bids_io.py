"""Small BIDS-oriented wrappers used by native preprocessing."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from src.backend.app.native_preproc.io.sidecar import (
    find_bids_sidecar_for_nifti,
    read_bids_metadata,
)


def resolve_bold_sidecar(bold_path: str | Path) -> Path | None:
    return find_bids_sidecar_for_nifti(bold_path)


def load_bold_metadata(bold_path: str | Path, sidecar_path: str | Path | None = None) -> dict[str, Any]:
    return read_bids_metadata(bold_path, sidecar_path)
