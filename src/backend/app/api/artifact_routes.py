"""Bundle, documentation inventory, and deployment profile route handlers."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.api.models import BundleCreateRequest

router = APIRouter()


@router.get("/api/deployment/profile")
def api_get_deployment_profile() -> dict[str, Any]:
    from src.backend.app.tools.deployment_profile import build_deployment_profile

    result = build_deployment_profile()
    return result


# ── rs-fMRI chain validation ──────────────────────────────────────────────

@router.post("/api/bundle/create")
def api_bundle_create(request: BundleCreateRequest) -> dict[str, Any]:
    from src.backend.app.tools.reproducibility_bundle import create_bundle

    result = create_bundle(
        bundle_id=request.bundle_id,
        include_logs=request.include_logs,
        include_reports=request.include_reports,
        include_artifact_index=request.include_artifact_index,
        max_file_size_bytes=request.max_file_size_bytes,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/api/bundle/preview")
def api_bundle_preview() -> dict[str, Any]:
    from src.backend.app.tools.reproducibility_bundle import preview_bundle

    result = preview_bundle("./work")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result)
    return result

@router.get("/api/bundle/download-info")
def api_bundle_download_info() -> dict[str, Any]:
    bundle_dir = Path("outputs/exports") / "bundles"
    bundles = []
    for path in sorted(bundle_dir.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
        bundles.append({
            "name": path.name,
            "path": str(path),
            "size_bytes": path.stat().st_size,
            "created": path.stat().st_mtime,
        })

    return {
        "ok": True,
        "total": len(bundles),
        "bundles": bundles,
    }


# ── Docs inventory ────────────────────────────────────────────────────────

@router.get("/api/docs/inventory")
def api_docs_inventory() -> dict[str, Any]:
    from src.backend.app.tools.docs_inventory import build_docs_inventory

    result = build_docs_inventory()
    return result


# ── Advisor endpoints ─────────────────────────────────────────────────────
