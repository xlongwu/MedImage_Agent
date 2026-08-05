"""Coregistration + Normalization Dry-Run Service — Phase 5G."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_coreg_norm_dry_run import (
    CoregNormDryRunRequest,
    CoregNormDryRunResponse,
    coreg_norm_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_coreg_norm_dry_run(
    project_id: str, run_id: str, request: CoregNormDryRunRequest, *, project_dir: str = ""
) -> CoregNormDryRunResponse:
    warnings: list[str] = []
    _blocking: list[str] = []

    project = mock_store.get_project(project_id)
    if not project:
        return CoregNormDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=coreg_norm_safety_flags(),
        )

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    # Locate functional input (from sandbox registration)
    func_input_dir = request.functional_input_dir or str(
        meta.get("current_functional_input_dir") or ""
    )
    if not func_input_dir:
        return CoregNormDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No functional input registered. Run sandbox registration first."],
            safety_flags=coreg_norm_safety_flags(),
        )

    func_path = Path(func_input_dir)
    if not func_path.exists():
        return CoregNormDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Functional input dir not found: {func_input_dir}"],
            safety_flags=coreg_norm_safety_flags(),
        )

    # Find functional BOLD outputs
    bold_outputs = [
        p
        for p in sorted(func_path.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]
    if not bold_outputs:
        return CoregNormDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No BOLD functional outputs found."],
            safety_flags=coreg_norm_safety_flags(),
        )

    # Find mean images and motion files
    mean_imgs = [p for p in sorted(func_path.rglob("mean*.nii*")) if p.is_file()]
    motion_files = [p for p in sorted(func_path.rglob("rp_*.txt")) if p.is_file()]
    if not mean_imgs:
        warnings.append("No mean functional image found; will use first BOLD as coreg target.")

    # Locate T1w from converted BIDS input
    conv_input = str(meta.get("preprocessing_input_dir") or "")
    t1w_files: list[Path] = []
    if conv_input:
        t1w_files = [
            p
            for p in sorted(Path(conv_input).rglob("*.nii*"))
            if p.is_file() and "t1" in p.name.lower()
        ]
    if not t1w_files:
        warnings.append("No T1w images found in converted input.")

    # Subject matching
    subjects: set[str] = set()
    planned: list[str] = []
    blocked_subjects: list[str] = []
    for bf in bold_outputs:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        subjects.add(subj)
        has_t1 = any(subj in str(t) for t in t1w_files)
        if has_t1:
            planned.append(subj)
        else:
            blocked_subjects.append(subj)

    # Create dry-run directory
    dry_id = (
        "cn-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    )
    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
        if effective_pd
        else Path(f"outputs/spm_dry_runs/{dry_id}")
    )
    dry_dir.mkdir(parents=True, exist_ok=True)

    batch_paths: list[str] = []
    output_paths: list[str] = []
    for bf in bold_outputs[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        out_dir = dry_dir / subj
        out_dir.mkdir(parents=True, exist_ok=True)
        batch = f"""%% SPM Coregistration + Normalization Dry-Run for {subj}
%% Dry-run only - no MATLAB/SPM execution.
func_file = '{bf}';
t1w_file = '{t1w_files[0] if t1w_files else "T1W_MISSING"}';
mean_file = '{mean_imgs[0] if mean_imgs else bf}';
coreg_target = mean_file;
%% Coregister T1 to mean functional
%% Segment T1
%% Estimate normalization
%% Apply normalization to functional
disp('COREG_NORM_DRY_RUN_ONLY - SPM batch preview generated.');
"""
        bp = out_dir / "spm_coreg_norm_batch_preview.m"
        bp.write_text(batch, encoding="utf-8")
        batch_paths.append(str(bp))
        output_paths.append(str(out_dir / f"w{bf.name}"))

    # Write manifest
    (dry_dir / "coreg_norm_dry_run_manifest.json").write_text(
        json.dumps(
            {
                "dry_run_id": dry_id,
                "status": "dry_run_preview",
                "subject_count": len(subjects),
                "planned": planned,
                "blocked": blocked_subjects,
            },
            indent=2,
        )
    )
    (dry_dir / "subject_planning_summary.json").write_text(
        json.dumps({"planned": planned, "blocked": blocked_subjects}, indent=2)
    )
    (dry_dir / "README.md").write_text(
        f"# Coreg/Norm Dry-Run {dry_id}\nDry-run only. MATLAB/SPM not executed. No image outputs.\n"
    )

    return CoregNormDryRunResponse(
        ok=True,
        status="dry_run_preview_ready" if planned else "warning",
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=dry_id,
        dry_run_dir=str(dry_dir),
        subject_count=len(subjects),
        planned_subjects=planned,
        blocked_subjects=blocked_subjects,
        functional_input_count=len(bold_outputs),
        t1w_count=len(t1w_files),
        mean_functional_count=len(mean_imgs),
        motion_parameter_count=len(motion_files),
        batch_preview_paths=batch_paths,
        planned_output_paths=output_paths,
        warnings=warnings,
        next_actions=["Review batch scripts.", "Enable MATLAB/SPM for execution."],
        safety_flags=coreg_norm_safety_flags(),
    )
