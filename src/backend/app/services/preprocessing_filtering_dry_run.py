"""Temporal Filtering Dry-Run Service — Phase 5K."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC
from pathlib import Path

from src.backend.app.schemas.preprocessing_filtering_dry_run import (
    FilteringDryRunRequest,
    FilteringDryRunResponse,
    filtering_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime

    return datetime.now(UTC).isoformat()


def run_filtering_dry_run(
    project_id: str, run_id: str, request: FilteringDryRunRequest, *, project_dir: str = ""
) -> FilteringDryRunResponse:
    blocking: list[str] = []
    warnings: list[str] = []

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    if not func_input:
        return FilteringDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No functional input registered."],
            safety_flags=filtering_safety_flags(),
        )

    func_path = Path(func_input)
    if not func_path.exists():
        return FilteringDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[f"Functional input not found: {func_input}"],
            safety_flags=filtering_safety_flags(),
        )

    # Validate cutoffs
    low, high = request.low_cut_hz, request.high_cut_hz
    if low <= 0 or high <= 0 or low >= high:
        blocking.append(f"Invalid cutoff: low={low}, high={high}")

    if blocking:
        return FilteringDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=blocking,
            safety_flags=filtering_safety_flags(),
        )

    # Check if current input source indicates metadata-only nuisance
    input_source = str(meta.get("current_functional_input_source", ""))
    if "metadata_only" in input_source.lower() or "not_ready" in input_source.lower():
        return FilteringDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=[
                "Nuisance regression was metadata-only; numerical outputs required for filtering."
            ],
            safety_flags=filtering_safety_flags(),
        )

    bold_files = [
        p
        for p in sorted(func_path.rglob("*.nii*"))
        if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())
    ]
    if not bold_files:
        return FilteringDryRunResponse(
            ok=False,
            status="blocked",
            project_id=project_id,
            blocking_issues=["No functional files found."],
            safety_flags=filtering_safety_flags(),
        )

    dry_id = (
        "tf-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    )
    dry_dir = (
        Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id
        if effective_pd
        else Path(f"outputs/spm_dry_runs/{dry_id}")
    )
    dry_dir.mkdir(parents=True, exist_ok=True)

    subjects: set[str] = set()
    filter_paths: list[str] = []
    output_paths: list[str] = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"):
                subj = part
                break
        subjects.add(subj)
        out_dir = dry_dir / subj
        out_dir.mkdir(parents=True, exist_ok=True)
        design = {
            "subject": subj,
            "functional": str(bf),
            "low_cut_hz": low,
            "high_cut_hz": high,
            "method": "bandpass",
            "planned_output": f"filtered_{bf.name}",
        }
        fp = out_dir / "filter_design_preview.json"
        fp.write_text(json.dumps(design, indent=2))
        filter_paths.append(str(fp))
        output_paths.append(str(out_dir / f"filtered_{bf.name}"))

    (dry_dir / "filtering_dry_run_manifest.json").write_text(
        json.dumps(
            {"dry_run_id": dry_id, "status": "dry_run_preview", "subjects": len(subjects)}, indent=2
        )
    )
    (dry_dir / "README.md").write_text("# Temporal Filtering Dry-Run\nDry-run only.\n")

    return FilteringDryRunResponse(
        ok=True,
        status="dry_run_preview_ready",
        project_id=project_id,
        preprocessing_run_id=run_id,
        dry_run_id=dry_id,
        dry_run_dir=str(dry_dir),
        subject_count=len(subjects),
        planned_subjects=sorted(subjects),
        functional_input_count=len(bold_files),
        filter_design_paths=filter_paths,
        planned_output_paths=output_paths,
        warnings=warnings,
        next_actions=["Review filter designs.", "Enable execution for temporal filtering."],
        safety_flags=filtering_safety_flags(),
    )
