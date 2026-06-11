"""FC Dry-Run Service — Phase 5M."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

from src.backend.app.schemas.preprocessing_fc_dry_run import (
    FcDryRunRequest, FcDryRunResponse, fc_safety_flags,
)
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def run_fc_dry_run(
    project_id: str, run_id: str, request: FcDryRunRequest,
    *, project_dir: str = ""
) -> FcDryRunResponse:
    blocking: list[str] = []; warnings: list[str] = []

    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")

    func_input = request.functional_input_dir or str(meta.get("current_functional_input_dir") or "")
    if not func_input:
        return FcDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional input registered."], safety_flags=fc_safety_flags())

    func_path = Path(func_input)
    if not func_path.exists():
        return FcDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=[f"Functional input not found: {func_input}"],
            safety_flags=fc_safety_flags())

    # Validate correlation method
    if request.correlation_method not in ("pearson", "spearman"):
        blocking.append(f"Invalid correlation method: {request.correlation_method}")

    # Validate atlas if provided
    atlas_status = "none"
    if request.atlas_path:
        if ".." in request.atlas_path:
            blocking.append("Path traversal in atlas path.")
        elif not Path(request.atlas_path).exists():
            warnings.append(f"Atlas not found: {request.atlas_path}")
            atlas_status = "missing"
        else:
            atlas_status = "provided"

    if blocking:
        return FcDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=blocking, safety_flags=fc_safety_flags())

    bold_files = [p for p in sorted(func_path.rglob("*.nii*")) if p.is_file() and ("bold" in p.name.lower() or "rest" in p.name.lower())]
    if not bold_files:
        return FcDryRunResponse(ok=False, status="blocked", project_id=project_id,
            blocking_issues=["No functional files found."], safety_flags=fc_safety_flags())

    dry_id = "fc-dr-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    dry_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "spm_dry_runs" / dry_id if effective_pd else Path(f"outputs/spm_dry_runs/{dry_id}")
    dry_dir.mkdir(parents=True, exist_ok=True)

    subjects: set[str] = set(); fc_paths: list[str] = []; output_paths: list[str] = []
    for bf in bold_files[:10]:
        subj = "sub-unknown"
        for part in bf.parts:
            if part.startswith("sub-"): subj = part; break
        subjects.add(subj); out_dir = dry_dir / subj; out_dir.mkdir(parents=True, exist_ok=True)
        plan = {"subject": subj, "functional": str(bf), "method": request.correlation_method,
                "fisher_z": request.fisher_z, "atlas": request.atlas_name or "none", "atlas_status": atlas_status}
        fp = out_dir / "fc_plan_preview.json"
        fp.write_text(json.dumps(plan, indent=2))
        fc_paths.append(str(fp))
        output_paths.append(str(out_dir / f"FC_matrix_{bf.name}.json"))

    (dry_dir / "fc_dry_run_manifest.json").write_text(json.dumps({
        "dry_run_id": dry_id, "status": "dry_run_preview", "subjects": len(subjects)}, indent=2))
    (dry_dir / "README.md").write_text("# FC Dry-Run\nDry-run only. FC not executed.\n")

    return FcDryRunResponse(
        ok=True, status="dry_run_preview_ready", project_id=project_id,
        preprocessing_run_id=run_id, dry_run_id=dry_id, dry_run_dir=str(dry_dir),
        subject_count=len(subjects), planned_subjects=sorted(subjects),
        functional_input_count=len(bold_files), atlas_status=atlas_status,
        fc_plan_paths=fc_paths, planned_output_paths=output_paths,
        warnings=warnings, next_actions=["Review FC plan.", "Enable FC execution."],
        safety_flags=fc_safety_flags())
