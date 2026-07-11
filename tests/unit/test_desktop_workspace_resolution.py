from __future__ import annotations

from pathlib import Path

import src.backend.app.desktop_launcher_entry as launcher_entry
from src.backend.app.desktop_launcher_entry import (
    _default_packaged_workspace,
    _find_repository_root,
)


def test_packaged_workspace_uses_repository_workspace_when_available(tmp_path: Path):
    repository = tmp_path / "MedImage_Agent"
    executable_dir = repository / "desktop" / "packaging" / "dist" / "launcher"
    executable_dir.mkdir(parents=True)
    (repository / "desktop" / "electron").mkdir(parents=True)
    (repository / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")

    assert _find_repository_root(executable_dir) == repository
    assert _default_packaged_workspace(executable_dir) == repository / "workspace"


def test_packaged_workspace_falls_back_beside_executable(tmp_path: Path, monkeypatch):
    executable_dir = tmp_path / "standalone"
    executable_dir.mkdir()
    monkeypatch.setattr(launcher_entry, "_find_repository_root", lambda _path: None)

    assert _default_packaged_workspace(executable_dir) == executable_dir / "workspace"
