"""Ticket-bound handoff from reviewed native DICOM conversion to preprocessing."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from src.backend.app.api.dependencies import ProjectStore
from src.backend.app.services.dicom_conversion_execution import (
    run_internal_user_dicom_conversion_from_persisted_package,
)
from src.backend.app.services.dicom_conversion_result_registration import (
    register_conversion_result,
)

if TYPE_CHECKING:
    from src.backend.app.runtime.tool_execution_context import ToolExecutionContext


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _within_any(path: Path, roots: tuple[Path, ...]) -> bool:
    resolved = path.expanduser().resolve()
    for root in roots:
        try:
            resolved.relative_to(root.expanduser().resolve())
            return True
        except ValueError:
            continue
    return False


def _registered_for_run(
    metadata: dict[str, Any],
    conversion_run_id: str,
    execution_context: ToolExecutionContext,
) -> bool:
    registry_path = Path(str(metadata.get("preprocessing_input_registry_path") or ""))
    registered_run = str(metadata.get("preprocessing_conversion_run_id") or "")
    if registered_run != conversion_run_id or not registry_path.is_file():
        return False
    if not _within_any(registry_path, execution_context.output_roots):
        return False
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if str(registry.get("conversion_run_id") or "") != conversion_run_id:
        return False
    project_root = Path(str(metadata.get("project_dir") or registry_path.parent)).resolve()
    artifacts = registry.get("artifacts")
    if not isinstance(artifacts, list) or not artifacts:
        return False
    for item in artifacts:
        if not isinstance(item, dict) or not item.get("path"):
            return False
        path = Path(str(item["path"]))
        if not path.is_absolute():
            path = project_root / path
        if not path.is_file():
            return False
        if not _within_any(
            path,
            (*execution_context.input_roots, *execution_context.output_roots),
        ):
            return False
        if _within_any(path, execution_context.readonly_roots):
            return False
    return True


def _verified_completed_result(
    project_dir: str,
    conversion_run_id: str,
    execution_context: ToolExecutionContext,
) -> dict[str, Any] | None:
    """Return verified persisted execution evidence suitable for crash recovery."""

    run_dir = Path(project_dir).resolve() / "conversion_runs" / conversion_run_id
    audit_path = run_dir / "audit_execution_final.json"
    manifest_path = run_dir / "output_manifest.json"
    provenance_path = run_dir / "execution_provenance.json"
    comparison_path = run_dir / "rawdata_checksum_comparison.json"
    required = (audit_path, manifest_path, provenance_path, comparison_path)
    if not all(path.is_file() for path in required):
        return None
    try:
        audit = json.loads(audit_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        comparison = json.loads(comparison_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if audit.get("audit_state") != "execution_succeeded":
        return None
    if comparison.get("unchanged") is not True:
        return None
    items = manifest.get("items")
    if not isinstance(items, list) or not items or manifest.get("error_count", 0):
        return None
    output_root_text = str(manifest.get("output_root") or "")
    if not output_root_text:
        return None
    output_root = Path(output_root_text)
    if not _within_any(output_root, execution_context.output_roots):
        return None
    if _within_any(output_root, execution_context.readonly_roots):
        return None
    for item in items:
        if not isinstance(item, dict) or item.get("verified") is not True:
            return None
        path = Path(str(item.get("path") or ""))
        checksum = str(item.get("checksum_sha256") or "")
        if not path.is_file() or not checksum or _sha256(path) != checksum:
            return None
        if not _within_any(path, execution_context.output_roots):
            return None
        if _within_any(path, execution_context.readonly_roots):
            return None
    return {
        "output_root": str(output_root),
        "manifest_path": str(manifest_path),
        "provenance_path": str(provenance_path),
        "mapping_count": int(audit.get("mapping_success_count") or 0),
        "created_artifact_count": len(items),
    }


def _register(
    store: ProjectStore,
    project_id: str,
    conversion_run_id: str,
    *,
    output_root: str,
    status: str,
    mapping_count: int,
    manifest_path: str | None,
    provenance_path: str | None,
    checksum_verified: bool,
) -> dict[str, Any]:
    return register_conversion_result(
        store,
        project_id,
        conversion_run_id=conversion_run_id,
        output_root=output_root,
        execution_status=status,
        mapping_count=mapping_count,
        manifest_path=manifest_path,
        provenance_path=provenance_path,
        checksum_verified=checksum_verified,
    )


def ensure_reviewed_native_conversion_handoff(
    store: ProjectStore,
    *,
    project_id: str,
    conversion_run_id: str,
    project_dir: str,
    rawdata_dir: str,
    execution_context: ToolExecutionContext,
) -> dict[str, Any]:
    """Execute once, or recover and register, a reviewed native conversion."""

    if execution_context.project_id != project_id:
        return {
            "ok": False,
            "status": "blocked",
            "blocking_issues": ["Conversion project does not match the execution ticket."],
        }
    project = store.get_project(project_id)
    if project is None:
        return {
            "ok": False,
            "status": "blocked",
            "blocking_issues": [f"Project not found: {project_id}"],
        }
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    if _registered_for_run(metadata, conversion_run_id, execution_context):
        return {
            "ok": True,
            "status": "already_registered",
            "conversion_run_id": conversion_run_id,
            "registry_path": metadata.get("preprocessing_input_registry_path"),
            "recovered": False,
        }

    completed = _verified_completed_result(
        project_dir,
        conversion_run_id,
        execution_context,
    )
    if completed is not None:
        registration = _register(
            store,
            project_id,
            conversion_run_id,
            output_root=completed["output_root"],
            status="succeeded",
            mapping_count=completed["mapping_count"],
            manifest_path=completed["manifest_path"],
            provenance_path=completed["provenance_path"],
            checksum_verified=True,
        )
        return {
            "ok": bool(registration.get("ok")),
            "status": "recovered_registration" if registration.get("ok") else "blocked",
            "conversion_run_id": conversion_run_id,
            "recovered": True,
            "registration": registration,
        }

    conversion = run_internal_user_dicom_conversion_from_persisted_package(
        project_id,
        conversion_run_id,
        project_dir=project_dir,
        rawdata_dir=rawdata_dir,
        input_roots=tuple(str(path) for path in execution_context.input_roots),
        output_roots=tuple(str(path) for path in execution_context.output_roots),
        readonly_roots=tuple(str(path) for path in execution_context.readonly_roots),
    )
    conversion_payload = conversion.model_dump(mode="json")
    if conversion.status not in {"succeeded", "partial"}:
        return {
            "ok": False,
            "status": conversion.status,
            "conversion_run_id": conversion_run_id,
            "conversion": conversion_payload,
            "blocking_issues": conversion.blocking_issues,
            "errors": conversion.errors,
        }
    registration = _register(
        store,
        project_id,
        conversion_run_id,
        output_root=str(conversion.output_root or ""),
        status=conversion.status,
        mapping_count=conversion.mapping_count,
        manifest_path=conversion.manifest_path,
        provenance_path=conversion.provenance_path,
        checksum_verified=True,
    )
    return {
        "ok": bool(conversion.ok and registration.get("ok")),
        "status": "registered" if conversion.ok and registration.get("ok") else "partial",
        "conversion_run_id": conversion_run_id,
        "recovered": False,
        "conversion": conversion_payload,
        "registration": registration,
    }


__all__ = ["ensure_reviewed_native_conversion_handoff"]
