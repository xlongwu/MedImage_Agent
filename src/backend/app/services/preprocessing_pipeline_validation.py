"""Preprocessing Pipeline Validation Service — Phase 5O."""
from __future__ import annotations
import json, os
from pathlib import Path

from src.backend.app.schemas.preprocessing_pipeline_validation import (
    PipelineValidationResponse, validation_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def validate_preprocessing_pipeline(
    project_id: str, run_id: str, *, project_dir: str = ""
) -> PipelineValidationResponse:
    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / run_id if effective_pd else None

    warnings: list[str] = []; errors: list[str] = []; stage_summary: list[dict] = []
    completed: list[str] = []; dry_run_only: list[str] = []; sandbox_executed: list[str] = []
    registered: list[str] = []; metadata_only: list[str] = []; blocked: list[str] = []

    if not run_dir or not run_dir.exists():
        return PipelineValidationResponse(ok=False, status="not_started", project_id=project_id,
            preprocessing_run_id=run_id,
            warnings=["Preprocessing run directory not found."],
            next_actions=["Create a preprocessing run and execute Python preflight."],
            safety_flags=validation_safety_flags())

    # Check converted BIDS input registration
    input_dir = str(meta.get("preprocessing_input_dir", ""))
    if not input_dir:
        warnings.append("Converted BIDS input not registered.")

    # Scan for dry-runs and executions
    dry_dir = run_dir / "spm_dry_runs"
    exec_dir = run_dir / "spm_exec"
    reg_dir = run_dir / "registered_stage_outputs"
    report_dir = run_dir / "reports"

    has_dry_runs = dry_dir.exists() and any(dry_dir.iterdir())
    has_execs = exec_dir.exists() and any(exec_dir.iterdir())
    has_regs = reg_dir.exists() and any(reg_dir.iterdir())
    has_reports = report_dir.exists() and any(report_dir.iterdir())

    if not has_dry_runs and not has_execs:
        warnings.append("No dry-runs or executions found. Only Python preflight may be complete.")

    # Always populate stage_summary
    stage_names = {
            "slice_timing_realign": "Slice Timing + Realign",
            "coreg_norm": "Coregistration + Normalization",
            "smoothing": "Smoothing",
            "nuisance_regression": "Nuisance Regression",
            "temporal_filtering": "Temporal Filtering",
            "alff_reho": "ALFF/ReHo",
            "functional_connectivity": "Functional Connectivity",
        }
    for sid, sname in stage_names.items():
        stage_info: dict = {"stage_id": sid, "name": sname, "dry_run": False, "executed": False, "registered": False, "metadata_only": False, "status": "not_started"}
        # Check dry-runs
        if dry_dir.exists():
            for d in dry_dir.iterdir():
                pattern = sid.replace("_", "-")
                if pattern in d.name.lower() or sid.replace("_", "") in d.name.lower():
                    stage_info["dry_run"] = True
                    stage_info["status"] = "dry_run_ready"
        # Check executions
        if exec_dir.exists():
            for e in exec_dir.iterdir():
                if e.is_dir() and (e / "manifest.json").exists():
                    mf = json.loads((e / "manifest.json").read_text())
                    status_val = mf.get("status", "")
                    if status_val in ("succeeded", "warning"):
                        stage_info["executed"] = True
                        stage_info["status"] = status_val
                        stage_info["metadata_only"] = mf.get("metadata_only", False)
        # Check registrations
        if reg_dir.exists():
            for r in reg_dir.iterdir():
                if r.is_dir():
                    for jf in r.rglob("*.json"):
                        if jf.exists() and sid in jf.read_text().lower():
                            stage_info["registered"] = True
                            stage_info["status"] = "registered" if stage_info["executed"] else "registered_from_dry_run"
        stage_summary.append(stage_info)
        if stage_info["dry_run"]:
            dry_run_only.append(sid) if not stage_info["executed"] else None
        if stage_info["executed"]:
            sandbox_executed.append(sid)
        if stage_info["registered"]:
            registered.append(sid)
        if stage_info["metadata_only"]:
            metadata_only.append(sid)

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

    status = "ready_for_review" if has_execs and not errors else ("warning" if warnings else "blocked" if errors else "not_started")

    return PipelineValidationResponse(
        ok=True, status=status, project_id=project_id, preprocessing_run_id=run_id,
        stage_summary=stage_summary, completed_stages=completed,
        dry_run_only_stages=dry_run_only, sandbox_executed_stages=sandbox_executed,
        registered_outputs=registered, metadata_only_stages=metadata_only,
        blocked_stages=blocked, warnings=warnings, errors=errors,
        next_actions=["Review validation results.", "Generate pipeline report."],
        safety_flags=validation_safety_flags())
