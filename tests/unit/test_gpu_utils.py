from __future__ import annotations

import builtins
import json

import pytest

from src.backend.app.tools.gpu_utils import (
    apply_gpu_guard,
    detect_gpu,
    is_scoped_derivative_path,
    write_gpu_provenance,
)


def test_detect_gpu_never_requires_gpu():
    result = detect_gpu()

    assert result["ok"] is True
    assert "cupy_available" in result
    assert "gpu_available" in result
    assert "warnings" in result
    assert "errors" in result


def test_detect_gpu_distinguishes_import_failure(monkeypatch: pytest.MonkeyPatch):
    original_import = builtins.__import__

    def reject_cupy(name, *args, **kwargs):
        if name == "cupy":
            raise ImportError("packaged CuPy dependency missing")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", reject_cupy)
    result = detect_gpu()

    assert result["capability_error_code"] == "CUPY_IMPORT_FAILED"
    assert "packaged CuPy dependency missing" in result["warnings"][0]


def test_scoped_derivative_path_blocks_rawdata_and_external_paths(tmp_path):
    derivatives = tmp_path / "derivatives"
    func = derivatives / "func.nii"
    raw = tmp_path / "rawdata" / "func.nii"
    external = tmp_path / "other" / "func.nii"
    func.parent.mkdir(parents=True)
    raw.parent.mkdir(parents=True)
    external.parent.mkdir(parents=True)
    func.write_bytes(b"\x00")
    raw.write_bytes(b"\x00")
    external.write_bytes(b"\x00")

    assert is_scoped_derivative_path(func, derivatives) is True
    assert is_scoped_derivative_path(raw, derivatives) is False
    assert is_scoped_derivative_path(external, derivatives) is False


def test_apply_gpu_guard_updates_result_without_gpu_allocation():
    result = {"ok": True, "errors": [], "warnings": []}

    ok = apply_gpu_guard(
        result,
        device="auto",
        functional_shape=(2, 3),
        dtype_bytes=4,
        batch_size=1,
        timeout_seconds=10,
        require_gpu=False,
        torch_cuda_available=False,
        device_count=0,
        active_jobs=0,
        max_concurrent_jobs=1,
        max_elements=100,
        max_bytes=1024,
    )

    assert ok is True
    assert result["ok"] is True
    assert result["gpu_guard"]["ok"] is True
    assert result["estimated_bytes"] == 24
    assert result["warnings"] == ["torch.cuda.is_available() is False."]


def test_write_gpu_provenance_uses_shared_json_format(tmp_path):
    provenance_path = write_gpu_provenance(tmp_path / "gpu" / "run", {"subject_id": "sub-001"})

    assert provenance_path.name == "provenance.json"
    assert json.loads(provenance_path.read_text(encoding="utf-8")) == {"subject_id": "sub-001"}
