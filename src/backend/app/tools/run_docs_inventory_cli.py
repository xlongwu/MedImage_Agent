"""Docs inventory CLI — verify documentation completeness."""
from __future__ import annotations

import json
import sys

from src.backend.app.tools.docs_inventory import build_docs_inventory


def main() -> int:
    result = build_docs_inventory()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
