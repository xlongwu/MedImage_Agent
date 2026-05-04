from __future__ import annotations
import json; from pathlib import Path; from typing import Any

def build_docs_inventory() -> dict[str, Any]:
    docs_dir = Path("docs"); docs_dir.mkdir(parents=True, exist_ok=True)
    found = []; missing: list[str] = []; w: list[str] = []; e: list[str] = []

    required = [
        ("README.md", Path("README.md")),
        ("specs/", Path("specs")),
        ("docs/architecture.md", docs_dir/"architecture.md"),
        ("docs/user_guide.md", docs_dir/"user_guide.md"),
        ("docs/developer_guide.md", docs_dir/"developer_guide.md"),
        ("docs/safety_and_limitations.md", docs_dir/"safety_and_limitations.md"),
    ]

    for name, path in required:
        ok = path.exists() if path.suffix else path.is_dir()
        if ok: found.append(name)
        else: missing.append(name); w.append(f"Missing: {name}")

    specs_count = len(list(Path("specs").glob("*.md"))) if Path("specs").is_dir() else 0
    docs_count = len(list(docs_dir.glob("*.md")))

    out = Path("outputs/reports/docs_inventory"); out.mkdir(parents=True, exist_ok=True)
    summary = {
        "ok": len(missing) == 0, "node_id": "docs_inventory", "backend": "python",
        "docs_found": len(found), "docs_missing": len(missing),
        "specs_count": specs_count, "docs_md_count": docs_count,
        "found": found, "missing": missing, "warnings": w, "errors": e,
    }
    (out/"docs_inventory.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = ["# Documentation Inventory", "", f"- Found: {len(found)}", f"- Missing: {len(missing)}", f"- Specs: {specs_count}", f"- Docs MD: {docs_count}", "", "## Found"]
    for f in found: lines.append(f"- {f}")
    lines += ["", "## Missing"]
    for m in missing: lines.append(f"- {m}")
    (out/"docs_inventory_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    summary["outputs"] = [str(out/"docs_inventory.json"), str(out/"docs_inventory_report.md")]
    return summary
