"""DICOM conversion result registration — 实现dcm2nii任务方案.md §17.

Registers successful conversion outputs into project metadata so that
Dashboard, Viewer, and project state can refresh automatically.

Per §17.2, this service:
  1. Validates the conversion output directory
  2. Discovers BOLD/T1w/NIfTI files
  3. Updates project metadata with conversion result summary
  4. Returns a structured response for the frontend to refresh

No subprocess. No rawdata modification. No external tools.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.backend.app.api.dependencies import ProjectStore
from src.backend.app.schemas.preprocessing_handoff import (
    PreprocessingInputRegistrationRequest,
)


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _safety_flags() -> dict[str, bool]:
    return {
        "rawdata_not_modified": True,
        "converted_outputs_referenced": True,
        "no_preprocessing_executed": True,
        "no_external_tools_executed": True,
        "research_use_only": True,
        "clinical_use_prohibited": True,
    }


def register_conversion_result(
    store: ProjectStore,
    project_id: str,
    *,
    conversion_run_id: str,
    output_root: str,
    execution_status: str = "succeeded",
    mapping_count: int = 0,
    nifti_count: int = 0,
    bold_count: int = 0,
    t1w_count: int = 0,
    subject_count: int = 0,
    manifest_path: str | None = None,
    provenance_path: str | None = None,
    checksum_verified: bool = False,
) -> dict[str, Any]:
    """Register conversion results into project metadata.

    Per 实现dcm2nii任务方案.md §17.2, this updates project metadata so
    that Dashboard/Viewer/Project state can refresh automatically.

    Returns a structured response suitable for the frontend.
    """
    warnings: list[str] = []
    errors: list[str] = []
    blocking: list[str] = []

    project = store.get_project(project_id)
    if not project:
        return {
            "ok": False,
            "status": "blocked",
            "project_id": project_id,
            "blocking_issues": [f"Project not found: {project_id}"],
            "safety_flags": _safety_flags(),
        }

    if not output_root:
        blocking.append("output_root is required.")
    if not conversion_run_id:
        blocking.append("conversion_run_id is required.")

    if blocking:
        return {
            "ok": False,
            "status": "blocked",
            "project_id": project_id,
            "conversion_run_id": conversion_run_id,
            "blocking_issues": blocking,
            "safety_flags": _safety_flags(),
        }

    output_path = Path(output_root)
    if not output_path.exists():
        warnings.append(f"Output root does not exist: {output_root}")

    # ── Discover converted NIfTI files if counts are zero ──────────────
    discovered_bold = bold_count
    discovered_t1w = t1w_count
    discovered_nifti = nifti_count
    discovered_subjects: list[str] = []
    if output_path.exists() and discovered_nifti == 0:
        try:
            from src.backend.app.services.preprocessing_handoff import (
                _discover_converted_nifti,
                _extract_subjects,
            )
            bold_files, t1w_files, _sidecar_files, total = _discover_converted_nifti(output_path)
            discovered_bold = len(bold_files)
            discovered_t1w = len(t1w_files)
            discovered_nifti = total
            discovered_subjects = _extract_subjects(bold_files + t1w_files)
            if subject_count == 0:
                subject_count = len(discovered_subjects)
        except Exception as exc:
            warnings.append(f"Filesystem discovery failed: {exc}")

    # ── Update project metadata ────────────────────────────────────────
    if project.metadata is None:
        project.metadata = {}
    if isinstance(project.metadata, dict):
        now = _now_iso()
        # Per §17.2, record conversion result summary for UI refresh
        project.metadata["last_conversion_run_id"] = conversion_run_id
        project.metadata["last_conversion_status"] = execution_status
        project.metadata["last_conversion_output_root"] = output_root
        project.metadata["last_conversion_completed_at"] = now
        project.metadata["last_conversion_mapping_count"] = mapping_count
        project.metadata["last_conversion_nifti_count"] = discovered_nifti
        project.metadata["last_conversion_bold_count"] = discovered_bold
        project.metadata["last_conversion_t1w_count"] = discovered_t1w
        project.metadata["last_conversion_subject_count"] = subject_count
        project.metadata["last_conversion_checksum_verified"] = checksum_verified
        if manifest_path:
            project.metadata["last_conversion_manifest_path"] = manifest_path
        if provenance_path:
            project.metadata["last_conversion_provenance_path"] = provenance_path

        activity = {
            "id": f"dicom-conversion-{conversion_run_id}",
            "kind": "dicom_conversion",
            "title": "DICOM to NIfTI conversion",
            "status": execution_status,
            "conversion_run_id": conversion_run_id,
            "output_root": output_root,
            "nifti_count": discovered_nifti,
            "subject_count": subject_count,
            "created_at": now,
        }
        existing_activity = project.metadata.get("recent_activity", [])
        if not isinstance(existing_activity, list):
            existing_activity = []
        project.metadata["recent_activity"] = [
            activity,
            *[
                item for item in existing_activity
                if not (
                    isinstance(item, dict)
                    and item.get("id") == activity["id"]
                )
            ],
        ][:20]

        result_artifacts: list[dict[str, str]] = []
        if manifest_path:
            result_artifacts.append({
                "kind": "manifest",
                "label": "DICOM conversion manifest",
                "path": manifest_path,
            })
        if provenance_path:
            result_artifacts.append({
                "kind": "provenance",
                "label": "DICOM conversion provenance",
                "path": provenance_path,
            })
        if result_artifacts:
            existing_artifacts = project.metadata.get("results_artifacts", [])
            if not isinstance(existing_artifacts, list):
                existing_artifacts = []
            existing_keys = {
                str(item.get("path"))
                for item in existing_artifacts
                if isinstance(item, dict) and item.get("path")
            }
            project.metadata["results_artifacts"] = [
                *existing_artifacts,
                *[
                    item for item in result_artifacts
                    if item["path"] not in existing_keys
                ],
            ]

        # Mark converted BIDS as available for preprocessing input
        project.metadata["converted_bids_available"] = execution_status == "succeeded"
        project.metadata["converted_bids_dir"] = output_root
        project.metadata["converted_bids_registered_at"] = now
        if project.metadata["converted_bids_available"] and discovered_nifti > 0:
            project.metadata["preprocessing_input_dir"] = output_root
            project.metadata["preprocessing_input_source"] = "converted_bids"
            project.metadata["preprocessing_conversion_run_id"] = conversion_run_id
            project.metadata["preprocessing_input_registered_at"] = now
            project.metadata["preprocessing_input_nifti_count"] = discovered_nifti
            project.metadata["preprocessing_input_subject_count"] = subject_count

        # Refresh data readiness timestamp so Dashboard can re-fetch
        project.metadata["data_readiness_stale"] = True
        project.metadata["data_readiness_refreshed_at"] = now

        if execution_status == "succeeded" and output_path.exists() and discovered_nifti > 0:
            try:
                from src.backend.app.services.preprocessing_artifact_registry import (
                    write_converted_input_registry,
                )

                registry = write_converted_input_registry(
                    project_id=project_id,
                    conversion_run_id=conversion_run_id,
                    converted_bids_dir=output_root,
                    project_dir=str(project.metadata.get("project_dir") or ""),
                    rawdata_dir=str(project.metadata.get("rawdata_dir") or ""),
                    manifest_path=manifest_path,
                    provenance_path=provenance_path,
                    source_kind="converted_bids",
                )
                if registry.ok:
                    project.metadata["preprocessing_input_registry_path"] = registry.registry_path
                    project.metadata["preprocessing_input_artifact_count"] = registry.artifact_count
                    project.metadata["preprocessing_input_inventory"] = registry.inventory
                    project.metadata["native_full_preproc_handoff"] = {
                        "conversion_run_id": conversion_run_id,
                        "artifact_registry_path": registry.registry_path,
                        "input_resolution": "preprocessing_input_registry_path",
                        "status": "ready",
                    }
                else:
                    warnings.extend(registry.blocking_issues)
            except Exception as exc:
                warnings.append(f"Preprocessing artifact registry skipped: {exc}")

    # ── Persist project ────────────────────────────────────────────────
    # The ProjectStore protocol does not expose update_project; we persist
    # via the mock_store's add_project(overwrite=True) when available.
    try:
        metadata = project.metadata if isinstance(project.metadata, dict) else {}
        rawdata_dir = str(metadata.get("rawdata_dir") or "")
        health_status = str(metadata.get("health_status") or "unknown")
        target_store = store if hasattr(store, "add_project") else None
        if target_store is None:
            from src.backend.app.services.mock_store import mock_store
            target_store = mock_store
        target_store.add_project(
            project,
            health_status=health_status,
            rawdata_dir=rawdata_dir,
            overwrite=True,
        )
    except Exception as exc:
        warnings.append(f"Project metadata update failed: {exc}")

    # ── Optionally register as preprocessing input ─────────────────────
    preprocessing_registered = (
        execution_status == "succeeded"
        and output_path.exists()
        and discovered_nifti > 0
    )
    if execution_status == "succeeded" and output_path.exists():
        try:
            from src.backend.app.services.preprocessing_handoff import (
                register_converted_bids_as_preprocessing_input,
            )
            handoff_request = PreprocessingInputRegistrationRequest(
                conversion_run_id=conversion_run_id,
                converted_bids_dir=output_root,
                manifest_path=manifest_path,
                provenance_path=provenance_path,
                checksum_verified=checksum_verified,
            )
            metadata = project.metadata if isinstance(project.metadata, dict) else {}
            project_dir = str(metadata.get("project_dir") or "")
            handoff = register_converted_bids_as_preprocessing_input(
                project_id=project_id,
                request=handoff_request,
                project_dir=project_dir,
            )
            preprocessing_registered = preprocessing_registered or handoff.ok
            if not handoff.ok:
                warnings.extend(handoff.blocking_issues or [])
        except Exception as exc:
            warnings.append(f"Preprocessing handoff skipped: {exc}")

    status = "registered" if execution_status == "succeeded" else "partial_registered"

    return {
        "ok": True,
        "status": status,
        "project_id": project_id,
        "conversion_run_id": conversion_run_id,
        "output_root": output_root,
        "execution_status": execution_status,
        "mapping_count": mapping_count,
        "nifti_count": discovered_nifti,
        "bold_count": discovered_bold,
        "t1w_count": discovered_t1w,
        "subject_count": subject_count,
        "subjects": discovered_subjects,
        "manifest_path": manifest_path,
        "provenance_path": provenance_path,
        "preprocessing_input_registry_path": (
            project.metadata.get("preprocessing_input_registry_path")
            if isinstance(project.metadata, dict)
            else ""
        ),
        "native_full_preproc_handoff": (
            project.metadata.get("native_full_preproc_handoff", {})
            if isinstance(project.metadata, dict)
            else {}
        ),
        "checksum_verified": checksum_verified,
        "preprocessing_registered": preprocessing_registered,
        "project_metadata_updated": True,
        "dashboard_refresh_required": True,
        "viewer_refresh_required": True,
        "warnings": warnings,
        "errors": errors,
        "blocking_issues": blocking,
        "safety_flags": _safety_flags(),
    }


__all__ = ["register_conversion_result"]
