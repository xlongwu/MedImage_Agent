"""Project-scoped reviewed plan and execution history APIs."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.backend.app.planner.reviewed_plan_store import (
    ReviewedPlanStoreError,
    artifact_warnings,
    save_reviewed_plan,
    snapshot_warnings,
)
from src.backend.app.schemas.desktop import ProjectDetail, ReviewedPlanRecord, RunLinkRecord
from src.backend.app.services.mock_store import mock_store
from src.backend.app.services.run_artifact_discovery import (
    discover_run_artifacts,
    find_run_artifact,
)
from src.backend.app.services.run_artifact_preview import artifact_preview_payload
from src.backend.app.tools.artifact_utils import is_safe_artifact_id, read_json_artifact

router = APIRouter()
RAW_SUMMARY_MAX_CHARS = 20_000
SUMMARY_WARNING_LIMIT = 50
OUTPUT_ITEM_LIMIT = 50


class ReviewedPlanSaveRequest(BaseModel):
    plan: dict[str, Any]
    project_config_path: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)
    goal: str | None = None
    provider: str | None = None
    status: str = "REVIEWED"
    warnings: list[str] = Field(default_factory=list)


def _ensure_project(project_id: str) -> None:
    if mock_store.get_project(project_id) is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")


def _get_project(project_id: str) -> ProjectDetail:
    project = mock_store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
    return project


def _reviewed_plan_payload(record: ReviewedPlanRecord) -> dict[str, Any]:
    payload = record.model_dump()
    payload["warnings"] = snapshot_warnings(record)
    return payload


def _run_link_payload(record: RunLinkRecord) -> dict[str, Any]:
    payload = record.model_dump()
    payload["warnings"] = artifact_warnings(record)
    return payload


def _dedupe(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(message for message in messages if message))


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value] if value else []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, str) and item]
    return []


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _relative_to_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def _project_summary_roots(project: ProjectDetail, record: RunLinkRecord) -> list[Path]:
    roots: list[Path] = []
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    candidates = [
        metadata.get("project_dir"),
        Path(record.project_config_path).parent if record.project_config_path else None,
    ]
    for candidate in candidates:
        if not candidate:
            continue
        base = Path(str(candidate)).expanduser().resolve()
        roots.extend(
            [
                base / "work",
                base / "reports",
                base / "logs",
                base / "derivatives",
            ]
        )
    return _dedupe_paths(roots)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    deduped: list[Path] = []
    for path in paths:
        resolved = path.resolve()
        key = str(resolved).casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(resolved)
    return deduped


def _rawdata_roots(project: ProjectDetail) -> list[Path]:
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    rawdata_dir = metadata.get("rawdata_dir")
    if not rawdata_dir:
        return []
    return [Path(str(rawdata_dir)).expanduser().resolve()]


def _resolve_summary_path(
    project: ProjectDetail,
    record: RunLinkRecord,
) -> tuple[Path | None, list[str]]:
    if not record.summary_path:
        return None, ["SUMMARY_PATH_MISSING: run link has no summary_path."]

    try:
        target = Path(record.summary_path).expanduser().resolve()
    except Exception as exc:
        return None, [f"SUMMARY_PATH_INVALID: {exc}"]

    if target.suffix.lower() != ".json":
        return None, [f"SUMMARY_PATH_REJECTED: summary_path must be a JSON file: {target}"]

    if _relative_to_any(target, _rawdata_roots(project)):
        return None, [f"SUMMARY_PATH_IN_RAWDATA_REJECTED: {target}"]

    allowed_roots = _project_summary_roots(project, record)
    if not allowed_roots or not _relative_to_any(target, allowed_roots):
        return None, [f"SUMMARY_PATH_OUTSIDE_PROJECT_OUTPUTS: {target}"]

    if not target.exists():
        return None, [f"SUMMARY_FILE_MISSING: {target}"]
    if not target.is_file():
        return None, [f"SUMMARY_PATH_NOT_FILE: {target}"]
    return target, []


def _node_results(raw: dict[str, Any]) -> list[dict[str, Any]]:
    node_results = raw.get("node_results")
    if isinstance(node_results, list):
        return [item for item in node_results if isinstance(item, dict)]
    nodes = raw.get("nodes")
    if isinstance(nodes, list):
        return [item for item in nodes if isinstance(item, dict)]
    return []


def _node_status(node: dict[str, Any]) -> str:
    status = str(node.get("status") or "").upper()
    if status:
        return status
    if node.get("ok") is True:
        return "SUCCESS"
    if node.get("ok") is False:
        return "FAILED"
    return "UNKNOWN"


def _node_id(node: dict[str, Any], index: int) -> str:
    return str(
        node.get("node_id")
        or node.get("node")
        or node.get("id")
        or node.get("name")
        or f"node_{index + 1}"
    )


def _count_nodes(raw: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, int | None]:
    statuses = [_node_status(node) for node in nodes]
    total = (
        _int_or_none(raw.get("nodes_total"))
        or _int_or_none(raw.get("node_count"))
        or (len(nodes) if nodes else _int_or_none(raw.get("nodes_count")))
    )
    succeeded = (
        _int_or_none(raw.get("nodes_succeeded"))
        if raw.get("nodes_succeeded") is not None
        else _int_or_none(raw.get("nodes_success"))
    )
    failed = _int_or_none(raw.get("nodes_failed"))
    skipped = _int_or_none(raw.get("nodes_skipped"))

    if succeeded is None and nodes:
        succeeded = sum(1 for status in statuses if status in {"SUCCESS", "COMPLETED", "PASS", "PASSED"})
    if failed is None and nodes:
        failed = sum(1 for status in statuses if status in {"FAILED", "ERROR", "FAIL"})
    if skipped is None and nodes:
        skipped = sum(1 for status in statuses if status in {"SKIPPED", "CANCELLED"})

    return {
        "nodes_total": total,
        "nodes_succeeded": succeeded,
        "nodes_failed": failed,
        "nodes_skipped": skipped,
    }


def _summary_warnings(raw: dict[str, Any], nodes: list[dict[str, Any]]) -> list[str]:
    warnings = _string_list(raw.get("warnings"))
    for index, node in enumerate(nodes):
        node_label = _node_id(node, index)
        for warning in _string_list(node.get("warnings")):
            warnings.append(f"{node_label}: {warning}")
    return _dedupe(warnings)[:SUMMARY_WARNING_LIMIT]


def _summary_errors(raw: dict[str, Any], nodes: list[dict[str, Any]]) -> list[Any]:
    errors: list[Any] = list(raw.get("errors") or []) if isinstance(raw.get("errors"), list) else []
    for index, node in enumerate(nodes):
        if _node_status(node) not in {"FAILED", "ERROR", "FAIL"}:
            continue
        node_errors = node.get("errors")
        errors.append(
            {
                "node_id": _node_id(node, index),
                "status": _node_status(node),
                "errors": node_errors if isinstance(node_errors, list) else _string_list(node_errors),
            }
        )
    return errors[:SUMMARY_WARNING_LIMIT]


def _failed_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    failed: list[dict[str, Any]] = []
    for index, node in enumerate(nodes):
        if _node_status(node) not in {"FAILED", "ERROR", "FAIL"}:
            continue
        failed.append(
            {
                "node_id": _node_id(node, index),
                "status": _node_status(node),
                "errors": _string_list(node.get("errors")),
            }
        )
    return failed[:SUMMARY_WARNING_LIMIT]


def _summary_outputs(raw: dict[str, Any], nodes: list[dict[str, Any]]) -> dict[str, Any]:
    outputs = raw.get("outputs")
    if isinstance(outputs, dict):
        return dict(list(outputs.items())[:OUTPUT_ITEM_LIMIT])
    if isinstance(outputs, list):
        return {
            "items": outputs[:OUTPUT_ITEM_LIMIT],
            "truncated": len(outputs) > OUTPUT_ITEM_LIMIT,
        }

    node_outputs: dict[str, Any] = {}
    for index, node in enumerate(nodes):
        outputs_value = node.get("outputs")
        if outputs_value:
            node_outputs[_node_id(node, index)] = outputs_value
        if len(node_outputs) >= OUTPUT_ITEM_LIMIT:
            node_outputs["truncated"] = True
            break
    if node_outputs:
        return node_outputs

    node_states = raw.get("node_states")
    if isinstance(node_states, list):
        return {
            "node_states": node_states[:OUTPUT_ITEM_LIMIT],
            "truncated": len(node_states) > OUTPUT_ITEM_LIMIT,
        }
    return {}


def _raw_preview(raw: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    encoded = json.dumps(raw, ensure_ascii=False)
    if len(encoded) <= RAW_SUMMARY_MAX_CHARS:
        return raw, False
    return (
        {
            "truncated": True,
            "size_chars": len(encoded),
            "top_level_keys": list(raw.keys())[:OUTPUT_ITEM_LIMIT],
            "note": "Raw summary exceeded preview budget and was truncated.",
        },
        True,
    )


def _build_summary_preview(raw: dict[str, Any], record: RunLinkRecord) -> dict[str, Any]:
    nodes = _node_results(raw)
    counts = _count_nodes(raw, nodes)
    raw_payload, raw_truncated = _raw_preview(raw)
    preview = {
        "run_id": raw.get("run_id") or record.run_id,
        "status": raw.get("status") or raw.get("pipeline_status") or record.status,
        "started_at": raw.get("started_at") or raw.get("start_time"),
        "finished_at": raw.get("finished_at") or raw.get("ended_at") or raw.get("end_time"),
        **counts,
        "warnings": _summary_warnings(raw, nodes),
        "outputs": _summary_outputs(raw, nodes),
        "errors": _summary_errors(raw, nodes),
        "failed_nodes": _failed_nodes(nodes),
        "raw": raw_payload,
        "raw_truncated": raw_truncated,
    }
    return preview


def _load_summary_preview(
    project: ProjectDetail,
    record: RunLinkRecord,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    target, warnings = _resolve_summary_path(project, record)
    if warnings:
        return None, warnings, None
    assert target is not None

    try:
        raw = read_json_artifact(target)
    except JSONDecodeError as exc:
        return None, [], f"SUMMARY_JSON_INVALID: {target}: {exc.msg}"
    except Exception as exc:
        return None, [], f"SUMMARY_READ_FAILED: {target}: {exc}"

    if not isinstance(raw, dict):
        return None, [], f"SUMMARY_JSON_INVALID: {target}: top-level JSON value must be an object"
    return _build_summary_preview(raw, record), [], None


@router.post("/api/projects/{project_id}/plans")
def save_project_reviewed_plan(
    project_id: str,
    request: ReviewedPlanSaveRequest,
) -> dict[str, Any]:
    _ensure_project(project_id)
    try:
        record = save_reviewed_plan(
            project_id=project_id,
            project_config_path=request.project_config_path,
            plan=request.plan,
            validation=request.validation,
            goal=request.goal,
            provider=request.provider,
            status=request.status,
            warnings=request.warnings,
        )
    except ReviewedPlanStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"ok": True, "reviewed_plan": _reviewed_plan_payload(record)}


@router.get("/api/projects/{project_id}/plans")
def list_project_reviewed_plans(project_id: str) -> dict[str, Any]:
    _ensure_project(project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "reviewed_plans": [
            _reviewed_plan_payload(record)
            for record in mock_store.list_reviewed_plans(project_id)
        ],
    }


@router.get("/api/projects/{project_id}/plans/{reviewed_plan_id}")
def get_project_reviewed_plan(
    project_id: str,
    reviewed_plan_id: str,
) -> dict[str, Any]:
    _ensure_project(project_id)
    record = mock_store.get_reviewed_plan(reviewed_plan_id)
    if record is None or record.project_id != project_id:
        raise HTTPException(status_code=404, detail="Reviewed plan not found")
    return {"ok": True, "reviewed_plan": _reviewed_plan_payload(record)}


@router.get("/api/projects/{project_id}/runs")
def list_project_run_links(
    project_id: str,
    reviewed_plan_id: str | None = Query(default=None),
) -> dict[str, Any]:
    _ensure_project(project_id)
    return {
        "ok": True,
        "project_id": project_id,
        "runs": [
            _run_link_payload(record)
            for record in mock_store.list_run_links(project_id, reviewed_plan_id)
        ],
    }


@router.get("/api/projects/{project_id}/runs/{run_id}")
def get_project_run_link(project_id: str, run_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    run_link = _run_link_payload(record)
    summary_preview, summary_warnings, summary_error = _load_summary_preview(
        project,
        record,
    )
    warnings = _dedupe(
        [
            *run_link.get("warnings", []),
            *summary_warnings,
            *([summary_error] if summary_error else []),
        ]
    )
    return {
        "ok": True,
        "run_link": run_link,
        "summary_preview": summary_preview,
        "summary_preview_error": summary_error,
        "warnings": warnings,
    }


@router.get("/api/projects/{project_id}/runs/{run_id}/artifacts")
def list_project_run_artifacts(project_id: str, run_id: str) -> dict[str, Any]:
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    artifacts, warnings = discover_run_artifacts(project, record)
    return {
        "ok": True,
        "project_id": project_id,
        "run_id": run_id,
        "artifacts": artifacts,
        "warnings": warnings,
    }


@router.get("/api/projects/{project_id}/runs/{run_id}/artifacts/{artifact_id}")
def get_project_run_artifact(
    project_id: str,
    run_id: str,
    artifact_id: str,
) -> dict[str, Any]:
    if not is_safe_artifact_id(artifact_id):
        raise HTTPException(status_code=400, detail="Invalid artifact_id")
    project = _get_project(project_id)
    record = mock_store.get_run_link_by_run_id(project_id, run_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Run link not found")
    artifact, warnings = find_run_artifact(project, record, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found for run")
    payload = artifact_preview_payload(artifact)
    payload["project_id"] = project_id
    payload["run_id"] = run_id
    payload["warnings"] = _dedupe([*warnings, *payload.get("warnings", [])])
    return payload
