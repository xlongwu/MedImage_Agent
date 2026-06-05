"""Resolve persisted project metadata and bind it to reviewed plans."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.backend.app.runtime.tool_catalog import build_tool_catalog
from src.backend.app.services.mock_store import mock_store


class ProjectContextError(ValueError):
    """Raised when a project context cannot be resolved safely."""


@dataclass(frozen=True)
class ProjectContext:
    project_id: str | None
    project_config_path: Path
    rawdata_dir: Path | None
    dataset_index_path: Path | None
    source: str
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "project_config_path": str(self.project_config_path),
            "rawdata_dir": str(self.rawdata_dir) if self.rawdata_dir else None,
            "dataset_index_path": (
                str(self.dataset_index_path) if self.dataset_index_path else None
            ),
            "source": self.source,
            "diagnostics": dict(self.diagnostics),
        }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _path(value: Any) -> Path | None:
    if not isinstance(value, (str, Path)) or not str(value).strip():
        return None
    return Path(value).expanduser().resolve()


def _same_path(first: Path | None, second: Path | None) -> bool:
    return first is not None and second is not None and first == second


def _is_example_config(path: Path) -> bool:
    try:
        path.relative_to(Path("examples").resolve())
        return True
    except ValueError:
        return False


def load_project_context(
    project_id: str | None,
    project_config_path: str | None,
) -> ProjectContext:
    """Load project paths from config, supplemented and checked against the store."""
    stored_project = None
    stored_metadata: dict[str, Any] = {}

    if project_id:
        stored_project = mock_store.get_project(project_id)
        if stored_project is None:
            raise ProjectContextError(f"PROJECT_NOT_FOUND: {project_id}")
        stored_metadata = _mapping(stored_project.metadata)

    stored_config_path = _path(stored_metadata.get("project_config_path"))
    supplied_config_path = _path(project_config_path)
    if supplied_config_path and stored_config_path and supplied_config_path != stored_config_path:
        raise ProjectContextError(
            "PROJECT_CONFIG_MISMATCH: supplied project_config_path does not match project metadata"
        )

    config_path = supplied_config_path or stored_config_path
    if config_path is None:
        raise ProjectContextError("PROJECT_CONFIG_REQUIRED: project_config_path is required")
    if not config_path.exists() or not config_path.is_file():
        raise ProjectContextError(
            f"PROJECT_CONFIG_INVALID: project config does not exist: {config_path}"
        )

    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ProjectContextError(f"PROJECT_CONFIG_INVALID: {exc}") from exc
    if not isinstance(config, dict):
        raise ProjectContextError("PROJECT_CONFIG_INVALID: project config must be a mapping")

    project_section = _mapping(config.get("project"))
    data_section = _mapping(config.get("data"))
    config_metadata = _mapping(config.get("metadata"))
    config_project_id = project_section.get("project_id")
    if project_id and config_project_id and str(config_project_id) != project_id:
        raise ProjectContextError(
            "PROJECT_ID_MISMATCH: project config does not belong to the selected project"
        )

    resolved_project_id = project_id or (
        str(config_project_id) if config_project_id else None
    )
    if stored_project is None and resolved_project_id:
        stored_project = mock_store.get_project(resolved_project_id)
        if stored_project is not None:
            stored_metadata = _mapping(stored_project.metadata)

    metadata_config_path = _path(stored_metadata.get("project_config_path"))
    if metadata_config_path and metadata_config_path != config_path:
        raise ProjectContextError(
            "PROJECT_CONFIG_MISMATCH: project config does not match persisted metadata"
        )

    config_rawdata = _path(
        data_section.get("rawdata_dir") or config_metadata.get("rawdata_dir")
    )
    metadata_rawdata = _path(stored_metadata.get("rawdata_dir"))
    if config_rawdata and metadata_rawdata and config_rawdata != metadata_rawdata:
        raise ProjectContextError(
            "RAWDATA_CONTEXT_MISMATCH: config rawdata_dir does not match project metadata"
        )
    rawdata_dir = config_rawdata or metadata_rawdata

    config_dataset_index = _path(
        data_section.get("dataset_index")
        or config_metadata.get("dataset_index_path")
    )
    metadata_dataset_index = _path(stored_metadata.get("dataset_index_path"))
    if (
        config_dataset_index
        and metadata_dataset_index
        and config_dataset_index != metadata_dataset_index
    ):
        raise ProjectContextError(
            "DATASET_INDEX_CONTEXT_MISMATCH: config dataset index does not match project metadata"
        )
    dataset_index_path = config_dataset_index or metadata_dataset_index

    source = str(
        stored_metadata.get("source")
        or config_metadata.get("source")
        or (
            "created"
            if config_project_id and data_section.get("copy_mode") == "reference"
            else "example"
            if _is_example_config(config_path)
            else "config"
        )
    )
    diagnostics = _mapping(
        stored_metadata.get("diagnostics") or config_metadata.get("diagnostics")
    )

    if source == "created":
        if rawdata_dir is None or not rawdata_dir.exists() or not rawdata_dir.is_dir():
            raise ProjectContextError(
                "RAWDATA_CONTEXT_INVALID: created project rawdata_dir is missing or invalid"
            )
        if (
            dataset_index_path is None
            or not dataset_index_path.exists()
            or not dataset_index_path.is_file()
        ):
            raise ProjectContextError(
                "DATASET_INDEX_CONTEXT_INVALID: created project dataset index is missing or invalid"
            )

    return ProjectContext(
        project_id=resolved_project_id,
        project_config_path=config_path,
        rawdata_dir=rawdata_dir,
        dataset_index_path=dataset_index_path,
        source=source,
        diagnostics=diagnostics,
    )


def _subject_level_node_ids() -> set[str]:
    return {
        item.id
        for item in build_tool_catalog()
        if item.parallel_level == "subject"
    }


def apply_project_context_to_plan(
    plan: dict[str, Any],
    context: ProjectContext,
) -> dict[str, Any]:
    """Return a reviewed-plan candidate with deterministic project paths injected."""
    nodes = plan.get("nodes", []) or []
    if context.source == "created" and any(
        isinstance(node, dict) and node.get("id") == "create_synthetic_bids"
        for node in nodes
    ):
        raise ProjectContextError(
            "SYNTHETIC_DATA_NOT_ALLOWED: created projects cannot use create_synthetic_bids"
        )

    enriched = deepcopy(plan)
    enriched["project_context"] = context.to_dict()
    subject_nodes = _subject_level_node_ids()

    for node in enriched.get("nodes", []) or []:
        if not isinstance(node, dict):
            continue
        params = node.setdefault("params", {})
        if not isinstance(params, dict):
            continue

        node_id = str(node.get("id", ""))
        if node_id == "data_inspection":
            if context.rawdata_dir is not None:
                params["rawdata_dir"] = str(context.rawdata_dir)
            if context.dataset_index_path is not None:
                params["output_dir"] = str(context.dataset_index_path.parent)

        is_subject_level = (
            node_id in subject_nodes or node.get("parallel_level") == "subject"
        )
        if context.dataset_index_path is not None and (
            is_subject_level or "dataset_index" in params
        ):
            params["dataset_index"] = str(context.dataset_index_path)

    return enriched


def validate_plan_project_context(
    plan: dict[str, Any],
    context: ProjectContext,
) -> list[str]:
    """Validate a reviewed plan without mutating the already-reviewed content."""
    if context.source != "created":
        return []

    errors: list[str] = []
    nodes = plan.get("nodes", []) or []
    if any(
        isinstance(node, dict) and node.get("id") == "create_synthetic_bids"
        for node in nodes
    ):
        errors.append(
            "SYNTHETIC_DATA_NOT_ALLOWED: created projects cannot use create_synthetic_bids"
        )

    summary = plan.get("project_context")
    if not isinstance(summary, dict):
        errors.append("PROJECT_CONTEXT_MISSING: reviewed plan has no project_context")
    else:
        if context.project_id and summary.get("project_id") != context.project_id:
            errors.append("PROJECT_ID_MISMATCH: reviewed plan project_id does not match")
        for key, expected in (
            ("project_config_path", context.project_config_path),
            ("rawdata_dir", context.rawdata_dir),
            ("dataset_index_path", context.dataset_index_path),
        ):
            if expected is not None and _path(summary.get(key)) != expected:
                errors.append(
                    f"{key.upper()}_MISMATCH: reviewed plan {key} does not match project context"
                )

    subject_nodes = _subject_level_node_ids()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", ""))
        params = node.get("params", {}) or {}
        if not isinstance(params, dict):
            continue

        rawdata_value = _path(params.get("rawdata_dir"))
        if rawdata_value is not None and not _same_path(rawdata_value, context.rawdata_dir):
            errors.append(
                f"RAWDATA_DIR_MISMATCH: node '{node_id}' rawdata_dir does not match project context"
            )
        if node_id == "data_inspection" and not _same_path(
            rawdata_value, context.rawdata_dir
        ):
            errors.append(
                "RAWDATA_DIR_REQUIRED: data_inspection must use the project rawdata_dir"
            )

        dataset_value = _path(params.get("dataset_index"))
        if dataset_value is not None and not _same_path(
            dataset_value, context.dataset_index_path
        ):
            errors.append(
                f"DATASET_INDEX_MISMATCH: node '{node_id}' dataset_index does not match project context"
            )
        if (
            node_id in subject_nodes or node.get("parallel_level") == "subject"
        ) and not _same_path(dataset_value, context.dataset_index_path):
            errors.append(
                f"DATASET_INDEX_REQUIRED: subject-level node '{node_id}' must use the project dataset index"
            )

    return errors
