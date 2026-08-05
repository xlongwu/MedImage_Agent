from __future__ import annotations

import json

from src.backend.app.native_preproc.orchestrator.gpu_performance_model import (
    clear_gpu_performance_model,
    performance_model_path,
    record_gpu_measurement,
)


def _compute(total: float) -> dict[str, object]:
    return {
        "actual_backend": "gpu-cupy",
        "runtime": {
            "total_seconds": total,
            "transfer_seconds": 0.1,
            "compute_seconds": total - 0.1,
        },
        "memory": {"estimated_peak_bytes": 1024},
        "validation": {
            "algorithm_version": "native_cupy_tier1_v1",
            "dtype": "float32",
            "plan": {
                "stage_id": "alff",
                "device_name": "Test GPU",
                "cupy_version": "13.6.0",
                "cuda_runtime_version": 12090,
                "driver_version": 12080,
                "estimated_input_bytes": 512,
                "estimated_peak_bytes": 1024,
                "chunk_size": 8,
            },
        },
    }


def test_gpu_performance_model_is_versioned_path_free_and_clearable(tmp_path) -> None:
    first = record_gpu_measurement(tmp_path, _compute(1.0))
    second = record_gpu_measurement(tmp_path, _compute(3.0))
    assert first is not None and first["cold_sample_count"] == 1
    assert second is not None and second["sample_count"] == 2
    payload = json.loads(performance_model_path(tmp_path).read_text(encoding="utf-8"))
    assert payload["_schema_version"] == 1
    serialized = json.dumps(payload)
    assert str(tmp_path) not in serialized
    assert clear_gpu_performance_model(tmp_path) is True
    assert clear_gpu_performance_model(tmp_path) is False
