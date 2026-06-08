"""DICOM conversion review package reader and audit export — Phase 4E-1.

Reads persisted conversion review metadata packages and exports metadata-only
audit bundles.  No dcm2niix is called.  No NIfTI files are created.
No rawdata is modified.  Export contains metadata only — no image data.

Reference:
  docs/DICOM_CONVERSION_APPROVAL_GATE_DESIGN.md  (Section 21.6)
"""

from __future__ import annotations

import hashlib
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════
# 1. Response models
# ═══════════════════════════════════════════════════════════════════════


class DicomConversionReviewPackageFile(BaseModel):
    """A single file in a conversion review package."""

    kind: str = "unknown"
    path: str = ""
    exists: bool = False
    size_bytes: int | None = None
    sha256: str | None = None
    preview_text: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class DicomConversionReviewPackageResponse(BaseModel):
    """Structured response for reading a conversion review package."""

    ok: bool = False
    project_id: str = ""
    conversion_run_id: str = ""
    run_dir: str | None = None
    files: list[DicomConversionReviewPackageFile] = Field(default_factory=list)
    approval_summary: dict[str, Any] = Field(default_factory=dict)
    mapping_count: int = 0
    command_template_count: int = 0
    manifest_path: str | None = None
    provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


class DicomConversionAuditExportResponse(BaseModel):
    """Response from exporting a conversion review package."""

    ok: bool = False
    project_id: str = ""
    conversion_run_id: str = ""
    export_path: str | None = None
    exists: bool = False
    size_bytes: int | None = None
    sha256: str | None = None
    included_files: list[str] = Field(default_factory=list)
    excluded_patterns: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════
# 2. Allowed / blocked export extensions
# ═══════════════════════════════════════════════════════════════════════

_ALLOWED_EXPORT_EXTS: frozenset[str] = frozenset({
    ".json", ".log", ".md", ".txt",
})

_BLOCKED_EXPORT_EXTS: frozenset[str] = frozenset({
    ".dcm", ".ima", ".nii", ".gz", ".img", ".hdr", ".m", ".mat",
})


def _safety_flags() -> dict[str, bool]:
    return {
        "metadata_only": True,
        "no_raw_dicom_included": True,
        "no_nifti_included": True,
        "no_conversion_executed": True,
        "rawdata_not_modified": True,
        "output_under_project": True,
        "clinical_use_prohibited": True,
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _file_info(path: str) -> tuple[bool, int | None, str | None]:
    p = Path(path)
    if not p.exists() or not p.is_file():
        return False, None, None
    try:
        size = p.stat().st_size
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        return True, size, sha
    except Exception:
        return False, None, None


def _preview_text(path: str, max_chars: int = 500) -> str | None:
    try:
        content = Path(path).read_text(encoding="utf-8", errors="replace")
        return content[:max_chars]
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════
# 3. Review package reader
# ═══════════════════════════════════════════════════════════════════════


def read_conversion_review_package(
    project_id: str,
    conversion_run_id: str,
    *,
    project_dir: str = "",
    rawdata_dir: str = "",
) -> DicomConversionReviewPackageResponse:
    """Read a persisted conversion review package from disk.

    Does NOT call dcm2niix.  Does NOT read image data.  Does NOT modify
    rawdata.  Validates all paths are under project_dir and not rawdata_dir.
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not project_dir:
        return DicomConversionReviewPackageResponse(
            ok=False,
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            errors=["project_dir is required."],
            safety_flags=_safety_flags(),
        )

    run_dir = Path(project_dir) / "conversion_runs" / conversion_run_id
    if not run_dir.exists():
        return DicomConversionReviewPackageResponse(
            ok=False,
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            run_dir=str(run_dir),
            errors=[f"Run directory not found: {run_dir}"],
            safety_flags=_safety_flags(),
        )

    # Path safety
    if rawdata_dir and str(run_dir).startswith(rawdata_dir):
        return DicomConversionReviewPackageResponse(
            ok=False,
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            run_dir=str(run_dir),
            errors=["Run directory is under rawdata_dir — refusing to read."],
            safety_flags=_safety_flags(),
        )

    if not str(run_dir).startswith(project_dir):
        return DicomConversionReviewPackageResponse(
            ok=False,
            project_id=project_id,
            conversion_run_id=conversion_run_id,
            run_dir=str(run_dir),
            errors=["Run directory is not under project_dir."],
            safety_flags=_safety_flags(),
        )

    # Read each expected file
    file_defs: list[tuple[str, str]] = [
        ("approval_record", "approval_record.json"),
        ("audit_preview", "audit_preview.json"),
        ("preflight_snapshot", "preflight_snapshot.json"),
        ("mapping_snapshot", "mapping_snapshot.json"),
        ("command_templates", "command_templates.json"),
        ("rawdata_checksum_before", "rawdata_checksum_before.json"),
        ("rollback_plan_dry_run", "rollback_plan_dry_run.json"),
        ("planned_manifest", "planned_output_manifest.json"),
        ("planned_provenance", "planned_execution_provenance.json"),
        ("stdout_log", "logs/stdout.log"),
        ("stderr_log", "logs/stderr.log"),
        ("readme", "README.md"),
    ]

    files: list[DicomConversionReviewPackageFile] = []
    approval_summary: dict[str, Any] = {}
    mapping_count = 0
    template_count = 0

    for kind, rel_path in file_defs:
        full_path = run_dir / rel_path
        exists, size, sha = _file_info(str(full_path))
        preview = _preview_text(str(full_path)) if exists else None
        file_warnings: list[str] = []
        if not exists:
            file_warnings.append("File not found in review package.")

        files.append(DicomConversionReviewPackageFile(
            kind=kind,
            path=str(full_path),
            exists=exists,
            size_bytes=size,
            sha256=sha,
            preview_text=preview,
            warnings=file_warnings,
        ))

        # Extract summary data
        if kind == "approval_record" and exists:
            try:
                data = json.loads(Path(full_path).read_text())
                approval_summary = {
                    "status": data.get("status", "unknown"),
                    "approved": data.get("approved", False),
                    "approved_by": data.get("approved_by", ""),
                }
            except Exception:
                pass
        if kind == "mapping_snapshot" and exists:
            try:
                data = json.loads(Path(full_path).read_text())
                mapping_count = len(data.get("mappings", []))
            except Exception:
                pass
        if kind == "command_templates" and exists:
            try:
                data = json.loads(Path(full_path).read_text())
                template_count = len(data.get("templates", []))
            except Exception:
                pass
        if kind == "rawdata_checksum_before" and exists:
            try:
                data = json.loads(Path(full_path).read_text())
                approval_summary["rawdata_fingerprint"] = data.get("fingerprint", "")
                approval_summary["rawdata_file_count"] = data.get("file_count", 0)
            except Exception:
                pass

    missing = [f.kind for f in files if not f.exists]
    if missing:
        warnings.append(f"Missing files in review package: {', '.join(missing)}")

    return DicomConversionReviewPackageResponse(
        ok=len(errors) == 0,
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        run_dir=str(run_dir),
        files=files,
        approval_summary=approval_summary,
        mapping_count=mapping_count,
        command_template_count=template_count,
        manifest_path=str(run_dir / "planned_output_manifest.json"),
        provenance_path=str(run_dir / "planned_execution_provenance.json"),
        stdout_log_path=str(run_dir / "logs" / "stdout.log"),
        stderr_log_path=str(run_dir / "logs" / "stderr.log"),
        warnings=warnings,
        errors=errors,
        safety_flags=_safety_flags(),
    )


# ═══════════════════════════════════════════════════════════════════════
# 4. Audit export
# ═══════════════════════════════════════════════════════════════════════


def export_conversion_review_package(
    project_id: str,
    conversion_run_id: str,
    *,
    project_dir: str = "",
    rawdata_dir: str = "",
) -> DicomConversionAuditExportResponse:
    """Export a metadata-only audit bundle of the review package.

    Creates a ZIP file containing only whitelisted metadata files.
    Excludes .dcm, .nii, .nii.gz, .img, .hdr, .m, .mat files.
    Does NOT call dcm2niix.  Does NOT include image data.
    Does NOT modify rawdata.
    """
    errors: list[str] = []
    warnings: list[str] = []

    if not project_dir:
        return DicomConversionAuditExportResponse(
            ok=False, project_id=project_id, conversion_run_id=conversion_run_id,
            errors=["project_dir required."], safety_flags=_safety_flags(),
        )

    run_dir = Path(project_dir) / "conversion_runs" / conversion_run_id
    if not run_dir.exists():
        return DicomConversionAuditExportResponse(
            ok=False, project_id=project_id, conversion_run_id=conversion_run_id,
            errors=[f"Run directory not found: {run_dir}"],
            safety_flags=_safety_flags(),
        )

    export_dir = run_dir / "exports"
    export_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    zip_path = export_dir / f"conversion_review_package_{ts}.zip"

    excluded: list[str] = []
    included: list[str] = []

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        checksums: list[str] = []
        for fpath in sorted(run_dir.rglob("*")):
            if fpath.is_dir():
                continue
            ext = fpath.suffix.lower()
            # Check for double extensions like .nii.gz
            full_suffix = "".join(fpath.suffixes).lower()

            if ext in _BLOCKED_EXPORT_EXTS or full_suffix in _BLOCKED_EXPORT_EXTS:
                excluded.append(fpath.name)
                continue
            if ext not in _ALLOWED_EXPORT_EXTS:
                excluded.append(fpath.name)
                continue

            try:
                arcname = str(fpath.relative_to(run_dir))
                zf.write(fpath, arcname)
                included.append(arcname)
                sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
                checksums.append(f"{sha}  {arcname}")
            except Exception as exc:
                warnings.append(f"Failed to include {fpath.name}: {exc}")

        # Write SHA256SUMS
        sums_content = "\n".join(checksums) + "\n"
        zf.writestr("SHA256SUMS.txt", sums_content)
        included.append("SHA256SUMS.txt")

    zip_size = zip_path.stat().st_size
    zip_sha = hashlib.sha256(zip_path.read_bytes()).hexdigest()

    return DicomConversionAuditExportResponse(
        ok=len(errors) == 0,
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        export_path=str(zip_path),
        exists=True,
        size_bytes=zip_size,
        sha256=zip_sha,
        included_files=included,
        excluded_patterns=excluded,
        warnings=warnings,
        errors=errors,
        safety_flags=_safety_flags(),
    )


# ═══════════════════════════════════════════════════════════════════════
# 5. Smoke result reader — Phase 4F-1
# ═══════════════════════════════════════════════════════════════════════


class DicomConversionSmokeResultFile(BaseModel):
    kind: str = "unknown"
    path: str = ""
    exists: bool = False
    size_bytes: int | None = None
    sha256: str | None = None
    metadata_only: bool = True
    warnings: list[str] = Field(default_factory=list)


class DicomConversionSmokeResultResponse(BaseModel):
    ok: bool = False
    project_id: str = ""
    conversion_run_id: str = ""
    status: str = "unknown"
    synthetic_only: bool = True
    manifest_path: str | None = None
    provenance_path: str | None = None
    stdout_log_path: str | None = None
    stderr_log_path: str | None = None
    files: list[DicomConversionSmokeResultFile] = Field(default_factory=list)
    safety_flags: dict[str, bool] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def _smoke_safety_flags() -> dict[str, bool]:
    return {
        "synthetic_only": True,
        "no_user_rawdata_conversion": True,
        "no_rawdata_modified": True,
        "no_image_preview": True,
        "metadata_only": True,
        "no_spm_dpabi_matlab": True,
        "clinical_use_prohibited": True,
    }


def read_synthetic_smoke_results(
    project_id: str,
    conversion_run_id: str,
    *,
    project_dir: str = "",
) -> DicomConversionSmokeResultResponse:
    """Read synthetic smoke result metadata — metadata only, no image data.

    Reads output manifest, execution provenance, stdout/stderr logs, and
    discovered output files.  Does NOT parse NIfTI image contents.
    Does NOT call dcm2niix.  Does NOT modify rawdata.
    """
    warnings: list[str] = []
    errors: list[str] = []

    if not project_dir:
        return DicomConversionSmokeResultResponse(
            ok=False, project_id=project_id, conversion_run_id=conversion_run_id,
            errors=["project_dir required."],
            safety_flags=_smoke_safety_flags(),
        )

    run_dir = Path(project_dir) / "conversion_runs" / conversion_run_id
    if not run_dir.exists():
        return DicomConversionSmokeResultResponse(
            ok=False, project_id=project_id, conversion_run_id=conversion_run_id,
            warnings=[f"Run directory not found: {run_dir}"],
            safety_flags=_smoke_safety_flags(),
        )

    # Look for updated manifest/provenance (from Phase 4F-0 execution)
    manifest_path = run_dir / "output_manifest.json"
    provenance_path = run_dir / "execution_provenance.json"
    stdout_path = run_dir / "logs" / "dcm2niix_stdout.log"
    stderr_path = run_dir / "logs" / "dcm2niix_stderr.log"

    # Also check planned files (from Phase 4E-0)
    if not manifest_path.exists():
        manifest_path = run_dir / "planned_output_manifest.json"
    if not provenance_path.exists():
        provenance_path = run_dir / "planned_execution_provenance.json"

    files: list[DicomConversionSmokeResultFile] = []

    manifest_exists, manifest_size, manifest_sha = _file_info(str(manifest_path))
    files.append(DicomConversionSmokeResultFile(
        kind="manifest", path=str(manifest_path),
        exists=manifest_exists, size_bytes=manifest_size, sha256=manifest_sha,
        warnings=[] if manifest_exists else ["Manifest not found."],
    ))

    prov_exists, prov_size, prov_sha = _file_info(str(provenance_path))
    files.append(DicomConversionSmokeResultFile(
        kind="provenance", path=str(provenance_path),
        exists=prov_exists, size_bytes=prov_size, sha256=prov_sha,
        warnings=[] if prov_exists else ["Provenance not found."],
    ))

    stdout_exists, stdout_size, stdout_sha = _file_info(str(stdout_path))
    files.append(DicomConversionSmokeResultFile(
        kind="stdout_log", path=str(stdout_path),
        exists=stdout_exists, size_bytes=stdout_size,
        warnings=[] if stdout_exists else ["Stdout log not found."],
    ))

    stderr_exists, stderr_size, stderr_sha = _file_info(str(stderr_path))
    files.append(DicomConversionSmokeResultFile(
        kind="stderr_log", path=str(stderr_path),
        exists=stderr_exists, size_bytes=stderr_size,
        warnings=[] if stderr_exists else ["Stderr log not found."],
    ))

    # Discover output artifacts (metadata only, no image parsing)
    for p in sorted(run_dir.rglob("*")):
        if not p.is_file():
            continue
        if p.name in {"output_manifest.json", "execution_provenance.json",
                       "planned_output_manifest.json", "planned_execution_provenance.json",
                       "dcm2niix_stdout.log", "dcm2niix_stderr.log"}:
            continue  # Already handled above
        ext = p.suffix.lower()
        full_ext = "".join(p.suffixes).lower()
        if ext in {".nii", ".gz"} or full_ext == ".nii.gz":
            # NIfTI — metadata only
            info = p.stat()
            files.append(DicomConversionSmokeResultFile(
                kind="nifti_output", path=str(p),
                exists=True, size_bytes=info.st_size,
                metadata_only=True,
            ))
        elif ext in {".json", ".log", ".md", ".txt"}:
            info = p.stat()
            files.append(DicomConversionSmokeResultFile(
                kind="output_file", path=str(p),
                exists=True, size_bytes=info.st_size,
                metadata_only=True,
            ))

    status = "results_available" if manifest_exists else "no_results"

    return DicomConversionSmokeResultResponse(
        ok=len(errors) == 0,
        project_id=project_id,
        conversion_run_id=conversion_run_id,
        status=status,
        synthetic_only=True,
        manifest_path=str(manifest_path) if manifest_exists else None,
        provenance_path=str(provenance_path) if prov_exists else None,
        stdout_log_path=str(stdout_path) if stdout_exists else None,
        stderr_log_path=str(stderr_path) if stderr_exists else None,
        files=files,
        safety_flags=_smoke_safety_flags(),
        warnings=warnings,
        errors=errors,
    )
