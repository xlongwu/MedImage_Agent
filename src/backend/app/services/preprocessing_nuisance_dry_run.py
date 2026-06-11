"""Nuisance Regression Dry-Run Service — Phase 5J."""
from __future__ import annotations
import json, hashlib
from pathlib import Path
from typing import Any

from src.backend.app.schemas.preprocessing_nuisance_dry_run import (
    NuisanceDryRunRequest, NuisanceDryRunResponse, nuisance_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_nuisance_dry_run(
    project_id: str, run_id: str, request: NuisanceDryRunRequest,
    *, project_dir: str = ""
) -> NuisanceDryRunResponse:
    warnings: list[str] = []; blocking: list[str] = []

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    if not func_input:
        return NuisanceDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional input registered."], safety_flags=nuisance_safety_flags())

    func_path = Path(func_input)
    if not func_path.exists():
        return NuisanceDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Functional input not found: {func_input}"],
            safety_flags=nuisance_safety_flags())

    smooth_bolds = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not smooth_bolds:
        return NuisanceDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No smoothed functional files found."], safety_flags=nuisance_safety_flags())

    # Find motion parameter files
    motion_files = [p for p in sorted(func_path.rglob("rp_*.txt")) if p.is_file()]
    if request.include_motion_24 and not motion_files:
        warnings.append("Motion parameters not found; motion regressors unavailable.")

    dry_id = "nr-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id if effective_pd else Path(f"outputs/spm_dry_runs/{dry_id}")
    dry_dir.mkdir(parents=True, exist_ok=True)

    subjects: set[str] = set(); regressor_paths: list[str] = []; output_paths: list[str] = []
    for bf in smooth_bolds[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        subjects.add(subj); out_dir = dry_dir / subj; out_dir.mkdir(parents=True, exist_ok=True)
        regressors = ["motion_24" if request.include_motion_24 else "",
                      "linear_trend" if request.include_linear_trend else "",
                      "constant" if request.include_constant else "",
                      "wm_csf" if request.include_wm_csf else "",
                      "global_signal" if request.include_global_signal else ""]
        regressors = [r for r in regressors if r]
        design = {"subject": subj, "functional": str(bf), "regressors": regressors,
                  "motion_file": str(motion_files[0]) if motion_files else "MISSING"}
        rp = out_dir / "regressor_design_preview.json"
        rp.write_text(json.dumps(design, indent=2))
        regressor_paths.append(str(rp))
        output_paths.append(str(out_dir / f"residuals_{bf.name}"))

    (dry_dir / "nuisance_dry_run_manifest.json").write_text(json.dumps({
        "dry_run_id": dry_id, "status": "dry_run_preview", "subjects": len(subjects)}, indent=2))
    (dry_dir / "README.md").write_text("# Nuisance Regression Dry-Run\nDry-run only.\n")

    return NuisanceDryRunResponse(
        ok=True, status="dry_run_preview_ready", project_id=project_id,
        preprocessing_run_id=run_id, dry_run_id=dry_id, dry_run_dir=str(dry_dir),
        subject_count=len(subjects), planned_subjects=sorted(subjects),
        functional_input_count=len(smooth_bolds), motion_parameter_count=len(motion_files),
        regressor_design_paths=regressor_paths, planned_output_paths=output_paths,
        warnings=warnings, next_actions=["Review regressor designs.", "Enable execution for nuisance regression."],
        safety_flags=nuisance_safety_flags())
