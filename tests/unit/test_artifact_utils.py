from __future__ import annotations

import json

import pytest

from src.backend.app.tools.artifact_utils import (
    read_json_artifact,
    read_optional_json_artifact,
)


def test_read_json_artifact_remains_strict_for_missing_file(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        read_json_artifact(tmp_path / "missing.json")


def test_read_optional_json_artifact_returns_default_only_when_missing(tmp_path) -> None:
    default = {"ok": True, "items": []}

    assert read_optional_json_artifact(tmp_path / "missing.json", default) is default


def test_read_optional_json_artifact_keeps_malformed_json_strict(tmp_path) -> None:
    path = tmp_path / "malformed.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(json.JSONDecodeError):
        read_optional_json_artifact(path, {})
