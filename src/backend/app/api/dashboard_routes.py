from __future__ import annotations

import asyncio
import hashlib
import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect

from src.backend.app.core.config import get_backend_settings
from src.backend.app.schemas.desktop import (
    AssistantChatRequest,
    AssistantChatResponse,
    BidsValidationResponse,
    ConversionDryRunRequest,
    ConversionDryRunResponse,
    DataReadinessResponse,
    BoldReferenceReadinessResponse,
    MotionMetricsDraftResponse,
    MotionQcReadinessResponse,
    RsfmriQcPlanningReportResponse,
    SpmRealignDryRunResponse,
    SpmRealignWrapperSkeletonResponse,
    NiftiQcSnapshotResponse,
    NiftiThumbnailResponse,
    QcDashboardReportResponse,
    QcDashboardFingerprintResponse,
    DatasetDiagnosticsPackageResponse,
    DatasetDiagnosticsPackageStatusResponse,
    DatasetDiagnosticsPackageVerifyResponse,
    DatasetImportHistoryResponse,
    DatasetImportRecord,
    DatasetImportRequest,
    DatasetImportResponse,
    DatasetSummary,
    DicomPreflightResponse,
    HealthResponse,
    ImagePlane,
    ImagePreviewResponse,
    ImageSourcesResponse,
    ImageValidationReport,
    ModelStatus,
    TaskApprovalRequest,
    TaskApprovalResponse,
    TaskAuditPackageResponse,
    TaskArtifactsResponse,
    TaskDiagnosticsResponse,
    PipelineRunRequest,
    PipelineRunResponse,
    ProjectDetail,
    ProjectSummary,
    StudyOverview,
    TaskDetail,
    TaskEvent,
    TaskLogEntry,
)
from src.backend.app.services.bids_validation import validate_bids
from src.backend.app.services.conversion_planner import plan_conversion
from src.backend.app.services.bold_reference_readiness import build_bold_reference_readiness
from src.backend.app.services.motion_metrics_draft import build_motion_metrics_draft
from src.backend.app.services.spm_realign_dry_run import build_spm_realign_dry_run
from src.backend.app.services.spm_realign_wrapper_skeleton import build_spm_realign_wrapper_skeleton
from src.backend.app.services.motion_qc_readiness import build_motion_qc_readiness
from src.backend.app.services.nifti_qc_snapshot import build_nifti_qc_snapshot
from src.backend.app.services.nifti_thumbnail import build_nifti_thumbnail
from src.backend.app.services.qc_dashboard_report import (
    build_qc_dashboard_report,
    load_latest_qc_dashboard_report,
)
from src.backend.app.services.rawdata_fingerprint import build_rawdata_fingerprint
from src.backend.app.services.qc_dashboard_fingerprint import collect_qc_dashboard_fingerprint_roots
from src.backend.app.services.rsfmri_qc_planning_report import build_rsfmri_qc_planning_report
from src.backend.app.services.data_readiness import build_data_readiness
from src.backend.app.services.dicom_preflight import build_dicom_preflight
from src.backend.app.services.image_preview import build_image_preview, build_image_validation_report, list_image_sources
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.pipeline_runner import run_pipeline_task
from src.backend.app.services.task_manager import task_manager

router = APIRouter()


def _safe_artifact_part(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)[:80] or "project"


def _zip_if_exists(archive: zipfile.ZipFile, source_path: str | None, arcname: str) -> None:
    if not source_path:
        return
    path = Path(source_path)
    if path.is_file():
        archive.write(path, arcname=arcname)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _parse_checksum_file(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    checksums: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, name = line.partition("  ")
        if digest and name:
            checksums[name] = digest
    return checksums


def _diagnostics_package_safety_flags() -> dict[str, bool]:
    return {
        "read_only_validation": True,
        "rawdata_not_bundled": True,
        "diagnostics_only": True,
        "no_matlab_execution": True,
    }


def _build_import_file_inventory(imports: list[DatasetImportRecord]) -> dict[str, Any]:
    roots: list[dict[str, Any]] = []
    total_files = 0
    extension_counts: dict[str, int] = {}
    for item in imports:
        root = Path(item.path)
        root_extensions: dict[str, int] = {}
        root_file_count = 0
        if root.exists():
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                root_file_count += 1
                ext = path.suffix.lower() or "<none>"
                root_extensions[ext] = root_extensions.get(ext, 0) + 1
                extension_counts[ext] = extension_counts.get(ext, 0) + 1
        total_files += root_file_count
        roots.append(
            {
                "dataset_id": item.dataset_id,
                "path": item.path,
                "dataset_type": item.dataset_type,
                "exists": root.exists(),
                "file_count": root_file_count,
                "extension_counts": dict(sorted(root_extensions.items())),
            }
        )
    return {
        "total_files": total_files,
        "extension_counts": dict(sorted(extension_counts.items())),
        "roots": roots,
    }


@router.get("/api/health", response_model=HealthResponse)
def api_health() -> HealthResponse:
    settings = get_backend_settings()
    return HealthResponse(
        status="ok",
        service=settings.service_name,
        version=settings.api_version,
    )


@router.get("/api/projects", response_model=list[ProjectSummary])
def list_projects() -> list[ProjectSummary]:
    return mock_store.list_projects()


@router.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: str) -> ProjectDetail:
    project = mock_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project


@router.get("/api/studies/{study_id}/overview", response_model=StudyOverview)
def get_study_overview(study_id: str) -> StudyOverview:
    overview = mock_store.get_study_overview(study_id)
    if not overview:
        raise HTTPException(status_code=404, detail=f"Study not found: {study_id}")
    return overview


@router.get("/api/datasets/summary", response_model=DatasetSummary)
def get_dataset_summary(project_id: str = Query(...)) -> DatasetSummary:
    summary = mock_store.get_dataset_summary(project_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return summary


@router.get("/api/datasets/imports", response_model=DatasetImportHistoryResponse)
def get_dataset_imports(project_id: str = Query(...)) -> DatasetImportHistoryResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    records = [DatasetImportRecord(**item) for item in mock_store.list_import_records(project_id)]
    return DatasetImportHistoryResponse(ok=True, project_id=project_id, imports=records)


@router.get("/api/datasets/dicom/preflight", response_model=DicomPreflightResponse)
def get_dicom_preflight(
    project_id: str = Query(...),
    path: str | None = Query(default=None),
    max_files: int = Query(default=2000, ge=1, le=10000),
) -> DicomPreflightResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    roots = [path] if path else list(mock_store.list_import_paths(project_id))
    demo_data = Path("data/DemoData")
    if not path and demo_data.exists() and str(demo_data) not in roots:
        roots.append(str(demo_data))
    return build_dicom_preflight(project_id=project_id, roots=roots, max_files=max_files)


@router.post("/api/datasets/diagnostics/package", response_model=DatasetDiagnosticsPackageResponse)
def create_dataset_diagnostics_package(project_id: str = Query(...)) -> DatasetDiagnosticsPackageResponse:
    project = mock_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    imports = [DatasetImportRecord(**item) for item in mock_store.list_import_records(project_id)]
    file_inventory = _build_import_file_inventory(imports)
    search_roots = mock_store.list_import_paths(project_id)
    sources = list_image_sources(project_id=project_id, search_roots=search_roots)
    validation = build_image_validation_report(
        project_id=project_id,
        expected_sequences=project.sequences,
        search_roots=search_roots,
    )
    dicom_roots = [item.path for item in imports if item.dataset_type == "dicom"]
    dicom_preflight = build_dicom_preflight(project_id=project_id, roots=dicom_roots) if dicom_roots else None
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    package_dir = Path("outputs/reports/import_diagnostics") / _safe_artifact_part(project_id)
    package_dir.mkdir(parents=True, exist_ok=True)
    json_path = package_dir / "import_diagnostics_package.json"
    report_path = package_dir / "import_diagnostics_package.md"
    zip_path = package_dir / "import_diagnostics_package.zip"
    checksum_path = package_dir / "CHECKSUMS.sha256"
    checksum_path = package_dir / "CHECKSUMS.sha256"
    checksum_path = package_dir / "CHECKSUMS.sha256"
    payload = {
        "ok": validation.ok,
        "project_id": project_id,
        "generated_at": generated_at,
        "package_dir": str(package_dir),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "zip_path": str(zip_path),
        "checksum_path": str(checksum_path),
        "safety_flags": _diagnostics_package_safety_flags(),
        "project": project.model_dump(),
        "imports": [item.model_dump() for item in imports],
        "file_inventory": file_inventory,
        "image_sources": sources.model_dump(),
        "validation": validation.model_dump(),
        "dicom_preflight": dicom_preflight.model_dump() if dicom_preflight else None,
        "artifacts": {
            "manifest_path": sources.manifest_path,
            "validation_report_path": validation.report_path,
            "validation_json_path": validation.json_path,
            "dicom_preflight_report_path": dicom_preflight.report_path if dicom_preflight else None,
            "dicom_preflight_json_path": dicom_preflight.json_path if dicom_preflight else None,
            "zip_path": str(zip_path),
            "checksum_path": str(checksum_path),
        },
    }
    report_text = _render_import_diagnostics_markdown(payload)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_text, encoding="utf-8")
    package_files: list[tuple[Path, str]] = [
        (report_path, "import_diagnostics_package.md"),
        (json_path, "import_diagnostics_package.json"),
    ]
    for source_path, arcname in [
        (sources.manifest_path, "artifacts/image_source_manifest.json"),
        (validation.report_path, "artifacts/image_validation_report.md"),
        (validation.json_path, "artifacts/image_validation_report.json"),
        (dicom_preflight.report_path if dicom_preflight else None, "artifacts/dicom_preflight_report.md"),
        (dicom_preflight.json_path if dicom_preflight else None, "artifacts/dicom_preflight_result.json"),
    ]:
        if source_path and Path(source_path).is_file():
            package_files.append((Path(source_path), arcname))
    checksums = {arcname: _sha256_file(path) for path, arcname in package_files}
    checksum_path.write_text(
        "".join(f"{digest}  {arcname}\n" for arcname, digest in sorted(checksums.items())),
        encoding="utf-8",
    )
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path, arcname in package_files:
            archive.write(path, arcname=arcname)
        archive.write(checksum_path, arcname="CHECKSUMS.sha256")
    return DatasetDiagnosticsPackageResponse(
        ok=validation.ok,
        project_id=project_id,
        generated_at=generated_at,
        package_dir=str(package_dir),
        report_path=str(report_path),
        json_path=str(json_path),
        zip_path=str(zip_path),
        checksum_path=str(checksum_path),
        report_text=report_text,
        checksums=checksums,
        safety_flags=_diagnostics_package_safety_flags(),
        file_inventory=file_inventory,
        manifest_path=sources.manifest_path,
        validation_report_path=validation.report_path,
        import_count=len(imports),
        image_source_count=len(sources.manifest),
        validation_issue_count=len(validation.issues),
        dicom_preflight_report_path=dicom_preflight.report_path if dicom_preflight else None,
        dicom_preflight_json_path=dicom_preflight.json_path if dicom_preflight else None,
        dicom_file_count=dicom_preflight.dicom_file_count if dicom_preflight else 0,
        dicom_series_count=dicom_preflight.series_count if dicom_preflight else 0,
    )


@router.get("/api/datasets/diagnostics/package/latest", response_model=DatasetDiagnosticsPackageStatusResponse)
def get_latest_dataset_diagnostics_package(project_id: str = Query(...)) -> DatasetDiagnosticsPackageStatusResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    package_dir = Path("outputs/reports/import_diagnostics") / _safe_artifact_part(project_id)
    json_path = package_dir / "import_diagnostics_package.json"
    report_path = package_dir / "import_diagnostics_package.md"
    zip_path = package_dir / "import_diagnostics_package.zip"
    checksum_path = package_dir / "CHECKSUMS.sha256"
    if not json_path.is_file():
        return DatasetDiagnosticsPackageStatusResponse(
            ok=False,
            project_id=project_id,
            errors=["No import diagnostics package has been generated yet."],
            next_actions=["Generate a handoff package from Advanced Mode -> Import Diagnostics."],
        )
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return DatasetDiagnosticsPackageStatusResponse(
            ok=False,
            project_id=project_id,
            errors=[f"Failed to parse import diagnostics package: {exc}"],
            next_actions=["Regenerate the import diagnostics handoff package."],
        )
    validation = payload.get("validation", {}) if isinstance(payload.get("validation"), dict) else {}
    image_sources = payload.get("image_sources", {}) if isinstance(payload.get("image_sources"), dict) else {}
    dicom_preflight = payload.get("dicom_preflight", {}) if isinstance(payload.get("dicom_preflight"), dict) else {}
    imports = payload.get("imports", []) if isinstance(payload.get("imports"), list) else []
    file_inventory = payload.get("file_inventory") if isinstance(payload.get("file_inventory"), dict) else {}
    latest = DatasetDiagnosticsPackageResponse(
        ok=bool(payload.get("ok", False)),
        project_id=project_id,
        generated_at=str(payload.get("generated_at", "")),
        package_dir=str(payload.get("package_dir") or package_dir),
        report_path=str(payload.get("report_path") or report_path),
        json_path=str(payload.get("json_path") or json_path),
        zip_path=str(payload.get("zip_path") or zip_path),
        checksum_path=str(payload.get("checksum_path") or checksum_path),
        report_text=report_path.read_text(encoding="utf-8") if report_path.is_file() else "",
        checksums=_parse_checksum_file(checksum_path),
        safety_flags=payload.get("safety_flags") if isinstance(payload.get("safety_flags"), dict) else _diagnostics_package_safety_flags(),
        file_inventory=file_inventory,
        manifest_path=(payload.get("artifacts") or {}).get("manifest_path") if isinstance(payload.get("artifacts"), dict) else None,
        validation_report_path=(payload.get("artifacts") or {}).get("validation_report_path") if isinstance(payload.get("artifacts"), dict) else None,
        import_count=len(imports),
        image_source_count=len(image_sources.get("manifest", [])),
        validation_issue_count=len(validation.get("issues", [])),
        dicom_preflight_report_path=(payload.get("artifacts") or {}).get("dicom_preflight_report_path") if isinstance(payload.get("artifacts"), dict) else None,
        dicom_preflight_json_path=(payload.get("artifacts") or {}).get("dicom_preflight_json_path") if isinstance(payload.get("artifacts"), dict) else None,
        dicom_file_count=int(dicom_preflight.get("dicom_file_count") or 0),
        dicom_series_count=int(dicom_preflight.get("series_count") or 0),
    )
    return DatasetDiagnosticsPackageStatusResponse(ok=True, project_id=project_id, latest=latest)


@router.post("/api/datasets/diagnostics/package/verify", response_model=DatasetDiagnosticsPackageVerifyResponse)
def verify_dataset_diagnostics_package(project_id: str = Query(...)) -> DatasetDiagnosticsPackageVerifyResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    checked_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    package_dir = Path("outputs/reports/import_diagnostics") / _safe_artifact_part(project_id)
    zip_path = package_dir / "import_diagnostics_package.zip"
    checksum_path = package_dir / "CHECKSUMS.sha256"
    errors: list[str] = []
    failed_files: list[str] = []
    missing_files: list[str] = []

    checksums = _parse_checksum_file(checksum_path)
    if not zip_path.is_file():
        errors.append(f"Missing handoff ZIP: {zip_path}")
    if not checksums:
        errors.append(f"Missing or empty checksum manifest: {checksum_path}")
    if errors:
        return DatasetDiagnosticsPackageVerifyResponse(
            ok=False,
            project_id=project_id,
            checked_at=checked_at,
            zip_path=str(zip_path),
            checksum_path=str(checksum_path),
            errors=errors,
        )

    try:
        with zipfile.ZipFile(zip_path) as archive:
            names = set(archive.namelist())
            for arcname, expected_digest in sorted(checksums.items()):
                if arcname not in names:
                    missing_files.append(arcname)
                    continue
                actual_digest = _sha256_bytes(archive.read(arcname))
                if actual_digest != expected_digest:
                    failed_files.append(arcname)
    except Exception as exc:
        errors.append(f"Failed to verify handoff ZIP: {exc}")

    passed_files = max(0, len(checksums) - len(failed_files) - len(missing_files))
    ok = not errors and not failed_files and not missing_files
    return DatasetDiagnosticsPackageVerifyResponse(
        ok=ok,
        project_id=project_id,
        checked_at=checked_at,
        zip_path=str(zip_path),
        checksum_path=str(checksum_path),
        checked_files=len(checksums),
        passed_files=passed_files,
        failed_files=failed_files,
        missing_files=missing_files,
        errors=errors,
    )


@router.post("/api/datasets/import", response_model=DatasetImportResponse)
def import_dataset(request: DatasetImportRequest) -> DatasetImportResponse:
    if not request.path.strip():
        raise HTTPException(status_code=400, detail="Dataset path is required")
    try:
        response = mock_store.import_dataset(request)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")
    sources = list_image_sources(project_id=request.project_id, search_roots=mock_store.list_import_paths(request.project_id))
    project = mock_store.get_project(request.project_id)
    validation = build_image_validation_report(
        project_id=request.project_id,
        expected_sequences=project.sequences if project else [],
        search_roots=mock_store.list_import_paths(request.project_id),
    )
    warnings = list(sources.warnings)
    if not Path(request.path).exists():
        warnings.append(f"Imported path does not exist yet: {request.path}")
    warnings.extend(issue.message for issue in validation.issues if issue.severity == "warning")
    return response.model_copy(
        update={
            "manifest_path": sources.manifest_path,
            "image_source_count": len(sources.manifest),
            "validation_report_path": validation.report_path,
            "validation_report_text": validation.report_text,
            "validation_issue_count": len(validation.issues),
            "warnings": warnings,
        }
    )


@router.get("/api/models/status", response_model=ModelStatus)
def get_model_status(project_id: str = Query(...)) -> ModelStatus:
    status = mock_store.get_model_status(project_id)
    if not status:
        raise HTTPException(status_code=404, detail=f"Model status not found for project: {project_id}")
    return status


@router.get("/api/tasks", response_model=list[TaskLogEntry])
def list_tasks() -> list[TaskLogEntry]:
    return mock_store.list_tasks()


@router.get("/api/tasks/{task_id}", response_model=TaskDetail)
def get_task(task_id: str) -> TaskDetail:
    task = mock_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task


@router.get("/api/tasks/{task_id}/events", response_model=list[TaskEvent])
def get_task_events(task_id: str) -> list[TaskEvent]:
    if not mock_store.get_task(task_id):
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return task_manager.list_events(task_id)


@router.post("/api/tasks/{task_id}/approve", response_model=TaskApprovalResponse)
async def approve_task(task_id: str, request: TaskApprovalRequest) -> TaskApprovalResponse:
    task = mock_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    if task.execution_mode != "external_smoke":
        raise HTTPException(status_code=400, detail="Only external_smoke tasks can receive run-level approval")
    if not request.approved:
        raise HTTPException(status_code=403, detail="approved=true is required before launching approved smoke")
    if not request.approved_by.strip():
        raise HTTPException(status_code=400, detail="approved_by is required")

    approval = mock_store.add_approval(
        task_id,
        approved=True,
        approved_by=request.approved_by.strip(),
        approval_scope=request.approval_scope,
        safety_flags=request.safety_flags,
    )
    await task_manager.update_task(
        task_id,
        status="running",
        progress=max(task.progress, 5),
        message=f"Approved external smoke run queued by {approval.approved_by}",
        source="approval_gate",
        metadata={"approval_id": approval.approval_id, "approval_scope": approval.approval_scope},
    )
    approved_request = PipelineRunRequest(
        project_id=task.project_id,
        pipeline_id=task.pipeline_id,
        model_id=task.model_id,
        input_sequences=task.input_sequences,
        output_type=task.output_type,
        execution_mode="external_smoke",
        external_smoke_mode="approved_smoke",
        approved=True,
        approved_by=approval.approved_by,
    )
    asyncio.create_task(run_pipeline_task(task_id, approved_request, task_manager))
    return TaskApprovalResponse(ok=True, approval=approval, message="Approved smoke run queued")


@router.get("/api/tasks/{task_id}/diagnostics", response_model=TaskDiagnosticsResponse)
def get_task_diagnostics(task_id: str) -> TaskDiagnosticsResponse:
    task = mock_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    return _build_task_diagnostics(task)


@router.get("/api/tasks/{task_id}/artifacts", response_model=TaskArtifactsResponse)
def get_task_artifacts(task_id: str) -> TaskArtifactsResponse:
    task = mock_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    payload = _load_artifact_payload(task)
    return TaskArtifactsResponse(
        ok=True,
        task_id=task_id,
        result_path=task.result_path,
        artifacts=dict(payload.get("artifacts", {})),
        approval=mock_store.get_latest_approval(task_id),
        errors=list(payload.get("errors", [])),
    )


@router.post("/api/tasks/{task_id}/audit-package", response_model=TaskAuditPackageResponse)
def generate_task_audit_package(task_id: str) -> TaskAuditPackageResponse:
    task = mock_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")
    diagnostics = _build_task_diagnostics(task)
    artifact_response = TaskArtifactsResponse(
        ok=True,
        task_id=task_id,
        result_path=task.result_path,
        artifacts=dict(_load_artifact_payload(task).get("artifacts", {})),
        approval=mock_store.get_latest_approval(task_id),
        errors=diagnostics.errors,
    )
    return _write_task_audit_package(task, diagnostics, artifact_response)


@router.post("/api/pipelines/run", response_model=PipelineRunResponse)
async def run_pipeline(request: PipelineRunRequest) -> PipelineRunResponse:
    if not request.input_sequences:
        raise HTTPException(status_code=400, detail="input_sequences must not be empty")
    if request.execution_mode == "external_smoke" and request.external_smoke_mode == "approved_smoke":
        if not request.approved:
            raise HTTPException(status_code=403, detail="approved=true is required for approved_smoke")
        if not (request.approved_by or "").strip():
            raise HTTPException(status_code=400, detail="approved_by is required for approved_smoke")
    try:
        task = task_manager.create_pipeline_task(request)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")
    if request.execution_mode == "external_smoke" and request.external_smoke_mode == "approved_smoke":
        approval = mock_store.add_approval(
            task.id,
            approved=True,
            approved_by=(request.approved_by or "").strip(),
            safety_flags={
                "rawdata_read_only": True,
                "no_dparsf_blackbox": True,
                "matlab_external_execution": True,
            },
        )
        mock_store.append_task_event(
            task.id,
            status=task.status,
            progress=task.progress,
            message=f"Run-level approval recorded by {approval.approved_by}",
            source="approval_gate",
            metadata={"approval_id": approval.approval_id},
        )
    asyncio.create_task(run_pipeline_task(task.id, request, task_manager))
    return PipelineRunResponse(task_id=task.id, status=task.status)


@router.websocket("/ws/tasks/{task_id}")
async def task_stream(websocket: WebSocket, task_id: str) -> None:
    await websocket.accept()
    if not mock_store.get_task(task_id):
        await websocket.send_json(
            {
                "task_id": task_id,
                "status": "failed",
                "progress": 0,
                "message": f"Task not found: {task_id}",
                "timestamp": "",
            }
        )
        await websocket.close(code=1008)
        return

    queue = await task_manager.subscribe(task_id)
    try:
        while True:
            message = await queue.get()
            await websocket.send_json(message.model_dump())
            if message.status in {"completed", "failed"}:
                await websocket.close()
                return
    except WebSocketDisconnect:
        return
    finally:
        task_manager.unsubscribe(task_id, queue)


@router.post("/api/assistant/chat", response_model=AssistantChatResponse)
def assistant_chat(request: AssistantChatRequest) -> AssistantChatResponse:
    project = mock_store.get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {request.project_id}")

    message = request.message.lower()
    dataset = mock_store.get_dataset_summary(request.project_id)
    if "pipeline" in message or "workflow" in message:
        reply = (
            f"Current pipeline is {project.current_pipeline_id}. Use approved runs for SPM/DPABI "
            "steps and keep rawdata read-only. The UI can start a simulated run now; real runners "
            "should plug into the same task event stream."
        )
    elif "failed" in message or "error" in message or "log" in message:
        reply = (
            "For failed tasks, open the latest task detail and inspect logs/result_path first. "
            "If it is an external SPM/DPABI smoke failure, verify the MATLAB stdout/stderr and "
            "expected result JSON path."
        )
    elif "dataset" in message or "data" in message:
        reply = (
            f"{project.name} currently has {dataset.subjects if dataset else project.subjects_count} subjects, "
            f"{dataset.scans if dataset else project.scans_count} scans, and health status "
            f"{dataset.health_status if dataset else 'Unknown'}."
        )
    else:
        reply = (
            "I can help review dataset readiness, explain pipeline settings, summarize task failures, "
            "or prepare the next auditable SPM/DPABI smoke run. TODO: connect this panel to a real LLM provider."
        )
    return AssistantChatResponse(reply=reply)


@router.get("/api/images/preview", response_model=ImagePreviewResponse)
def image_preview(
    project_id: str = Query(...),
    subject_id: str | None = Query(default=None),
    sequence: str = Query(default="T1"),
    slice_index: int | None = Query(default=None, ge=0),
    plane: ImagePlane = Query(default="axial"),
) -> ImagePreviewResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    search_roots = mock_store.list_import_paths(project_id)
    return build_image_preview(
        project_id=project_id,
        subject_id=subject_id,
        sequence=sequence,
        slice_index=slice_index,
        plane=plane,
        search_roots=search_roots,
    )


@router.get("/api/images/sources", response_model=ImageSourcesResponse)
def image_sources(project_id: str = Query(...)) -> ImageSourcesResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return list_image_sources(project_id=project_id, search_roots=mock_store.list_import_paths(project_id))


@router.get("/api/images/manifest", response_model=ImageSourcesResponse)
def image_manifest(project_id: str = Query(...)) -> ImageSourcesResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return list_image_sources(project_id=project_id, search_roots=mock_store.list_import_paths(project_id))


@router.get("/api/images/validation", response_model=ImageValidationReport)
def image_validation(project_id: str = Query(...)) -> ImageValidationReport:
    project = mock_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_image_validation_report(
        project_id=project_id,
        expected_sequences=project.sequences,
        search_roots=mock_store.list_import_paths(project_id),
    )


@router.post("/api/projects/{project_id}/qc-dashboard/report", response_model=QcDashboardReportResponse)
def post_qc_dashboard_report(
    project_id: str,
    cache: str = "off",
) -> QcDashboardReportResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    if cache not in ("off", "prefer", "refresh"):
        raise HTTPException(status_code=400, detail=f"Invalid cache mode: {cache}. Use off, prefer, or refresh.")
    return build_qc_dashboard_report(project_id, cache_mode=cache)


@router.get("/api/projects/{project_id}/qc-dashboard/report/latest", response_model=QcDashboardReportResponse)
def get_latest_qc_dashboard_report(project_id: str) -> QcDashboardReportResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    result = load_latest_qc_dashboard_report(project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="No QC dashboard report has been generated yet.")
    return result


@router.get("/api/projects/{project_id}/qc-dashboard/fingerprint", response_model=QcDashboardFingerprintResponse)
def get_qc_dashboard_fingerprint(project_id: str) -> QcDashboardFingerprintResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    project = mock_store.get_project(project_id)
    metadata = (project.metadata if isinstance(project.metadata, dict) else {}) if project else {}
    roots = collect_qc_dashboard_fingerprint_roots(metadata)
    fp = build_rawdata_fingerprint(roots)
    return QcDashboardFingerprintResponse(
        ok=fp.ok,
        project_id=project_id,
        fingerprint=fp,
        roots=fp.roots,
        warnings=fp.warnings,
        errors=fp.errors,
        safety_flags={
            "read_only": True, "rawdata_not_modified": True,
            "metadata_only": True, "no_cache_files_created": True,
            "no_preprocessing_executed": True, "no_external_tools_executed": True,
        },
    )


@router.get("/api/projects/{project_id}/data-readiness", response_model=DataReadinessResponse)
def get_project_data_readiness(project_id: str) -> DataReadinessResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_data_readiness(project_id)


@router.get("/api/projects/{project_id}/bids-validation", response_model=BidsValidationResponse)
def get_project_bids_validation(project_id: str) -> BidsValidationResponse:
    project = mock_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    roots: list[str] = []
    rawdata = metadata.get("rawdata_dir")
    if rawdata and isinstance(rawdata, str):
        roots.append(rawdata)
    try:
        import_roots = mock_store.list_import_paths(project_id)
        for r in import_roots:
            if r not in roots:
                roots.append(r)
    except Exception:
        pass
    result = validate_bids(roots)
    result.project_id = project_id
    return result


@router.get("/api/projects/{project_id}/bold-reference/readiness", response_model=BoldReferenceReadinessResponse)
def get_project_bold_reference_readiness(project_id: str) -> BoldReferenceReadinessResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_bold_reference_readiness(project_id)


@router.post("/api/projects/{project_id}/rsfmri-qc/planning-report", response_model=RsfmriQcPlanningReportResponse)
def post_rsfmri_qc_planning_report(project_id: str) -> RsfmriQcPlanningReportResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_rsfmri_qc_planning_report(project_id)


@router.post("/api/projects/{project_id}/motion-qc/metrics-draft", response_model=MotionMetricsDraftResponse)
def post_motion_metrics_draft(project_id: str) -> MotionMetricsDraftResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_motion_metrics_draft(project_id)


@router.post("/api/projects/{project_id}/spm-realign/dry-run", response_model=SpmRealignDryRunResponse)
def post_spm_realign_dry_run(project_id: str) -> SpmRealignDryRunResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_spm_realign_dry_run(project_id)


@router.post("/api/projects/{project_id}/spm-realign/wrapper-skeleton", response_model=SpmRealignWrapperSkeletonResponse)
def post_spm_realign_wrapper_skeleton(project_id: str) -> SpmRealignWrapperSkeletonResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_spm_realign_wrapper_skeleton(project_id)


@router.get("/api/projects/{project_id}/nifti-qc/snapshot", response_model=NiftiQcSnapshotResponse)
def get_project_nifti_qc_snapshot(project_id: str) -> NiftiQcSnapshotResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_nifti_qc_snapshot(project_id)


@router.get("/api/projects/{project_id}/nifti-qc/images/{image_id}/thumbnail", response_model=NiftiThumbnailResponse)
def get_project_nifti_thumbnail(
    project_id: str, image_id: str,
    view: str = "all", volume_index: int | None = None, size: int | None = None,
) -> NiftiThumbnailResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    if view not in ("axial", "coronal", "sagittal", "all"):
        raise HTTPException(status_code=400, detail=f"Invalid view: {view}")
    if volume_index is not None and volume_index < 0:
        raise HTTPException(status_code=400, detail=f"volume_index must be >= 0, got {volume_index}")
    try:
        return build_nifti_thumbnail(project_id, image_id, view, volume_index, size)
    except ValueError as exc:
        msg = str(exc)
        if "volume_index" in msg or "out of range" in msg:
            raise HTTPException(status_code=400, detail=msg) from exc
        raise


@router.get("/api/projects/{project_id}/motion-qc/readiness", response_model=MotionQcReadinessResponse)
def get_project_motion_qc_readiness(project_id: str) -> MotionQcReadinessResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return build_motion_qc_readiness(project_id)


@router.post("/api/projects/{project_id}/conversion/dry-run", response_model=ConversionDryRunResponse)
def post_conversion_dry_run(
    project_id: str,
    request: ConversionDryRunRequest = ConversionDryRunRequest(),
) -> ConversionDryRunResponse:
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return plan_conversion(project_id, request)


@router.post("/api/projects/{project_id}/conversion/preflight")
def post_conversion_preflight(
    project_id: str,
) -> dict[str, Any]:
    """Read-only DICOM conversion preflight — never executes conversion.

    Returns conversion readiness, dcm2niix availability, command templates,
    safety flags, and gating status.  Does NOT call dcm2niix, write NIfTI
    files, or modify rawdata.
    """
    if not mock_store.get_project(project_id):
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

    from src.backend.app.services.dicom_conversion_execution import (
        check_dcm2niix_availability,
        run_conversion_preflight,
    )

    preflight = run_conversion_preflight(project_id)

    # Check dcm2niix availability independently
    env_flags: dict[str, str] = {}
    import os
    for flag in [
        "MEDIMAGE_ENABLE_DICOM_CONVERSION",
        "MEDIMAGE_MATLAB_ENABLED",
        "MEDIMAGE_SPM_SMOKE_ENABLED",
        "MEDIMAGE_ENABLE_REVIEWED_EXECUTION",
        "MEDIMAGE_ENABLE_REAL_PREPROCESSING",
    ]:
        env_flags[flag] = os.environ.get(flag, "")

    availability = check_dcm2niix_availability(env=env_flags)

    return {
        "ok": preflight.ok,
        "project_id": project_id,
        "status": preflight.status,
        "conversion_disabled_by_default": preflight.conversion_disabled_by_default,
        "dcm2niix_available": availability.status == "available",
        "dcm2niix_status": availability.status,
        "dcm2niix_path": availability.executable_path,
        "dcm2niix_version": availability.version,
        "env_enabled": preflight.env_enabled,
        "missing_env_flags": preflight.missing_env_flags,
        "approval_required": preflight.approval_required,
        "audit_required": preflight.audit_required,
        "output_root_preview": preflight.output_root_preview,
        "output_dir_safe": preflight.output_dir_safe,
        "mapping_count": preflight.mapping_count,
        "mappings": [
            {
                "subject_id": m.subject_id,
                "modality": m.modality,
                "suffix": m.suffix,
                "task": m.task,
                "source_path": m.source_path,
                "suggested_relative_path": m.suggested_relative_path,
                "confidence": m.confidence,
            }
            for m in preflight.mappings
        ],
        "command_templates": [
            {
                "tool": t.tool,
                "executable": t.executable,
                "input_dir": t.input_dir,
                "output_dir": t.output_dir,
                "filename_pattern": t.filename_pattern,
                "compress": t.compress,
                "bids_sidecar": t.bids_sidecar,
                "create_bids": t.create_bids,
                "command_preview": t.command_preview,
            }
            for t in preflight.command_templates
        ],
        "warnings": preflight.warnings,
        "errors": preflight.errors,
        "blocking_issues": preflight.blocking_issues,
        "safety_flags": preflight.safety_flags.model_dump(),
    }


def _render_import_diagnostics_markdown(payload: dict[str, Any]) -> str:
    validation = payload.get("validation", {})
    dicom_preflight = payload.get("dicom_preflight", {})
    image_sources = payload.get("image_sources", {})
    artifacts = payload.get("artifacts", {})
    imports = payload.get("imports", [])
    issues = validation.get("issues", []) if isinstance(validation, dict) else []
    lines = [
        f"# Import Diagnostics Package: {payload.get('project_id')}",
        "",
        f"- Generated at: {payload.get('generated_at')}",
        f"- Validation status: {validation.get('status') if isinstance(validation, dict) else 'unknown'}",
        f"- Imports: {len(imports) if isinstance(imports, list) else 0}",
        f"- Files indexed: {payload.get('file_inventory', {}).get('total_files') if isinstance(payload.get('file_inventory'), dict) else 0}",
        f"- Image sources: {len(image_sources.get('manifest', [])) if isinstance(image_sources, dict) else 0}",
        f"- Validation issues: {len(issues) if isinstance(issues, list) else 0}",
        f"- DICOM files: {dicom_preflight.get('dicom_file_count') if isinstance(dicom_preflight, dict) else 0}",
        f"- DICOM series: {dicom_preflight.get('series_count') if isinstance(dicom_preflight, dict) else 0}",
        f"- Manifest: {artifacts.get('manifest_path') if isinstance(artifacts, dict) else 'Not generated'}",
        f"- Validation report: {artifacts.get('validation_report_path') if isinstance(artifacts, dict) else 'Not generated'}",
        f"- DICOM preflight: {artifacts.get('dicom_preflight_report_path') if isinstance(artifacts, dict) and artifacts.get('dicom_preflight_report_path') else 'Not generated'}",
        f"- Checksums: {artifacts.get('checksum_path') if isinstance(artifacts, dict) else 'Not generated'}",
        "",
        "## Safety Flags",
        "",
    ]
    safety_flags = payload.get("safety_flags", {})
    if isinstance(safety_flags, dict):
        for key, value in sorted(safety_flags.items()):
            lines.append(f"- {key}: {bool(value)}")
    lines += [
        "",
        "## Imported Roots",
        "",
    ]
    if isinstance(imports, list) and imports:
        for item in imports:
            if isinstance(item, dict):
                exists = "exists" if item.get("exists") else "missing"
                lines.append(f"- [{exists}] {item.get('dataset_id')} ({item.get('dataset_type')}): {item.get('path')}")
    else:
        lines.append("- No imported roots recorded.")
    lines += ["", "## File Inventory", ""]
    inventory = payload.get("file_inventory", {})
    if isinstance(inventory, dict):
        extension_counts = inventory.get("extension_counts", {})
        if isinstance(extension_counts, dict) and extension_counts:
            for ext, count in sorted(extension_counts.items()):
                lines.append(f"- {ext}: {count}")
        else:
            lines.append("- No files discovered under existing imported roots.")
    lines += ["", "## Validation Issues", ""]
    if isinstance(issues, list) and issues:
        for issue in issues:
            if isinstance(issue, dict):
                scope = " / ".join(str(item) for item in [issue.get("subject_id"), issue.get("sequence")] if item)
                scope_text = f" ({scope})" if scope else ""
                lines.append(f"- [{issue.get('severity')}] {issue.get('code')}{scope_text}: {issue.get('message')}")
    else:
        lines.append("- No validation issues detected.")
    lines += ["", "## DICOM Metadata Preflight", ""]
    if isinstance(dicom_preflight, dict) and dicom_preflight:
        safety_flags = dicom_preflight.get("safety_flags", {})
        lines.append(f"- Status: {'pass' if dicom_preflight.get('ok') else 'needs review'}")
        lines.append(f"- Files: {dicom_preflight.get('dicom_file_count', 0)}")
        lines.append(f"- Sampled: {dicom_preflight.get('sampled_file_count', 0)}")
        lines.append(f"- Series: {dicom_preflight.get('series_count', 0)}")
        lines.append(f"- Subjects: {', '.join(dicom_preflight.get('subjects', [])) if isinstance(dicom_preflight.get('subjects'), list) else 'Not detected'}")
        if isinstance(safety_flags, dict):
            for key, value in sorted(safety_flags.items()):
                lines.append(f"- {key}: {bool(value)}")
    else:
        lines.append("- No DICOM import roots were included in this package.")
    return "\n".join(lines) + "\n"


@router.get("/api/dashboard/state")
def dashboard_state(project_id: str = Query(default="brain-tumor-study")) -> dict[str, Any]:
    project = mock_store.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return {
        "project": project.model_dump(),
        "study_overview": mock_store.get_study_overview(project.study_id).model_dump(),
        "dataset_summary": mock_store.get_dataset_summary(project.id).model_dump(),
        "model_status": mock_store.get_model_status(project.id).model_dump(),
        "tasks": [task.model_dump() for task in mock_store.list_tasks()],
    }


def _build_task_diagnostics(task: TaskDetail) -> TaskDiagnosticsResponse:
    payload = _load_artifact_payload(task)
    events = task_manager.list_events(task.id)
    errors = list(payload.get("errors", []))
    warnings = list(payload.get("warnings", []))
    external_tool_results = list(payload.get("external_tool_results", []))
    diagnosis: list[dict[str, Any]] = []

    for error in errors:
        diagnosis.append(
            {
                "severity": "error",
                "code": _classify_external_error(str(error)),
                "message": str(error),
            }
        )
    for warning in warnings:
        diagnosis.append({"severity": "warning", "code": "warning", "message": str(warning)})
    for result in external_tool_results:
        if isinstance(result, dict) and result.get("returncode") not in {None, 0}:
            diagnosis.append(
                {
                    "severity": "error",
                    "code": "non_zero_returncode",
                    "message": f"External command returned {result.get('returncode')}",
                    "command": result.get("command"),
                }
            )
        if isinstance(result, dict) and result.get("outputs"):
            outputs = result.get("outputs")
            missing = []
            if isinstance(outputs, dict):
                missing = [key for key, value in outputs.items() if value in {None, "", False}]
            if missing:
                diagnosis.append(
                    {
                        "severity": "error",
                        "code": "missing_expected_outputs",
                        "message": f"Missing expected outputs: {', '.join(missing)}",
                    }
                )
    if task.execution_mode == "external_smoke" and not mock_store.get_latest_approval(task.id):
        diagnosis.append(
            {
                "severity": "info",
                "code": "approval_pending",
                "message": "Manual package is reviewable; approved smoke requires explicit run-level approval.",
            }
        )
    if not diagnosis and task.status == "completed":
        diagnosis.append({"severity": "info", "code": "no_critical_findings", "message": "No critical diagnostics were recorded."})

    logs = [event.message for event in events] or task.logs
    return TaskDiagnosticsResponse(
        ok=not any(item.get("severity") == "error" for item in diagnosis),
        task_id=task.id,
        status=task.status,
        diagnosis=diagnosis,
        external_tool_results=external_tool_results,
        logs=logs,
        artifacts=dict(payload.get("artifacts", {})),
        approval=mock_store.get_latest_approval(task.id),
        errors=errors,
        warnings=warnings,
    )


def _load_artifact_payload(task: TaskDetail) -> dict[str, Any]:
    payload = dict(mock_store.get_task_artifacts(task.id))
    result_path = task.result_path or str(payload.get("artifacts", {}).get("result_json", ""))
    if result_path:
        parsed = _read_json_if_exists(Path(result_path))
        if parsed:
            payload = {
                **payload,
                "artifacts": parsed.get("artifacts", payload.get("artifacts", {})),
                "external_tool_results": parsed.get("external_tool_results", payload.get("external_tool_results", [])),
                "checks": parsed.get("checks", payload.get("checks", [])),
                "errors": parsed.get("errors", payload.get("errors", [])),
                "warnings": parsed.get("warnings", payload.get("warnings", [])),
                "next_actions": parsed.get("next_actions", payload.get("next_actions", [])),
            }
    return payload


def _read_json_if_exists(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _classify_external_error(message: str) -> str:
    lower = message.lower()
    if "matlab" in lower and ("not found" in lower or "missing" in lower):
        return "missing_matlab"
    if "spm" in lower and ("not found" in lower or "missing" in lower):
        return "missing_spm_path"
    if "dpabi" in lower and ("not found" in lower or "missing" in lower):
        return "missing_dpabi_path"
    if "result json" in lower or "expected output" in lower:
        return "missing_expected_outputs"
    if "returncode" in lower or "non-zero" in lower:
        return "non_zero_returncode"
    return "external_smoke_error"


def _write_task_audit_package(
    task: TaskDetail,
    diagnostics: TaskDiagnosticsResponse,
    artifact_response: TaskArtifactsResponse,
) -> TaskAuditPackageResponse:
    generated_at = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    package_dir = Path("outputs/reports/task_audits") / _safe_path_part(task.id)
    package_dir.mkdir(parents=True, exist_ok=True)
    events = task_manager.list_events(task.id)
    payload = {
        "ok": diagnostics.ok and not artifact_response.errors,
        "task": task.model_dump(),
        "events": [event.model_dump() for event in events],
        "diagnostics": diagnostics.model_dump(),
        "artifacts": artifact_response.model_dump(),
        "generated_at": generated_at,
        "safety": {
            "rawdata_read_only": True,
            "no_dparsf_blackbox": True,
            "approval_required_for_approved_smoke": task.execution_mode == "external_smoke",
        },
    }
    report_text = _render_task_audit_markdown(task, diagnostics, artifact_response, generated_at, events)
    json_path = package_dir / "task_audit_package.json"
    report_path = package_dir / "task_audit_report.md"
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path.write_text(report_text, encoding="utf-8")
    existing_artifacts = dict(mock_store.get_task_artifacts(task.id))
    existing_artifacts["audit_package"] = {
        "package_dir": str(package_dir),
        "report_path": str(report_path),
        "json_path": str(json_path),
        "generated_at": generated_at,
    }
    mock_store.save_task_artifacts(task.id, existing_artifacts)
    return TaskAuditPackageResponse(
        ok=payload["ok"],
        task_id=task.id,
        generated_at=generated_at,
        package_dir=str(package_dir),
        report_path=str(report_path),
        json_path=str(json_path),
        report_text=report_text,
        artifacts=existing_artifacts,
        errors=diagnostics.errors + artifact_response.errors,
    )


def _render_task_audit_markdown(
    task: TaskDetail,
    diagnostics: TaskDiagnosticsResponse,
    artifacts: TaskArtifactsResponse,
    generated_at: str,
    events: list[TaskEvent],
) -> str:
    approval = diagnostics.approval
    lines = [
        f"# Task Audit Package: {task.id}",
        "",
        f"- Generated at: {generated_at}",
        f"- Run name: {task.run_name}",
        f"- Pipeline: {task.pipeline_id}",
        f"- Project: {task.project_id}",
        f"- Execution mode: {task.execution_mode}",
        f"- Status: {task.status}",
        f"- Progress: {task.progress}%",
        f"- Result path: {task.result_path or 'Pending'}",
        "",
        "## Approval",
        "",
    ]
    if approval:
        lines.extend(
            [
                f"- Approval ID: {approval.approval_id}",
                f"- Approved by: {approval.approved_by}",
                f"- Approved at: {approval.approved_at}",
                f"- Scope: {approval.approval_scope}",
                f"- Safety flags: `{json.dumps(approval.safety_flags, ensure_ascii=False)}`",
            ]
        )
    else:
        lines.append("- No run-level approval recorded.")

    lines.extend(["", "## Diagnostics", ""])
    if diagnostics.diagnosis:
        for item in diagnostics.diagnosis:
            lines.append(f"- [{item.get('severity', 'info')}] {item.get('code', 'diagnostic')}: {item.get('message', '')}")
    else:
        lines.append("- No diagnostics recorded.")

    lines.extend(["", "## External Tool Results", ""])
    if diagnostics.external_tool_results:
        for index, result in enumerate(diagnostics.external_tool_results, start=1):
            command = result.get("command", result.get("function", f"external-run-{index}"))
            lines.append(f"- {index}. command: `{command}`; returncode: `{result.get('returncode', 'n/a')}`")
    else:
        lines.append("- No external tool results recorded.")

    lines.extend(["", "## Artifacts", ""])
    if artifacts.artifacts:
        for key, value in artifacts.artifacts.items():
            lines.append(f"- {key}: `{value}`")
    else:
        lines.append("- No artifact paths recorded.")

    lines.extend(["", "## Event Timeline", ""])
    if events:
        for event in events:
            lines.append(f"- {event.timestamp} | {event.status} | {event.progress}% | {event.message}")
    else:
        lines.append("- No events recorded.")

    lines.extend(
        [
            "",
            "## Safety Boundaries",
            "",
            "- rawdata remains read-only.",
            "- DPARSF/DPARSFA black-box batch flows remain prohibited.",
            "- Approved external smoke requires explicit run-level approval.",
        ]
    )
    return "\n".join(lines) + "\n"


def _safe_path_part(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)[:120]
