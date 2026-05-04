"""Unified advisor router — dispatch to appropriate advisor by type."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import wrap_advisor_response


def route_advisor(advisor_type: str, input_data: dict | None = None) -> dict[str, Any]:
    """Route to the appropriate advisor based on type."""
    input_data = input_data or {}

    if advisor_type == "protocol":
        from src.backend.app.advisor.protocol_advisor import advise_protocol
        return advise_protocol(
            modality=input_data.get("modality", "rs-fMRI"),
            task_goal=input_data.get("task_goal", ""),
            tr=input_data.get("tr", 2.0),
            slice_count=input_data.get("slice_count", 32),
            has_fieldmap=input_data.get("has_fieldmap", False),
            available_data=input_data.get("available_data", ["T1w", "BOLD"]),
            constraints=input_data.get("constraints", []),
        )

    elif advisor_type == "error":
        from src.backend.app.advisor.error_advisor import advise_error
        return advise_error(
            error_message=input_data.get("error_message", ""),
            node_id=input_data.get("node_id", ""),
            backend=input_data.get("backend", "python"),
            error_category=input_data.get("error_category", "UNKNOWN_ERROR"),
            subject_id=input_data.get("subject_id", ""),
        )

    elif advisor_type == "qc-report":
        from src.backend.app.advisor.qc_report_advisor import advise_qc_report
        return advise_qc_report(
            qc_data=input_data.get("qc_data", {}),
            subjects_total=input_data.get("subjects_total", 0),
            subjects_passed=input_data.get("subjects_passed", 0),
        )

    elif advisor_type == "parameters":
        from src.backend.app.advisor.parameter_advisor import advise_parameters
        return advise_parameters(parameters=input_data.get("parameters", {}))

    elif advisor_type == "docs-qa":
        from src.backend.app.advisor.docs_qa_advisor import advise_docs_qa
        return advise_docs_qa(
            question=input_data.get("question", ""),
            context_docs=input_data.get("context_docs", []),
        )

    else:
        return wrap_advisor_response({
            "error": f"Unknown advisor_type: {advisor_type}",
            "available_types": ["protocol", "error", "qc-report", "parameters", "docs-qa"],
        }, advisor_type, fallback=True)
