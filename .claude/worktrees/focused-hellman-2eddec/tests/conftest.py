from __future__ import annotations

import shutil
from pathlib import Path

import pytest


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
