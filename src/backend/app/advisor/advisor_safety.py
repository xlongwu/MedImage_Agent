"""LLM Advisor safety gate — enforce advice-only, no-execution policy."""
from __future__ import annotations

from typing import Any

SAFETY_FLAGS = {
    "advice_only": True,
    "requires_human_confirmation": True,
    "will_execute_pipeline": False,
    "will_modify_data": False,
    "clinical_conclusion": False,
}


def wrap_advisor_response(data: dict[str, Any], advisor_type: str, fallback: bool = False) -> dict[str, Any]:
    """Wrap any advisor output with mandatory safety flags."""
    result = dict(data)
    result.update(SAFETY_FLAGS)
    result["advisor_type"] = advisor_type
    result["fallback"] = fallback
    return result


def advisor_fallback(advisor_type: str) -> dict[str, Any]:
    """Deterministic fallback when LLM is not configured."""
    return wrap_advisor_response({
        "message": (
            f"LLM advisor '{advisor_type}' is not enabled. "
            "Set MEDIMAGE_LLM_ENABLED=true and configure MEDIMAGE_LLM_API_KEY to enable LLM-powered advice. "
            "The system continues to operate with deterministic pipeline execution."
        ),
        "suggestion": "Use deterministic tools (SessionDB, Insights, Error KB) for operational guidance.",
    }, advisor_type, fallback=True)


def is_llm_enabled() -> bool:
    """Check if LLM advisor is configured and enabled."""
    import os
    enabled = os.environ.get("MEDIMAGE_LLM_ENABLED", "false").lower() == "true"
    has_key = bool(os.environ.get("MEDIMAGE_LLM_API_KEY", ""))
    return enabled and has_key


def get_llm_config() -> dict[str, str]:
    """Get LLM configuration from environment."""
    import os
    return {
        "enabled": os.environ.get("MEDIMAGE_LLM_ENABLED", "false"),
        "provider": os.environ.get("MEDIMAGE_LLM_PROVIDER", "openai"),
        "model": os.environ.get("MEDIMAGE_LLM_MODEL", "gpt-4o-mini"),
        "base_url": os.environ.get("MEDIMAGE_LLM_BASE_URL", ""),
    }
