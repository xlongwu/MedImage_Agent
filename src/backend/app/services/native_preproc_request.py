"""Build the native preprocessing request shared by readiness and execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.backend.app.schemas.native_preproc_api import (
    NativeFullPreprocConfirmations,
    NativeFullPreprocRequest,
)

_CONFIRMATION_FIELDS = tuple(NativeFullPreprocConfirmations.model_fields)


def build_native_full_request(
    params: Mapping[str, Any] | None,
    *,
    fallback_run_id: str = "",
) -> NativeFullPreprocRequest:
    """Validate every supported request field without readiness/execution drift."""

    values = dict(params or {})
    request_values = {
        field_name: values[field_name]
        for field_name in NativeFullPreprocRequest.model_fields
        if field_name in values and field_name != "confirmations"
    }
    request_values["run_id"] = str(values.get("run_id") or fallback_run_id)

    nested = values.get("confirmations")
    confirmation_values = dict(nested) if isinstance(nested, Mapping) else {}
    for field_name in _CONFIRMATION_FIELDS:
        if values.get(field_name) is True:
            confirmation_values[field_name] = True
    request_values["confirmations"] = confirmation_values
    return NativeFullPreprocRequest.model_validate(request_values)


__all__ = ["build_native_full_request"]
