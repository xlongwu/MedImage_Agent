from __future__ import annotations

import pytest

from backend.app.runtime.path_safety import PathSafetyError, assert_allowed_read_path


def test_path_safety_rejects_path_traversal():
    with pytest.raises(PathSafetyError):
        assert_allowed_read_path("../../etc/passwd")


def test_path_safety_rejects_third_party():
    with pytest.raises(PathSafetyError):
        assert_allowed_read_path("third_party/spm12/spm.m")
