"""Read-only BOLD reference readiness inspector.

Discovers BOLD NIfTI files, inspects dimensionality and sidecar metadata
using nibabel if available, and proposes a reference strategy without
computing or writing any reference image.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    BoldReferenceCandidate,
    BoldReferenceReadinessResponse,
)
from src.backend.app.services.image_preview import list_image_sources
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.qc_evidence_roots import collect_qc_evidence_roots

_NIFTI_EXT = (".nii", ".nii.gz")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_bold(path: Path) -> bool:
    return "bold" in path.name.lower()


def _read_nifti_dims(path: Path) -> tuple[list[int], list[float], int | None, bool]:
    """Return (dimensions, voxel_spacing, volume_count, is_4d)."""
    try:
        import nibabel as nib
        img = nib.load(str(path))
        shape = list(img.shape)
        hdr = img.header
        zooms = list(getattr(hdr, "get_zooms", lambda: [1.0, 1.0, 1.0, 1.0])())[:3]
        ndim = len(shape)
        is_4d = ndim == 4
        volume_count = shape[3] if is_4d else (1 if ndim == 3 else None)
        return shape, zooms, volume_count, is_4d
    except Exception:
        return [], [], None, False


def _read_sidecar(path: Path) -> dict[str, Any]:
    """Try to read a BOLD sidecar JSON; return empty dict on failure."""
    base = path.name
    for ext in (".nii.gz", ".nii"):
        if base.endswith(ext):
            base = base[: -len(ext)]
            break
    json_path = path.with_name(base + ".json")
    if not json_path.is_file():
        json_path = path.with_suffix("").with_suffix("").with_suffix(".json")
    if not json_path.is_file():
        return {}
    try:
        return json.loads(json_path.read_text(encoding="utf-8"))
    except (JSONDecodeError, OSError):
        return {"_malformed": True}


def _propose_strategy(volume_count: int | None, is_4d: bool) -> str:
    if volume_count is None:
        return "manual_required"
    if is_4d and volume_count >= 3:
        return "middle_volume"
    if is_4d or volume_count == 1:
        return "single_volume"
    return "manual_required"


def build_bold_reference_readiness(project_id: str) -> BoldReferenceReadinessResponse:
    """Inspect BOLD files and report reference readiness."""

    now = _now_iso()
    warnings: list[str] = []
    errors: list[str] = []
    candidates: list[dict[str, Any]] = []

    project = mock_store.get_project(project_id)
    if project is None:
        return BoldReferenceReadinessResponse(
            ok=False, project_id=project_id, status="blocked", checked_at=now,
            errors=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    search_roots = [
        str(root)
        for root in collect_qc_evidence_roots(project_id, include_native_outputs=False)
    ]

    # Discover BOLD NIfTI files
    bold_paths: list[tuple[str | None, Path, str | None]] = []
    try:
        sources = list_image_sources(project_id=project_id, search_roots=search_roots)
        for subject in sources.subjects:
            for detail in subject.file_details:
                if _is_bold(Path(detail.file_path)):
                    bold_paths.append((subject.subject_id, Path(detail.file_path), detail.session_id))
    except Exception as exc:
        warnings.append(f"IMAGE_SOURCE_DISCOVERY_FAILED: {exc}")

    for root_str in search_roots:
        try:
            root = Path(root_str).expanduser().resolve()
        except Exception:
            continue
        if not root.exists():
            continue
        for nifti in root.rglob("*"):
            if not nifti.is_file() or "".join(nifti.suffixes) not in _NIFTI_EXT:
                continue
            if not _is_bold(nifti):
                continue
            if any(str(nifti) == str(bp[1]) for bp in bold_paths):
                continue
            subj = None
            for ancestor in nifti.parents:
                if ancestor.name.startswith("sub-"):
                    subj = ancestor.name
                    break
            bold_paths.append((subj or nifti.parent.name, nifti, None))

    if not bold_paths:
        return BoldReferenceReadinessResponse(
            ok=True, project_id=project_id, status="blocked", checked_at=now,
            warnings=["No BOLD NIfTI files were found in registered project evidence roots."],
            next_actions=["Run DICOM-to-NIfTI conversion or register a BIDS dataset with BOLD functional data."],
            safety_flags=_safety_flags(),
        )

    ready_count = 0
    warning_count = 0
    blocked_count = 0
    for subject_id, bold_path, session_id in bold_paths[:100]:
        dims, voxel_spacing, volume_count, is_4d = _read_nifti_dims(bold_path)
        sidecar = _read_sidecar(bold_path)
        has_sidecar = len(sidecar) > 0 and not sidecar.get("_malformed")
        sidecar_malformed = sidecar.get("_malformed", False)
        tr = sidecar.get("RepetitionTime")
        task_name = sidecar.get("TaskName")
        has_slice_timing = "SliceTiming" in sidecar
        pe_dir = sidecar.get("PhaseEncodingDirection")

        strategy = _propose_strategy(volume_count, is_4d)

        cand_warnings: list[str] = []
        if not dims:
            cand_warnings.append("Could not read NIfTI dimensions (nibabel may be unavailable).")
            blocked_count += 1
        elif not is_4d:
            cand_warnings.append("BOLD file is 3D (single volume). A reference can still be planned.")
            warning_count += 1
        elif volume_count and volume_count < 3:
            cand_warnings.append(f"BOLD has only {volume_count} volume(s); middle-volume reference not available.")
            warning_count += 1
        else:
            ready_count += 1

        if not has_sidecar:
            cand_warnings.append("Missing BOLD sidecar JSON.")
            if not dims:
                pass  # already counted
            elif volume_count and volume_count >= 3:
                warning_count = max(warning_count, 1)  # at least one warning
        if sidecar_malformed:
            cand_warnings.append("BOLD sidecar JSON is malformed.")
        if not tr:
            cand_warnings.append("RepetitionTime is missing from sidecar.")
        if not task_name:
            cand_warnings.append("TaskName is missing from sidecar.")

        candidates.append({
            "subject_id": subject_id,
            "session_id": session_id,
            "bold_path": str(bold_path),
            "relative_path": None,
            "dimensions": dims,
            "voxel_spacing": voxel_spacing[:3] if len(voxel_spacing) >= 3 else voxel_spacing,
            "volume_count": volume_count,
            "is_4d": is_4d,
            "has_sidecar": has_sidecar,
            "repetition_time": float(tr) if isinstance(tr, (int, float)) else None,
            "task_name": str(task_name) if task_name else None,
            "has_slice_timing": has_slice_timing,
            "phase_encoding_direction": str(pe_dir) if pe_dir else None,
            "reference_strategy": strategy,
            "warnings": cand_warnings,
        })

    if blocked_count == len(candidates) and len(candidates) > 0:
        status = "blocked"
    elif warning_count > 0:
        status = "warning"
    elif ready_count > 0:
        status = "ready"
    else:
        status = "unknown"

    next_actions: list[str] = []
    if status == "blocked":
        next_actions.append("Import a BIDS dataset with readable 4D BOLD NIfTI files.")
    if any(not c["has_sidecar"] for c in candidates):
        next_actions.append("Create missing BOLD sidecar JSON files with RepetitionTime and TaskName.")
    if any(not c["is_4d"] for c in candidates):
        next_actions.append("3D BOLD files detected — single-volume reference will be used.")
    if ready_count > 0:
        next_actions.append(f"{ready_count} BOLD candidate(s) are ready for reference planning.")

    return BoldReferenceReadinessResponse(
        ok=True, project_id=project_id, status=status, checked_at=now,
        candidate_count=len(candidates),
        ready_count=ready_count, warning_count=warning_count, blocked_count=blocked_count,
        candidates=[BoldReferenceCandidate(**c) for c in candidates],
        warnings=warnings[:30], errors=errors[:20],
        next_actions=next_actions[:10],
        safety_flags=_safety_flags(),
    )


def _safety_flags() -> dict[str, bool]:
    return {
        "read_only": True,
        "rawdata_not_modified": True,
        "no_reference_image_written": True,
        "no_external_tools_executed": True,
        "planning_only": True,
    }
