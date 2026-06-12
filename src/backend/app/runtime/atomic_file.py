from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any


_LOCKS_GUARD = threading.Lock()
_PATH_LOCKS: dict[Path, threading.Lock] = {}


def _path_lock(path: Path) -> threading.Lock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        lock = _PATH_LOCKS.get(resolved)
        if lock is None:
            lock = threading.Lock()
            _PATH_LOCKS[resolved] = lock
        return lock


def atomic_write_json(
    path: str | Path,
    data: dict[str, Any],
    *,
    schema_version: str | int | None = None,
) -> Path:
    """Write JSON through a same-directory temp file and atomic replace."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(data)
    if schema_version is not None:
        payload.setdefault("_schema_version", schema_version)

    with _path_lock(target):
        tmp_fd, tmp_name = tempfile.mkstemp(
            dir=str(target.parent),
            prefix=f".{target.name}.",
            suffix=".tmp",
            text=True,
        )
        tmp_path = Path(tmp_name)
        try:
            with os.fdopen(tmp_fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_path, target)
        except Exception:
            try:
                tmp_path.unlink(missing_ok=True)
            finally:
                raise
    return target
