from __future__ import annotations

import os
import shutil
from pathlib import Path
from uuid import uuid4

import pytest


# Keep module-level SQLiteDesktopStore instances created during pytest away
# from the persistent desktop database used by the local application.
os.environ.setdefault(
    "MEDIMAGE_DESKTOP_STORE_PATH",
    str(Path(".pytest_tmp") / f"desktop_state_{os.getpid()}_{uuid4().hex}.sqlite"),
)


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
