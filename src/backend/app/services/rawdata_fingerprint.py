"""Rawdata fingerprint — pure, read-only filesystem metadata hash.

Computes a bounded fingerprint suitable for future cache invalidation
without reading file contents.  Never modifies rawdata, never writes
files, never calls external tools.
"""

from __future__ import annotations

import hashlib
import os
from datetime import UTC
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import RawdataFingerprint


def _suffixes(name: str) -> list[str]:
    """Return all suffix combinations for a filename (handles .nii.gz)."""
    if name.endswith(".nii.gz"):
        return [".nii.gz"]
    p = Path(name)
    return p.suffixes or [p.suffix] if p.suffix else []


def _matches_filter(name: str, include_suffixes: set[str] | None) -> bool:
    if include_suffixes is None:
        return True
    parts = _suffixes(name)
    full = "".join(parts)
    for sfx in include_suffixes:
        if sfx == full or sfx in parts:
            return True
    return False


def build_rawdata_fingerprint(
    roots: list[str | Path],
    *,
    max_files: int = 20000,
    include_suffixes: set[str] | None = None,
) -> RawdataFingerprint:
    """Compute a bounded metadata-only fingerprint for a set of filesystem roots.

    Args:
        roots: one or more directory paths to scan.
        max_files: cap on scanned files to prevent runaway scans.
        include_suffixes: optional filter; e.g. {".nii", ".nii.gz", ".json"}.

    Returns a dict with keys: ok, roots, exists_count, missing_roots,
    file_count, total_size_bytes, newest_mtime, newest_mtime_iso,
    relative_path_hash, fingerprint, truncated, max_files, warnings, errors.
    """
    warnings: list[str] = []
    errors: list[str] = []
    entries: list[dict[str, Any]] = []
    missing: list[str] = []
    exists = 0

    for raw in roots:
        root = Path(raw).expanduser().resolve()
        if not root.exists():
            missing.append(str(raw))
            warnings.append(f"Root does not exist: {raw}")
            continue
        if not root.is_dir():
            missing.append(str(raw))
            warnings.append(f"Root is not a directory: {raw}")
            continue
        exists += 1

        try:
            for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
                dirnames.sort()
                for fn in sorted(filenames):
                    if len(entries) >= max_files:
                        break
                    if not _matches_filter(fn, include_suffixes):
                        continue
                    fp = Path(dirpath) / fn
                    try:
                        st = fp.stat()
                    except OSError:
                        continue
                    rel = str(fp.relative_to(root)).replace("\\", "/")
                    entries.append({
                        "path": rel,
                        "size": st.st_size,
                        "mtime": st.st_mtime,
                    })
                if len(entries) >= max_files:
                    break
        except PermissionError:
            warnings.append(f"Permission denied scanning root: {root}")
        except OSError as exc:
            errors.append(f"Error scanning root {root}: {exc}")

    truncated = len(entries) >= max_files
    if truncated:
        warnings.append(f"File count capped at {max_files}.")

    file_count = len(entries)
    total_size = sum(e["size"] for e in entries)
    newest = max((e["mtime"] for e in entries), default=None)

    # Deterministic relative path hash
    path_hasher = hashlib.sha256()
    for e in entries:
        path_hasher.update(e["path"].encode("utf-8"))
        path_hasher.update(b"\x00")
    path_hash = path_hasher.hexdigest() if entries else None

    # Final fingerprint
    fin_hasher = hashlib.sha256()
    fin_hasher.update(str(len(roots)).encode())
    fin_hasher.update(b"|")
    fin_hasher.update(str(file_count).encode())
    fin_hasher.update(b"|")
    fin_hasher.update(str(total_size).encode())
    fin_hasher.update(b"|")
    fin_hasher.update(str(newest or 0).encode())
    fin_hasher.update(b"|")
    if path_hash:
        fin_hasher.update(path_hash.encode())
    fin_hasher.update(b"|")
    fin_hasher.update(str(max_files).encode())
    final_fp = fin_hasher.hexdigest()

    return RawdataFingerprint(
        ok=len(errors) == 0,
        roots=[str(r) for r in roots],
        exists_count=exists,
        missing_roots=missing,
        file_count=file_count,
        total_size_bytes=total_size,
        newest_mtime=newest,
        newest_mtime_iso=None if newest is None else _mtime_to_iso(newest),
        relative_path_hash=path_hash,
        fingerprint=final_fp,
        truncated=truncated,
        max_files=max_files,
        warnings=warnings[:20],
        errors=errors[:20],
    )


def _mtime_to_iso(mtime: float) -> str:
    from datetime import datetime
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()
