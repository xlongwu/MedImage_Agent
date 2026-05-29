from __future__ import annotations

from typing import Any


DPABI_SINGLE_FUNCTION_CONTRACTS: dict[str, dict[str, Any]] = {
    "y_Smooth": {
        "description": "Spatial smoothing for one image or image list.",
        "parameters": {"fwhm": {"type": "list[float]", "default": [6, 6, 6], "length": 3}},
        "expected_outputs": ["smoothed NIfTI"],
        "qc": ["output_exists", "fwhm"],
    },
    "y_Filter": {
        "description": "Temporal band-pass filtering.",
        "parameters": {
            "tr": {"type": "float", "default": 2.0, "min": 0.001},
            "band": {"type": "list[float]", "default": [0.01, 0.08], "length": 2},
        },
        "expected_outputs": ["filtered NIfTI"],
        "qc": ["band", "tr", "output_exists"],
    },
    "y_RegressOutImgCovariates": {
        "description": "Image covariate regression for nuisance removal.",
        "parameters": {"covariate_def": {"type": "string", "default": "Friston24"}},
        "expected_outputs": ["residual NIfTI"],
        "qc": ["covariate_def", "output_exists"],
    },
    "y_alff_falff": {
        "description": "ALFF/fALFF metric computation.",
        "parameters": {
            "tr": {"type": "float", "default": 2.0, "min": 0.001},
            "band": {"type": "list[float]", "default": [0.01, 0.08], "length": 2},
        },
        "expected_outputs": ["ALFF NIfTI", "fALFF NIfTI"],
        "qc": ["band", "tr", "output_exists"],
    },
    "y_Reho": {
        "description": "Regional Homogeneity metric computation.",
        "parameters": {"neighborhood": {"type": "int", "default": 27, "allowed": [7, 19, 27]}},
        "expected_outputs": ["ReHo NIfTI"],
        "qc": ["neighborhood", "output_exists"],
    },
    "y_ROItseries": {
        "description": "ROI time series extraction.",
        "parameters": {"atlas_file": {"type": "path", "required": False}},
        "expected_outputs": ["ROI time series table"],
        "qc": ["atlas_file", "output_exists"],
    },
    "y_FC": {
        "description": "Functional connectivity matrix computation.",
        "parameters": {"atlas_file": {"type": "path", "required": False}},
        "expected_outputs": ["FC matrix"],
        "qc": ["atlas_file", "output_exists"],
    },
}


def get_dpabi_single_function_contract(function_name: str) -> dict[str, Any] | None:
    return DPABI_SINGLE_FUNCTION_CONTRACTS.get(function_name)
