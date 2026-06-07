"""QC Dashboard module-level cache adapter.

Caches individual module results using project-scoped JSON files.
Cache keys are derived from project_id, module_id, module_version,
and rawdata fingerprint.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.backend.app.schemas.desktop import QcDashboardModuleCacheRecord

_CACHE_ROOT = Path("outputs/cache/qc_dashboard")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_slug(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in value)[:80]


def _module_version(module_id: str) -> str:
    return f"{module_id}_v1"


def build_module_cache_key(
    *,
    project_id: str,
    module_id: str,
    module_version: str | None = None,
    fingerprint: str | None = None,
    params: dict[str, Any] | None = None,
) -> str:
    """Build a deterministic SHA-256 cache key."""
    ver = module_version or _module_version(module_id)
    parts = [project_id, module_id, ver]
    if fingerprint:
        parts.append(fingerprint)
    if params:
        parts.append(json.dumps(params, sort_keys=True, default=str))
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_path(project_id: str, module_id: str, cache_key: str) -> Path:
    return _CACHE_ROOT / _safe_slug(project_id) / module_id / f"{cache_key}.json"


def load_module_cache(
    *,
    project_id: str,
    module_id: str,
    cache_key: str,
) -> tuple[dict[str, Any] | None, QcDashboardModuleCacheRecord]:
    """Load a cached module result. Returns (payload, record)."""
    path = _cache_path(project_id, module_id, cache_key)
    rec = QcDashboardModuleCacheRecord(
        module_id=module_id,
        status="miss",
        cache_key=cache_key,
        hit=False,
    )

    if not path.is_file():
        return None, rec

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        rec.status = "error"
        rec.errors = [f"Corrupt cache file: {exc}"]
        return None, rec

    payload = data.get("payload")
    if payload is None:
        rec.status = "error"
        rec.errors = ["Cache file missing 'payload' key."]
        return None, rec

    rec.status = "hit"
    rec.hit = True
    rec.stale = False
    rec.generated_at = data.get("generated_at")
    rec.fingerprint = data.get("fingerprint")
    rec.module_version = data.get("module_version")
    rec.artifact_path = str(path)
    return payload, rec


def save_module_cache(
    *,
    project_id: str,
    module_id: str,
    cache_key: str,
    payload: dict[str, Any],
    fingerprint: str | None = None,
    module_version: str | None = None,
) -> QcDashboardModuleCacheRecord:
    """Save a module result to cache. Returns the module cache record."""
    path = _cache_path(project_id, module_id, cache_key)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "module_id": module_id,
        "module_version": module_version or _module_version(module_id),
        "cache_key": cache_key,
        "fingerprint": fingerprint,
        "generated_at": _now_iso(),
        "payload": payload,
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    return QcDashboardModuleCacheRecord(
        module_id=module_id,
        status="miss",
        cache_key=cache_key,
        fingerprint=fingerprint,
        module_version=data["module_version"],
        generated_at=data["generated_at"],
        artifact_path=str(path),
        hit=False,
    )
