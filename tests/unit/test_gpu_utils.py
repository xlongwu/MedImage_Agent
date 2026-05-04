from __future__ import annotations

from src.backend.app.tools.gpu_utils import detect_gpu


def test_detect_gpu_never_requires_gpu():
    result = detect_gpu()

    assert result["ok"] is True
    assert "cupy_available" in result
    assert "gpu_available" in result
    assert "warnings" in result
    assert "errors" in result
