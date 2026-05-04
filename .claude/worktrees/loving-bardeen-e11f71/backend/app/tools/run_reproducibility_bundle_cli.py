from __future__ import annotations

import json
import sys

from backend.app.tools.reproducibility_bundle import (
    create_reproducibility_bundle,
    list_reproducibility_bundles,
    inspect_reproducibility_bundle,
)


def main() -> int:
    args = sys.argv[1:]

    if args and args[0] == "--list":
        result = list_reproducibility_bundles()
    elif args and args[0] == "--inspect":
        if len(args) < 2:
            print(json.dumps({"ok": False, "errors": ["Missing bundle_id after --inspect"]}, indent=2))
            return 2
        result = inspect_reproducibility_bundle(args[1])
    elif args and args[0] == "--create":
        bundle_id = args[1] if len(args) > 1 else None
        result = create_reproducibility_bundle(bundle_id=bundle_id)
    else:
        result = create_reproducibility_bundle()

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
