from __future__ import annotations

import json
from pathlib import Path
from typing import TypeVar


_T = TypeVar("_T")


def write_json_artifact(path: str | Path, data: dict) -> Path:
    """Write a JSON artifact file, creating parent directories as needed."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def read_json_artifact(path: str | Path) -> dict:
    """Read a JSON artifact file."""
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8"))


def read_optional_json_artifact(
    path: str | Path,
    default: _T | None = None,
) -> dict | _T | None:
    """Read an optional JSON artifact, returning the default only if absent."""
    p = Path(path)
    if not p.exists():
        return default
    return read_json_artifact(p)


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    import hashlib
    h = hashlib.sha256()
    h.update(Path(path).read_bytes())
    return h.hexdigest()


def is_safe_artifact_id(artifact_id: str) -> bool:
    """Check that an artifact ID is safe (no path traversal, reasonable length)."""
    if not artifact_id or len(artifact_id) > 256:
        return False
    if ".." in artifact_id:
        return False
    if "/" in artifact_id or "\\" in artifact_id:
        return False
    return all(ch.isalnum() or ch in "_-." for ch in artifact_id)
