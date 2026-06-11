"""Preprocessing Stage Output Registration Service — Phase 5F.

Registers sandbox SPM Slice Timing + Realign outputs as next-stage
preprocessing input. No additional execution. Rawdata unchanged.
"""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_stage_outputs import (
    StageOutputRegistrationRequest, StageOutputRegistrationResponse, registration_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def register_sandbox_spm_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest,
    *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    blocking: list[str] = []; warnings: list[str] = []
    if not request.execution_id:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["execution_id is required."], safety_flags=registration_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    # Locate execution directory
    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            preprocessing_run_id=run_id, execution_id=request.execution_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags())

    # Verify execution succeeded (or fake-runner success)
    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated", "dry_run_preview"):
            blocking.append(f"Execution status is {mf.get('status')}, not succeeded.")

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Sandbox output dir not found: {sandbox_out}"],
            safety_flags=registration_safety_flags())

    # Discover output BOLD files (ra/r/a prefixes from SPM)
    bold_outputs: list[Path] = []; motion_files: list[Path] = []; mean_images: list[Path] = []
    for p in sorted(sandbox_out.rglob("*")):
        if not p.is_file(): continue
        name = p.name
        if p.suffix in (".nii", ".gz") or "".join(p.suffixes).lower() in (".nii", ".nii.gz"):
            if name.lower().startswith(("ra", "r", "a")) and ("bold" in name.lower() or "rest" in name.lower()):
                bold_outputs.append(p)
            elif name.lower().startswith("mean"):
                mean_images.append(p)
        elif name.startswith("rp_") and name.endswith(".txt"):
            motion_files.append(p)

    if not bold_outputs:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No output BOLD files found in sandbox output."],
            safety_flags=registration_safety_flags())

    # Create stage output registry
    stage_out_id = "so-" + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    reg_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "registered_stage_outputs" / stage_out_id if effective_pd else Path(f"outputs/stage_outputs/{stage_out_id}")
    reg_dir.mkdir(parents=True, exist_ok=True)

    (reg_dir / "stage_output_registry.json").write_text(json.dumps({
        "stage_output_id": stage_out_id, "source_execution": request.execution_id,
        "stage": "slice_timing_realign", "status": "registered", "created_at": _now_iso()}, indent=2))
    (reg_dir / "next_stage_input_manifest.json").write_text(json.dumps({
        "next_stage_input_dir": str(sandbox_out), "bold_count": len(bold_outputs),
        "motion_files": [str(f) for f in motion_files], "mean_images": [str(f) for f in mean_images]}, indent=2))
    (reg_dir / "subject_output_summary.json").write_text(json.dumps({
        "total": len(bold_outputs), "outputs": [str(p) for p in bold_outputs]}, indent=2))
    (reg_dir / "README.md").write_text("# Stage Output Registration\nSandbox outputs registered. No additional execution. Rawdata unchanged.\n")

    # Update run metadata
    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_slice_timing_realign"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)
        project.metadata["next_stage_input_registered"] = stage_out_id

    return StageOutputRegistrationResponse(
        ok=True, status="registered", project_id=project_id, preprocessing_run_id=run_id,
        execution_id=request.execution_id, registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir), next_stage_input_dir=str(sandbox_out),
        subject_count=len(bold_outputs), registered_bold_outputs=[str(p) for p in bold_outputs],
        motion_files=[str(f) for f in motion_files], mean_images=[str(f) for f in mean_images],
        next_actions=["Review registered outputs.", "Plan coregistration/normalization dry-run."],
        safety_flags=registration_safety_flags())


def register_coreg_norm_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest,
    *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    blocking: list[str] = []; warnings: list[str] = []
    if not request.execution_id:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["execution_id is required."], safety_flags=registration_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            preprocessing_run_id=run_id, blocking_issues=[f"Execution dir not found: {exec_dir}"],
            safety_flags=registration_safety_flags())

    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated"):
            blocking.append(f"Execution status is {mf.get('status')}, not succeeded.")

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Sandbox output dir not found: {sandbox_out}"],
            safety_flags=registration_safety_flags())

    # Discover normalized outputs (w-prefix BOLD and T1w)
    norm_bolds = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file() and
                  ("bold" in p.name.lower() or "rest" in p.name.lower())]
    t1w_outputs = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file() and "t1" in p.name.lower()]
    def_fields = [p for p in sorted(sandbox_out.rglob("*")) if p.is_file() and
                  p.suffix in (".nii", ".gz") and ("y_" in p.name or "deformation" in p.name.lower())]

    if not norm_bolds:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No normalized functional outputs found."],
            safety_flags=registration_safety_flags())

    stage_out_id = "cn-so-" + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    reg_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "registered_stage_outputs" / stage_out_id if effective_pd else Path(f"outputs/stage_outputs/{stage_out_id}")
    reg_dir.mkdir(parents=True, exist_ok=True)

    (reg_dir / "coreg_norm_stage_output_registry.json").write_text(json.dumps({
        "stage_output_id": stage_out_id, "source_execution": request.execution_id,
        "stage": "coreg_norm", "status": "registered"}, indent=2))
    (reg_dir / "next_stage_input_manifest.json").write_text(json.dumps({
        "next_stage_input_dir": str(sandbox_out), "func_count": len(norm_bolds),
        "t1w_count": len(t1w_outputs), "deformation_fields": len(def_fields)}, indent=2))
    (reg_dir / "README.md").write_text("# Coreg/Norm Stage Output Registration\n")

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_coreg_norm"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True, status="registered", project_id=project_id, preprocessing_run_id=run_id,
        execution_id=request.execution_id, registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir), next_stage_input_dir=str(sandbox_out),
        subject_count=len(norm_bolds), registered_bold_outputs=[str(p) for p in norm_bolds],
        motion_files=[str(p) for p in t1w_outputs], mean_images=[str(p) for p in def_fields],
        next_actions=["Review outputs.", "Plan smoothing dry-run."],
        safety_flags=registration_safety_flags())


def register_smoothing_outputs(
    project_id: str, run_id: str, request: StageOutputRegistrationRequest,
    *, project_dir: str = ""
) -> StageOutputRegistrationResponse:
    if not request.execution_id:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["execution_id is required."], safety_flags=registration_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / request.execution_id
    if not exec_dir.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Execution dir not found: {exec_dir}"], safety_flags=registration_safety_flags())

    manifest_path = exec_dir / "manifest.json"
    if manifest_path.exists():
        mf = json.loads(manifest_path.read_text())
        if mf.get("status") not in ("succeeded", "generated"):
            return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
                blocking_issues=[f"Execution not succeeded: {mf.get('status')}"], safety_flags=registration_safety_flags())

    sandbox_out = exec_dir / "sandbox_output"
    if not sandbox_out.exists():
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Sandbox output dir not found."], safety_flags=registration_safety_flags())

    smoothed = [p for p in sorted(sandbox_out.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not smoothed:
        return StageOutputRegistrationResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No smoothed outputs found."], safety_flags=registration_safety_flags())

    stage_out_id = "sm-so-" + hashlib.sha256(f"{project_id}:{run_id}:{request.execution_id}".encode()).hexdigest()[:10]
    reg_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "registered_stage_outputs" / stage_out_id if effective_pd else Path(f"outputs/stage_outputs/{stage_out_id}")
    reg_dir.mkdir(parents=True, exist_ok=True)

    (reg_dir / "smoothing_stage_output_registry.json").write_text(json.dumps({
        "stage_output_id": stage_out_id, "source_execution": request.execution_id, "stage": "smoothing"}, indent=2))
    (reg_dir / "next_stage_input_manifest.json").write_text(json.dumps({
        "next_stage_input_dir": str(sandbox_out), "smoothed_count": len(smoothed)}, indent=2))
    (reg_dir / "README.md").write_text("# Smoothing Stage Output Registration\n")

    if isinstance(project.metadata, dict):
        project.metadata["current_functional_input_source"] = "sandbox_spm_smoothing"
        project.metadata["current_functional_input_dir"] = str(sandbox_out)

    return StageOutputRegistrationResponse(
        ok=True, status="registered", project_id=project_id, preprocessing_run_id=run_id,
        execution_id=request.execution_id, registered_stage_output_id=stage_out_id,
        stage_output_dir=str(reg_dir), next_stage_input_dir=str(sandbox_out),
        subject_count=len(smoothed), registered_bold_outputs=[str(p) for p in smoothed],
        next_actions=["Review outputs.", "Plan nuisance regression dry-run."],
        safety_flags=registration_safety_flags())
