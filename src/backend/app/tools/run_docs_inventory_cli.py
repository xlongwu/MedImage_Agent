"""Docs inventory CLI — verify documentation completeness."""
from __future__ import annotations

from src.backend.app.tools.cli_utils import emit_json_result
from src.backend.app.tools.docs_inventory import build_docs_inventory


def main() -> int:
    result = build_docs_inventory()
    return emit_json_result(result, failure_code=2)


if __name__ == "__main__":
    raise SystemExit(main())
