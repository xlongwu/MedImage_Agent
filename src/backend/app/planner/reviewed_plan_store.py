"""Persist stable reviewed plans and link each real-project execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.planner.project_context import (
    ProjectContext,
    ProjectContextError,
    load_project_context,
    validate_plan_project_context,
)
from src.backend.app.schemas.desktop import ReviewedPlanRecord, RunLinkRecord
from src.backend.app.services.mock_store import mock_store, utc_now_iso


class ReviewedPlanStoreError(ValueError):
    """Raised when a reviewed plan cannot be persisted or linked safely."""


def reviewed_plan_identity(project_id: str, plan: dict[str, Any]) -> tuple[str, str]:
    plan_hash = stable_hash(plan)
    identity_hash = stable_hash({"project_id": project_id, "plan_hash": plan_hash})
    return f"reviewed_{identity_hash[:20]}", plan_hash


def new_run_identity() -> tuple[str, str]:
    return f"runlink_{uuid4().hex[:20]}", f"run_{uuid4().hex[:20]}"


def _project_dir(project_id: str) -> Path:
    project = mock_store.get_project(project_id)
    if project is None:
        raise ReviewedPlanStoreError(f"PROJECT_NOT_FOUND: {project_id}")
    value = project.metadata.get("project_dir")
    if not isinstance(value, str) or not value.strip():
        raise ReviewedPlanStoreError(
            "PROJECT_DIR_REQUIRED: persisted project metadata has no project_dir"
        )
    path = Path(value).expanduser().resolve()
    if not path.exists() or not path.is_dir():
        raise ReviewedPlanStoreError(f"PROJECT_DIR_INVALID: {path}")
    return path


def _snapshot_path(project_dir: Path, reviewed_plan_id: str) -> Path:
    plans_dir = (project_dir / "plans").resolve()
    try:
        plans_dir.relative_to(project_dir)
    except ValueError as exc:
        raise ReviewedPlanStoreError("PLAN_PATH_INVALID: plans directory escapes project") from exc
    return plans_dir / f"{reviewed_plan_id}.json"


def write_reviewed_plan_snapshot(record: ReviewedPlanRecord, project_dir: Path) -> Path:
    """Write the first immutable project-local snapshot for a reviewed plan."""
    target = _snapshot_path(project_dir, record.reviewed_plan_id)
    if target.exists():
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(
        json.dumps(record.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    tmp.replace(target)
    return target


def save_reviewed_plan(
    *,
    project_id: str,
    project_config_path: str | None,
    plan: dict[str, Any],
    validation: dict[str, Any] | None = None,
    goal: str | None = None,
    provider: str | None = None,
    status: str = "REVIEWED",
    warnings: list[str] | None = None,
) -> ReviewedPlanRecord:
    """Upsert a stable SQLite plan index and write its immutable snapshot."""
    try:
        context = load_project_context(project_id, project_config_path)
    except ProjectContextError as exc:
        raise ReviewedPlanStoreError(str(exc)) from exc
    context_errors = validate_plan_project_context(plan, context)
    if context_errors:
        raise ReviewedPlanStoreError("; ".join(context_errors))

    project_dir = _project_dir(project_id)
    reviewed_plan_id, plan_hash = reviewed_plan_identity(project_id, plan)
    now = utc_now_iso()
    plan_path = _snapshot_path(project_dir, reviewed_plan_id)
    record = ReviewedPlanRecord(
        reviewed_plan_id=reviewed_plan_id,
        project_id=project_id,
        project_config_path=str(context.project_config_path),
        dataset_index_path=(
            str(context.dataset_index_path) if context.dataset_index_path else None
        ),
        rawdata_dir=str(context.rawdata_dir) if context.rawdata_dir else None,
        plan_hash=plan_hash,
        plan_path=str(plan_path),
        status=status,
        created_at=now,
        updated_at=now,
        warnings=list(warnings or []),
        payload={
            "plan": plan,
            "validation": dict(validation or {}),
            "goal": goal,
            "provider": provider,
        },
    )
    stored = mock_store.add_reviewed_plan(record)
    try:
        write_reviewed_plan_snapshot(stored, project_dir)
    except Exception as exc:
        snapshot_warning = f"PLAN_SNAPSHOT_WRITE_FAILED: {exc}"
        stored = mock_store.update_reviewed_plan(
            stored.reviewed_plan_id,
            warnings=list(dict.fromkeys([*stored.warnings, snapshot_warning])),
        ) or stored
    return stored


def snapshot_warnings(record: ReviewedPlanRecord) -> list[str]:
    warnings = list(record.warnings)
    if not record.plan_path or not Path(record.plan_path).is_file():
        warnings.append("PLAN_SNAPSHOT_MISSING")
    return list(dict.fromkeys(warnings))


def artifact_warnings(record: RunLinkRecord) -> list[str]:
    warnings = list(record.warnings)
    if not record.pipeline_path or not Path(record.pipeline_path).is_file():
        warnings.append("PIPELINE_YAML_MISSING")
    if record.summary_path and not Path(record.summary_path).is_file():
        warnings.append("SUMMARY_MISSING")
    return list(dict.fromkeys(warnings))


def resolve_reviewed_plan_for_execution(
    context: ProjectContext,
    plan: dict[str, Any],
    reviewed_plan_id: str | None,
) -> ReviewedPlanRecord:
    if not context.project_id:
        raise ReviewedPlanStoreError("PROJECT_ID_REQUIRED: real execution needs a project id")
    expected_id, plan_hash = reviewed_plan_identity(context.project_id, plan)
    if reviewed_plan_id and reviewed_plan_id != expected_id:
        raise ReviewedPlanStoreError(
            "REVIEWED_PLAN_MISMATCH: reviewed_plan_id does not match the submitted plan"
        )
    record = mock_store.get_reviewed_plan(reviewed_plan_id or expected_id)
    if record is None:
        record = mock_store.find_reviewed_plan(context.project_id, plan_hash)
    if record is None:
        raise ReviewedPlanStoreError(
            "REVIEWED_PLAN_NOT_FOUND: save this reviewed plan before execution"
        )
    if record.project_id != context.project_id or record.plan_hash != plan_hash:
        raise ReviewedPlanStoreError(
            "REVIEWED_PLAN_MISMATCH: persisted reviewed plan does not match execution"
        )
    if Path(record.project_config_path).resolve() != context.project_config_path:
        raise ReviewedPlanStoreError(
            "PROJECT_CONFIG_MISMATCH: reviewed plan uses a different project config"
        )
    return record


def build_run_link(
    *,
    project_id: str,
    reviewed_plan_id: str,
    run_link_id: str,
    run_id: str,
    project_config_path: str,
    pipeline_path: str,
) -> RunLinkRecord:
    now = utc_now_iso()
    return RunLinkRecord(
        run_link_id=run_link_id,
        project_id=project_id,
        reviewed_plan_id=reviewed_plan_id,
        run_id=run_id,
        pipeline_path=pipeline_path,
        project_config_path=project_config_path,
        created_at=now,
        updated_at=now,
    )
