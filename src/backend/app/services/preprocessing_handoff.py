"""Preprocessing handoff service — Phase 5A.

Discovers converted BIDS/NIfTI outputs from a DICOM conversion run and
registers them as preprocessing input.  Never modifies rawdata, never
executes external tools, never runs preprocessing.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_handoff import (
    PreprocessingInputRegistrationRequest,
    PreprocessingInputRegistrationResponse,
)
from src.backend.app.services.mock_store import mock_store

_NIFTI_EXTS = (".nii", ".nii.gz")


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _safety_flags() -> dict[str, bool]:
    return {
        "rawdata_not_modified": True,
        "converted_outputs_referenced": True,
        "no_preprocessing_executed": True,
        "no_external_tools_executed": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }


def _discover_converted_nifti(
    converted_dir: Path,
) -> tuple[list[Path], list[Path], list[Path], int]:
    """Discover BOLD, T1w, and sidecar files under converted_dir."""
    bold_files: list[Path] = []
    t1w_files: list[Path] = []
    sidecar_files: list[Path] = []
    for p in sorted(converted_dir.rglob("*")):
        if not p.is_file():
            continue
        name_lower = p.name.lower()
        if p.suffix in _NIFTI_EXTS or "".join(p.suffixes).lower() in _NIFTI_EXTS:
            if "bold" in name_lower or "rest" in name_lower:
                bold_files.append(p)
            elif "t1" in name_lower:
                t1w_files.append(p)
        elif p.suffix == ".json":
            sidecar_files.append(p)
    return bold_files, t1w_files, sidecar_files, len(bold_files) + len(t1w_files)


def _extract_subjects(nifti_paths: list[Path]) -> list[str]:
    subjects: list[str] = []
    seen: set[str] = set()
    for p in nifti_paths:
        # Extract sub-XXX from path
        for part in p.parts:
            if part.startswith("sub-"):
                if part not in seen:
                    seen.add(part)
                    subjects.append(part)
                break
    return subjects


def register_converted_bids_as_preprocessing_input(
    project_id: str,
    request: PreprocessingInputRegistrationRequest,
    *,
    project_dir: str = "",
) -> PreprocessingInputRegistrationResponse:
    """Register converted BIDS/NIfTI outputs as preprocessing input."""
    warnings: list[str] = []
    errors: list[str] = []
    blocking: list[str] = []

    if not request.conversion_run_id:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            blocking_issues=["conversion_run_id is required."],
            safety_flags=_safety_flags(),
        )

    project = mock_store.get_project(project_id)
    if not project:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=_safety_flags(),
        )

    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    rawdata_dir = str(metadata.get("rawdata_dir") or "")
    effective_project_dir = project_dir or str(metadata.get("project_dir") or "")

    # Determine converted BIDS directory
    converted_bids_dir = request.converted_bids_dir
    if not converted_bids_dir:
        converted_bids_dir = f"{effective_project_dir}/conversion_runs/{request.conversion_run_id}" if effective_project_dir else ""

    if not converted_bids_dir:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Could not determine converted_bids directory."],
            safety_flags=_safety_flags(),
        )

    converted_path = Path(converted_bids_dir).expanduser().resolve()

    # Path safety checks
    if rawdata_dir:
        rawdata_path = Path(rawdata_dir).expanduser().resolve()
        try:
            converted_path.relative_to(rawdata_path)
            return PreprocessingInputRegistrationResponse(
                ok=False, status="blocked", project_id=project_id,
                blocking_issues=["Converted BIDS directory is inside rawdata — refusing."],
                safety_flags=_safety_flags(),
            )
        except ValueError:
            pass

    if ".." in converted_bids_dir:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Path traversal detected in converted_bids_dir."],
            safety_flags=_safety_flags(),
        )

    if not converted_path.exists() or not converted_path.is_dir():
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            conversion_run_id=request.conversion_run_id,
            blocking_issues=[f"Converted BIDS directory not found: {converted_bids_dir}"],
            safety_flags=_safety_flags(),
        )

    # Try to read output manifest for better discovery
    manifest_path = converted_path / "output_manifest.json"
    manifest_found = manifest_path.exists()

    # Discover NIfTI files
    bold_files, t1w_files, sidecar_files, nifti_count = _discover_converted_nifti(converted_path)

    if nifti_count == 0:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            conversion_run_id=request.conversion_run_id,
            preprocessing_input_dir=converted_bids_dir,
            blocking_issues=["No NIfTI files found in converted BIDS directory."],
            safety_flags=_safety_flags(),
        )

    if not manifest_found:
        warnings.append("Output manifest not found; using filesystem discovery.")

    # Extract subjects
    all_nifti = bold_files + t1w_files
    subjects = _extract_subjects(all_nifti)
    bold_subjects = _extract_subjects(bold_files)
    t1w_subjects = _extract_subjects(t1w_files)

    missing_t1w = [s for s in bold_subjects if s not in t1w_subjects]
    missing_bold = [s for s in t1w_subjects if s not in bold_subjects]

    # Warn on missing pairings
    for s in missing_t1w:
        warnings.append(f"Subject {s} has BOLD but no T1w.")
    for s in missing_bold:
        warnings.append(f"Subject {s} has T1w but no BOLD.")

    # Update project metadata to record preprocessing input
    if project.metadata is None:
        project.metadata = {}
    if isinstance(project.metadata, dict):
        project.metadata["preprocessing_input_dir"] = converted_bids_dir
        project.metadata["preprocessing_input_source"] = "converted_bids"
        project.metadata["preprocessing_conversion_run_id"] = request.conversion_run_id
        project.metadata["preprocessing_input_registered_at"] = _now_iso()
        project.metadata["preprocessing_input_nifti_count"] = nifti_count
        project.metadata["preprocessing_input_subject_count"] = len(subjects)

    status = "ready" if not missing_t1w and not missing_bold else "warning"

    return PreprocessingInputRegistrationResponse(
        ok=True, status=status, project_id=project_id,
        conversion_run_id=request.conversion_run_id,
        preprocessing_input_dir=converted_bids_dir,
        rawdata_dir=rawdata_dir,
        subject_count=len(subjects),
        bold_count=len(bold_files),
        t1w_count=len(t1w_files),
        nifti_count=nifti_count,
        sidecar_count=len(sidecar_files),
        missing_t1w_subjects=missing_t1w,
        missing_bold_subjects=missing_bold,
        subjects=subjects,
        warnings=warnings,
        next_actions=[
            "Review preprocessing input registration.",
            "Run NIfTI QC against converted inputs.",
            "Generate preprocessing plan preview.",
        ],
        safety_flags=_safety_flags(),
    )
