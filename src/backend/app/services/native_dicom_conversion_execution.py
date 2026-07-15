"""Guarded execution adapter for the in-project DICOM converter."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.native_preproc.io.dicom_to_nifti import (
    ALGORITHM_ID,
    ALGORITHM_VERSION,
    convert_dicom_series,
)
from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.dicom_conversion_execution import (
    DicomConversionSafetyFlags,
    DicomConversionSandboxResult,
)
from src.backend.app.schemas.execution_manifest import (
    ExecutionProvenance,
    OutputManifest,
    OutputManifestItem,
)
from src.backend.app.services.dicom_conversion_safety import (
    build_post_conversion_rawdata_snapshot,
    compare_conversion_rawdata_snapshots,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_under(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _output_name(mapping: dict[str, Any], template: dict[str, Any]) -> str:
    name = str(mapping.get("output_filename") or "").strip()
    if not name:
        name = str(template.get("filename_pattern") or "converted").strip() + ".nii.gz"
    if not name.lower().endswith((".nii", ".nii.gz")):
        name += ".nii.gz"
    if Path(name).name != name or name in {".nii", ".nii.gz"}:
        raise ValueError(f"Unsafe native conversion output filename: {name!r}")
    return name


def execute_native_persisted_conversion(
    *,
    project_id: str,
    conversion_run_id: str,
    project_dir: str,
    rawdata_dir: str,
    evidence_root: str,
    approval: Any,
    approval_record_path: str,
    gate: Any,
    audit_preview_path: str,
    mapping_snapshot_path: str,
    template_snapshot_path: str,
    mappings: list[dict[str, Any]],
    templates: list[dict[str, Any]],
    checksum_before: Any,
    checksum_before_path: str,
    rollback_plan_path: str,
) -> DicomConversionSandboxResult:
    """Execute reviewed mappings with no shell or external process."""

    evidence = Path(evidence_root).resolve()
    project_root = Path(project_dir).resolve()
    raw_root = Path(rawdata_dir).resolve() if rawdata_dir else None
    approved_output_root = Path(str(approval.output_root or project_root / "converted_bids")).resolve()
    blockers: list[str] = []
    errors: list[str] = []
    warnings: list[str] = []
    records: list[dict[str, Any]] = []
    results: list[Any] = []

    if len(mappings) != len(templates) or not mappings:
        blockers.append(
            f"Native conversion requires equal non-zero mapping/template counts; got {len(mappings)}/{len(templates)}."
        )
    if not _is_under(evidence, project_root):
        blockers.append("Execution evidence root is outside the project directory.")
    if not _is_under(approved_output_root, project_root):
        blockers.append("Approved converted output root is outside the project directory.")
    if raw_root and (_is_under(evidence, raw_root) or _is_under(approved_output_root, raw_root)):
        blockers.append("Execution evidence or converted output root is inside rawdata.")
    if blockers:
        return DicomConversionSandboxResult(
            ok=False,
            status="blocked",
            mode="disabled",
            project_id=project_id,
            blocking_issues=blockers,
            safety_flags=DicomConversionSafetyFlags(conversion_disabled_by_default=True),
        )

    evidence.mkdir(parents=True, exist_ok=True)
    audit_start_path = evidence / "audit_execution_start.json"
    audit_final_path = evidence / "audit_execution_final.json"
    manifest_path = evidence / "output_manifest.json"
    provenance_path = evidence / "execution_provenance.json"
    started_at = _now_iso()
    atomic_write_json(
        audit_start_path,
        {
            "project_id": project_id,
            "conversion_run_id": conversion_run_id,
            "audit_state": "execution_started",
            "backend": "medimage-native",
            "algorithm_id": ALGORITHM_ID,
            "algorithm_version": ALGORITHM_VERSION,
            "approval_record_path": approval_record_path,
            "audit_record_path": audit_preview_path,
            "mapping_snapshot_path": mapping_snapshot_path,
            "template_snapshot_path": template_snapshot_path,
            "checksum_before_path": checksum_before_path,
            "rollback_plan_path": rollback_plan_path,
            "started_at": started_at,
            "no_external_process": True,
        },
        schema_version=1,
    )

    for index, (mapping, template) in enumerate(zip(mappings, templates), start=1):
        source = Path(str(mapping.get("source_path") or template.get("input_dir") or "")).resolve()
        output_dir = Path(str(template.get("output_dir") or approved_output_root)).resolve()
        try:
            if raw_root and not _is_under(source, raw_root):
                raise ValueError("Mapping source is outside the approved rawdata directory.")
            if not _is_under(output_dir, approved_output_root):
                raise ValueError("Mapping output is outside the approved converted output root.")
            if raw_root and _is_under(output_dir, raw_root):
                raise ValueError("Mapping output is inside rawdata.")
            output_path = output_dir / _output_name(mapping, template)
            result = convert_dicom_series(
                source,
                output_path,
                subject_id=mapping.get("subject_id"),
                session_id=mapping.get("session_id"),
                modality=mapping.get("modality"),
                overwrite=getattr(approval, "overwrite_policy", "fail_if_exists") == "overwrite_derivatives_only",
            )
            results.append(result)
            warnings.extend(result.warnings)
            records.append(
                {
                    "mapping_index": index,
                    "status": "succeeded",
                    "source_fingerprint_sha256": result.source_fingerprint_sha256,
                    "series_instance_uid_sha256": result.series_instance_uid_sha256,
                    "series_kind": result.series_kind,
                    "source_file_count": result.source_file_count,
                    "output_path": result.nifti_path,
                    "sidecar_path": result.sidecar_path,
                    "output_sha256": result.output_sha256,
                    "shape": list(result.shape),
                    "dtype": result.dtype,
                    "zooms": list(result.zooms),
                }
            )
        except Exception as exc:
            errors.append(f"Native conversion failed for mapping {index}: {exc}")
            records.append({"mapping_index": index, "status": "failed", "error": str(exc)})

    checksum_after = None
    checksum_unchanged = True
    if rawdata_dir:
        checksum_after = build_post_conversion_rawdata_snapshot([rawdata_dir])
        atomic_write_json(evidence / "rawdata_checksum_after.json", checksum_after.model_dump(), schema_version=1)
        if checksum_before is not None:
            comparison = compare_conversion_rawdata_snapshots(checksum_before, checksum_after)
            checksum_unchanged = bool(comparison.unchanged)
            atomic_write_json(
                evidence / "rawdata_checksum_comparison.json",
                comparison.model_dump(),
                schema_version=1,
            )
            if not checksum_unchanged:
                errors.append("Rawdata checksum changed during native conversion.")

    items: list[OutputManifestItem] = []
    for result in results:
        for kind, value in (("nifti", result.nifti_path), ("json", result.sidecar_path)):
            path = Path(value)
            items.append(
                OutputManifestItem(
                    kind=kind,
                    path=str(path),
                    relative_path=str(path.relative_to(approved_output_root)),
                    exists=path.exists(),
                    verified=path.exists(),
                    verification_status="verified" if path.exists() else "missing",
                    size_bytes=path.stat().st_size if path.exists() else None,
                    checksum_sha256=_sha256(path) if path.exists() else None,
                    metadata={"backend": "medimage-native"},
                )
            )
    manifest = OutputManifest(
        project_id=project_id,
        run_id=conversion_run_id,
        node_id="dicom_to_nifti",
        output_root=str(approved_output_root),
        items=items,
        missing_required_count=sum(1 for item in items if not item.exists),
        verified_count=sum(1 for item in items if item.verified),
        error_count=len(errors),
        errors=errors,
    )
    atomic_write_json(manifest_path, manifest.model_dump(), schema_version=1)

    finished_at = _now_iso()
    success_count = len(results)
    failure_count = len(mappings) - success_count
    status = "failed" if errors and not success_count else "partial" if failure_count else "succeeded"
    provenance = ExecutionProvenance(
        project_id=project_id,
        run_id=conversion_run_id,
        node_id="dicom_to_nifti",
        backend="python",
        command_template_id="medimage-native-dicom-v1",
        output_paths=[item.path for item in items],
        output_checksums={item.path: item.checksum_sha256 or "" for item in items},
        software_versions={"native_converter": ALGORITHM_VERSION},
        approval_context={"approval_id": getattr(approval, "approval_id", ""), "gate_status": gate.status},
        audit_id=Path(audit_preview_path).stem,
        started_at=started_at,
        finished_at=finished_at,
        return_code=0 if status == "succeeded" else 1,
        warnings=warnings,
        errors=errors,
        metadata={
            "algorithm_id": ALGORITHM_ID,
            "capability_level": "computed" if success_count else "unavailable",
            "no_external_process": True,
            "rawdata_unchanged": checksum_unchanged,
            "approval_record_path": approval_record_path,
            "approval_status": gate.status,
            "audit_record_path": audit_preview_path,
            "audit_final_path": str(audit_final_path),
            "audit_state": "execution_succeeded" if status == "succeeded" else "execution_failed",
            "checksum_before_path": checksum_before_path,
            "checksum_after_path": str(evidence / "rawdata_checksum_after.json") if checksum_after else None,
            "mapping_success_count": success_count,
            "mapping_failure_count": failure_count,
            "return_code": 0 if status == "succeeded" else 1,
            "rollback_plan_path": rollback_plan_path,
            "rollback_result_path": str(evidence / "rollback_result.json") if status != "succeeded" else None,
            "mapping_records": records,
            "supported_scope": ["classic_single_frame_mr", "siemens_single_frame_mosaic_mr"],
        },
    )
    atomic_write_json(provenance_path, provenance.model_dump(), schema_version=1)
    atomic_write_json(
        audit_final_path,
        {
            "project_id": project_id,
            "conversion_run_id": conversion_run_id,
            "audit_state": "execution_succeeded" if status == "succeeded" else "execution_failed",
            "backend": "medimage-native",
            "started_at": started_at,
            "finished_at": finished_at,
            "output_manifest_path": str(manifest_path),
            "execution_provenance_path": str(provenance_path),
            "checksum_unchanged": checksum_unchanged,
            "mapping_success_count": success_count,
            "mapping_failure_count": failure_count,
            "return_code": 0 if status == "succeeded" else 1,
            "rollback_plan_path": rollback_plan_path,
            "rollback_result_path": str(evidence / "rollback_result.json") if status != "succeeded" else None,
            "warnings": warnings,
            "errors": errors,
            "no_external_process": True,
        },
        schema_version=1,
    )

    return DicomConversionSandboxResult(
        ok=status == "succeeded",
        status=status,
        mode="native",
        project_id=project_id,
        output_root=str(approved_output_root),
        mapping_count=len(mappings),
        command_template_count=len(templates),
        created_artifact_count=len(items),
        manifest_path=str(manifest_path),
        provenance_path=str(provenance_path),
        warnings=warnings,
        errors=errors,
        safety_flags=DicomConversionSafetyFlags(
            conversion_disabled_by_default=False,
            env_flags_missing=False,
            command_template_only=False,
        ),
    )


__all__ = ["execute_native_persisted_conversion"]
