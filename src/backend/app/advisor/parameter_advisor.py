"""Parameter Advisor — explain and suggest preprocessing parameters."""
from __future__ import annotations

from typing import Any

from src.backend.app.advisor.advisor_safety import (
    is_llm_enabled,
    wrap_advisor_response,
    advisor_fallback,
)


_PARAMETER_KNOWLEDGE = {
    "filter_band": {
        "explanation": "Band-pass filter range for resting-state fMRI. 0.01-0.08 Hz is the standard resting-state band (periods 12.5-125s), capturing low-frequency fluctuations while removing physiological noise.",
        "candidates": [[0.01, 0.08], [0.01, 0.1], [0.008, 0.09]],
        "risks": [
            "Too wide (>0.15 Hz) may include respiratory noise",
            "Too narrow may miss relevant neural signal",
        ],
    },
    "smoothing_fwhm": {
        "explanation": "Gaussian smoothing kernel FWHM in mm. Typically 2-3x voxel size. 6mm is common for 2-3mm voxels.",
        "candidates": [[4, 4, 4], [6, 6, 6], [8, 8, 8]],
        "risks": [
            "Too large reduces spatial specificity",
            "Too small may leave residual noise",
        ],
    },
    "tr": {
        "explanation": "Repetition Time — the interval between consecutive volume acquisitions. Determines Nyquist frequency (1/(2*TR)).",
        "candidates": [],
        "risks": [
            "Long TR (>3s) reduces temporal degrees of freedom",
            "Short TR (<0.5s) may require multiband acquisition",
        ],
    },
    "nuisance_model": {
        "explanation": "Confound regression model. Friston24 includes 6 motion params + derivatives + squares. aCompCor adds CSF/WM signals.",
        "candidates": ["friston24", "acompcor", "friston24+acompcor"],
        "risks": [
            "Too many regressors may remove signal of interest",
            "Global signal regression is controversial in rs-fMRI",
        ],
    },
}


def advise_parameters(parameters: dict | None = None) -> dict[str, Any]:
    parameters = parameters or {}
    explanations = {}
    candidates = {}
    risks = []

    for param_name, value in parameters.items():
        kb = _PARAMETER_KNOWLEDGE.get(param_name)
        if kb:
            explanations[param_name] = kb["explanation"]
            candidates[param_name] = kb["candidates"]
            risks.extend(kb["risks"])
        else:
            explanations[param_name] = f"No knowledge base entry for '{param_name}'."

    result = {
        "explanations": explanations,
        "candidate_values": candidates,
        "risks": list(set(risks))[:5],
        "requires_confirmation": True,
    }

    if is_llm_enabled():
        try:
            llm_result = _llm_parameter_advice(parameters)
            result.update(llm_result)
        except Exception:
            pass

    return wrap_advisor_response(result, "parameters")


def _llm_parameter_advice(parameters: dict) -> dict:
    from src.backend.app.advisor.protocol_advisor import _call_llm
    from src.backend.app.advisor.advisor_safety import get_llm_config
    import json

    config = get_llm_config()
    prompt = (
        f"Explain these neuroimaging preprocessing parameters briefly (max 1 sentence each):\n"
        f"{json.dumps(parameters, ensure_ascii=False)}\n\n"
        f"For each parameter, state what it does and any risks. Be concise."
    )
    explanation = _call_llm(config, prompt)
    return {"llm_explanation": explanation}
