from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ALLOWLISTED_FUNCTIONS = {"y_Smooth", "rest_Smooth"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _safe_id(value: str) -> bool:
    if not value:
        return False
    return "/" not in value and "\\" not in value and ".." not in value


def _template_index_path(work_dir: str) -> Path:
    return Path(work_dir) / "dpabi" / "templates" / "dpabi_template_index.json"


def _template_pipeline_root(work_dir: str) -> Path:
    return (Path(work_dir) / "dpabi" / "templates" / "pipelines").resolve()


def _instance_root(work_dir: str, instance_id: str) -> Path:
    return Path(work_dir) / "dpabi" / "template_instances" / instance_id


def _find_template(index: dict[str, Any], template_id: str) -> dict[str, Any] | None:
    for item in index.get("templates", []):
        if item.get("template_id") == template_id:
            return item
    return None


def _validate_template_path(template_path: Path, work_dir: str) -> None:
    root = _template_pipeline_root(work_dir)
    resolved = template_path.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Template path escapes template root: {template_path}") from exc


def _validate_template_metadata(pipeline: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    metadata = pipeline.get("template_metadata", {}) or {}

    if metadata.get("synthetic_only") is not True:
        errors.append("template_metadata.synthetic_only must be true.")

    if metadata.get("full_dpabi_execution") is not False:
        errors.append("template_metadata.full_dpabi_execution must be false.")

    if metadata.get("dparsf_run_allowed") is not False:
        errors.append("template_metadata.dparsf_run_allowed must be false.")

    if metadata.get("dparsfa_run_allowed") is not False:
        errors.append("template_metadata.dparsfa_run_allowed must be false.")

    if metadata.get("dpabi_gui_allowed") is not False:
        errors.append("template_metadata.dpabi_gui_allowed must be false.")

    return errors


def _update_nodes(
    pipeline: dict[str, Any],
    function_name: str | None,
    fwhm: list[float] | None,
    subjects: list[str] | None,
    approved: bool,
) -> None:
    for node in pipeline.get("nodes", []):
        if node.get("id") == "dpabi_subject_smooth":
            node.setdefault("params", {})
            if function_name:
                node["params"]["function_name"] = function_name
            if fwhm:
                node["params"]["fwhm"] = fwhm
            node["params"]["approved"] = approved
            node["params"]["synthetic_only"] = True

        if node.get("id") == "create_synthetic_bids" and subjects:
            node.setdefault("params", {})
            node["params"]["subjects"] = subjects


def list_dpabi_templates(work_dir: str = "./work") -> dict[str, Any]:
    index_path = _template_index_path(work_dir)
    index = _read_json(index_path)

    if not index:
        return {
            "ok": False,
            "templates": [],
            "errors": [f"Missing or invalid template index: {index_path}"],
            "warnings": [],
        }

    return {
        "ok": True,
        "template_index_path": str(index_path),
        "templates": index.get("templates", []),
        "warnings": index.get("warnings", []),
        "errors": [],
    }


def instantiate_dpabi_template(
    template_id: str,
    instance_id: str | None = None,
    run_id: str | None = None,
    function_name: str | None = None,
    fwhm: list[float] | None = None,
    subjects: list[str] | None = None,
    scheduler: dict[str, Any] | None = None,
    work_dir: str = "./work",
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if not _safe_id(template_id):
        return {
            "ok": False,
            "errors": ["Invalid template_id."],
            "warnings": warnings,
        }

    instance_id = instance_id or f"instance_{template_id}_001"

    if not _safe_id(instance_id):
        return {
            "ok": False,
            "errors": ["Invalid instance_id."],
            "warnings": warnings,
        }

    if function_name and function_name not in ALLOWLISTED_FUNCTIONS:
        return {
            "ok": False,
            "errors": [f"Function is not allowlisted: {function_name}"],
            "warnings": warnings,
        }

    index = _read_json(_template_index_path(work_dir))
    if not index:
        return {
            "ok": False,
            "errors": [f"Missing template index: {_template_index_path(work_dir)}"],
            "warnings": warnings,
        }

    template = _find_template(index, template_id)
    if not template:
        return {
            "ok": False,
            "errors": [f"Template not found: {template_id}"],
            "warnings": warnings,
        }

    template_path = Path(template.get("template_path", ""))
    try:
        _validate_template_path(template_path, work_dir)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [str(exc)],
            "warnings": warnings,
        }

    try:
        pipeline = _load_yaml(template_path)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to load template YAML: {exc}"],
            "warnings": warnings,
        }

    metadata_errors = _validate_template_metadata(pipeline)
    if metadata_errors:
        return {
            "ok": False,
            "errors": metadata_errors,
            "warnings": warnings,
        }

    final_run_id = run_id or f"run_{instance_id}"

    pipeline.setdefault("execution", {})
    pipeline["execution"]["run_id"] = final_run_id

    if scheduler:
        pipeline["execution"]["scheduler"] = scheduler

    _update_nodes(
        pipeline=pipeline,
        function_name=function_name,
        fwhm=fwhm,
        subjects=subjects,
        approved=False,
    )

    instance_dir = _instance_root(work_dir, instance_id)
    instance_dir.mkdir(parents=True, exist_ok=True)

    pipeline_out = instance_dir / "pipeline.yaml"
    manifest_out = instance_dir / "instance_manifest.json"
    review_out = instance_dir / "instance_review.md"

    _write_yaml(pipeline_out, pipeline)

    manifest = {
        "ok": True,
        "template_id": template_id,
        "instance_id": instance_id,
        "run_id": final_run_id,
        "template_path": str(template_path),
        "pipeline_path": str(pipeline_out),
        "function_name": function_name or template.get("function_name"),
        "fwhm": fwhm,
        "subjects": subjects,
        "scheduler": pipeline.get("execution", {}).get("scheduler", {}),
        "requires_approval": True,
        "approved": False,
        "execution_allowed": False,
        "synthetic_only": True,
        "full_dpabi_execution": False,
        "dparsf_run_allowed": False,
        "dparsfa_run_allowed": False,
        "dpabi_gui_allowed": False,
        "created_at": _now_iso(),
        "warnings": warnings,
        "errors": errors,
    }

    manifest_out.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    lines = []
    lines.append("# DPABI Template Instance Review")
    lines.append("")
    lines.append(f"- Template ID: {template_id}")
    lines.append(f"- Instance ID: {instance_id}")
    lines.append(f"- Run ID: {final_run_id}")
    lines.append(f"- Pipeline: `{pipeline_out}`")
    lines.append(f"- Requires approval: true")
    lines.append(f"- Approved: false")
    lines.append(f"- Execution allowed: false")
    lines.append(f"- Synthetic only: true")
    lines.append("")
    lines.append("## Safety Gates")
    lines.append("")
    lines.append("- Full DPABI execution: false")
    lines.append("- DPARSF_run allowed: false")
    lines.append("- DPARSFA_run allowed: false")
    lines.append("- DPABI GUI allowed: false")
    lines.append("- Rawdata modification: false")
    lines.append("")
    lines.append("This instance is review-only until explicitly approved.")

    review_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "ok": True,
        "mode": "INSTANTIATE_ONLY",
        "template_id": template_id,
        "instance_id": instance_id,
        "run_id": final_run_id,
        "outputs": [str(pipeline_out), str(manifest_out), str(review_out)],
        "pipeline_path": str(pipeline_out),
        "manifest_path": str(manifest_out),
        "review_path": str(review_out),
        "warnings": warnings,
        "errors": errors,
    }


def execute_dpabi_template_instance(
    instance_id: str,
    project_config_path: str = "examples/project_config_dataset.yaml",
    approved: bool = False,
    approved_by: str = "local-user",
    work_dir: str = "./work",
) -> dict[str, Any]:
    if not _safe_id(instance_id):
        return {
            "ok": False,
            "errors": ["Invalid instance_id."],
            "warnings": [],
        }

    if not approved:
        return {
            "ok": False,
            "mode": "EXECUTE",
            "instance_id": instance_id,
            "errors": ["Template instance execution requires approved=true."],
            "warnings": [],
        }

    instance_dir = _instance_root(work_dir, instance_id)
    pipeline_path = instance_dir / "pipeline.yaml"
    manifest_path = instance_dir / "instance_manifest.json"

    if not pipeline_path.exists():
        return {
            "ok": False,
            "errors": [f"Instance pipeline not found: {pipeline_path}"],
            "warnings": [],
        }

    manifest = _read_json(manifest_path)
    if not manifest:
        return {
            "ok": False,
            "errors": [f"Instance manifest missing or invalid: {manifest_path}"],
            "warnings": [],
        }

    if manifest.get("synthetic_only") is not True:
        return {
            "ok": False,
            "errors": ["Refusing to execute non-synthetic template instance."],
            "warnings": [],
        }

    try:
        pipeline = _load_yaml(pipeline_path)
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Failed to load instance pipeline: {exc}"],
            "warnings": [],
        }

    metadata_errors = _validate_template_metadata(pipeline)
    if metadata_errors:
        return {
            "ok": False,
            "errors": metadata_errors,
            "warnings": [],
        }

    _update_nodes(
        pipeline=pipeline,
        function_name=None,
        fwhm=None,
        subjects=None,
        approved=True,
    )

    approved_pipeline = instance_dir / "approved_pipeline.yaml"
    _write_yaml(approved_pipeline, pipeline)

    approval = {
        "approved": True,
        "approved_by": approved_by,
        "approved_at": _now_iso(),
        "execution_type": "dpabi_template_instance_execution",
        "instance_id": instance_id,
        "pipeline_path": str(approved_pipeline),
        "synthetic_only": True,
        "full_dpabi_execution": False,
        "dparsf_run_called": False,
        "dparsfa_run_called": False,
        "dpabi_gui_called": False,
        "rawdata_modified": False,
        "files_deleted": False,
    }

    approval_path = instance_dir / "approval.json"
    approval_path.write_text(
        json.dumps(approval, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    try:
        from src.backend.app.runtime.pipeline_executor import run_pipeline

        summary = run_pipeline(
            project_config=Path(project_config_path),
            pipeline=approved_pipeline,
        )
    except Exception as exc:
        return {
            "ok": False,
            "errors": [f"Pipeline execution failed: {exc}"],
            "warnings": [],
        }

    execution_summary = {
        "ok": summary.get("status") == "SUCCESS",
        "instance_id": instance_id,
        "run_id": summary.get("run_id"),
        "status": summary.get("status"),
        "completed_at": _now_iso(),
        "approved_by": approved_by,
        "synthetic_only": True,
        "outputs": summary.get("outputs", []),
        "metrics": summary.get("metrics", {}),
    }

    summary_path = instance_dir / "execution_summary.json"
    summary_path.write_text(
        json.dumps(execution_summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {
        "ok": execution_summary["ok"],
        "mode": "EXECUTE",
        "instance_id": instance_id,
        "run_id": summary.get("run_id"),
        "status": summary.get("status"),
        "outputs": [str(approval_path), str(summary_path)],
        "execution_summary": execution_summary,
        "warnings": [],
        "errors": [],
    }
