"""Tool Catalog API — read-only metadata endpoints.

Exposes GET /api/tools/catalog and GET /api/tools/catalog/{node_id}
for use by Plan Validator, LLM Planner, and frontend Plan Review Console.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from src.backend.app.runtime.tool_catalog import build_tool_catalog, catalog_as_dicts, get_tool_catalog_item

router = APIRouter()


@router.get("/api/tools/catalog")
def api_list_tool_catalog() -> dict[str, Any]:
    """Return the complete read-only tool catalog."""
    items = catalog_as_dicts()
    return {
        "ok": True,
        "count": len(items),
        "items": items,
    }


@router.get("/api/tools/catalog/{node_id}")
def api_get_tool_catalog_item(node_id: str) -> dict[str, Any]:
    """Return metadata for a single tool by node id."""
    try:
        item = get_tool_catalog_item(node_id)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail=f"Tool catalog item not found: {node_id}",
        )
    return {
        "ok": True,
        "item": {
            "id": item.id,
            "name": item.name,
            "backend": item.backend,
            "parallel_level": item.parallel_level,
            "description": item.description,
            "requires_approval": item.requires_approval,
            "manual_required": item.manual_required,
            "risk_level": item.risk_level,
            "inputs": item.inputs,
            "outputs": item.outputs,
            "tags": item.tags,
        },
    }
