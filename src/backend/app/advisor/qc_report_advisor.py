"""QC Report Advisor — generate human-readable QC narratives."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import (
    is_llm_enabled,
    wrap_advisor_response,
    advisor_fallback,
)


def advise_qc_report(
    qc_data: dict | None = None,
    subjects_total: int = 0,
    subjects_passed: int = 0,
) -> dict[str, Any]:
    qc_data = qc_data or {}
    failed = subjects_total - subjects_passed

    narrative = (
        f"Dataset of {subjects_total} subjects. "
        f"{subjects_passed} passed preprocessing ({round(subjects_passed / max(subjects_total, 1) * 100)}%). "
        f"{failed} flagged for review."
    )

    result = {
        "narrative": narrative,
        "subjects_total": subjects_total,
        "subjects_passed": subjects_passed,
        "subjects_failed": failed,
        "pass_rate": round(subjects_passed / max(subjects_total, 1) * 100, 1),
        "limitations": ["QC thresholds based on default values. Adjust per project requirements."],
    }

    if is_llm_enabled():
        try:
            narrative_llm = _llm_qc_narrative(qc_data, subjects_total, subjects_passed)
            result["narrative"] = narrative_llm
        except Exception:
            pass

    return wrap_advisor_response(result, "qc-report")


def _llm_qc_narrative(qc_data: dict, subjects_total: int, subjects_passed: int) -> str:
    from src.backend.app.advisor.protocol_advisor import _call_llm
    from src.backend.app.advisor.advisor_safety import get_llm_config
    import json

    config = get_llm_config()
    prompt = (
        f"Write a 2-3 sentence QC summary for a neuroimaging preprocessing run:\n"
        f"Subjects: {subjects_total} total, {subjects_passed} passed.\n"
        f"QC data: {json.dumps(qc_data, ensure_ascii=False)[:500]}\n\n"
        f"Do NOT make clinical conclusions. Just summarize quality metrics."
    )
    return _call_llm(config, prompt)
