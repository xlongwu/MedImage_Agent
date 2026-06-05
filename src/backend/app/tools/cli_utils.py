"""Small shared helpers for JSON-emitting command-line entry points."""

from __future__ import annotations

import json
from typing import Any


def emit_json(payload: Any) -> None:
    """Print one JSON document to stdout."""
    print(json.dumps(payload, ensure_ascii=False, indent=2, default=str))


def emit_json_result(payload: dict[str, Any], failure_code: int = 1) -> int:
    """Print a result payload and return a conventional process exit code."""
    emit_json(payload)
    return 0 if bool(payload.get("ok")) else failure_code
