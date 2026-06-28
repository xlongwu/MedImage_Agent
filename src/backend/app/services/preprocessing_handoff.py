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
from src.backend.app.services.preprocessing_artifact_registry import (
    write_converted_input_registry,
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
    store: Any | None = None,
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

    project_store = store or mock_store
    project = project_store.get_project(project_id)
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

    registry_result = write_converted_input_registry(
        project_id=project_id,
        conversion_run_id=request.conversion_run_id,
        converted_bids_dir=str(converted_path),
        project_dir=effective_project_dir,
        rawdata_dir=rawdata_dir,
        manifest_path=request.manifest_path or str(manifest_path) if manifest_found else request.manifest_path,
        provenance_path=request.provenance_path,
        source_kind="converted_bids",
    )
    if not registry_result.ok:
        return PreprocessingInputRegistrationResponse(
            ok=False, status="blocked", project_id=project_id,
            conversion_run_id=request.conversion_run_id,
            preprocessing_input_dir=converted_bids_dir,
            blocking_issues=registry_result.blocking_issues,
            warnings=registry_result.warnings,
            errors=registry_result.errors,
            safety_flags=_safety_flags(),
        )

    inventory = registry_result.inventory
    bold_count = int(inventory.get("bold_count", 0))
    t1w_count = int(inventory.get("t1w_count", 0))
    sidecar_count = int(inventory.get("sidecar_count", 0))
    nifti_count = int(inventory.get("nifti_count", 0))
    subjects = [str(s) for s in inventory.get("subjects", [])]
    missing_t1w = [str(s) for s in inventory.get("missing_t1w_subjects", [])]
    missing_bold = [str(s) for s in inventory.get("missing_bold_subjects", [])]
    missing_sidecars = [
        item for item in inventory.get("missing_sidecar_pairings", [])
        if isinstance(item, dict)
    ]

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
    warnings.extend(registry_result.warnings)

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
        project.metadata["preprocessing_input_registry_path"] = registry_result.registry_path
        project.metadata["preprocessing_input_artifact_count"] = registry_result.artifact_count
        project.metadata["preprocessing_input_inventory"] = inventory
        try:
            if hasattr(project_store, "add_project"):
                project_store.add_project(
                    project,
                    health_status=str(project.metadata.get("health_status") or "unknown"),
                    rawdata_dir=rawdata_dir,
                    overwrite=True,
                )
        except Exception as exc:
            warnings.append(f"Project metadata persistence failed: {exc}")

    status = "ready" if not missing_t1w and not missing_bold else "warning"

    return PreprocessingInputRegistrationResponse(
        ok=True, status=status, project_id=project_id,
        conversion_run_id=request.conversion_run_id,
        preprocessing_input_dir=converted_bids_dir,
        rawdata_dir=rawdata_dir,
        subject_count=len(subjects),
        bold_count=bold_count,
        t1w_count=t1w_count,
        nifti_count=nifti_count,
        sidecar_count=sidecar_count,
        artifact_registry_path=registry_result.registry_path,
        artifact_count=registry_result.artifact_count,
        artifacts_by_type=registry_result.artifacts_by_type,
        missing_sidecar_pairings=missing_sidecars,
        bids_entities=[
            item for item in inventory.get("bids_entities", [])
            if isinstance(item, dict)
        ],
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
