from __future__ import annotations

from src.backend.app.planner.approval_gate import check_approval_gate
from src.backend.app.planner.plan_adapter import adapt_reviewed_plan, classify_plan_nodes


def _native_execute_plan(params: dict[str, object] | None = None) -> dict[str, object]:
    return {
        "pipeline_id": "native-full",
        "nodes": [
            {
                "id": "native_preproc_full_execute",
                "backend": "native_python",
                "params": {
                    "input_bold": "examples/synthetic_bids/sub-001/func/sub-001_task-rest_bold.nii.gz",
                    "sidecar_json": "examples/synthetic_bids/sub-001/func/sub-001_task-rest_bold.json",
                    "output_dir": "derivatives/native-full",
                    "confirmations": {
                        "confirm_reviewed_native_execution": True,
                        "confirm_rawdata_readonly": True,
                        "confirm_no_external_tools": True,
                        "confirm_research_use_only": True,
                        "confirm_no_clinical_use": True,
                    },
                    **(params or {}),
                },
            }
        ],
    }


def _validation() -> dict[str, object]:
    return {
        "ok": True,
        "approval_required_nodes": ["native_preproc_full_execute"],
        "risk_summary": {"requires_approval": True},
    }


def test_plan_adapter_allows_confirmed_native_full_execute_node() -> None:
    plan = _native_execute_plan()

    policy = classify_plan_nodes(plan)
    adapted = adapt_reviewed_plan(plan)

    assert policy["allowed_native_preproc_nodes"] == ["native_preproc_full_execute"]
    assert policy["blocked_native_preproc_nodes"] == []
    assert policy["blocked_uncataloged_nodes"] == []
    assert adapted.ok is True


def test_plan_adapter_allows_conversion_registry_handoff_without_direct_bold_path() -> None:
    plan = _native_execute_plan({"input_bold": "", "conversion_run_id": "conv-001"})

    policy = classify_plan_nodes(plan)

    assert policy["allowed_native_preproc_nodes"] == ["native_preproc_full_execute"]
    assert policy["blocked_native_preproc_nodes"] == []


def test_plan_adapter_blocks_native_full_execute_without_confirmations_or_safe_paths() -> None:
    plan = _native_execute_plan(
        {
            "input_bold": "../rawdata/sub-001_bold.nii.gz",
            "confirmations": {"confirm_reviewed_native_execution": True},
        }
    )

    policy = classify_plan_nodes(plan)
    adapted = adapt_reviewed_plan(plan)

    assert policy["blocked_native_preproc_nodes"] == ["native_preproc_full_execute"]
    assert adapted.ok is False
    assert "native_preproc_full_execute" in " ".join(adapted.errors)


def test_approval_gate_requires_native_preprocessing_acknowledgements() -> None:
    plan = _native_execute_plan()

    result = check_approval_gate(
        plan,
        _validation(),
        {
            "approved": True,
            "approved_nodes": ["native_preproc_full_execute"],
            "rawdata_read_only_confirmed": True,
            "risk_acknowledgement": True,
            "subject_scope_confirmed": True,
            "no_external_tools_confirmed": True,
        },
    )

    assert result.ok is False
    assert result.errors[0].code == "NATIVE_PREPROC_ACKNOWLEDGEMENT_REQUIRED"


def test_approval_gate_allows_native_full_execute_with_audit_warning() -> None:
    plan = _native_execute_plan()

    result = check_approval_gate(
        plan,
        _validation(),
        {
            "approved": True,
            "approved_nodes": ["native_preproc_full_execute"],
            "native_preprocessing_acknowledgement": True,
            "no_external_tools_confirmed": True,
            "rawdata_read_only_confirmed": True,
            "risk_acknowledgement": True,
            "subject_scope_confirmed": True,
        },
    )

    assert result.ok is True
    assert result.execution_allowed is True
    assert [warning.code for warning in result.warnings] == ["NATIVE_PREPROC_APPROVED"]
