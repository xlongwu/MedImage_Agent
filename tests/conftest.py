from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest


# Keep module-level SQLiteDesktopStore instances created during pytest away
# from the persistent desktop database used by the local application.
_DESKTOP_STORE_ROOT = Path(tempfile.gettempdir()) / "medimage_agent_pytest"
_DESKTOP_STORE_ROOT.mkdir(parents=True, exist_ok=True)
_DESKTOP_STORE_PATH = _DESKTOP_STORE_ROOT / (
    f"desktop_state_{os.getpid()}_{uuid4().hex}.sqlite"
)
os.environ.setdefault(
    "MEDIMAGE_DESKTOP_STORE_PATH",
    str(_DESKTOP_STORE_PATH),
)


@pytest.fixture(scope="session", autouse=True)
def cleanup_desktop_store() -> None:
    yield
    for suffix in ("", "-wal", "-shm"):
        Path(f"{_DESKTOP_STORE_PATH}{suffix}").unlink(missing_ok=True)
    try:
        _DESKTOP_STORE_ROOT.rmdir()
    except OSError:
        pass


@pytest.fixture()
def tmp_workspace(tmp_path: Path) -> Path:
    workspace = tmp_path / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return workspace


@pytest.fixture()
def clean_synthetic_dir(tmp_path: Path) -> Path:
    root = tmp_path / "synthetic_bids" / "rawdata"
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)
    return root
