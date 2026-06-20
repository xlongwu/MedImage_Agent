"""Structured error classifier backed by error_kb.yaml v0.2.0.

ERROR_KB is a static resource at src/backend/app/resources/error_kb.yaml.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

_DEFAULT_KB_REL = "src/backend/app/resources/error_kb.yaml"


def _resolve_kb_path(kb_path: str | None = None) -> Path:
    """Resolve error_kb.yaml robustly across environments.

    Priority:
      1. MEDIMAGE_ERROR_KB_PATH env var
      2. Walk upward from __file__ to find repo root containing src/backend/app/resources/error_kb.yaml
      3. CWD fallback
    """
    env_path = os.environ.get("MEDIMAGE_ERROR_KB_PATH")
    if env_path:
        return Path(env_path)

    # Walk upward from this file to find repo root
    current = Path(__file__).resolve().parent
    for _ in range(10):  # safety limit
        candidate = current / _DEFAULT_KB_REL
        if candidate.exists():
            return candidate
        if current == current.parent:
            break
        current = current.parent

    return Path.cwd() / _DEFAULT_KB_REL


def _load_error_kb(kb_path: str | None = None) -> dict[str, Any]:
    try:
        import yaml
    except ImportError:
        raise RuntimeError("PyYAML required")
    path = _resolve_kb_path(kb_path)
    if not path.exists():
        return {"version": "0.0.0", "categories": {}}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {"version": "0.0.0", "categories": {}}


def classify_error(
    message: str,
    kb_path: str | None = None,
) -> dict[str, Any]:
    kb = _load_error_kb(kb_path)
    categories = kb.get("categories", {})
    best_match = None
    best_score = 0

    for cat_name, cat_def in categories.items():
        patterns = cat_def.get("patterns", [])
        score = 0
        for pattern in patterns:
            if pattern.lower() in message.lower():
                score += 1
        if score > best_score:
            best_score = score
            best_match = cat_name

    if best_match and best_score > 0:
        cat = categories[best_match]
        return {
            "classified": True,
            "category": best_match,
            "severity": cat.get("severity", "unknown"),
            "retryable": cat.get("retryable", False),
            "human_action_required": cat.get("human_action_required", True),
            "likely_causes": cat.get("likely_causes", []),
            "suggested_fixes": cat.get("suggested_fixes", []),
            "affected_backends": cat.get("affected_backends", []),
            "match_score": best_score,
        }

    return {
        "classified": False,
        "category": "UNKNOWN_ERROR",
        "severity": "medium",
        "retryable": False,
        "human_action_required": True,
        "likely_causes": [],
        "suggested_fixes": ["Manual review required"],
        "affected_backends": [],
        "match_score": 0,
    }


def classify_errors_batch(
    errors: list[str],
    kb_path: str | None = None,
) -> list[dict[str, Any]]:
    return [classify_error(msg, kb_path) for msg in errors]
