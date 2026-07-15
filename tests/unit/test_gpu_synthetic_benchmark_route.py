from __future__ import annotations

import asyncio

import pytest
from fastapi import HTTPException

from src.backend.app.api.gpu_routes import gpu_synthetic_benchmark


def test_synthetic_benchmark_requires_reviewed_execution_contract():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(gpu_synthetic_benchmark({"shape": [2, 2, 2, 8]}))

    assert exc_info.value.status_code == 410
    assert exc_info.value.detail["error_code"] == "EXECUTION_CONTRACT_REQUIRED"
    assert exc_info.value.detail["entry_id"] == "gpu.synthetic_benchmark"
