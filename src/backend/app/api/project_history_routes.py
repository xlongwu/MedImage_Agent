"""Project-scoped reviewed plan and execution history APIs."""

from __future__ import annotations

import csv
import io
import json
from json import JSONDecodeError
import hashlib
from datetime import datetime, timezone
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
from src.backend.app.tools.artifact_utils import is_safe_artifact_id, read_json_artifact

router = APIRouter()
RAW_SUMMARY_MAX_CHARS = 20_000
SUMMARY_WARNING_LIMIT = 50
OUTPUT_ITEM_LIMIT = 50
ARTIFACT_PREVIEW_MAX_BYTES = 80_000
ARTIFACT_CSV_MAX_LINES = 100
ARTIFACT_CSV_MAX_COLUMNS = 50
ARTIFACT_ERROR_EXCERPT_MAX_CHARS = 1_200
ARTIFACT_QC_METRIC_LIMIT = 12
PREVIEWABLE_SUFFIXES = {".json", ".txt", ".md", ".csv", ".log"}
PATH_SUFFIXES = {
    ".json",
    ".txt",
    ".md",
    ".csv",
    ".log",
    ".yaml",
    ".yml",
    ".html",
    ".nii",
    ".nii.gz",
    ".mat",
    ".png",
    ".jpg",
    ".jpeg",
}


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


def _project_artifact_roots(project: ProjectDetail, record: RunLinkRecord) -> list[Path]:
    roots = _project_summary_roots(project, record)
    if record.pipeline_path:
        try:
            roots.append(Path(record.pipeline_path).expanduser().resolve().parent)
        except Exception:
            pass
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


def _path_suffix(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return path.suffix.lower()


def _artifact_kind(path: Path) -> str:
    suffix = _path_suffix(path)
    if suffix == ".json":
        return "json"
    if suffix == ".md":
        return "markdown"
    if suffix == ".csv":
        return "csv"
    if suffix == ".log":
        return "log"
    if suffix == ".txt":
        return "text"
    if suffix in {".yaml", ".yml"}:
        return "yaml"
    if suffix in {".png", ".jpg", ".jpeg"}:
        return "image"
    if suffix == ".nii.gz" or suffix == ".nii":
        return "nifti"
    if suffix == ".mat":
        return "matlab"
    return "binary"


def _is_previewable(path: Path) -> bool:
    return _path_suffix(path) in PREVIEWABLE_SUFFIXES


def _artifact_id_for(path: Path) -> str:
    return f"artifact_{hashlib.sha256(str(path).casefold().encode('utf-8')).hexdigest()[:16]}"


def _modified_at(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return datetime.fromtimestamp(
        path.stat().st_mtime,
        timezone.utc,
    ).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative_artifact_path(path: Path, project: ProjectDetail, roots: list[Path]) -> str:
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    project_dir = metadata.get("project_dir")
    if project_dir:
        try:
            return str(path.relative_to(Path(str(project_dir)).expanduser().resolve()))
        except ValueError:
            pass
    for root in roots:
        try:
            return str(path.relative_to(root))
        except ValueError:
            continue
    return path.name


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


def _load_summary_raw(
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
    return raw, [], None


def _looks_like_artifact_path(value: str) -> bool:
    if not value or "\n" in value or "\r" in value:
        return False
    path = Path(value)
    if _path_suffix(path) in PATH_SUFFIXES:
        return True
    normalized = value.replace("\\", "/")
    return any(part in normalized for part in ("/reports/", "/work/", "/logs/", "/derivatives/"))


def _collect_path_candidates(value: Any) -> list[str]:
    candidates: list[str] = []
    if isinstance(value, str):
        if _looks_like_artifact_path(value):
            candidates.append(value)
        return candidates
    if isinstance(value, list):
        for item in value:
            candidates.extend(_collect_path_candidates(item))
        return candidates
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key).lower()
            if isinstance(item, str) and (
                key_text.endswith("path")
                or key_text.endswith("_path")
                or key_text.endswith("log")
                or key_text in {"outputs", "artifacts"}
                or _looks_like_artifact_path(item)
            ):
                candidates.append(item)
            else:
                candidates.extend(_collect_path_candidates(item))
    return candidates


def _resolve_candidate_path(
    raw_path: str,
    project: ProjectDetail,
    record: RunLinkRecord,
    *,
    base_dirs: list[Path],
) -> tuple[Path | None, str | None]:
    try:
        candidate = Path(raw_path).expanduser()
    except Exception as exc:
        return None, f"ARTIFACT_PATH_INVALID: {raw_path}: {exc}"

    resolved_candidates: list[Path] = []
    if candidate.is_absolute():
        resolved_candidates.append(candidate.resolve())
    else:
        for base_dir in base_dirs:
            resolved_candidates.append((base_dir / candidate).resolve())

    allowed_roots = _project_artifact_roots(project, record)
    rawdata_roots = _rawdata_roots(project)
    last_reason = "ARTIFACT_PATH_OUTSIDE_PROJECT_OUTPUTS"
    for target in _dedupe_paths(resolved_candidates):
        if _relative_to_any(target, rawdata_roots):
            return None, f"ARTIFACT_PATH_IN_RAWDATA_REJECTED: {target}"
        if not allowed_roots or not _relative_to_any(target, allowed_roots):
            last_reason = f"ARTIFACT_PATH_OUTSIDE_PROJECT_OUTPUTS: {target}"
            continue
        return target, None
    return None, last_reason


def _node_id_from_source(source: str, path: Path) -> str | None:
    if source.startswith("node_state:"):
        return source.removeprefix("node_state:").removesuffix(".json") or None
    normalized = str(path).replace("\\", "/")
    parts = normalized.split("/")
    if "states" in parts:
        index = parts.index("states")
        if len(parts) > index + 2:
            return Path(parts[index + 2]).stem
    return None


def _artifact_text_for_matching(path: Path, source: str) -> str:
    return f"{path.name} {path} {source}".replace("\\", "/").lower()


def _looks_like_qc_json_artifact(path: Path, source: str) -> bool:
    text = _artifact_text_for_matching(path, source)
    return any(
        token in text
        for token in ("qc", "quality", "motion", "mean_fd", "fd_", "metrics")
    )


def _json_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        return text if text else None
    return None


def _first_scalar_field(value: Any, keys: tuple[str, ...], depth: int = 0) -> str | None:
    if depth > 3:
        return None
    if isinstance(value, dict):
        for key in keys:
            scalar = _json_scalar(value.get(key))
            if scalar:
                return scalar
        for item in value.values():
            found = _first_scalar_field(item, keys, depth + 1)
            if found:
                return found
    elif isinstance(value, list):
        for item in value[:10]:
            found = _first_scalar_field(item, keys, depth + 1)
            if found:
                return found
    return None


def _message_list(value: Any) -> list[str]:
    if value is None:
        return []
    items = value if isinstance(value, list) else [value]
    messages: list[str] = []
    for item in items[:10]:
        if isinstance(item, str):
            if item:
                messages.append(item)
        elif isinstance(item, (int, float, bool)):
            messages.append(str(item))
        elif isinstance(item, dict):
            message = _first_scalar_field(
                item,
                ("message", "error_message", "error", "reason", "detail"),
            )
            if message:
                messages.append(message)
            else:
                messages.append(_json_message_sample(item))
    return messages


def _bool_or_none(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "yes", "1", "pass", "passed", "success", "ok"}:
            return True
        if normalized in {"false", "no", "0", "fail", "failed", "error"}:
            return False
    return None


def _status_booleans(status: Any) -> tuple[bool | None, bool | None]:
    normalized = str(status or "").strip().upper()
    if normalized in {"PASS", "PASSED", "SUCCESS", "OK", "TRUE"}:
        return True, False
    if normalized in {"FAIL", "FAILED", "ERROR", "FALSE"}:
        return False, True
    return None, None


def _metric_rows_from_value(value: Any) -> list[dict[str, str]]:
    metrics: list[dict[str, str]] = []
    if isinstance(value, dict):
        iterable = value.items()
    elif isinstance(value, list):
        iterable = []
        for item in value:
            if isinstance(item, dict):
                label = _first_scalar_field(item, ("label", "name", "key", "metric"))
                metric_value = _first_scalar_field(item, ("value", "score", "result"))
                if label and metric_value:
                    metrics.append({"label": label, "value": metric_value})
                if len(metrics) >= ARTIFACT_QC_METRIC_LIMIT:
                    return metrics
        return metrics
    else:
        return metrics

    for key, item in iterable:
        scalar = _json_scalar(item)
        if scalar:
            metrics.append({"label": str(key), "value": scalar})
        if len(metrics) >= ARTIFACT_QC_METRIC_LIMIT:
            break
    return metrics


def _metric_rows_from_payload(payload: Any) -> list[dict[str, str]]:
    if not isinstance(payload, dict):
        return []
    metrics = _metric_rows_from_value(payload.get("metrics"))
    if metrics:
        return metrics
    metric_tokens = ("metric", "mean", "fd", "dvars", "snr", "tsnr", "motion")
    derived: dict[str, Any] = {}
    for key, value in payload.items():
        key_text = str(key).lower()
        if any(token in key_text for token in metric_tokens):
            derived[str(key)] = value
    return _metric_rows_from_value(derived)


def _qc_summary_from_json(payload: Any) -> dict[str, Any]:
    status = _json_status_value(payload)
    passed_from_status, failed_from_status = _status_booleans(status)
    passed = passed_from_status
    failed = failed_from_status
    if isinstance(payload, dict):
        passed = (
            _bool_or_none(payload.get("passed"))
            if payload.get("passed") is not None
            else _bool_or_none(payload.get("ok"))
        )
        if passed is None:
            passed = passed_from_status
        failed = _bool_or_none(payload.get("failed"))
        if failed is None:
            failed = failed_from_status

    warnings = _message_list(payload.get("warnings")) if isinstance(payload, dict) else []
    errors = _message_list(payload.get("errors")) if isinstance(payload, dict) else []
    error_message = (
        _first_scalar_field(payload, ("error_message", "error", "message"))
        or (errors[0] if errors else None)
    )
    return {
        "status": status,
        "passed": passed,
        "failed": failed,
        "warnings": warnings[:5],
        "metrics": _metric_rows_from_payload(payload),
        "subject_id": _first_scalar_field(payload, ("subject_id", "subject")),
        "node_id": _first_scalar_field(payload, ("node_id", "node")),
        "error_message": error_message,
    }


def _enrich_qc_json_artifact(
    artifact: dict[str, Any],
    path: Path,
    source: str,
    warnings: list[str],
) -> None:
    if artifact["kind"] != "json" or not artifact["exists"] or not _looks_like_qc_json_artifact(path, source):
        return
    size_bytes = artifact.get("size_bytes")
    if not isinstance(size_bytes, int) or size_bytes > ARTIFACT_PREVIEW_MAX_BYTES:
        artifact["qc_summary"] = {"truncated": True}
        return
    try:
        payload = read_json_artifact(path)
    except JSONDecodeError as exc:
        warnings.append(f"ARTIFACT_JSON_INVALID: {path}: {exc.msg}")
        return
    except Exception as exc:
        warnings.append(f"ARTIFACT_QC_SUMMARY_READ_FAILED: {path}: {exc}")
        return
    json_summary = _json_preview_summary(payload)
    artifact["json_summary"] = json_summary
    qc_summary = _qc_summary_from_json(payload)
    qc_summary["json_summary"] = json_summary
    artifact["qc_summary"] = qc_summary


def _error_excerpt_for_artifact(path: Path, kind: str) -> str | None:
    if kind not in {"log", "text"} or not path.exists() or not path.is_file():
        return None
    raw, truncated = _read_preview_bytes(path)
    text = raw.decode("utf-8", errors="replace")
    lines = [line.rstrip() for line in text.splitlines() if line.strip()]
    if not lines:
        return None
    interesting_index = next(
        (
            index
            for index, line in enumerate(lines)
            if any(token in line.lower() for token in ("error", "failed", "traceback", "stderr"))
        ),
        0,
    )
    excerpt = "\n".join(lines[interesting_index : interesting_index + 8])
    if truncated or len(excerpt) > ARTIFACT_ERROR_EXCERPT_MAX_CHARS:
        excerpt = excerpt[:ARTIFACT_ERROR_EXCERPT_MAX_CHARS].rstrip() + "..."
    return excerpt


def _artifact_record(
    path: Path,
    project: ProjectDetail,
    record: RunLinkRecord,
    source: str,
) -> dict[str, Any]:
    roots = _project_artifact_roots(project, record)
    exists = path.exists() and path.is_file()
    warnings: list[str] = []
    if not exists:
        warnings.append(f"ARTIFACT_FILE_MISSING: {path}")
    suffix = _path_suffix(path)
    artifact = {
        "artifact_id": _artifact_id_for(path),
        "name": path.name,
        "kind": _artifact_kind(path),
        "path": str(path),
        "relative_path": _relative_artifact_path(path, project, roots),
        "exists": exists,
        "size_bytes": int(path.stat().st_size) if exists else None,
        "modified_at": _modified_at(path),
        "previewable": exists and _is_previewable(path),
        "warnings": warnings,
        "source": source,
        "suffix": suffix,
    }
    node_id = _node_id_from_source(source, path)
    if node_id:
        artifact["node_id"] = node_id
    _enrich_qc_json_artifact(artifact, path, source, warnings)
    error_excerpt = _error_excerpt_for_artifact(path, str(artifact["kind"]))
    if error_excerpt:
        artifact["error_excerpt"] = error_excerpt
    return artifact


def _read_node_state_candidates(
    path: Path,
    project: ProjectDetail,
    record: RunLinkRecord,
) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    if not path.exists() or not path.is_file() or _path_suffix(path) != ".json":
        return [], warnings
    try:
        payload = read_json_artifact(path)
    except Exception as exc:
        warnings.append(f"NODE_STATE_READ_FAILED: {path}: {exc}")
        return [], warnings
    if not isinstance(payload, dict):
        return [], warnings
    candidates: list[str] = []
    for key in ("outputs", "stdout_log", "stderr_log", "log_path", "result_json"):
        candidates.extend(_collect_path_candidates(payload.get(key)))
    return candidates, warnings


def _discover_run_artifacts(
    project: ProjectDetail,
    record: RunLinkRecord,
) -> tuple[list[dict[str, Any]], list[str]]:
    warnings: list[str] = []
    summary_raw, summary_warnings, summary_error = _load_summary_raw(project, record)
    warnings.extend(summary_warnings)
    if summary_error:
        warnings.append(summary_error)

    base_dirs: list[Path] = []
    metadata = project.metadata if isinstance(project.metadata, dict) else {}
    if metadata.get("project_dir"):
        base_dirs.append(Path(str(metadata["project_dir"])).expanduser().resolve())
    if record.summary_path:
        try:
            base_dirs.append(Path(record.summary_path).expanduser().resolve().parent)
        except Exception:
            pass
    if record.project_config_path:
        base_dirs.append(Path(record.project_config_path).expanduser().resolve().parent)
    base_dirs = _dedupe_paths(base_dirs or [Path.cwd().resolve()])

    raw_candidates: list[tuple[str, str]] = []
    if record.pipeline_path:
        raw_candidates.append((record.pipeline_path, "run_link.pipeline_path"))
    if record.summary_path:
        raw_candidates.append((record.summary_path, "run_link.summary_path"))

    if summary_raw:
        for key in ("outputs", "artifacts", "reports", "report_paths", "node_states"):
            for candidate in _collect_path_candidates(summary_raw.get(key)):
                raw_candidates.append((candidate, f"summary.{key}"))
        for index, node in enumerate(_node_results(summary_raw)):
            for candidate in _collect_path_candidates(node):
                raw_candidates.append((candidate, f"summary.node_results[{index}]"))

    discovered_paths: dict[str, dict[str, Any]] = {}
    node_state_paths: list[Path] = []
    for raw_path, source in raw_candidates:
        resolved, warning = _resolve_candidate_path(
            raw_path,
            project,
            record,
            base_dirs=base_dirs,
        )
        if warning:
            warnings.append(warning)
            continue
        assert resolved is not None
        artifact = _artifact_record(resolved, project, record, source)
        discovered_paths.setdefault(str(resolved).casefold(), artifact)
        if source.endswith("node_states") or "/states/" in str(resolved).replace("\\", "/"):
            node_state_paths.append(resolved)

    for node_state_path in _dedupe_paths(node_state_paths):
        state_candidates, state_warnings = _read_node_state_candidates(
            node_state_path,
            project,
            record,
        )
        warnings.extend(state_warnings)
        state_base_dirs = _dedupe_paths([node_state_path.parent, *base_dirs])
        for raw_path in state_candidates:
            resolved, warning = _resolve_candidate_path(
                raw_path,
                project,
                record,
                base_dirs=state_base_dirs,
            )
            if warning:
                warnings.append(warning)
                continue
            assert resolved is not None
            artifact = _artifact_record(
                resolved,
                project,
                record,
                f"node_state:{node_state_path.name}",
            )
            discovered_paths.setdefault(str(resolved).casefold(), artifact)

    artifacts = sorted(
        discovered_paths.values(),
        key=lambda item: (
            not bool(item.get("exists")),
            str(item.get("kind") or ""),
            str(item.get("relative_path") or ""),
        ),
    )
    return artifacts, _dedupe(warnings)


def _find_run_artifact(
    project: ProjectDetail,
    record: RunLinkRecord,
    artifact_id: str,
) -> tuple[dict[str, Any] | None, list[str]]:
    artifacts, warnings = _discover_run_artifacts(project, record)
    for artifact in artifacts:
        if artifact.get("artifact_id") == artifact_id:
            return artifact, warnings
    return None, warnings


def _read_preview_bytes(path: Path) -> tuple[bytes, bool]:
    with path.open("rb") as handle:
        raw = handle.read(ARTIFACT_PREVIEW_MAX_BYTES + 1)
    return raw[:ARTIFACT_PREVIEW_MAX_BYTES], len(raw) > ARTIFACT_PREVIEW_MAX_BYTES


def _json_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _json_value_shape(value: Any) -> dict[str, Any]:
    shape: dict[str, Any] = {"type": _json_value_type(value)}
    if isinstance(value, dict):
        shape["size"] = len(value)
        shape["keys"] = [str(key) for key in list(value.keys())[:10]]
    elif isinstance(value, list):
        sample_types: list[str] = []
        for item in value[:10]:
            item_type = _json_value_type(item)
            if item_type not in sample_types:
                sample_types.append(item_type)
        shape["size"] = len(value)
        shape["sample_types"] = sample_types
    elif isinstance(value, str):
        shape["size"] = len(value)
    return shape


def _json_message_sample(value: Any) -> str:
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        return str(value)


def _json_message_summary(value: Any) -> dict[str, Any]:
    if value is None:
        items: list[Any] = []
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    return {
        "count": len(items),
        "sample": [_json_message_sample(item) for item in items[:5]],
    }


def _json_status_value(value: Any) -> Any:
    if not isinstance(value, dict):
        return None
    for key in ("status", "pipeline_status", "ok", "success"):
        candidate = value.get(key)
        if isinstance(candidate, (str, int, float, bool)) or candidate is None:
            return candidate
    return None


def _json_preview_summary(value: Any) -> dict[str, Any]:
    root_shape = _json_value_shape(value)
    summary: dict[str, Any] = {
        "type": root_shape["type"],
        "size": root_shape.get("size"),
        "top_level_keys": [],
        "status": None,
        "warnings": {"count": 0, "sample": []},
        "errors": {"count": 0, "sample": []},
        "field_summaries": [],
    }

    if isinstance(value, dict):
        keys = list(value.keys())
        summary["top_level_keys"] = [str(key) for key in keys[:OUTPUT_ITEM_LIMIT]]
        summary["status"] = _json_status_value(value)
        summary["warnings"] = _json_message_summary(value.get("warnings"))
        summary["errors"] = _json_message_summary(value.get("errors"))
        summary["field_summaries"] = [
            {"key": str(key), **_json_value_shape(value[key])}
            for key in keys[:OUTPUT_ITEM_LIMIT]
        ]
    elif isinstance(value, list):
        summary["field_summaries"] = [
            {"key": f"[{index}]", **_json_value_shape(item)}
            for index, item in enumerate(value[:10])
        ]
    return summary


def _normalize_csv_row(row: list[str], width: int) -> list[str]:
    return [row[index] if index < len(row) else "" for index in range(width)]


def _csv_preview_from_text(text: str, truncated: bool) -> dict[str, Any]:
    parsed_rows = [
        row
        for row in csv.reader(io.StringIO(text))
        if any(cell != "" for cell in row)
    ]
    if not parsed_rows:
        return {
            "columns": [],
            "rows": [],
            "row_count": 0,
            "displayed_rows": 0,
            "truncated": truncated,
            "columns_truncated": False,
        }

    detected_width = max(len(row) for row in parsed_rows)
    width = min(detected_width, ARTIFACT_CSV_MAX_COLUMNS)
    header = _normalize_csv_row(parsed_rows[0], width)
    columns = [
        cell.strip() if cell.strip() else f"column_{index + 1}"
        for index, cell in enumerate(header)
    ]
    rows = [_normalize_csv_row(row, width) for row in parsed_rows[1:]]
    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "displayed_rows": len(rows),
        "truncated": truncated,
        "columns_truncated": detected_width > ARTIFACT_CSV_MAX_COLUMNS,
    }


def _preview_text_artifact(
    path: Path,
    kind: str,
) -> tuple[str, Any, dict[str, Any] | None, bool, list[str], list[str]]:
    warnings: list[str] = []
    errors: list[str] = []
    raw, truncated = _read_preview_bytes(path)
    text = raw.decode("utf-8", errors="replace")
    parsed_json = None
    csv_preview = None

    if kind == "json":
        if truncated:
            warnings.append(f"ARTIFACT_PREVIEW_TRUNCATED: {path}")
            return text, None, None, True, warnings, errors
        try:
            parsed_json = json.loads(text)
        except JSONDecodeError as exc:
            errors.append(f"ARTIFACT_JSON_INVALID: {path}: {exc.msg}")
            return "", None, None, False, warnings, errors
    elif kind == "csv":
        lines = text.splitlines()
        if len(lines) > ARTIFACT_CSV_MAX_LINES:
            text = "\n".join(lines[:ARTIFACT_CSV_MAX_LINES])
            truncated = True
        try:
            csv_preview = _csv_preview_from_text(text, truncated)
        except csv.Error as exc:
            errors.append(f"ARTIFACT_CSV_INVALID: {path}: {exc}")
        if csv_preview and csv_preview.get("columns_truncated"):
            warnings.append(f"ARTIFACT_CSV_COLUMNS_TRUNCATED: {path}")

    if truncated:
        warnings.append(f"ARTIFACT_PREVIEW_TRUNCATED: {path}")
    return text, parsed_json, csv_preview, truncated, warnings, errors


def _artifact_preview_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    path = Path(str(artifact["path"]))
    warnings = list(artifact.get("warnings", []))
    errors: list[str] = []
    preview_type = "metadata_only"
    content = None
    parsed_json = None
    json_summary = None
    csv_preview = None
    truncated = False

    if not artifact.get("exists"):
        return {
            "ok": True,
            "artifact_id": artifact["artifact_id"],
            "artifact": artifact,
            "kind": artifact["kind"],
            "path": artifact["path"],
            "exists": False,
            "preview_type": preview_type,
            "content": None,
            "json": None,
            "json_summary": None,
            "csv": None,
            "truncated": False,
            "warnings": warnings,
            "errors": errors,
        }

    if not artifact.get("previewable"):
        warnings.append(f"ARTIFACT_NOT_PREVIEWABLE: {path}")
    else:
        kind = str(artifact.get("kind") or "text")
        preview_type = {
            "json": "json",
            "csv": "csv",
            "markdown": "markdown",
            "log": "log",
        }.get(kind, "text")
        content, parsed_json, csv_preview, truncated, preview_warnings, preview_errors = _preview_text_artifact(
            path,
            kind,
        )
        if parsed_json is not None:
            json_summary = _json_preview_summary(parsed_json)
        warnings.extend(preview_warnings)
        errors.extend(preview_errors)

    return {
        "ok": not errors,
        "artifact_id": artifact["artifact_id"],
        "artifact": artifact,
        "kind": artifact["kind"],
        "path": artifact["path"],
        "exists": artifact.get("exists", False),
        "preview_type": preview_type,
        "content": content,
        "json": parsed_json,
        "json_summary": json_summary,
        "csv": csv_preview,
        "truncated": truncated,
        "warnings": _dedupe(warnings),
        "errors": _dedupe(errors),
    }


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
    artifacts, warnings = _discover_run_artifacts(project, record)
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
    artifact, warnings = _find_run_artifact(project, record, artifact_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail="Artifact not found for run")
    payload = _artifact_preview_payload(artifact)
    payload["project_id"] = project_id
    payload["run_id"] = run_id
    payload["warnings"] = _dedupe([*warnings, *payload.get("warnings", [])])
    return payload
