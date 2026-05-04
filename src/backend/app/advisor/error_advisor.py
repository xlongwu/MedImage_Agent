"""Error Advisor — explain errors and suggest fixes using Error KB."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import (
    is_llm_enabled,
    wrap_advisor_response,
    advisor_fallback,
)


def advise_error(
    error_message: str = "",
    node_id: str = "",
    backend: str = "python",
    error_category: str = "UNKNOWN_ERROR",
    subject_id: str = "",
) -> dict[str, Any]:
    # Always use deterministic error classifier first
    from src.backend.app.tools.error_classifier import classify_error

    classified = classify_error(error_message) if error_message else {"classified": False, "category": "UNKNOWN_ERROR"}

    base = {
        "error_category": classified.get("category", error_category),
        "classified": classified.get("classified", False),
        "severity": classified.get("severity", "medium"),
        "retryable": classified.get("retryable", False),
        "likely_causes": classified.get("likely_causes", []),
        "suggested_fixes": classified.get("suggested_fixes", []),
        "node_id": node_id,
        "subject_id": subject_id,
        "backend": backend,
    }

    if is_llm_enabled():
        try:
            explanation = _llm_error_explanation(error_message, node_id, backend, classified.get("category", "UNKNOWN"), subject_id)
            base["plain_language_explanation"] = explanation
        except Exception:
            base["plain_language_explanation"] = _deterministic_explanation(classified, error_message, subject_id)
    else:
        base["plain_language_explanation"] = _deterministic_explanation(classified, error_message, subject_id)

    return wrap_advisor_response(base, "error")


def _deterministic_explanation(classified: dict, error_message: str, subject_id: str) -> str:
    if not classified.get("classified"):
        if "not found" in error_message.lower():
            return f"File or resource not found. Check if the expected derivative exists and upstream processing completed successfully."
        return f"Unclassified error: {error_message[:200]}. Review logs and run error diagnosis."

    category = classified.get("category", "")
    causes = ", ".join(classified.get("likely_causes", [])[:3])
    if subject_id:
        return f"Error (category: {category}) occurred for subject {subject_id}. Likely causes: {causes}."
    return f"Error (category: {category}). Likely causes: {causes}."


def _llm_error_explanation(error_message: str, node_id: str, backend: str, category: str, subject_id: str) -> str:
    from src.backend.app.advisor.protocol_advisor import _call_llm
    from src.backend.app.advisor.advisor_safety import get_llm_config

    config = get_llm_config()
    prompt = (
        f"Explain this medical imaging pipeline error in plain language (max 3 sentences):\n"
        f"Error: {error_message[:300]}\nNode: {node_id}\nBackend: {backend}\n"
        f"Category: {category}\nSubject: {subject_id}\n\n"
        f"Do NOT suggest executing anything. Just explain what went wrong."
    )
    return _call_llm(config, prompt)
