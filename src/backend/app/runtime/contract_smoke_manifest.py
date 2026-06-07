"""Output manifest and provenance helpers for contract_smoke node.

Pure helpers that write standardized Phase 3 OutputManifest and
ExecutionProvenance artifacts alongside the existing contract_smoke
outputs.  No external tools, no rawdata access, no subprocess.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.backend.app.schemas.execution_manifest import (
    ExecutionProvenance,
    OutputManifest,
    OutputManifestItem,
    build_output_manifest,
)
from src.backend.app.schemas.execution_state import (
    is_node_reuse_eligible,
    is_node_retry_eligible,
    is_node_terminal,
)


_MANIFEST_FILENAME = "contract_smoke_output_manifest.json"
_PROVENANCE_FILENAME = "contract_smoke_execution_provenance.json"
_NODE_STATE_FILENAME = "contract_smoke_node_state.json"


def _file_info(path: Path) -> dict[str, Any]:
    """Return size_bytes + exists for a path, without importing os.stat."""
    exists = path.exists() and path.is_file()
    size: int | None = None
    if exists:
        try:
            size = path.stat().st_size
        except OSError:
            pass
    return {"exists": exists, "size_bytes": size}


def _output_kind(path: Path) -> str:
    """Map a file suffix to an OutputArtifactKind."""
    name = path.name.lower()
    if name.endswith(".json"):
        # provenance JSON and manifest JSON are special
        if "provenance" in name:
            return "provenance_json"
        if "manifest" in name:
            return "node_state_json"
        return "json"
    if name.endswith(".log"):
        return "log"
    if name.endswith(".md"):
        return "markdown"
    if name.endswith(".csv"):
        return "csv"
    return "other"


def _previewable(path: Path) -> bool:
    return path.suffix.lower() in {".json", ".log", ".txt", ".md", ".csv"}


def _build_manifest_items(
    output_paths: list[Path],
    manifest_path: Path,
    provenance_path: Path,
    node_state_path: Path,
) -> list[OutputManifestItem]:
    """Build OutputManifestItem entries for existing + new artifacts."""
    items: list[OutputManifestItem] = []

    # Existing contract_smoke outputs
    for op in output_paths:
        info = _file_info(op)
        items.append(OutputManifestItem(
            kind=_output_kind(op),
            path=str(op),
            relative_path=op.name,
            required=(op.suffix == ".json"),  # JSON report is required
            exists=info["exists"],
            verified=info["exists"] and (info["size_bytes"] or 0) > 0,
            verification_status=(
                "verified" if (info["exists"] and (info["size_bytes"] or 0) > 0)
                else "missing"
            ),
            size_bytes=info["size_bytes"],
            previewable=_previewable(op),
        ))

    # Node-state artifact (normalized Phase 3 state, written before manifest)
    ns_info = _file_info(node_state_path)
    items.append(OutputManifestItem(
        kind="node_state_json",
        path=str(node_state_path),
        relative_path=node_state_path.name,
        required=True,
        exists=ns_info["exists"],
        verified=ns_info["exists"] and (ns_info["size_bytes"] or 0) > 0,
        verification_status="verified" if ns_info["exists"] else "missing",
        size_bytes=ns_info["size_bytes"],
        previewable=True,
    ))

    # Output manifest artifact itself (written after items built, so not required)
    m_info = _file_info(manifest_path)
    items.append(OutputManifestItem(
        kind="json",
        path=str(manifest_path),
        relative_path=manifest_path.name,
        required=False,
        exists=m_info["exists"],
        verified=m_info["exists"] and (m_info["size_bytes"] or 0) > 0,
        verification_status="verified" if m_info["exists"] else "missing",
        size_bytes=m_info["size_bytes"],
        previewable=True,
    ))

    # Provenance artifact (written after manifest, so not required)
    p_info = _file_info(provenance_path)
    items.append(OutputManifestItem(
        kind="provenance_json",
        path=str(provenance_path),
        relative_path=provenance_path.name,
        required=False,
        exists=p_info["exists"],
        verified=p_info["exists"] and (p_info["size_bytes"] or 0) > 0,
        verification_status="verified" if p_info["exists"] else "missing",
        size_bytes=p_info["size_bytes"],
        previewable=True,
    ))

    return items


def _project_id_from_context(context: Any) -> str:
    """Extract project_id from NodeExecutionContext."""
    # Try project_config dict first
    if hasattr(context, "project_config") and isinstance(context.project_config, dict):
        pid = context.project_config.get("project_id", "")
        if pid:
            return str(pid)
    # Fall back to project_id attribute
    pid = getattr(context, "project_id", "") or ""
    if pid:
        return str(pid)
    return "unknown"


def write_contract_smoke_manifest(
    *,
    project_id: str,
    run_id: str,
    node_id: str,
    work_dir: str,
    output_paths: list[Path],
) -> OutputManifest:
    """Write contract_smoke_output_manifest.json and return the model.

    Writes the manifest BEFORE the provenance file so provenance can
    reference the manifest path.  The manifest includes items for
    all existing outputs plus itself and the upcoming provenance file.
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    manifest_path = work_path / _MANIFEST_FILENAME
    provenance_path = work_path / _PROVENANCE_FILENAME
    node_state_path = work_path / _NODE_STATE_FILENAME

    items = _build_manifest_items(
        output_paths, manifest_path, provenance_path, node_state_path,
    )

    manifest = build_output_manifest(
        project_id=project_id,
        run_id=run_id,
        node_id=node_id,
        items=items,
        output_root=str(work_path),
    )

    manifest_path.write_text(
        manifest.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return manifest


def write_contract_smoke_provenance(
    *,
    project_id: str,
    run_id: str,
    node_id: str,
    work_dir: str,
    output_paths: list[Path],
    params: dict[str, Any] | None = None,
    started_at: str | None = None,
    finished_at: str | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> ExecutionProvenance:
    """Write contract_smoke_execution_provenance.json and return the model.

    Must be called after ``write_contract_smoke_manifest`` so the manifest
    file is included in output_paths.
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)

    provenance_path = work_path / _PROVENANCE_FILENAME
    manifest_path = work_path / _MANIFEST_FILENAME

    all_paths = [str(p) for p in output_paths]
    # Include the manifest itself
    all_paths.append(str(manifest_path))
    all_paths.append(str(provenance_path))

    checksums: dict[str, str] = {}
    # No expensive checksum computation — leave empty

    provenance = ExecutionProvenance(
        project_id=project_id,
        run_id=run_id,
        node_id=node_id,
        backend="python",
        params=params or {},
        input_paths=[],
        input_checksums={},
        output_paths=all_paths,
        output_checksums=checksums,
        software_versions={},
        environment_fingerprint=None,
        approval_context=None,
        audit_id=None,
        started_at=started_at,
        finished_at=finished_at,
        return_code=0,
        stdout_log_path=next(
            (str(p) for p in output_paths if p.suffix == ".log"), None
        ),
        stderr_log_path=None,
        warnings=warnings or [],
        errors=errors or [],
    )

    provenance_path.write_text(
        provenance.model_dump_json(indent=2),
        encoding="utf-8",
    )

    return provenance


def write_contract_smoke_node_state(
    *,
    node_id: str,
    work_dir: str,
    state: str,
    started_at: str | None = None,
    finished_at: str | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
) -> Path:
    """Write a normalized Phase 3 node-state JSON artifact.

    Returns the path of the written file so the caller can include it
    in the node's output list.
    """
    work_path = Path(work_dir)
    work_path.mkdir(parents=True, exist_ok=True)
    node_state_path = work_path / _NODE_STATE_FILENAME

    payload = {
        "schema_version": "phase3-node-state-v1",
        "node_id": node_id,
        "state": state,
        "terminal": is_node_terminal(state),
        "retry_eligible": is_node_retry_eligible(state),
        "reuse_eligible": is_node_reuse_eligible(state),
        "started_at": started_at,
        "finished_at": finished_at,
        "warnings": warnings or [],
        "errors": errors or [],
        "metadata": {
            "backend": "python",
            "risk_level": "low",
        },
    }

    node_state_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )

    return node_state_path


def contract_smoke_artifact_paths(work_dir: str) -> tuple[Path, Path, Path]:
    """Return (node_state_path, manifest_path, provenance_path)."""
    work_path = Path(work_dir)
    return (
        work_path / _NODE_STATE_FILENAME,
        work_path / _MANIFEST_FILENAME,
        work_path / _PROVENANCE_FILENAME,
    )


def contract_smoke_manifest_paths(work_dir: str) -> tuple[Path, Path]:
    """Return (manifest_path, provenance_path) for the given work_dir."""
    work_path = Path(work_dir)
    return (
        work_path / _MANIFEST_FILENAME,
        work_path / _PROVENANCE_FILENAME,
    )
