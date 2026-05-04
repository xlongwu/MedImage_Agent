from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml
    except ImportError as exc:
        raise RuntimeError("Missing dependency: PyYAML. Install with: pip install pyyaml") from exc

    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data or {}


def ensure_memory_layout(root_dir: str = ".") -> dict[str, str]:
    root = Path(root_dir)
    global_dir = root / "memory" / "global"
    projects_dir = root / "memory" / "projects"
    sessions_dir = root / "memory" / "sessions"

    global_dir.mkdir(parents=True, exist_ok=True)
    projects_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)

    defaults = {
        "MEMORY.md": "# MedImage Agent Memory\n",
        "USER.md": "# User Memory\n",
        "ENVIRONMENT.md": "# Environment Memory\n",
    }

    for filename, content in defaults.items():
        path = global_dir / filename
        if not path.exists():
            path.write_text(content, encoding="utf-8")

    error_kb = global_dir / "ERROR_KB.yaml"
    if not error_kb.exists():
        error_kb.write_text("version: '0.1.0'\nerrors: []\n", encoding="utf-8")

    return {
        "global_dir": str(global_dir),
        "projects_dir": str(projects_dir),
        "sessions_dir": str(sessions_dir),
    }


def sanitize_project_name(project_name: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in project_name)
    return safe or "default_project"


def get_project_memory_dir(project_name: str, root_dir: str = ".") -> Path:
    ensure_memory_layout(root_dir)
    project_dir = Path(root_dir) / "memory" / "projects" / sanitize_project_name(project_name)
    project_dir.mkdir(parents=True, exist_ok=True)

    project_md = project_dir / "PROJECT.md"
    lessons_md = project_dir / "LESSONS.md"

    if not project_md.exists():
        project_md.write_text(f"# Project Memory: {project_name}\n", encoding="utf-8")
    if not lessons_md.exists():
        lessons_md.write_text(f"# Lessons: {project_name}\n", encoding="utf-8")

    return project_dir


def append_run_history(
    project_name: str,
    record: dict[str, Any],
    root_dir: str = ".",
) -> Path:
    project_dir = get_project_memory_dir(project_name, root_dir)
    history_path = project_dir / "RUN_HISTORY.jsonl"

    safe_record = dict(record)
    safe_record.pop("raw_patient_data", None)
    safe_record.pop("phi", None)

    with history_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe_record, ensure_ascii=False) + "\n")

    return history_path


def read_error_kb(root_dir: str = ".") -> dict[str, Any]:
    ensure_memory_layout(root_dir)
    return _load_yaml(Path(root_dir) / "memory" / "global" / "ERROR_KB.yaml")


def match_error_patterns(
    errors: list[str],
    root_dir: str = ".",
) -> list[dict[str, Any]]:
    kb = read_error_kb(root_dir)
    entries = kb.get("errors", []) or []

    matches: list[dict[str, Any]] = []
    joined_errors = "\n".join(errors)

    for entry in entries:
        pattern = str(entry.get("pattern", ""))
        if pattern and pattern in joined_errors:
            matches.append(entry)

    return matches
