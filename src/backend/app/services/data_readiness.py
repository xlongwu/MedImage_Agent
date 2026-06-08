"""Pure read-only project data readiness aggregator.

Consolidates project metadata, import records, image source discovery,
image validation, DICOM preflight, and dataset index into a single
readiness summary.  Never modifies rawdata, never executes external tools.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import (
    DataReadinessCheck,
    DataReadinessResponse,
    DatasetImportRecord,
)
from src.backend.app.services.bids_validation import bids_summary_check
from src.backend.app.services.dicom_preflight import build_dicom_preflight
from src.backend.app.services.funraw_t1raw_detector import detect_funraw_t1raw_layout
from src.backend.app.services.image_preview import (
    build_image_validation_report,
    list_image_sources,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string_list(items: Any) -> list[str]:
    if not items:
        return []
    if isinstance(items, list):
        return [str(x) for x in items if x]
    return [str(items)]


def _build_check(
    name: str,
    status: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "name": name,
        "status": status,
        "message": message,
        "details": details or {},
    }


def build_data_readiness(project_id: str) -> DataReadinessResponse:
    """Aggregate all data readiness information for a project."""

    warnings: list[str] = []
    errors: list[str] = []
    checks: list[dict[str, Any]] = []
    now = _now_iso()

    # ── 1. Project metadata ──
    project = mock_store.get_project(project_id)
    if project is None:
        return DataReadinessResponse(
            ok=False,
            project_id=project_id,
            status="blocked",
            checked_at=now,
            checks=[
                _build_check("project_metadata", "fail", f"Project not found: {project_id}"),
            ],
            warnings=[],
            errors=[f"Project not found: {project_id}"],
            next_actions=["Create a project from a valid BIDS/rawdata directory."],
        )

    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    rawdata_dir = str(metadata.get("rawdata_dir") or "")
    project_config_path = str(metadata.get("project_config_path") or "")
    dataset_index_path = str(metadata.get("dataset_index_path") or "")

    rawdata_exists = bool(rawdata_dir) and Path(rawdata_dir).exists()
    config_exists = bool(project_config_path) and Path(project_config_path).exists()
    dataset_index_exists = bool(dataset_index_path) and Path(dataset_index_path).exists()

    checks.append(
        _build_check(
            "project_metadata",
            "pass" if (rawdata_dir and project_config_path) else "warning",
            "Project metadata is present." if (rawdata_dir and project_config_path)
            else "Project metadata is incomplete.",
            {
                "rawdata_dir": rawdata_dir or None,
                "project_config_path": project_config_path or None,
                "dataset_index_path": dataset_index_path or None,
            },
        )
    )

    # ── 2. Rawdata path ──
    if rawdata_dir:
        checks.append(
            _build_check(
                "rawdata_path",
                "pass" if rawdata_exists else "fail",
                f"Rawdata directory exists: {rawdata_dir}"
                if rawdata_exists
                else f"Rawdata directory does not exist: {rawdata_dir}",
                {"path": rawdata_dir, "exists": rawdata_exists},
            )
        )
    else:
        checks.append(
            _build_check(
                "rawdata_path",
                "fail",
                "No rawdata directory configured.",
                {"path": None, "exists": False},
            )
        )
        errors.append("No rawdata directory is configured for this project.")

    # ── 3. Import records ──
    imports: list[DatasetImportRecord] = []
    try:
        imports = [
            DatasetImportRecord(**item)
            for item in mock_store.list_import_records(project_id)
        ]
    except Exception as exc:
        warnings.append(f"IMPORT_RECORDS_FAILED: {exc}")

    import_count = len(imports)
    import_paths_exist = sum(
        1 for imp in imports if Path(imp.path).exists()
    )
    has_imports = import_count > 0
    has_dicom = any(imp.dataset_type == "dicom" for imp in imports)

    checks.append(
        _build_check(
            "import_records",
            "pass" if has_imports and import_paths_exist == import_count
            else "warning" if has_imports
            else "warning",
            f"{import_count} import(s) recorded, {import_paths_exist} path(s) exist."
            if has_imports
            else "No dataset imports have been recorded.",
            {
                "import_count": import_count,
                "paths_exist": import_paths_exist,
                "has_dicom": has_dicom,
            },
        )
    )

    if import_count > import_paths_exist:
        warnings.append(f"{import_count - import_paths_exist} import path(s) are missing on disk.")
    if not has_imports:
        warnings.append("No dataset imports recorded. Import a dataset root to enable image discovery.")

    # ── 4. Image source discovery ──
    image_source_count = 0
    subject_count = 0
    sequence_count = 0
    try:
        search_roots = mock_store.list_import_paths(project_id)
        sources = list_image_sources(project_id=project_id, search_roots=search_roots)
        image_source_count = len(sources.manifest)
        subject_count = len(sources.subjects)
        sequence_count = len(sources.sequences)
        warnings.extend(sources.warnings[:10])
    except Exception as exc:
        warnings.append(f"IMAGE_SOURCE_DISCOVERY_FAILED: {exc}")

    checks.append(
        _build_check(
            "image_source_discovery",
            "pass" if image_source_count > 0
            else "warning" if has_imports
            else "fail",
            f"{image_source_count} image source(s) found across {subject_count} subject(s), "
            f"{sequence_count} sequence(s)."
            if image_source_count > 0
            else "No image sources were discovered.",
            {
                "image_source_count": image_source_count,
                "subject_count": subject_count,
                "sequence_count": sequence_count,
            },
        )
    )

    if not image_source_count and has_imports:
        warnings.append("Image sources were not discovered despite recorded imports.")

    # ── 5. Image validation ──
    validation_status = "unknown"
    validation_issues = 0

    # Check for DICOM fallback BEFORE computing image_validation check status
    has_dicom_fallback = False
    if rawdata_dir:
        ft_early = detect_funraw_t1raw_layout(rawdata_dir)
        if ft_early.get("dicom_file_count", 0) > 0:
            has_dicom_fallback = True

    try:
        validation = build_image_validation_report(
            project_id=project_id,
            expected_sequences=project.sequences,
            search_roots=search_roots if has_imports else [],
        )
        validation_status = validation.status
        validation_issues = len(validation.issues)
    except Exception as exc:
        warnings.append(f"IMAGE_VALIDATION_FAILED: {exc}")

    # When DICOM data exists but no NIfTI, downgrade image_validation from fail to warning
    check_status = (
        "pass" if validation_status == "pass"
        else "warning" if validation_status == "warning"
        else "warning" if validation_status == "fail" and has_dicom_fallback and not image_source_count
        else "fail" if validation_status == "fail"
        else "unknown"
    )

    checks.append(
        _build_check(
            "image_validation",
            check_status,
            f"Image validation status: {validation_status}, {validation_issues} issue(s)."
            if image_source_count > 0
            else "Image validation not applicable — no image sources.",
            {
                "status": validation_status,
                "issue_count": validation_issues,
            },
        )
    )

    if validation_status == "fail":
        if not has_dicom_fallback:
            errors.append("Image validation failed — review image validation issues.")
        else:
            warnings.append(
                "No NIfTI image sources found, but DICOM files were detected. "
                "Run Conversion Dry-Run to plan DICOM-to-NIfTI conversion."
            )
    elif validation_status == "warning":
        warnings.append("Image validation returned warnings — review image validation details.")

    # ── 6. Dataset index ──
    checks.append(
        _build_check(
            "dataset_index",
            "pass" if dataset_index_exists
            else "warning" if image_source_count > 0
            else "unknown",
            f"Dataset index exists: {dataset_index_path}"
            if dataset_index_exists
            else "Dataset index has not been generated.",
            {
                "path": dataset_index_path or None,
                "exists": dataset_index_exists,
            },
        )
    )

    if not dataset_index_exists and image_source_count > 0:
        warnings.append(
            "A dataset index has not been generated. Re-create the project "
            "with run_inspection=true or re-run dataset inspection."
        )

    # ── 7. BIDS validation ──
    bids_check = {"name": "bids_validation", "status": "unknown", "message": "BIDS validation not run.", "details": {}}
    roots_for_bids: list[str] = []
    if rawdata_dir:
        roots_for_bids.append(rawdata_dir)
    for imp in imports:
        if imp.path not in roots_for_bids:
            roots_for_bids.append(imp.path)
    if roots_for_bids:
        try:
            bids_check = dict(bids_summary_check(roots_for_bids))
        except Exception as exc:
            bids_check = {
                "name": "bids_validation",
                "status": "unknown",
                "message": f"BIDS validation could not run: {exc}",
                "details": {},
            }
    checks.append(_build_check(**bids_check))

    # ── 8. DICOM preflight ──
    dicom_file_count = 0
    dicom_series_count = 0

    # FunRaw/T1Raw path-based detection (does not require pydicom)
    funraw_detected = False
    if rawdata_dir:
        ft = detect_funraw_t1raw_layout(rawdata_dir)
        if ft["layout_type"] == "funraw_t1raw":
            if ft["dicom_file_count"] > 0:
                funraw_detected = True
                has_dicom = True
                dicom_file_count = ft["dicom_file_count"]
                dicom_series_count = ft["series_count"]
                if not subject_count:
                    subject_count = ft["subject_count"]
                warnings.append(
                    "FunRaw/T1Raw DICOM layout detected. "
                    "Run Conversion Dry-Run to plan DICOM-to-NIfTI conversion."
                )

    if has_dicom and not funraw_detected:
        try:
            dicom_roots = [imp.path for imp in imports if imp.dataset_type == "dicom"]
            preflight = build_dicom_preflight(
                project_id=project_id,
                roots=dicom_roots,
            )
            dicom_file_count = preflight.dicom_file_count
            dicom_series_count = preflight.series_count
            checks.append(
                _build_check(
                    "dicom_preflight",
                    "pass" if dicom_file_count > 0 else "warning",
                    f"DICOM preflight: {dicom_file_count} file(s), "
                    f"{dicom_series_count} series."
                    if dicom_file_count > 0
                    else "DICOM preflight found no DICOM files.",
                    {
                        "dicom_file_count": dicom_file_count,
                        "dicom_series_count": dicom_series_count,
                    },
                )
            )
        except Exception as exc:
            warnings.append(f"DICOM_PREFLIGHT_FAILED: {exc}")
            checks.append(
                _build_check(
                    "dicom_preflight",
                    "warning",
                    f"DICOM preflight failed: {exc}",
                    {},
                )
            )
    elif funraw_detected:
        checks.append(
            _build_check(
                "dicom_preflight",
                "pass" if dicom_file_count > 0 else "warning",
                f"FunRaw/T1Raw DICOM layout: {dicom_file_count} file(s), "
                f"{dicom_series_count} subject-modality group(s).",
                {
                    "dicom_file_count": dicom_file_count,
                    "dicom_series_count": dicom_series_count,
                    "detection_method": "path-based",
                },
            )
        )
    else:
        checks.append(
            _build_check(
                "dicom_preflight",
                "unknown",
                "No DICOM imports recorded — DICOM preflight not applicable.",
                {},
            )
        )

    # ── 9. Rawdata read-only safety ──
    checks.append(
        _build_check(
            "rawdata_read_only",
            "pass",
            "Rawdata directory is referenced read-only. No rawdata files will be modified.",
            {"copy_mode": "reference", "rawdata_readonly": True},
        )
    )

    # ── 9. Determine overall readiness ──
    check_statuses = [c["status"] for c in checks]
    # FunRaw/T1Raw with DICOM files: valid dataset, just needs conversion
    has_dicom_data = has_dicom and dicom_file_count > 0
    if "fail" in check_statuses or not rawdata_exists:
        # Downgrade image_validation fail to warning when DICOM data exists
        if has_dicom_data and not image_source_count:
            overall = "warning"
        else:
            overall = "blocked"
    elif not image_source_count and not has_dicom_data:
        overall = "blocked"
    elif "warning" in check_statuses or validation_status == "warning" or not dataset_index_exists:
        overall = "warning"
    elif validation_status in ("pass", "unknown") and image_source_count > 0:
        overall = "ready"
    else:
        overall = "unknown"

    # ── 10. Next actions ──
    next_actions: list[str] = []
    if not rawdata_exists:
        next_actions.append("Create a project from a valid BIDS/rawdata directory.")
    if not has_imports:
        next_actions.append("Import a dataset root directory to enable image source discovery.")
    if not image_source_count and has_imports:
        next_actions.append("Verify the imported directory contains NIfTI or DICOM files.")
    if validation_status == "fail" and not has_dicom_data:
        next_actions.append("Review and resolve image validation errors.")
    elif validation_status == "fail" and has_dicom_data:
        next_actions.append("Run Conversion Dry-Run to plan DICOM-to-NIfTI conversion.")
    if validation_status == "warning":
        next_actions.append("Review image validation warnings — expected sequences may be incomplete.")
    if has_dicom and dicom_file_count > 0:
        next_actions.append("Run DICOM-to-BIDS conversion to produce a BIDS-compatible rawdata tree.")
    if not dataset_index_exists and image_source_count > 0:
        next_actions.append("Generate a dataset index by re-creating the project with run_inspection=true.")
    if overall in ("ready", "warning"):
        next_actions.append("Generate a reviewed preprocessing plan in Plan Review.")
    if not next_actions:
        next_actions.append("Review project metadata and imports in the Datasets tab.")

    return DataReadinessResponse(
        ok=True,
        project_id=project_id,
        status=overall,
        checked_at=now,
        project_config_path=project_config_path or None,
        dataset_index_path=dataset_index_path or None,
        rawdata_dir=rawdata_dir or None,
        import_count=import_count,
        image_source_count=image_source_count,
        subject_count=subject_count,
        sequence_count=sequence_count,
        dicom_file_count=dicom_file_count,
        dicom_series_count=dicom_series_count,
        checks=[DataReadinessCheck(**c) for c in checks],
        warnings=warnings[:30],
        errors=errors[:20],
        next_actions=next_actions[:10],
    )
