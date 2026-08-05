"""Pure run artifact preview helpers."""

from __future__ import annotations

import csv
import io
import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

OUTPUT_ITEM_LIMIT = 50
ARTIFACT_PREVIEW_MAX_BYTES = 80_000
ARTIFACT_CSV_MAX_LINES = 100
ARTIFACT_CSV_MAX_COLUMNS = 50
ARTIFACT_CSV_MAX_RAW_BYTES = 5 * 1024 * 1024  # 5 MB memory guard for CSV parsing


def _dedupe(messages: list[str]) -> list[str]:
    return list(dict.fromkeys(message for message in messages if message))


def _read_preview_bytes(path: Path) -> tuple[bytes, bool]:
    with path.open("rb") as handle:
        raw = handle.read(ARTIFACT_PREVIEW_MAX_BYTES + 1)
    return raw[:ARTIFACT_PREVIEW_MAX_BYTES], len(raw) > ARTIFACT_PREVIEW_MAX_BYTES


def _json_value_type(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
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
        if isinstance(candidate, str | int | float | bool) or candidate is None:
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


def _csv_preview_from_text(text: str, truncated: bool, raw_bytes: int = 0) -> dict[str, Any]:
    # Memory guard: refuse to parse very large CSV in memory
    if raw_bytes > ARTIFACT_CSV_MAX_RAW_BYTES:
        lines = text.splitlines()
        head_lines = lines[:ARTIFACT_CSV_MAX_LINES]
        head_text = "\n".join(head_lines)
        parsed_rows = [
            row
            for row in csv.reader(io.StringIO(head_text))
            if any(cell != "" for cell in row)
        ]
    else:
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
    raw_bytes = len(raw)
    parsed_json = None
    csv_preview = None

    if kind == "json":
        if truncated:
            warnings.append(f"ARTIFACT_PREVIEW_TRUNCATED: {path}")
            return text, None, None, True, warnings, errors
        try:
            parsed_json = json.loads(text)
        except JSONDecodeError as exc:
            # Malformed JSON: return raw text so the frontend can still show
            # a bounded preview rather than nothing.
            errors.append(f"ARTIFACT_JSON_INVALID: {path}: {exc.msg}")
            return text, None, None, False, warnings, errors
    elif kind == "csv":
        lines = text.splitlines()
        if len(lines) > ARTIFACT_CSV_MAX_LINES:
            text = "\n".join(lines[:ARTIFACT_CSV_MAX_LINES])
            truncated = True
        try:
            csv_preview = _csv_preview_from_text(text, truncated, raw_bytes)
        except csv.Error as exc:
            errors.append(f"ARTIFACT_CSV_INVALID: {path}: {exc}")
            # Return raw text as fallback
            return text, None, None, truncated, warnings, errors
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
            "preview_type": "missing",
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
        # Map TSV to CSV preview; all others fall through.
        effective_kind = "csv" if kind == "tsv" else kind
        preview_type = {
            "json": "json",
            "csv": "csv",
            "markdown": "markdown",
            "log": "log",
        }.get(effective_kind, "text")
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


def json_preview_summary(value: Any) -> dict[str, Any]:
    return _json_preview_summary(value)


def artifact_preview_payload(artifact: dict[str, Any]) -> dict[str, Any]:
    return _artifact_preview_payload(artifact)
