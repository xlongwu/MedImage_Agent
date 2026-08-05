"""Preprocessing SPM Dry-Run Service — Phase 5D.

Generates Slice Timing + Realign dry-run batch previews on converted BIDS.
Never executes MATLAB/SPM. No image outputs. No rawdata modification.
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_spm_dry_run import (
    SliceTimingRealignDryRunRequest,
    SliceTimingRealignDryRunResponse,
    safety_flags_dry_run,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_slice_timing_realign_dry_run(
    project_id: str, run_id: str, request: SliceTimingRealignDryRunRequest, *, project_dir: str = ""
) -> SliceTimingRealignDryRunResponse:
    blocking: list[str] = []
    warnings: list[str] = []
    _errors: list[str] = []

    project = mock_store.get_project(project_id)
    if not project:
        return SliceTimingRealignDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Project not found: {project_id}"],
            safety_flags=safety_flags_dry_run(),
        )

    meta = project.metadata if isinstance(project.metadata, dict) else {}
    input_dir = request.preprocessing_input_dir or str(meta.get("preprocessing_input_dir") or "")
    if not input_dir:
        return SliceTimingRealignDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No preprocessing input registered."],
            safety_flags=safety_flags_dry_run(),
        )

    _rawdata_dir = str(meta.get("rawdata_dir") or "")
    input_path = Path(input_dir)
    if not input_path.exists():
        return SliceTimingRealignDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Input dir not found: {input_dir}"],
            safety_flags=safety_flags_dry_run(),
        )

    # Find BOLD files
    bold_files: list[Path] = []
    for p in sorted(input_path.rglob("*.nii*")):
        name = p.name.lower()
        if ("bold" in name or "rest" in name) and p.is_file():
            bold_files.append(p)

    if not bold_files:
        return SliceTimingRealignDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            preprocessing_run_id=run_id,
            blocking_issues=["No BOLD files found in preprocessing input."],
            safety_flags=safety_flags_dry_run(),
        )

    # Validate parameters
    tr = request.tr
    nslices = request.num_slices
    ref_slice = request.reference_slice or 1
    if tr is not None and tr <= 0:
        blocking.append(f"Invalid TR: {tr}")
    if nslices is not None and nslices <= 0:
        blocking.append(f"Invalid num_slices: {nslices}")
    if ref_slice < 1:
        blocking.append(f"Invalid reference_slice: {ref_slice}")

    # Check sidecars for TR if not provided
    subjects: set[str] = set()
    planned: list[str] = []
    blocked_subjects: list[str] = []
    for bf in bold_files:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        subjects.add(subj)
        sidecar = bf.with_suffix("").with_suffix(".json")
        if not sidecar.exists():
            sidecar = Path(str(bf).replace(".nii.gz", ".json").replace(".nii", ".json"))
        if tr is None and sidecar.exists():
            try:
                sc = json.loads(sidecar.read_text())
                if "RepetitionTime" in sc:
                    tr = float(sc["RepetitionTime"])
            except Exception:
                pass
        if tr is None:
            warnings.append(f"No TR provided and not found in sidecar for {subj}.")
            blocked_subjects.append(subj)
        else:
            planned.append(subj)

    if blocking:
        return SliceTimingRealignDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            preprocessing_run_id=run_id,
            blocking_issues=blocking,
            safety_flags=safety_flags_dry_run(),
        )

    # Create dry-run directory
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    dry_id = (
        "spm-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    )
    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
        if effective_pd
        else Path(f"outputs/spm_dry_runs/{dry_id}")
    )
    dry_dir.mkdir(parents=True, exist_ok=True)

    batch_paths: list[str] = []
    output_paths: list[str] = []
    for bf in bold_files[:20]:  # Cap at 20 subjects
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        out_dir = dry_dir / subj
        out_dir.mkdir(parents=True, exist_ok=True)
        # Generate batch preview
        batch = f"""%% SPM Slice Timing + Realign Dry-Run Preview for {subj}
%% Dry-run only — no MATLAB/SPM execution.
tr_val = {tr or 2.0};
nslices_val = {nslices or 36};
ref_slice_val = {ref_slice};
slice_order_val = {request.slice_order or "[1:2:nslices_val 2:2:nslices_val]"};
in_file = '{bf}';
out_dir = '{out_dir}';
%% Planned stages: spm_jobman('run', matlabbatch) — NOT EXECUTED.
disp('DRY_RUN_ONLY — SPM batch preview generated.');
"""
        batch_path = out_dir / "spm_slice_timing_realign_batch_preview.m"
        batch_path.write_text(batch, encoding="utf-8")
        batch_paths.append(str(batch_path))
        output_paths.append(str(out_dir / f"ar_{bf.name}"))

    # Write manifest
    manifest = {
        "project_id": project_id,
        "run_id": run_id,
        "dry_run_id": dry_id,
        "status": "dry_run_preview",
        "subject_count": len(subjects),
        "planned_subjects": planned,
        "blocked_subjects": blocked_subjects,
        "bold_count": len(bold_files),
        "created_at": _now_iso(),
    }
    (dry_dir / "dry_run_manifest.json").write_text(json.dumps(manifest, indent=2))
    (dry_dir / "subject_planning_summary.json").write_text(
        json.dumps(
            {
                "planned": planned,
                "blocked": blocked_subjects,
                "params": {"tr": tr, "nslices": nslices, "ref_slice": ref_slice},
            },
            indent=2,
        )
    )
    (dry_dir / "README.md").write_text(
        f"# SPM Dry-Run {dry_id}\nDry-run only. MATLAB/SPM not executed. No image outputs.\n"
    )

    status = "dry_run_preview_ready" if planned else "warning"
    return SliceTimingRealignDryRunResponse(
        ok=True,
        status=status,
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=dry_id,
        dry_run_dir=str(dry_dir),
        subject_count=len(subjects),
        planned_subjects=planned,
        blocked_subjects=blocked_subjects,
        bold_count=len(bold_files),
        batch_preview_paths=batch_paths,
        planned_output_paths=output_paths,
        warnings=warnings,
        next_actions=["Review batch preview scripts.", "Enable MATLAB/SPM to execute."],
        safety_flags=safety_flags_dry_run(),
    )
