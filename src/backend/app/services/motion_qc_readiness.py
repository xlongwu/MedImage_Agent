"""Read-only motion QC readiness inspector.

Scans project BOLD NIfTI files and existing motion parameter / confounds
TSV files to determine whether motion QC can be planned.  Never computes
realignment, never writes files, never calls external tools.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    MotionQcInputCandidate,
    MotionQcReadinessResponse,
)
from src.backend.app.services.image_preview import list_image_sources
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.qc_evidence_roots import collect_qc_evidence_roots


_MOTION_PARAM_PATTERNS = [
    "rp_*.txt",
    "motion*.txt",
    "*motion*.tsv",
    "*fd*.tsv",
    "*framewise_displacement*.tsv",
    "*confound*.tsv",
    "desc-confounds_timeseries.tsv",
    "confounds*.tsv",
]

_FD_COLUMN_NAMES = {"framewise_displacement", "fd", "FD", "framewise_displacement_mm"}

_NIFTI_EXT = (".nii", ".nii.gz")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_bold(path: Path) -> bool:
    name = path.name.lower()
    return "bold" in name


def _find_motion_files(root: Path) -> list[Path]:
    results: list[Path] = []
    for pattern in _MOTION_PARAM_PATTERNS:
        try:
            results.extend(root.rglob(pattern))
        except (OSError, PermissionError):
            pass
    return sorted(set(results))


def _has_fd_column(tsv_path: Path) -> bool:
    try:
        with tsv_path.open("r", encoding="utf-8", errors="replace") as handle:
            reader = csv.reader(handle, delimiter="\t")
            header = next(reader, [])
            return any(col.strip() in _FD_COLUMN_NAMES for col in header)
    except Exception:
        return False


def _has_subject_segment(path: Path) -> bool:
    return any(part.lower().startswith("sub-") for part in path.parts)


def build_motion_qc_readiness(project_id: str) -> MotionQcReadinessResponse:
    """Inspect project data for motion-QC readiness without realignment."""

    now = _now_iso()
    warnings: list[str] = []
    errors: list[str] = []
    candidates: list[dict[str, Any]] = []

    project = mock_store.get_project(project_id)
    if project is None:
        return MotionQcReadinessResponse(
            ok=False, project_id=project_id, status="blocked", checked_at=now,
            errors=[f"Project not found: {project_id}"],
            safety_flags={
                "read_only": True, "rawdata_not_modified": True,
                "no_realign_executed": True, "no_external_tools_executed": True,
                "planning_only": True,
            },
        )

    search_roots = [
        str(root)
        for root in collect_qc_evidence_roots(project_id, include_native_outputs=False)
    ]
    motion_roots = collect_qc_evidence_roots(
        project_id,
        include_rawdata=False,
        include_native_outputs=True,
    )

    # Discover image sources (NIfTI files)
    bold_paths: list[tuple[str, Path, str | None]] = []  # (subject_id, path, session_id)
    try:
        sources = list_image_sources(project_id=project_id, search_roots=search_roots)
        for subject in sources.subjects:
            for detail in subject.file_details:
                if _is_bold(Path(detail.file_path)):
                    bold_paths.append((
                        subject.subject_id,
                        Path(detail.file_path),
                        detail.session_id,
                    ))
    except Exception as exc:
        warnings.append(f"IMAGE_SOURCE_DISCOVERY_FAILED: {exc}")

    # Also scan rawdata roots directly for BOLD files in BIDS structure
    for root_str in search_roots:
        try:
            root = Path(root_str).expanduser().resolve()
        except Exception:
            continue
        if not root.exists():
            continue
        for nifti in root.rglob("*"):
            if not nifti.is_file():
                continue
            if "".join(nifti.suffixes) not in _NIFTI_EXT:
                continue
            if not _is_bold(nifti):
                continue
            # Avoid duplicates
            if any(str(nifti) == str(bp[1]) for bp in bold_paths):
                continue
            subject_id = None
            for ancestor in nifti.parents:
                if ancestor.name.startswith("sub-"):
                    subject_id = ancestor.name
                    break
            bold_paths.append((subject_id or nifti.parent.name, nifti, None))

    if not bold_paths:
        return MotionQcReadinessResponse(
            ok=True, project_id=project_id, status="blocked", checked_at=now,
            warnings=["No BOLD NIfTI files were found in registered project evidence roots."],
            next_actions=["Run DICOM-to-NIfTI conversion or register a BIDS dataset with BOLD functional data."],
            safety_flags={
                "read_only": True, "rawdata_not_modified": True,
                "no_realign_executed": True, "no_external_tools_executed": True,
                "planning_only": True,
            },
        )

    project_motion_files: list[Path] = []
    for root in motion_roots:
        project_motion_files.extend(_find_motion_files(root))
    project_motion_files = sorted(set(project_motion_files))
    unscoped_project_motion = [
        path for path in project_motion_files if not _has_subject_segment(path)
    ]

    # Analyse each BOLD candidate
    missing_motion_count = 0
    fd_available_count = 0
    for subject_id, bold_path, session_id in bold_paths[:100]:
        bold_dir = bold_path.parent
        has_sidecar = bold_path.with_suffix("").with_suffix(".json").exists()
        # Also check for .nii.gz sidecar
        if not has_sidecar:
            sidecar = bold_path.with_suffix("").with_suffix("").with_suffix(".json")
            has_sidecar = sidecar.exists()

        motion_files = _find_motion_files(bold_dir)
        # Also check parent (subject) directory
        parent_motion = _find_motion_files(bold_path.parent.parent)
        subject_motion = [
            path
            for path in project_motion_files
            if subject_id and subject_id.lower() in str(path).lower()
        ]
        project_level_motion_used = not subject_motion and bool(unscoped_project_motion)
        all_motion = sorted(
            set(
                motion_files
                + parent_motion
                + subject_motion
                + (unscoped_project_motion if project_level_motion_used else [])
            )
        )
        has_motion = len(all_motion) > 0

        fd_source: str | None = None
        has_fd = False
        for mp in all_motion:
            if mp.suffix == ".tsv" and _has_fd_column(mp):
                has_fd = True
                fd_source = str(mp)
                break

        if not has_motion:
            missing_motion_count += 1
        if has_fd:
            fd_available_count += 1

        cand_warnings: list[str] = []
        if not has_sidecar:
            cand_warnings.append("Missing BOLD sidecar JSON.")
        if not has_motion:
            cand_warnings.append("No motion parameter or confounds files found for this subject.")
        elif project_level_motion_used:
            cand_warnings.append(
                "Project-level native motion evidence found; subject linkage is not explicit."
            )

        candidates.append({
            "subject_id": subject_id,
            "session_id": session_id,
            "bold_path": str(bold_path),
            "relative_path": None,
            "has_sidecar": has_sidecar,
            "has_motion_params": has_motion,
            "motion_param_paths": [str(p) for p in all_motion],
            "has_fd_column": has_fd,
            "fd_source_path": fd_source,
            "warnings": cand_warnings,
        })

    # Determine status
    if missing_motion_count == len(candidates):
        status: str = "warning"
        warnings.append("No BOLD file has motion parameter or confounds files. Motion QC cannot be planned without motion inputs.")
    elif fd_available_count > 0:
        status = "ready"
    elif missing_motion_count > 0:
        status = "warning"
    else:
        status = "ready"

    next_actions: list[str] = []
    if status == "blocked":
        next_actions.append("Import a BIDS dataset with BOLD functional data and run realignment to produce motion parameters.")
    if missing_motion_count > 0:
        next_actions.append(f"{missing_motion_count} BOLD file(s) lack motion parameters. Run realignment (SPM/FSL) to generate rp_*.txt files.")
    if fd_available_count > 0:
        fd_subject_count = len({
            str(candidate.get("subject_id") or "")
            for candidate in candidates
            if candidate.get("has_fd_column") and candidate.get("subject_id")
        })
        next_actions.append(
            f"FD column available for {fd_available_count} BOLD candidate(s) "
            f"across {fd_subject_count} subject(s). Motion QC computation can proceed."
        )
    if status == "ready":
        next_actions.append("Motion QC data is ready. Generate a preprocessing plan in the Plan Review Console.")

    return MotionQcReadinessResponse(
        ok=True,
        project_id=project_id,
        status=status,
        checked_at=now,
        candidate_count=len(candidates),
        candidates=[MotionQcInputCandidate(**c) for c in candidates],
        missing_motion_param_count=missing_motion_count,
        fd_available_count=fd_available_count,
        warnings=warnings[:30],
        errors=errors[:20],
        next_actions=next_actions[:10],
        safety_flags={
            "read_only": True,
            "rawdata_not_modified": True,
            "no_realign_executed": True,
            "no_external_tools_executed": True,
            "planning_only": True,
        },
    )
