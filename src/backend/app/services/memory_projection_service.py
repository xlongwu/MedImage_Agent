"""Rebuild human-readable memory projections from the SQLite authority."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from src.backend.app.core.config_schema import MemoryConfig
from src.backend.app.planner.audit_record import stable_hash
from src.backend.app.runtime.atomic_file import atomic_write_json, atomic_write_text
from src.backend.app.services.memory_repository import MemoryRepository, MemoryRepositoryError

PROJECTION_SCHEMA_VERSION = "memory-projection-v1"


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class MemoryProjectionService:
    def __init__(
        self,
        *,
        project_store,
        memory_repository: MemoryRepository,
        config: MemoryConfig,
    ) -> None:
        self.project_store = project_store
        self.repository = memory_repository
        self.config = config

    def rebuild(
        self, *, project_id: str, explicit_approved: bool = False
    ) -> dict[str, Any]:
        if not self.config.projection_enabled and not explicit_approved:
            raise MemoryRepositoryError("MEMORY_PROJECTION_DISABLED")
        project = self.project_store.get_project(project_id)
        if project is None:
            raise MemoryRepositoryError("MEMORY_PROJECT_NOT_FOUND")
        metadata = project.metadata if isinstance(project.metadata, dict) else {}
        root_value = metadata.get("project_dir")
        if not isinstance(root_value, str) or not root_value.strip():
            raise MemoryRepositoryError("MEMORY_PROJECT_DIR_REQUIRED")
        project_root = Path(root_value).expanduser().resolve()
        work_root = (project_root / "work").resolve()
        target = (work_root / "memory").resolve()
        try:
            target.relative_to(work_root)
        except ValueError as exc:
            raise MemoryRepositoryError("MEMORY_PROJECTION_PATH_UNSAFE") from exc
        raw_roots = [
            Path(value).expanduser().resolve()
            for key in ("rawdata_dir", "bids_dir", "dicom_dir")
            if isinstance((value := metadata.get(key)), str) and value.strip()
        ]
        for raw_root in raw_roots:
            try:
                target.relative_to(raw_root)
            except ValueError:
                continue
            raise MemoryRepositoryError("MEMORY_PROJECTION_IN_RAWDATA")

        items = self.repository.list_items(
            project_id=project_id, status="active", limit=200
        )
        candidates = self.repository.list_candidates(
            project_id=project_id, status="proposed", limit=200
        )
        memory_lines = ["# Project Memory", "", f"Project: `{project_id}`", ""]
        for item in items:
            memory_lines.extend(
                [
                    f"## {item.kind}: {item.canonical_key}",
                    "",
                    f"- Memory ID: `{item.memory_id}`",
                    f"- Revision: `{item.revision.content_hash}`",
                    f"- Impact: `{item.revision.impact_class}`",
                    f"- Pinned: `{str(item.pinned).lower()}`",
                    f"- Summary: {item.revision.content_text}",
                    "",
                ]
            )
        candidate_lines = ["# Memory Candidates", "", f"Project: `{project_id}`", ""]
        for candidate in candidates:
            candidate_lines.extend(
                [
                    f"## {candidate.kind}: {candidate.canonical_key}",
                    "",
                    f"- Candidate ID: `{candidate.candidate_id}`",
                    f"- Impact: `{candidate.impact_class}`",
                    f"- Source: `{candidate.source.source_ref}`",
                    f"- Summary: {candidate.content_text}",
                    "",
                ]
            )
        memory_text = "\n".join(memory_lines).rstrip() + "\n"
        candidate_text = "\n".join(candidate_lines).rstrip() + "\n"
        checksums = {
            "MEMORY.md": _sha256_text(memory_text),
            "CANDIDATES.md": _sha256_text(candidate_text),
        }
        manifest = {
            "_schema_version": PROJECTION_SCHEMA_VERSION,
            "project_id": project_id,
            "db_revision": self.repository.projection_revision(project_id=project_id),
            "checksums": checksums,
            "authority": "sqlite",
        }
        target.mkdir(parents=True, exist_ok=True)
        atomic_write_text(target / "MEMORY.md", memory_text)
        atomic_write_text(target / "CANDIDATES.md", candidate_text)
        atomic_write_json(
            target / "manifest.json",
            manifest,
            schema_version=PROJECTION_SCHEMA_VERSION,
        )
        manifest_hash = stable_hash(manifest)
        self.repository.record_projection_rebuilt(
            project_id=project_id,
            manifest_hash=manifest_hash,
            file_count=3,
        )
        return {
            "status": "rebuilt",
            "projection_dir": str(target),
            "manifest_hash": manifest_hash,
            "checksums": checksums,
        }

    def verify(self, *, project_id: str) -> dict[str, Any]:
        project = self.project_store.get_project(project_id)
        if project is None:
            raise MemoryRepositoryError("MEMORY_PROJECT_NOT_FOUND")
        metadata = project.metadata if isinstance(project.metadata, dict) else {}
        root_value = metadata.get("project_dir")
        if not isinstance(root_value, str) or not root_value.strip():
            raise MemoryRepositoryError("MEMORY_PROJECT_DIR_REQUIRED")
        target = Path(root_value).expanduser().resolve() / "work" / "memory"
        manifest_path = target / "manifest.json"
        if not manifest_path.exists():
            return {"ok": False, "error_code": "MEMORY_PROJECTION_MISSING"}
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            checksums = manifest["checksums"]
            actual = {
                name: hashlib.sha256((target / name).read_bytes()).hexdigest()
                for name in ("MEMORY.md", "CANDIDATES.md")
            }
        except Exception as exc:
            return {
                "ok": False,
                "error_code": "MEMORY_PROJECTION_INVALID",
                "detail": type(exc).__name__,
            }
        return {
            "ok": actual == checksums,
            "error_code": None if actual == checksums else "MEMORY_PROJECTION_CHECKSUM_MISMATCH",
            "checksums": actual,
        }

