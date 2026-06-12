"""Audit Record Read-only API — GET /api/audit/records."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api._errors import raise_api_error
from src.backend.app.core.exceptions import StateStoreError

router = APIRouter()

AUDIT_RECORD_DIR = Path("outputs/reports/audit_records")

_VALID_AUDIT_ID = re.compile(r"^[a-zA-Z0-9_-]+$")


def _list_records() -> list[dict[str, Any]]:
    if not AUDIT_RECORD_DIR.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for f in sorted(AUDIT_RECORD_DIR.glob("*.json"), key=lambda p: -p.stat().st_mtime):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            continue
        records.append({
            "audit_id": data.get("audit_id"),
            "created_at": data.get("created_at"),
            "event_type": data.get("event_type"),
            "plan_hash": data.get("plan_hash"),
            "validation_hash": data.get("validation_hash"),
            "approval_hash": data.get("approval_hash"),
            "actor": data.get("actor"),
            "source": data.get("source"),
            "path": str(f),
        })
    return records


@router.get("/api/audit/records")
def api_list_audit_records() -> dict[str, Any]:
    records = _list_records()
    return {"ok": True, "count": len(records), "items": records}


@router.get("/api/audit/records/{audit_id}")
def api_get_audit_record(audit_id: str) -> dict[str, Any]:
    # Path traversal guard
    if not _VALID_AUDIT_ID.fullmatch(audit_id):
        raise HTTPException(status_code=400, detail=f"Invalid audit_id: {audit_id}")
    if ".." in audit_id or "/" in audit_id or "\\" in audit_id:
        raise HTTPException(status_code=400, detail=f"Invalid audit_id: {audit_id}")

    # Find file by audit_id prefix (exact match preferred)
    target = None
    if AUDIT_RECORD_DIR.is_dir():
        for f in AUDIT_RECORD_DIR.glob("*.json"):
            if f.stem == audit_id or f.stem.startswith(audit_id):
                target = f
                break

    if target is None:
        raise HTTPException(status_code=404, detail=f"Audit record not found: {audit_id}")

    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        raise_api_error(
            exc,
            error_cls=StateStoreError,
            message=f"Failed to read audit record: {exc}",
        )

    return {"ok": True, "record": data}
