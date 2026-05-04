from __future__ import annotations

from pathlib import Path


class PathSafetyError(Exception):
    pass


ALLOWED_READ_DIRS = [
    "examples",
    "work",
    "logs",
    "reports",
    "memory",
    "specs",
]

ALLOWED_TEXT_SUFFIXES = {
    ".json",
    ".yaml",
    ".yml",
    ".md",
    ".txt",
    ".csv",
    ".html",
    ".log",
}


def get_repo_root() -> Path:
    return Path.cwd().resolve()


def resolve_under_root(path: str | Path) -> Path:
    root = get_repo_root()
    target = Path(path)

    if not target.is_absolute():
        target = root / target

    target = target.resolve()

    try:
        target.relative_to(root)
    except ValueError as exc:
        raise PathSafetyError(f"Path escapes repository root: {path}") from exc

    return target


def is_allowed_read_path(path: str | Path) -> bool:
    try:
        root = get_repo_root()
        target = resolve_under_root(path)
        rel = target.relative_to(root)

        if not rel.parts:
            return False

        if rel.parts[0] not in ALLOWED_READ_DIRS:
            return False

        if target.suffix.lower() not in ALLOWED_TEXT_SUFFIXES:
            return False

        return target.is_file()
    except Exception:
        return False


def assert_allowed_read_path(path: str | Path) -> Path:
    target = resolve_under_root(path)

    if not is_allowed_read_path(target):
        raise PathSafetyError(
            f"File is not allowed for API reading: {path}. "
            f"Allowed folders: {ALLOWED_READ_DIRS}; "
            f"allowed suffixes: {sorted(ALLOWED_TEXT_SUFFIXES)}"
        )

    return target


def read_safe_text_file(path: str | Path) -> dict:
    target = assert_allowed_read_path(path)
    content = target.read_text(encoding="utf-8", errors="replace")

    return {
        "ok": True,
        "path": str(target),
        "relative_path": str(target.relative_to(get_repo_root())),
        "content": content,
        "size_bytes": target.stat().st_size,
    }
