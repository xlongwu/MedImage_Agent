"""Preprocessing Pipeline Validation Service — Phase 5O."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_pipeline_validation import (
    PipelineValidationResponse,
    validation_safety_flags,
)
from src.backend.app.schemas.preprocessing_stage_catalog import (
    contains_stage_marker,
    iter_preprocessing_stage_specs,
    normalize_stage_execution_status,
    stage_dry_run_manifest_names,
)
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.preprocessing_artifact_registry import (
    REGISTRY_FILENAME,
    load_artifact_registry,
)

_RELOAD_REQUIRED_TYPES = {
    "alff_map",
    "atlas",
    "denoised_bold",
    "falff_map",
    "filtered_bold",
    "fc_matrix",
    "fisher_z_matrix",
    "roi_timeseries",
    "fd_timeseries",
    "reho_map",
}


def _resolve_registry_path(artifact: dict[str, Any], project_root: Path | None) -> Path:
    raw_path = Path(str(artifact.get("path") or ""))
    if artifact.get("path_kind") == "project_relative" and project_root:
        return project_root / raw_path
    return raw_path


def _reload_artifact(path: Path) -> tuple[bool, str]:
    if not path.exists() or not path.is_file():
        return False, f"Artifact does not exist: {path}"
    suffixes = "".join(path.suffixes).lower()
    try:
        if suffixes.endswith((".nii", ".nii.gz")):
            import nibabel as nib

            img = nib.load(str(path))
            _ = img.shape
            return True, "nifti_reload_ok"
        if path.suffix.lower() == ".npy":
            import numpy as np

            arr = np.load(path, mmap_mode="r")
            _ = arr.shape
            return True, "npy_reload_ok"
        if path.suffix.lower() in {".tsv", ".csv"}:
            first_line = path.read_text(encoding="utf-8", errors="replace").splitlines()[:1]
            return bool(first_line), "table_reload_ok" if first_line else "table_empty"
        if path.suffix.lower() == ".json":
            json.loads(path.read_text(encoding="utf-8"))
            return True, "json_reload_ok"
    except Exception as exc:
        return False, f"Reload failed: {exc}"
    return True, "exists"


def validate_preprocessing_pipeline(
    project_id: str, run_id: str, *, project_dir: str = ""
) -> PipelineValidationResponse:
    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / run_id if effective_pd else None

    warnings: list[str] = []
    errors: list[str] = []
    stage_summary: list[dict] = []
    completed: list[str] = []
    dry_run_only: list[str] = []
    sandbox_executed: list[str] = []
    registered: list[str] = []
    metadata_only: list[str] = []
    preview_only: list[str] = []
    blocked: list[str] = []

    if not run_dir or not run_dir.exists():
        return PipelineValidationResponse(
            ok=False,
            status="not_started",
            project_id=project_id,
            preprocessing_run_id=run_id,
            warnings=["Preprocessing run directory not found."],
            next_actions=["Create a preprocessing run and execute Python preflight."],
            safety_flags=validation_safety_flags(),
        )

    # Check converted BIDS input registration
    input_dir = str(meta.get("preprocessing_input_dir", ""))
    if not input_dir:
        warnings.append("Converted BIDS input not registered.")

    registry_path = run_dir / REGISTRY_FILENAME
    registry_artifacts: list[dict] = []
    if registry_path.exists():
        registry_data = load_artifact_registry(registry_path)
        registry_artifacts = [
            item for item in registry_data.get("artifacts", []) if isinstance(item, dict)
        ]
    project_root = Path(effective_pd).resolve() if effective_pd else None
    manifest_stage_statuses: dict[str, dict] = {}
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_stage_statuses = {
                str(item.get("stage_id")): item
                for item in manifest_data.get("stage_statuses", [])
                if isinstance(item, dict) and item.get("stage_id")
            }
        except (json.JSONDecodeError, OSError):
            warnings.append("Preprocessing run manifest could not be parsed.")

    # Scan for dry-runs and executions
    dry_dir = run_dir / "spm_dry_runs"
    exec_dir = run_dir / "spm_exec"
    reg_dir = run_dir / "registered_stage_outputs"
    report_dir = run_dir / "reports"

    has_dry_runs = dry_dir.exists() and any(dry_dir.iterdir())
    has_execs = exec_dir.exists() and any(exec_dir.iterdir())
    _has_regs = bool(registry_artifacts) or (reg_dir.exists() and any(reg_dir.iterdir()))
    has_reports = report_dir.exists() and any(report_dir.iterdir())

    if not has_dry_runs and not has_execs:
        warnings.append("No dry-runs or executions found. Only Python preflight may be complete.")

    # Always populate stage_summary from the unified catalog.
    for spec in iter_preprocessing_stage_specs():
        sid = spec.stage_id
        stage_info: dict = {
            "stage_id": sid,
            "name": spec.display_name,
            "category": spec.category,
            "backend": spec.default_backend,
            "requires_external_tool": spec.requires_external_tool,
            "requires_approval": spec.requires_approval,
            "requires_env_flags": list(spec.requires_env_flags),
            "required_for_fc": spec.required_for_fc,
            "optional": spec.optional,
            "depends_on": list(spec.depends_on),
            "input_artifact_types": list(spec.input_artifact_types),
            "optional_input_artifact_types": list(spec.optional_input_artifact_types),
            "output_artifact_types": list(spec.output_artifact_types),
            "prerequisite_notes": list(spec.prerequisite_notes),
            "scientific_status": spec.scientific_status,
            "validation_status": spec.validation_status,
            "dry_run": False,
            "executed": False,
            "registered": False,
            "metadata_only": False,
            "preview_only": False,
            "artifact_ids": [],
            "status": "blocked" if spec.requires_external_tool else "not_started",
        }
        # Check dry-runs
        if dry_dir.exists():
            for d in dry_dir.iterdir():
                expected_manifests = stage_dry_run_manifest_names(sid)
                has_manifest = any((d / name).exists() for name in expected_manifests)
                if has_manifest or contains_stage_marker(d.name, sid):
                    stage_info["dry_run"] = True
                    stage_info["status"] = "preview_only"
        # Check executions
        if exec_dir.exists():
            for e in exec_dir.iterdir():
                if e.is_dir() and (e / "manifest.json").exists():
                    mf = json.loads((e / "manifest.json").read_text())
                    blob = json.dumps(mf).lower() + " " + e.name.lower()
                    if not contains_stage_marker(blob, sid):
                        continue
                    status_val = mf.get("status", "")
                    if status_val in ("succeeded", "warning", "partial", "metadata_only"):
                        stage_info["executed"] = True
                        stage_info["metadata_only"] = mf.get("metadata_only", False)
                        stage_info["preview_only"] = mf.get("preview_only", False)
                        stage_info["status"] = normalize_stage_execution_status(
                            str(status_val),
                            metadata_only=bool(stage_info["metadata_only"]),
                            preview_only=bool(stage_info["preview_only"]),
                        )
        # Check registrations
        if reg_dir.exists():
            for r in reg_dir.iterdir():
                if r.is_dir():
                    for jf in r.rglob("*.json"):
                        if jf.exists() and contains_stage_marker(jf.read_text().lower(), sid):
                            stage_info["registered"] = True
                            if not stage_info["metadata_only"] and not stage_info["preview_only"]:
                                stage_info["status"] = (
                                    "succeeded" if stage_info["executed"] else "preview_only"
                                )
        stage_artifacts = [
            artifact for artifact in registry_artifacts if artifact.get("stage_id") == sid
        ]
        if stage_artifacts:
            stage_info["registered"] = True
            stage_info["artifact_ids"] = [
                str(artifact.get("artifact_id"))
                for artifact in stage_artifacts
                if artifact.get("artifact_id")
            ]
            reload_checks: list[dict[str, Any]] = []
            for artifact in stage_artifacts:
                artifact_type = str(artifact.get("artifact_type") or "")
                if artifact_type not in _RELOAD_REQUIRED_TYPES:
                    continue
                artifact_path = _resolve_registry_path(artifact, project_root)
                ok, message = _reload_artifact(artifact_path)
                reload_checks.append(
                    {
                        "artifact_id": str(artifact.get("artifact_id") or ""),
                        "artifact_type": artifact_type,
                        "path": str(artifact_path),
                        "ok": ok,
                        "message": message,
                    }
                )
                if not ok:
                    errors.append(f"{sid}:{artifact_type}: {message}")
            if reload_checks:
                stage_info["reload_checks"] = reload_checks
                stage_info["reload_validated"] = all(item["ok"] for item in reload_checks)
            if not stage_info["metadata_only"] and not stage_info["preview_only"]:
                stage_info["status"] = (
                    "succeeded"
                    if any(
                        artifact.get("artifact_type")
                        not in {"stage_manifest", "qc_json", "provenance_json"}
                        for artifact in stage_artifacts
                    )
                    else stage_info["status"]
                )
        manifest_stage = manifest_stage_statuses.get(sid)
        if manifest_stage:
            manifest_status = str(manifest_stage.get("status", ""))
            should_overlay = bool(manifest_stage.get("output_manifest")) or manifest_status not in {
                "",
                "not_started",
                "planned",
            }
            if should_overlay:
                stage_info["status"] = normalize_stage_execution_status(manifest_status)
                stage_info["metadata_only"] = stage_info["status"] == "metadata_only"
                stage_info["preview_only"] = stage_info["status"] == "preview_only"
                stage_info["manifest_status"] = manifest_status
                stage_info["error_message"] = manifest_stage.get("error_message")
                stage_info["orchestrator_result"] = manifest_stage.get("output_manifest", {})
                scope = (
                    stage_info["orchestrator_result"].get("result", {}).get("execution_scope", {})
                )
                if isinstance(scope, dict):
                    stage_info["execution_scope"] = scope
        stage_summary.append(stage_info)
        if stage_info["dry_run"]:
            dry_run_only.append(sid) if not stage_info["executed"] else None
        if stage_info["executed"]:
            sandbox_executed.append(sid)
        if stage_info["registered"]:
            registered.extend(stage_info.get("artifact_ids") or [sid])
        if stage_info["metadata_only"]:
            metadata_only.append(sid)
        if stage_info["preview_only"]:
            preview_only.append(sid)
        if stage_info["status"] == "blocked":
            blocked.append(sid)
        if stage_info["status"] == "succeeded":
            completed.append(sid)
    if registry_artifacts and not registered:
        registered = [
            str(artifact.get("artifact_id"))
            for artifact in registry_artifacts
            if artifact.get("artifact_id")
        ]

    # Safety checks
    if has_execs and exec_dir.exists():
        for e in exec_dir.iterdir():
            if e.is_dir():
                readme = e / "README.md"
                if readme.exists():
                    text = readme.read_text().lower()
                    if "rawdata" in text and "modified" in text:
                        errors.append(f"Potential rawdata write detected in {e.name}")
                    if "dpabi" in text:
                        warnings.append(f"DPABI reference found in {e.name}")
                    if "group statistics" in text or "classification" in text:
                        errors.append(f"Group statistics/classification in {e.name}")

    if not has_reports:
        warnings.append("No pipeline reports generated. Run report export.")

    if metadata_only:
        warnings.append(
            "Metadata-only stages do not satisfy computed scientific completion: "
            + ", ".join(sorted(set(metadata_only)))
        )
    if preview_only:
        warnings.append(
            "Preview-only stages do not satisfy full atlas-grounded E2E completion: "
            + ", ".join(sorted(set(preview_only)))
        )

    if errors:
        status = "blocked"
    elif metadata_only or preview_only:
        status = "warning"
    elif has_execs and not warnings:
        status = "ready_for_review"
    elif warnings:
        status = "warning"
    else:
        status = "not_started"

    return PipelineValidationResponse(
        ok=True,
        status=status,
        project_id=project_id,
        preprocessing_run_id=run_id,
        artifact_registry_path=str(registry_path) if registry_path.exists() else "",
        stage_summary=stage_summary,
        completed_stages=completed,
        dry_run_only_stages=dry_run_only,
        sandbox_executed_stages=sandbox_executed,
        registered_outputs=registered,
        metadata_only_stages=metadata_only,
        preview_only_stages=preview_only,
        blocked_stages=blocked,
        warnings=warnings,
        errors=errors,
        next_actions=["Review validation results.", "Generate pipeline report."],
        safety_flags=validation_safety_flags(),
    )
