"""Preprocessing Pipeline Report Service — Phase 5N."""
from __future__ import annotations
import json, hashlib
from pathlib import Path

from src.backend.app.runtime.atomic_file import atomic_write_json
from src.backend.app.schemas.preprocessing_pipeline_report import PipelineReportResponse
from src.backend.app.schemas.preprocessing_stage_catalog import (
    contains_stage_marker,
    iter_preprocessing_stage_specs,
    normalize_stage_execution_status,
    stage_dry_run_manifest_names,
)
from src.backend.app.services.preprocessing_artifact_registry import (
    REGISTRY_FILENAME,
    load_artifact_registry,
)
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

    # Collect stage statuses from dry-runs, executions, registrations.
    stages: list[dict] = []; warnings: list[str] = []; registered: list[dict] = []

    registry_path = run_dir / REGISTRY_FILENAME
    registry_data: dict = {}
    registry_artifacts: list[dict] = []
    if registry_path.exists():
        registry_data = load_artifact_registry(registry_path)
        registry_artifacts = [
            item for item in registry_data.get("artifacts", [])
            if isinstance(item, dict)
        ]
    manifest_stage_statuses: dict[str, dict] = {}
    manifest_path = run_dir / "preprocessing_run_manifest.json"
    if manifest_path.exists():
        try:
            manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest_stage_statuses = {
                str(item.get("stage_id")): item
                for item in manifest_data.get("stage_statuses", [])
                if isinstance(item, dict) and item.get("stage_id")
            }
        except (json.JSONDecodeError, OSError):
            warnings.append("Preprocessing run manifest could not be parsed.")
    for spec in iter_preprocessing_stage_specs():
        stage = spec.stage_id
        st = {
            "stage_id": stage,
            "name": spec.display_name,
            "category": spec.category,
            "backend": spec.default_backend,
            "requires_external_tool": spec.requires_external_tool,
            "requires_approval": spec.requires_approval,
            "requires_env_flags": list(spec.requires_env_flags),
            "required_for_fc": spec.required_for_fc,
            "optional": spec.optional,
            "depends_on": list(spec.depends_on),
            "input_artifact_types": list(spec.input_artifact_types),
            "optional_input_artifact_types": list(spec.optional_input_artifact_types),
            "output_artifact_types": list(spec.output_artifact_types),
            "prerequisite_notes": list(spec.prerequisite_notes),
            "scientific_status": spec.scientific_status,
            "validation_status": spec.validation_status,
            "status": "blocked" if spec.requires_external_tool else "not_started",
            "dry_run_ids": [],
            "execution_ids": [],
            "registration_ids": [],
            "artifact_ids": [],
            "metadata_only": False,
            "preview_only": False,
        }
        # Find dry-runs
        dry_dir = run_dir / "spm_dry_runs"
        if dry_dir.exists():
            for d in sorted(dry_dir.iterdir()):
                if d.is_dir():
                    manifest_names = stage_dry_run_manifest_names(stage)
                    mf = next((d / name for name in manifest_names if (d / name).exists()), None)
                    if mf and mf.exists():
                        st["dry_run_ids"].append(d.name)
                        st["status"] = "preview_only"
        # Find executions
        exec_dir = run_dir / "spm_exec"
        if exec_dir.exists():
            for e in sorted(exec_dir.iterdir()):
                if e.is_dir() and (e / "manifest.json").exists():
                    mf = json.loads((e / "manifest.json").read_text())
                    blob = json.dumps(mf).lower() + " " + e.name.lower()
                    if contains_stage_marker(blob, stage):
                        st["execution_ids"].append(e.name)
                        st["metadata_only"] = bool(mf.get("metadata_only", False))
                        st["preview_only"] = bool(mf.get("preview_only", False))
                        st["status"] = normalize_stage_execution_status(
                            str(mf.get("status", "unknown")),
                            metadata_only=st["metadata_only"],
                            preview_only=st["preview_only"],
                        )
        # Find registrations
        reg_dir = run_dir / "registered_stage_outputs"
        if reg_dir.exists():
            for r in sorted(reg_dir.iterdir()):
                if not r.is_dir():
                    continue
                for jf in r.rglob("*.json"):
                    if jf.exists() and contains_stage_marker(jf.read_text().lower(), stage):
                        st["registration_ids"].append(r.name)
                        if not st["metadata_only"] and not st["preview_only"]:
                            st["status"] = "succeeded" if st["execution_ids"] else "preview_only"
                        break
        stage_artifacts = [
            artifact for artifact in registry_artifacts
            if artifact.get("stage_id") == stage
        ]
        if stage_artifacts:
            st["artifact_ids"] = [
                str(artifact.get("artifact_id"))
                for artifact in stage_artifacts
                if artifact.get("artifact_id")
            ]
            if not st["metadata_only"] and not st["preview_only"]:
                st["status"] = "succeeded" if any(
                    artifact.get("artifact_type") not in {"stage_manifest", "qc_json", "provenance_json"}
                    for artifact in stage_artifacts
                ) else st["status"]
        manifest_stage = manifest_stage_statuses.get(stage)
        if manifest_stage:
            manifest_status = str(manifest_stage.get("status", ""))
            should_overlay = bool(manifest_stage.get("output_manifest")) or manifest_status not in {"", "not_started", "planned"}
            if should_overlay:
                st["status"] = normalize_stage_execution_status(manifest_status)
                st["metadata_only"] = st["status"] == "metadata_only"
                st["preview_only"] = st["status"] == "preview_only"
                st["manifest_status"] = manifest_status
                st["error_message"] = manifest_stage.get("error_message")
                st["orchestrator_result"] = manifest_stage.get("output_manifest", {})
                scope = st["orchestrator_result"].get("result", {}).get("execution_scope", {})
                if isinstance(scope, dict):
                    st["execution_scope"] = scope
        stages.append(st)

    # Registered outputs
    if registry_artifacts:
        registered = [
            {
                "artifact_id": str(item.get("artifact_id") or ""),
                "artifact_type": str(item.get("artifact_type") or ""),
                "stage_id": str(item.get("stage_id") or ""),
                "path": str(item.get("path") or ""),
                "path_kind": str(item.get("path_kind") or ""),
                "shape": list(item.get("shape", [])),
                "dtype": str(item.get("dtype") or ""),
                "checksum": str(item.get("checksum") or ""),
                "provenance_path": str(item.get("provenance_path") or ""),
                "qc_path": str(item.get("qc_path") or ""),
                "source_artifact_ids": list(item.get("source_artifact_ids", [])),
            }
            for item in registry_artifacts
        ]
    else:
        reg_dir = run_dir / "registered_stage_outputs"
        if reg_dir.exists():
            for r in sorted(reg_dir.iterdir()):
                if r.is_dir():
                    registered.append({"stage_output_id": r.name, "artifacts": sorted(str(p) for p in r.rglob("*") if p.is_file())})

    summary = f"Pipeline report for {project_id}/{run_id}. {len(stages)} stages tracked."
    warnings.append("This report is metadata-only. No raw image data included.")
    lineage_summary = {
        "artifact_count": len(registry_artifacts),
        "lineage_edge_count": sum(
            len(v) for v in registry_data.get("lineage", {}).values()
            if isinstance(v, list)
        ) if registry_data else 0,
    }

    # Write report files
    report = {"project_id": project_id, "run_id": run_id, "stages": stages,
              "artifact_registry_path": str(registry_path) if registry_path.exists() else "",
              "lineage_summary": lineage_summary,
              "registered_outputs": registered, "safety_flags": {"rawdata_not_modified": True, "no_dpabi": True, "sandbox_only": True, "no_clinical_diagnosis": True}}
    atomic_write_json(report_dir / "preprocessing_pipeline_report.json", report, schema_version=1)
    (report_dir / "preprocessing_pipeline_report.md").write_text(f"# Pipeline Report: {project_id}/{run_id}\n\n{summary}\n")

    return PipelineReportResponse(
        ok=True, status="generated", project_id=project_id, preprocessing_run_id=run_id,
        report_id=report_id, report_path=str(report_dir),
        summary=summary, artifact_registry_path=str(registry_path) if registry_path.exists() else "",
        lineage_summary=lineage_summary, stage_statuses=stages, registered_outputs=registered,
        warnings=warnings, safety_flags={"rawdata_not_modified": True, "no_dpabi": True, "no_clinical_diagnosis": True, "research_use_only": True})
