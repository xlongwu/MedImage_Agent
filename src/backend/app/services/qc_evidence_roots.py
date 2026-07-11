"""Project-scoped evidence roots for read-only QC services."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from src.backend.app.services.mock_store import mock_store


_REGISTERED_INPUT_FIELDS = (
    "preprocessing_input_dir",
    "converted_bids_dir",
    "last_conversion_output_root",
)


def _resolved_existing_dirs(paths: Iterable[str | Path]) -> list[Path]:
    roots: list[Path] = []
    seen: set[str] = set()
    for raw in paths:
        if not raw:
            continue
        try:
            root = Path(raw).expanduser().resolve()
        except (OSError, RuntimeError, ValueError):
            continue
        if not root.is_dir():
            continue
        key = str(root)
        if key in seen:
            continue
        seen.add(key)
        roots.append(root)
    return roots


def collect_qc_evidence_roots(
    project_id: str,
    *,
    include_rawdata: bool = True,
    include_native_outputs: bool = False,
) -> list[Path]:
    """Return existing project roots that may hold QC evidence.

    Registered converted/preprocessing inputs are preferred over rawdata so
    projects converted from DICOM can be reviewed without re-importing BIDS.
    """

    project = mock_store.get_project(project_id)
    if project is None:
        return []

    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    candidates: list[str | Path] = []

    for field in _REGISTERED_INPUT_FIELDS:
        value = str(metadata.get(field) or "")
        if value:
            candidates.append(value)

    project_dir = str(metadata.get("project_dir") or "")
    if project_dir:
        project_root = Path(project_dir)
        candidates.append(project_root / "converted_bids")
        if include_native_outputs:
            candidates.append(project_root / "preprocessing_native_runs")

    try:
        candidates.extend(mock_store.list_import_paths(project_id))
    except Exception:
        pass

    if include_rawdata:
        rawdata = str(metadata.get("rawdata_dir") or "")
        if rawdata:
            candidates.append(rawdata)

    return _resolved_existing_dirs(candidates)
