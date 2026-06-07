"""QC Dashboard fingerprint root discovery — pure metadata helper.

Collects project-scoped filesystem roots for fingerprinting.
No filesystem writes, no external tools, no user-supplied paths.
"""

from __future__ import annotations

from typing import Any


def collect_qc_dashboard_fingerprint_roots(project_metadata: dict[str, Any] | None) -> list[str]:
    """Collect unique roots from project metadata.

    Returns a deduplicated list of root paths in order of discovery:
    rawdata_dir, import_roots entries, import_records path/root/output_dir.
    """
    roots: list[str] = []
    seen: set[str] = set()

    def _add(path_str: str) -> None:
        if not path_str or not isinstance(path_str, str):
            return
        cleaned = path_str.strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            roots.append(cleaned)

    if not isinstance(project_metadata, dict):
        return roots

    # rawdata_dir
    _add(project_metadata.get("rawdata_dir", ""))

    # import_roots (list or string)
    import_roots = project_metadata.get("import_roots") or project_metadata.get("import_root")
    if isinstance(import_roots, list):
        for ir in import_roots:
            _add(str(ir) if ir else "")
    elif isinstance(import_roots, str):
        _add(import_roots)

    # import_records
    import_records = project_metadata.get("import_records")
    if isinstance(import_records, list):
        for rec in import_records:
            if isinstance(rec, dict):
                for key in ("path", "root", "output_dir"):
                    val = rec.get(key)
                    if val and isinstance(val, str):
                        _add(val)
                        break  # one per record

    return roots
