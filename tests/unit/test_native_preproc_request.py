from __future__ import annotations

from src.backend.app.runtime.node_contract_registry import (
    get_node_contract,
    validate_and_normalize_parameters,
)
from src.backend.app.services.native_preproc_request import build_native_full_request


def test_native_request_builder_preserves_reviewed_compute_and_scientific_parameters() -> None:
    request = build_native_full_request(
        {
            "compute_policy": {
                "backend": "gpu",
                "device": "cuda:0",
                "allow_cpu_fallback": False,
                "stage_backends": {"alff": "gpu"},
            },
            "cpu_policy": {"mode": "process", "max_subject_workers": 3},
            "reference_time": 1.0,
            "fd_threshold_mm": 0.2,
            "reho_neighborhood": 19,
            "confirmations": {"confirm_reviewed_native_execution": True},
            "confirm_no_external_tools": True,
        },
        fallback_run_id="fallback-run",
    )

    assert request.run_id == "fallback-run"
    assert request.compute_policy.backend == "gpu"
    assert request.compute_policy.stage_backends == {"alff": "gpu"}
    assert request.compute_policy.allow_cpu_fallback is False
    assert request.cpu_policy.mode == "process"
    assert request.cpu_policy.max_subject_workers == 3
    assert request.reference_time == 1.0
    assert request.fd_threshold_mm == 0.2
    assert request.reho_neighborhood == 19
    assert request.confirmations.confirm_reviewed_native_execution is True
    assert request.confirmations.confirm_no_external_tools is True


def test_native_execute_contract_accepts_reviewed_resource_policies() -> None:
    contract = get_node_contract("native_preproc_full_execute")
    normalized, evidence, errors = validate_and_normalize_parameters(
        contract,
        {
            "conversion_run_id": "conv-001",
            "confirmations": {"confirm_reviewed_native_execution": True},
            "cpu_policy": {"mode": "serial", "max_subject_workers": 1},
            "compute_policy": {"backend": "gpu", "device": "cuda:0"},
        },
    )

    assert errors == []
    assert evidence is not None
    assert evidence.contract_version == "1.1.0"
    assert normalized["compute_policy"]["backend"] == "gpu"
