from __future__ import annotations

import pytest

from src.backend.app.schemas.pipeline_schema import PipelineValidationError, validate_pipeline_dict


def test_pipeline_schema_accepts_minimal_valid_pipeline():
    spec = validate_pipeline_dict({
        "pipeline_id": "test_pipeline",
        "version": "0.1.0",
        "modality": "test",
        "description": "test",
        "execution": {"run_id": "run_test"},
        "nodes": [
            {
                "id": "node_a",
                "name": "Node A",
                "agent": "system",
                "backend": "python",
                "depends_on": [],
                "inputs": [],
                "outputs": [],
                "params": {},
                "parallel_level": "project",
                "gpu_supported": False,
                "cache": False,
            }
        ],
    })

    assert spec.pipeline_id == "test_pipeline"
    assert len(spec.nodes) == 1


def test_pipeline_schema_rejects_missing_dependency():
    with pytest.raises(PipelineValidationError):
        validate_pipeline_dict({
            "pipeline_id": "bad_pipeline",
            "version": "0.1.0",
            "modality": "test",
            "description": "bad",
            "execution": {"run_id": "run_bad"},
            "nodes": [
                {
                    "id": "node_b",
                    "name": "Node B",
                    "agent": "system",
                    "backend": "python",
                    "depends_on": ["missing_node"],
                    "inputs": [],
                    "outputs": [],
                    "params": {},
                    "parallel_level": "project",
                    "gpu_supported": False,
                    "cache": False,
                }
            ],
        })
