"""Protocol Advisor — recommend preprocessing pipeline templates."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import (
    is_llm_enabled,
    get_llm_config,
    wrap_advisor_response,
    advisor_fallback,
)


def advise_protocol(
    modality: str = "rs-fMRI",
    task_goal: str = "",
    tr: float = 2.0,
    slice_count: int = 32,
    has_fieldmap: bool = False,
    available_data: list[str] | None = None,
    constraints: list[str] | None = None,
) -> dict[str, Any]:
    available_data = available_data or ["T1w", "BOLD"]
    constraints = constraints or []

    if not is_llm_enabled():
        return _deterministic_protocol_advice(
            modality, task_goal, tr, slice_count, has_fieldmap, available_data, constraints
        )

    # LLM path (when configured)
    try:
        return _llm_protocol_advice(
            modality, task_goal, tr, slice_count, has_fieldmap, available_data, constraints
        )
    except Exception:
        return advisor_fallback("protocol")


def _deterministic_protocol_advice(
    modality: str, task_goal: str, tr: float, slice_count: int,
    has_fieldmap: bool, available_data: list[str], constraints: list[str],
) -> dict[str, Any]:
    has_matlab = "no MATLAB license" not in str(constraints).lower() and "matlab not available" not in str(constraints).lower()

    if modality == "rs-fMRI":
        if has_matlab:
            template = "rsfmri_spm_standard_v1"
        else:
            template = "rsfmri_python_quickstart"
    else:
        template = "generic_preprocessing"

    suggestions = {
        "slice_timing_reference": "middle_slice",
        "smoothing_fwhm": [6, 6, 6],
        "filter_band": [0.01, 0.08],
        "nuisance_model": "friston24",
        "tr": tr,
    }

    warnings = []
    if not has_fieldmap:
        warnings.append("No fieldmap available; distortion correction will be skipped.")
    if not has_matlab:
        warnings.append("MATLAB not available; using Python-only pipeline (limited normalization).")

    return wrap_advisor_response({
        "recommended_pipeline_template": template,
        "parameter_suggestions": suggestions,
        "warnings": warnings,
        "unsupported_items": [
            "Fieldmap distortion correction (requires fieldmap data)",
        ] if not has_fieldmap else [],
    }, "protocol")


def _llm_protocol_advice(
    modality: str, task_goal: str, tr: float, slice_count: int,
    has_fieldmap: bool, available_data: list[str], constraints: list[str],
) -> dict[str, Any]:
    import json, os, urllib.request

    config = get_llm_config()
    prompt = f"""You are a medical imaging protocol advisor. Recommend ONLY, never execute.
Modality: {modality}
Goal: {task_goal}
TR: {tr}s, Slices: {slice_count}
Fieldmap: {has_fieldmap}
Available data: {available_data}
Constraints: {constraints}

Respond with JSON containing: recommended_pipeline_template, parameter_suggestions, warnings (list), unsupported_items (list)."""

    response = _call_llm(config, prompt)
    try:
        data = json.loads(response)
    except json.JSONDecodeError:
        data = {"raw_response": response}

    return wrap_advisor_response(data, "protocol")


def _call_llm(config: dict, prompt: str) -> str:
    import json, urllib.request

    api_key = __import__("os").environ.get("MEDIMAGE_LLM_API_KEY", "")
    base_url = config.get("base_url") or "https://api.openai.com/v1"
    model = config.get("model", "gpt-4o-mini")

    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500,
        "temperature": 0.3,
    }).encode()

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read())
    return result["choices"][0]["message"]["content"]
