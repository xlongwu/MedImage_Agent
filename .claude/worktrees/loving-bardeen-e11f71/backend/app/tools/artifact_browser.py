from __future__ import annotations

import json
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TEXT_EXTENSIONS = {
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".log",
    ".csv",
    ".tsv",
    ".html",
}
NIFTI_EXTENSIONS = {".nii", ".nii.gz"}
EXCLUDED_PARTS = {"third_party", ".git", "node_modules", "__pycache__", "rawdata"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _is_nifti(path: Path) -> bool:
    name = path.name.lower()
    return name.endswith(".nii") or name.endswith(".nii.gz")


def _extension(path: Path) -> str:
    name = path.name.lower()
    if name.endswith(".nii.gz"):
        return ".nii.gz"
    return path.suffix.lower()


def _allowed_roots() -> list[Path]:
    return [
        Path("work").resolve(),
        Path("reports").resolve(),
        Path("logs").resolve(),
        Path("derivatives").resolve(),
        Path("examples").resolve(),
    ]


def _is_under_allowed_root(path: Path) -> bool:
    resolved = path.resolve()
    for root in _allowed_roots():
        try:
            resolved.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _is_excluded(path: Path) -> bool:
    parts = set(path.parts)
    return any(part in EXCLUDED_PARTS for part in parts)


def _category_for(path: Path) -> str:
    text = str(path).replace("\\", "/")

    if "/pipeline_runs/" in text:
        return "pipeline_run"
    if text.startswith("reports/") or "/reports/" in text:
        return "report"
    if text.startswith("logs/") or "/logs/" in text:
        return "log"
    if "/dpabi/" in text:
        return "dpabi"
    if "/experiments/" in text:
        return "experiment"
    if text.startswith("derivatives/") or "/derivatives/" in text:
        return "derivative"
    if text.startswith("examples/") and path.suffix.lower() in {".yaml", ".yml", ".json"}:
        return "config"
    return "unknown"


def _guess_run_id(path: Path) -> str | None:
    parts = list(path.parts)

    if "pipeline_runs" in parts:
        idx = parts.index("pipeline_runs")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    if "template_instances" in parts:
        idx = parts.index("template_instances")
        if idx + 1 < len(parts):
            return parts[idx + 1]

    return None


def _preview_type(path: Path) -> str:
    ext = _extension(path)
    if ext in TEXT_EXTENSIONS:
        return "text"
    if _is_nifti(path):
        return "nifti_metadata"
    return "metadata_only"


def _artifact_record(path: Path) -> dict[str, Any]:
    stat = path.stat()
    ext = _extension(path)
    preview_type = _preview_type(path)

    return {
        "path": str(path),
        "name": path.name,
        "extension": ext,
        "size_bytes": stat.st_size,
        "modified_time": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "category": _category_for(path),
        "preview_supported": preview_type in {"text", "nifti_metadata"},
        "preview_type": preview_type,
        "mime_type": mimetypes.guess_type(str(path))[0],
        "run_id_guess": _guess_run_id(path),
    }


def build_artifact_index(
    work_dir: str = "./work",
    report_dir: str = "./reports",
    log_dir: str = "./logs",
    derivatives_dir: str = "./derivatives",
    examples_dir: str = "./examples",
) -> dict[str, Any]:
    roots = [
        Path(work_dir),
        Path(report_dir),
        Path(log_dir),
        Path(derivatives_dir),
        Path(examples_dir),
    ]

    artifacts: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []

    for root in roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file():
                continue

            if _is_excluded(path):
                continue

            try:
                if not _is_under_allowed_root(path):
                    warnings.append(f"Skipped path outside allowed roots: {path}")
                    continue

                artifacts.append(_artifact_record(path))

            except Exception as exc:
                warnings.append(f"Failed to index {path}: {exc}")

    artifacts = sorted(
        artifacts,
        key=lambda item: item.get("modified_time") or "",
        reverse=True,
    )

    out_dir = Path(work_dir) / "artifacts"
    out_dir.mkdir(parents=True, exist_ok=True)

    index_path = out_dir / "artifact_index.json"

    payload = {
        "ok": True,
        "node_id": "artifact_browser",
        "backend": "python",
        "generated_at": _now_iso(),
        "artifacts_total": len(artifacts),
        "artifacts": artifacts,
        "categories": _count_by(artifacts, "category"),
        "extensions": _count_by(artifacts, "extension"),
        "warnings": warnings,
        "errors": errors,
    }

    index_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    payload["outputs"] = [str(index_path)]
    return payload


def _count_by(items: list[dict[str, Any]], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for item in items:
        value = str(item.get(key) or "unknown")
        out[value] = out.get(value, 0) + 1
    return dict(sorted(out.items(), key=lambda pair: pair[0]))


def _read_text_preview(path: Path, max_text_bytes: int) -> dict[str, Any]:
    raw = path.read_bytes()
    truncated = len(raw) > max_text_bytes
    raw = raw[:max_text_bytes]

    text = raw.decode("utf-8", errors="replace")
    ext = _extension(path)

    parsed = None
    if ext == ".json":
        try:
            parsed = json.loads(text)
        except Exception:
            parsed = None

    if ext in {".csv", ".tsv"}:
        lines = text.splitlines()
        text = "\n".join(lines[:101])
        truncated = truncated or len(lines) > 101

    return {
        "preview_type": "text",
        "text": text,
        "parsed": parsed,
        "truncated": truncated,
        "bytes_returned": len(raw),
    }


def _nifti_metadata(path: Path) -> dict[str, Any]:
    try:
        import nibabel as nib
    except ImportError:
        return {
            "preview_type": "nifti_metadata",
            "ok": False,
            "error": "Missing dependency: nibabel. Install with: pip install nibabel",
        }

    try:
        img = nib.load(str(path))
        header = img.header

        return {
            "preview_type": "nifti_metadata",
            "ok": True,
            "shape": list(img.shape),
            "dtype": str(header.get_data_dtype()),
            "zooms": list(header.get_zooms()),
            "affine": img.affine.tolist(),
            "note": "Voxel data was not loaded or returned.",
        }
    except Exception as exc:
        return {
            "preview_type": "nifti_metadata",
            "ok": False,
            "error": str(exc),
        }


def preview_artifact(
    path: str,
    max_text_bytes: int = 200_000,
) -> dict[str, Any]:
    target = Path(path)

    if ".." in target.parts:
        return {
            "ok": False,
            "errors": ["Path traversal is not allowed."],
            "warnings": [],
        }

    if not target.exists() or not target.is_file():
        return {
            "ok": False,
            "errors": [f"Artifact file not found: {target}"],
            "warnings": [],
        }

    if _is_excluded(target):
        return {
            "ok": False,
            "errors": [f"Path is excluded from artifact preview: {target}"],
            "warnings": [],
        }

    if not _is_under_allowed_root(target):
        return {
            "ok": False,
            "errors": [f"Path is outside allowed roots: {target}"],
            "warnings": [],
        }

    record = _artifact_record(target)
    preview_type = record["preview_type"]

    if preview_type == "text":
        preview = _read_text_preview(target, max_text_bytes=max_text_bytes)
    elif preview_type == "nifti_metadata":
        preview = _nifti_metadata(target)
    else:
        preview = {
            "preview_type": "metadata_only",
            "text": None,
            "parsed": None,
            "truncated": False,
            "note": "Preview is not supported for this file type.",
        }

    return {
        "ok": True,
        "artifact": record,
        "preview": preview,
        "warnings": [],
        "errors": [],
    }
