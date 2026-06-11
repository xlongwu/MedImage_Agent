"""Preprocessing Pipeline Report Service — Phase 5N."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

from src.backend.app.schemas.preprocessing_pipeline_report import PipelineReportResponse
from src.backend.app.services.mock_store import mock_store


def _now_iso() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def generate_pipeline_report(
    project_id: str, run_id: str, *, project_dir: str = ""
) -> PipelineReportResponse:
    project = mock_store.get_project(project_id)
    meta = project.metadata if project and isinstance(project.metadata, dict) else {}
    effective_pd = project_dir or str(meta.get("project_dir") or "")
    run_dir = Path(effective_pd) / "preprocessing_runs" / run_id if effective_pd else Path(f"outputs/preprocessing_runs/{run_id}")

    report_id = "rpt-" + hashlib.sha256(f"{project_id}:{run_id}:{_now_iso()}".encode()).hexdigest()[:10]
    report_dir = Path(effective_pd) / "preprocessing_runs" / run_id / "reports" / report_id if effective_pd else Path(f"outputs/reports/{report_id}")
    report_dir.mkdir(parents=True, exist_ok=True)

    # Collect stage statuses from dry-runs, executions, registrations
    stages: list[dict] = []; warnings: list[str] = []; registered: list[dict] = []
    flow = ["input_validation", "dummy_scan_removal", "slice_timing", "realign",
            "coregistration", "segmentation", "normalization", "smoothing",
            "nuisance_regression", "temporal_filtering", "alff_falff", "reho", "functional_connectivity",
            "subject_qc", "group_summary"]

    for stage in flow:
        st = {"stage_id": stage, "status": "not_started", "dry_run_ids": [], "execution_ids": [], "registration_ids": []}
        # Find dry-runs
        dry_dir = run_dir / "spm_dry_runs"
        if dry_dir.exists():
            for d in sorted(dry_dir.iterdir()):
                if d.is_dir():
                    mf = d / f"{stage}_dry_run_manifest.json"
                    if not mf.exists():
                        mf = d / "coreg_norm_dry_run_manifest.json" if stage in ("coregistration","segmentation","normalization") else None
                        if not mf: mf = d / "alff_reho_dry_run_manifest.json" if stage in ("alff_falff","reho") else None
                        if not mf: mf = d / "filtering_dry_run_manifest.json" if stage == "temporal_filtering" else None
                        if not mf: mf = d / "fc_dry_run_manifest.json" if stage == "functional_connectivity" else None
                        if not mf: mf = d / "smoothing_dry_run_manifest.json" if stage == "smoothing" else None
                        if not mf: mf = d / "nuisance_dry_run_manifest.json" if stage == "nuisance_regression" else None
                    if mf and mf.exists():
                        st["dry_run_ids"].append(d.name)
                        st["status"] = "dry_run_ready"
        # Find executions
        exec_dir = run_dir / "spm_exec"
        if exec_dir.exists():
            for e in sorted(exec_dir.iterdir()):
                if e.is_dir() and (e / "manifest.json").exists():
                    mf = json.loads((e / "manifest.json").read_text())
                    if stage in mf.get("stage", ""):
                        st["execution_ids"].append(e.name)
                        st["status"] = mf.get("status", "unknown")
        stages.append(st)

    # Registered outputs
    reg_dir = run_dir / "registered_stage_outputs"
    if reg_dir.exists():
        for r in sorted(reg_dir.iterdir()):
            if r.is_dir():
                registered.append({"stage_output_id": r.name, "artifacts": sorted(str(p) for p in r.rglob("*") if p.is_file())})

    summary = f"Pipeline report for {project_id}/{run_id}. {len(stages)} stages tracked."
    warnings.append("This report is metadata-only. No raw image data included.")

    # Write report files
    report = {"project_id": project_id, "run_id": run_id, "stages": stages,
              "registered_outputs": registered, "safety_flags": {"rawdata_not_modified": True, "no_dpabi": True, "sandbox_only": True, "no_clinical_diagnosis": True}}
    (report_dir / "preprocessing_pipeline_report.json").write_text(json.dumps(report, indent=2))
    (report_dir / "preprocessing_pipeline_report.md").write_text(f"# Pipeline Report: {project_id}/{run_id}\n\n{summary}\n")

    return PipelineReportResponse(
        ok=True, status="generated", project_id=project_id, preprocessing_run_id=run_id,
        report_id=report_id, report_path=str(report_dir),
        summary=summary, stage_statuses=stages, registered_outputs=registered,
        warnings=warnings, safety_flags={"rawdata_not_modified": True, "no_dpabi": True, "no_clinical_diagnosis": True, "research_use_only": True})
