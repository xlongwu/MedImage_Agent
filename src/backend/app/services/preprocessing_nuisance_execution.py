"""Nuisance Regression Sandbox Execution Service — Phase 5K. Python-only."""
from __future__ import annotations
import os, json, hashlib, shutil
from pathlib import Path

from src.backend.app.schemas.preprocessing_nuisance_execution import (
    NuisanceSandboxExecutionRequest, NuisanceSandboxExecutionResponse,
    validate_nuisance_env, nuisance_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_nuisance_sandbox_execution(
    project_id: str, run_id: str, request: NuisanceSandboxExecutionRequest,
    *, project_dir: str = "", env: dict[str, str] | None = None
) -> NuisanceSandboxExecutionResponse:
    eff_env = env or dict(os.environ)
    ok_flags, missing = validate_nuisance_env(eff_env)
    if not ok_flags:
        return NuisanceSandboxExecutionResponse(ok=False, status="disabled", project_id=project_id,
            blocking_issues=[f"Missing env flags: {missing}"], safety_flags=nuisance_safety_flags())

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / request.dry_run_id if effective_pd else None
    if not dry_dir or not dry_dir.exists():
        return NuisanceSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Dry-run not found: {request.dry_run_id}"], safety_flags=nuisance_safety_flags())

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    func_path = Path(func_input) if func_input else None
    if not func_path or not func_path.exists():
        return NuisanceSandboxExecutionResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["Functional input not found."], safety_flags=nuisance_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    motion_files = [p for p in sorted(func_path.rglob("rp_*.txt")) if p.is_file()]

    exec_id = "nr-ex-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    exec_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_exec" / exec_id if effective_pd else Path(f"outputs/spm_exec/{exec_id}")
    exec_dir.mkdir(parents=True, exist_ok=True)
    sandbox_in = exec_dir / "sandbox_input"; sandbox_in.mkdir()
    sandbox_out = exec_dir / "sandbox_output"; sandbox_out.mkdir()
    logs_dir = exec_dir / "logs"; logs_dir.mkdir()

    warnings: list[str] = []
    copied = []; designs = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        dest = sandbox_in / subj; dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(bf, dest / bf.name)
        copied.append(dest / bf.name)
        motion_match = [m for m in motion_files if subj in str(m)]
        mf = motion_match[0] if motion_match else None
        if mf: shutil.copy2(mf, dest / mf.name)
        design = {"subject": subj, "functional": str(dest / bf.name),
                  "motion_file": str(dest / mf.name) if mf else "MISSING",
                  "regression_applied": False}
        designs.append(design)
    if not motion_files:
        warnings.append("No motion parameter files found; metadata-only execution.")
    warnings.append("Nuisance regression is metadata-only. Numerical regression not yet applied.")

    # Metadata-only execution: write regressor design, no numerical regression
    rd_path = exec_dir / "regressor_design.json"
    rd_path.write_text(json.dumps({"designs": designs, "metadata_only": True}, indent=2))

    stdout_log = logs_dir / "stdout.log"; stderr_log = logs_dir / "stderr.log"
    stdout_log.write_text("Nuisance regression metadata-only execution.\n")
    stderr_log.write_text("")

    (exec_dir / "manifest.json").write_text(json.dumps({"status": "warning", "metadata_only": True}))
    (exec_dir / "provenance.json").write_text(json.dumps({"sandbox_only": True, "metadata_only": True}))
    (exec_dir / "subject_status.json").write_text(json.dumps({"total": len(copied), "regressed": 0, "metadata_only": True}))
    (exec_dir / "README.md").write_text("# Nuisance Regression Sandbox\nMetadata-only. No numerical regression applied.\n")

    return NuisanceSandboxExecutionResponse(
        ok=True, status="warning", project_id=project_id, preprocessing_run_id=run_id,
        dry_run_id=request.dry_run_id, execution_id=exec_id, execution_dir=str(exec_dir),
        sandbox_input_dir=str(sandbox_in), sandbox_output_dir=str(sandbox_out),
        subjects_total=len(copied), regressor_design_path=str(rd_path),
        stdout_log_path=str(stdout_log), stderr_log_path=str(stderr_log),
        manifest_path=str(exec_dir / "manifest.json"), provenance_path=str(exec_dir / "provenance.json"),
        subject_status_path=str(exec_dir / "subject_status.json"),
        warnings=warnings, next_actions=["Review regressor designs.", "Numerical regression will be applied in a future phase."],
        safety_flags=nuisance_safety_flags())
