"""Read-only run event and log helpers for project history APIs.

These helpers are pure read-only — they never modify state, change
executor behaviour, or write files.  They synthesise events from
existing run data and read bounded previews of discovered log files.
"""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import ProjectDetail, RunLinkRecord
from src.backend.app.services.run_artifact_discovery import discover_run_artifacts
from src.backend.app.services.run_summary_preview import (
    load_run_summary_preview,
    resolve_run_summary_path,
)
from src.backend.app.tools.artifact_utils import read_json_artifact


DEFAULT_MAX_BYTES = 20_000
MIN_MAX_BYTES = 1_000
MAX_MAX_BYTES = 200_000
CONTENT_PREVIEW_MAX_BYTES = MAX_MAX_BYTES


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


def _safe_utf8_read(path: Path, max_bytes: int) -> tuple[str, bool]:
    """Read up to *max_bytes* bytes, decode as UTF-8 with replacement."""
    try:
        with path.open("rb") as handle:
            raw = handle.read(max_bytes + 1)
    except (OSError, PermissionError) as exc:
        raise exc
    truncated = len(raw) > max_bytes
    content_bytes = raw[:max_bytes]
    try:
        text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = content_bytes.decode("utf-8", errors="replace")
    return text, truncated


def _file_metadata(path: Path) -> dict[str, Any]:
    try:
        stat = path.stat()
    except (OSError, PermissionError):
        return {"exists": False, "size_bytes": None, "modified_at": None}
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "modified_at": (
            None
            if stat.st_mtime == 0
            else __import__("datetime")
            .datetime.fromtimestamp(stat.st_mtime)
            .isoformat()
        ),
    }


def _is_log_like_artifact(artifact: dict[str, Any]) -> bool:
    """Check whether an artifact record looks like a log file."""
    kind = str(artifact.get("kind") or "").lower()
    if kind == "log":
        return True
    name = str(artifact.get("name") or "").lower()
    suffix = str(artifact.get("suffix") or "").lower()
    if suffix == ".log":
        return True
    log_keywords = ("stdout", "stderr", "log", ".log")
    if any(kw in name for kw in log_keywords):
        return True
    return False


# ── Event discovery ──────────────────────────────────────────────────────────

def discover_run_events(
    project: ProjectDetail,
    record: RunLinkRecord,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Synthesise an ordered list of run events from existing sources."""

    events: list[dict[str, Any]] = []
    warnings: list[str] = []

    # ── 1. Run link events ──
    events.append(
        {
            "timestamp": record.created_at,
            "level": "info",
            "source": "run_link",
            "message": f"Run link created with status {record.status}.",
            "node_id": None,
            "subject_id": None,
            "path": record.pipeline_path,
            "metadata": {"run_link_id": record.run_link_id, "run_id": record.run_id},
        }
    )
    if record.status not in ("REQUESTED",):
        events.append(
            {
                "timestamp": record.updated_at,
                "level": "info",
                "source": "run_link",
                "message": f"Run link updated to status {record.status}.",
                "node_id": None,
                "subject_id": None,
                "path": record.summary_path,
                "metadata": {},
            }
        )

    # ── 2. Summary preview events ──
    summary, summary_warnings, summary_error = load_run_summary_preview(
        project, record,
    )
    warnings.extend(summary_warnings)
    if summary_error:
        warnings.append(summary_error)

    if summary:
        if summary.get("status"):
            events.append(
                {
                    "timestamp": summary.get("finished_at") or summary.get("started_at"),
                    "level": "info",
                    "source": "summary",
                    "message": f"Pipeline finished with status {summary['status']}.",
                    "node_id": None,
                    "subject_id": None,
                    "path": record.summary_path,
                    "metadata": {"nodes_total": summary.get("nodes_total")},
                }
            )

        if summary.get("started_at"):
            events.append(
                {
                    "timestamp": summary["started_at"],
                    "level": "info",
                    "source": "summary",
                    "message": "Pipeline execution started.",
                    "node_id": None,
                    "subject_id": None,
                    "path": record.summary_path,
                    "metadata": {},
                }
            )

        if summary.get("finished_at"):
            events.append(
                {
                    "timestamp": summary["finished_at"],
                    "level": "info",
                    "source": "summary",
                    "message": "Pipeline execution finished.",
                    "node_id": None,
                    "subject_id": None,
                    "path": record.summary_path,
                    "metadata": {},
                }
            )

        # Summary warnings as events
        for warning in summary.get("warnings", [])[:20]:
            events.append(
                {
                    "timestamp": summary.get("finished_at"),
                    "level": "warning",
                    "source": "summary",
                    "message": str(warning),
                    "node_id": None,
                    "subject_id": None,
                    "path": record.summary_path,
                    "metadata": {},
                }
            )

        # Summary errors as events
        for error_entry in summary.get("errors", [])[:20]:
            if isinstance(error_entry, dict):
                node_id = error_entry.get("node_id")
                events.append(
                    {
                        "timestamp": summary.get("finished_at"),
                        "level": "error",
                        "source": "summary",
                        "message": f"Node {node_id or 'unknown'} reported errors.",
                        "node_id": node_id,
                        "subject_id": None,
                        "path": record.summary_path,
                        "metadata": {"errors": error_entry.get("errors")},
                    }
                )

        # Failed nodes as events
        for failed in summary.get("failed_nodes", [])[:20]:
            node_id = failed.get("node_id")
            events.append(
                {
                    "timestamp": summary.get("finished_at"),
                    "level": "error",
                    "source": "summary",
                    "message": f"Node {node_id or 'unknown'} failed with status {failed.get('status', 'FAILED')}.",
                    "node_id": node_id,
                    "subject_id": None,
                    "path": record.summary_path,
                    "metadata": {"errors": failed.get("errors")},
                }
            )

    # ── 3. Artifact error excerpts as events ──
    try:
        artifacts, artifact_warnings = discover_run_artifacts(project, record)
        warnings.extend(artifact_warnings)
    except Exception as exc:
        warnings.append(f"ARTIFACT_DISCOVERY_FAILED: {exc}")
        artifacts = []

    for artifact in artifacts[:20]:
        error_excerpt = artifact.get("error_excerpt")
        if not error_excerpt or not isinstance(error_excerpt, str) or not error_excerpt.strip():
            continue
        events.append(
            {
                "timestamp": artifact.get("modified_at"),
                "level": "error",
                "source": "artifact",
                "message": error_excerpt[:500],
                "node_id": artifact.get("node_id"),
                "subject_id": None,
                "path": artifact.get("path"),
                "metadata": {"artifact_id": artifact.get("artifact_id")},
            }
        )

    # ── Sort by timestamp (most recent first) ──
    def _sort_key(event: dict[str, Any]) -> str:
        return event.get("timestamp") or ""

    events.sort(key=_sort_key, reverse=True)

    # ── Deduplicate messages ──
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for event in events:
        key = (event.get("timestamp") or "", event.get("message") or "")
        if key in seen:
            continue
        seen.add(key)
        unique.append(event)

    warnings_clean = _dedupe(warnings)[:50]
    if not unique and not warnings_clean:
        warnings_clean.append("No run events were discovered for this run yet.")

    return unique, warnings_clean


# ── Log discovery ────────────────────────────────────────────────────────────

def discover_run_logs(
    project: ProjectDetail,
    record: RunLinkRecord,
    max_bytes: int = DEFAULT_MAX_BYTES,
    include_content: bool = True,
) -> tuple[list[dict[str, Any]], list[str], list[str]]:
    """Discover log-like artifacts and return bounded content previews."""

    effective_max = max(MIN_MAX_BYTES, min(max_bytes, MAX_MAX_BYTES))
    logs: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    # ── 1. Discover artifacts ──
    try:
        artifacts, artifact_warnings = discover_run_artifacts(project, record)
        warnings.extend(artifact_warnings)
    except Exception as exc:
        errors.append(f"ARTIFACT_DISCOVERY_FAILED: {exc}")
        return logs, warnings, errors

    # ── 2. Filter log-like artifacts ──
    log_artifacts = [a for a in artifacts if _is_log_like_artifact(a)]

    # ── 3. Build log records ──
    for idx, artifact in enumerate(log_artifacts[:30]):
        path_str = artifact.get("path")
        if not path_str or not isinstance(path_str, str):
            warnings.append(f"LOG_PATH_MISSING: artifact {artifact.get('artifact_id')}")
            continue

        try:
            target = Path(path_str).expanduser().resolve()
        except Exception as exc:
            warnings.append(f"LOG_PATH_INVALID: {path_str}: {exc}")
            continue

        meta = _file_metadata(target)
        log_id = f"log_{record.run_id}_{idx}"
        name = str(artifact.get("name") or f"log_{idx}")
        relative_path = str(artifact.get("relative_path") or "")

        log_entry: dict[str, Any] = {
            "log_id": log_id,
            "name": name,
            "path": str(target),
            "relative_path": relative_path or None,
            "exists": meta["exists"],
            "size_bytes": meta["size_bytes"],
            "modified_at": meta["modified_at"],
            "content": None,
            "truncated": False,
            "warnings": [],
        }

        if log_entry["exists"] and include_content and meta["size_bytes"] is not None:
            if meta["size_bytes"] > 0:
                try:
                    content, truncated = _safe_utf8_read(target, effective_max)
                    log_entry["content"] = content
                    log_entry["truncated"] = truncated
                except (OSError, PermissionError) as exc:
                    log_entry["warnings"].append(f"LOG_READ_FAILED: {exc}")
            else:
                log_entry["content"] = ""
                log_entry["warnings"].append("LOG_FILE_EMPTY")

        elif not log_entry["exists"]:
            log_entry["warnings"].append("LOG_FILE_MISSING")

        logs.append(log_entry)

    # ── 4. Also check node state files for log references ──
    target_summary, summary_path_warnings = resolve_run_summary_path(project, record)
    if target_summary and target_summary.exists() and target_summary.is_file():
        try:
            raw = read_json_artifact(target_summary)
        except (JSONDecodeError, OSError) as exc:
            warnings.append(f"SUMMARY_READ_FAILED_FOR_LOGS: {exc}")
        else:
            if isinstance(raw, dict):
                node_states = raw.get("node_states") or []
                if isinstance(node_states, list):
                    for state_path_str in node_states[:20]:
                        state_path = None
                        try:
                            state_path = Path(str(state_path_str)).expanduser().resolve()
                        except Exception:
                            continue
                        if not state_path or not state_path.exists():
                            continue
                        try:
                            state_data = read_json_artifact(state_path)
                        except (JSONDecodeError, OSError):
                            continue
                        if not isinstance(state_data, dict):
                            continue
                        log_path = state_data.get("log_path") or state_data.get("stdout_log")
                        stderr_path = state_data.get("stderr_log")

                        for log_type, log_file_str in [("stdout", log_path), ("stderr", stderr_path)]:
                            if not log_file_str or not isinstance(log_file_str, str):
                                continue
                            try:
                                log_file = Path(log_file_str).expanduser().resolve()
                            except Exception:
                                continue
                            meta = _file_metadata(log_file)
                            # Skip if already covered
                            if any(l["path"] == str(log_file) for l in logs):
                                continue
                            node_id = state_data.get("node") or state_data.get("node_id") or "unknown"
                            log_entry = {
                                "log_id": f"log_{record.run_id}_node_{len(logs)}",
                                "name": f"{node_id}_{log_type}.log",
                                "path": str(log_file),
                                "relative_path": None,
                                "exists": meta["exists"],
                                "size_bytes": meta["size_bytes"],
                                "modified_at": meta["modified_at"],
                                "content": None,
                                "truncated": False,
                                "warnings": [],
                            }
                            if log_entry["exists"] and include_content and meta["size_bytes"] is not None and meta["size_bytes"] > 0:
                                try:
                                    content, truncated = _safe_utf8_read(log_file, effective_max)
                                    log_entry["content"] = content
                                    log_entry["truncated"] = truncated
                                except (OSError, PermissionError) as exc:
                                    log_entry["warnings"].append(f"LOG_READ_FAILED: {exc}")
                            elif not log_entry["exists"]:
                                log_entry["warnings"].append("LOG_FILE_MISSING")
                            logs.append(log_entry)

    warnings_clean = _dedupe(warnings)[:50]
    errors_clean = _dedupe(errors)[:50]
    if not logs and not warnings_clean and not errors_clean:
        warnings_clean.append("No run logs were discovered for this run yet.")

    return logs, warnings_clean, errors_clean
