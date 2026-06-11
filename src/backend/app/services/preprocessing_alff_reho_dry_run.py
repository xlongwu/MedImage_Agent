"""ALFF/ReHo Dry-Run Service — Phase 5L."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

from src.backend.app.schemas.preprocessing_alff_reho_dry_run import (
    AlffRehoDryRunRequest, AlffRehoDryRunResponse, alff_reho_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_alff_reho_dry_run(
    project_id: str, run_id: str, request: AlffRehoDryRunRequest,
    *, project_dir: str = ""
) -> AlffRehoDryRunResponse:
    blocking: list[str] = []; warnings: list[str] = []

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    if not func_input:
        return AlffRehoDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional input registered."], safety_flags=alff_reho_safety_flags())

    func_path = Path(func_input)
    if not func_path.exists():
        return AlffRehoDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Functional input not found: {func_input}"],
            safety_flags=alff_reho_safety_flags())

    # Validate at least one metric selected
    if not any([request.compute_alff, request.compute_falff, request.compute_reho]):
        blocking.append("At least one metric (ALFF, fALFF, ReHo) must be selected.")

    if request.reho_neighbors not in (7, 19, 27):
        blocking.append(f"Invalid ReHo neighbors: {request.reho_neighbors}")

    if blocking:
        return AlffRehoDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=blocking, safety_flags=alff_reho_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not bold_files:
        return AlffRehoDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional files found."], safety_flags=alff_reho_safety_flags())

    dry_id = "ar-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id if effective_pd else Path(f"outputs/spm_dry_runs/{dry_id}")
    dry_dir.mkdir(parents=True, exist_ok=True)

    subjects: set[str] = set(); alff_paths: list[str] = []; reho_paths: list[str] = []; output_paths: list[str] = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        subjects.add(subj); out_dir = dry_dir / subj; out_dir.mkdir(parents=True, exist_ok=True)
        plan = {"subject": subj, "functional": str(bf), "alff": request.compute_alff,
                "falff": request.compute_falff, "reho": request.compute_reho,
                "reho_neighbors": request.reho_neighbors}
        pp = out_dir / "alff_reho_plan_preview.json"
        pp.write_text(json.dumps(plan, indent=2))
        if request.compute_alff or request.compute_falff:
            alff_paths.append(str(pp))
            output_paths.append(str(out_dir / f"ALFF_{bf.name}"))
        if request.compute_reho:
            reho_paths.append(str(pp))
            output_paths.append(str(out_dir / f"ReHo_{bf.name}"))

    (dry_dir / "alff_reho_dry_run_manifest.json").write_text(json.dumps({
        "dry_run_id": dry_id, "status": "dry_run_preview", "subjects": len(subjects)}, indent=2))
    (dry_dir / "README.md").write_text("# ALFF/ReHo Dry-Run\nDry-run only.\n")

    return AlffRehoDryRunResponse(
        ok=True, status="dry_run_preview_ready", project_id=project_id,
        preprocessing_run_id=run_id, dry_run_id=dry_id, dry_run_dir=str(dry_dir),
        subject_count=len(subjects), planned_subjects=sorted(subjects),
        functional_input_count=len(bold_files),
        alff_plan_paths=alff_paths, reho_plan_paths=reho_paths,
        planned_output_paths=output_paths, warnings=warnings,
        next_actions=["Review plan.", "Enable execution for ALFF/ReHo."],
        safety_flags=alff_reho_safety_flags())
