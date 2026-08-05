from __future__ import annotations

from src.backend.app.runtime.node_contract_registry import get_node_contract
from src.backend.app.runtime.tool_catalog import build_tool_catalog
from src.backend.app.services.approval_summary_service import ApprovalSummaryService


def test_native_conversion_has_executable_reviewed_contract() -> None:
    contract = get_node_contract("native_dicom_conversion_execute")
    catalog = {item.id: item for item in build_tool_catalog()}

    assert contract.executable is True
    assert contract.backend == "medimage-native"
    assert contract.parameter_schema["rawdata_dir"].path_access == "read"
    assert contract.parameter_schema["project_dir"].path_access == "write"
    assert catalog[contract.node_id].requires_approval is True
    assert "no-external-tools" in catalog[contract.node_id].tags


def test_native_conversion_expands_no_external_tool_confirmation() -> None:
    confirmations = ApprovalSummaryService._confirmations(
        plan={},
        node_ids=("native_dicom_conversion_execute",),
        backend_ids=("medimage-native",),
    )

    assert confirmations["conversion_scope_confirmed"] is True
    assert confirmations["no_external_tools_confirmed"] is True
    assert confirmations["external_tool_acknowledgement"] is False
