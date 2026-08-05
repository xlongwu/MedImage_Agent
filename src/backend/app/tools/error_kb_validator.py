"""ERROR_KB schema validator."""
from __future__ import annotations

from typing import Any

from src.backend.app.tools.error_classifier import _load_error_kb


def validate_error_kb(kb_path: str | None = None) -> dict[str, Any]:
    kb = _load_error_kb(kb_path)
    errors: list[str] = []
    warnings: list[str] = []

    version = kb.get("version", "unknown")
    if version != "0.2.0":
        warnings.append(f"ERROR_KB version is {version}, expected 0.2.0")

    categories = kb.get("categories", {})
    if not categories:
        errors.append("No categories defined")
    else:
        required_fields = ["severity", "retryable", "patterns", "suggested_fixes"]
        for name, cat in categories.items():
            for field in required_fields:
                if field not in cat:
                    errors.append(f"Category '{name}': missing '{field}'")
            if not isinstance(cat.get("patterns"), list) or len(cat.get("patterns", [])) == 0:
                errors.append(f"Category '{name}': patterns must be non-empty list")

    return {
        "ok": len(errors) == 0,
        "version": version,
        "categories_count": len(categories),
        "errors": errors,
        "warnings": warnings,
    }
