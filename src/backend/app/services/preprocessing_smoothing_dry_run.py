"""Smoothing Dry-Run Service — Phase 5I."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_smoothing_dry_run import (
    SmoothingDryRunRequest,
    SmoothingDryRunResponse,
    smoothing_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_smoothing_dry_run(
    project_id: str, run_id: str, request: SmoothingDryRunRequest, *, project_dir: str = ""
) -> SmoothingDryRunResponse:
    warnings: list[str] = []
    blocking: list[str] = []

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    if not func_input:
        return SmoothingDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No functional input registered."],
            safety_flags=smoothing_safety_flags(),
        )

    func_path = Path(func_input)
    if not func_path.exists():
        return SmoothingDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Functional input not found: {func_input}"],
            safety_flags=smoothing_safety_flags(),
        )

    # Find normalized functional files (w-prefixed BOLD)
    norm_bolds = [
        p
        for p in sorted(func_path.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]
    if not norm_bolds:
        return SmoothingDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No functional files found for smoothing."],
            safety_flags=smoothing_safety_flags(),
        )

    # Validate FWHM
    fwhm = request.fwhm or "[6,6,6]"
    if not fwhm.startswith("[") and not fwhm.endswith("]"):
        blocking.append(f"Invalid FWHM format: {fwhm}")

    # Create dry-run dir
    dry_id = (
        "s-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    )
    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
        if effective_pd
        else Path(f"outputs/spm_dry_runs/{dry_id}")
    )
    dry_dir.mkdir(parents=True, exist_ok=True)

    batch_paths: list[str] = []
    output_paths: list[str] = []
    subjects: set[str] = set()
    for bf in norm_bolds[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        subjects.add(subj)
        out_dir = dry_dir / subj
        out_dir.mkdir(parents=True, exist_ok=True)
        batch = f"""%% SPM Smoothing Dry-Run for {subj}
%% Dry-run only - no MATLAB/SPM execution.
fwhm_val = {fwhm};
in_file = '{bf}';
out_file = '{out_dir / f"s{bf.name}"}';
%% spm('defaults','FMRI');
%% matlabbatch{{1}}.spm.spatial.smooth.data = {{in_file}};
%% matlabbatch{{1}}.spm.spatial.smooth.fwhm = fwhm_val;
%% spm_jobman('run',matlabbatch);
disp('SMOOTHING_DRY_RUN_ONLY - SPM batch preview generated.');
"""
        bp = out_dir / "spm_smoothing_batch_preview.m"
        bp.write_text(batch, encoding="utf-8")
        batch_paths.append(str(bp))
        output_paths.append(str(out_dir / f"s{bf.name}"))

    (dry_dir / "smoothing_dry_run_manifest.json").write_text(
        json.dumps(
            {"dry_run_id": dry_id, "status": "dry_run_preview", "subjects": len(subjects)}, indent=2
        )
    )
    (dry_dir / "subject_planning_summary.json").write_text(
        json.dumps({"total": len(subjects)}, indent=2)
    )
    (dry_dir / "README.md").write_text(f"# Smoothing Dry-Run {dry_id}\nDry-run only.\n")

    return SmoothingDryRunResponse(
        ok=True,
        status="dry_run_preview_ready",
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=dry_id,
        dry_run_dir=str(dry_dir),
        subject_count=len(subjects),
        planned_subjects=sorted(subjects),
        functional_input_count=len(norm_bolds),
        batch_preview_paths=batch_paths,
        planned_output_paths=output_paths,
        warnings=warnings,
        next_actions=["Review batch preview.", "Enable MATLAB/SPM for execution."],
        safety_flags=smoothing_safety_flags(),
    )
