from __future__ import annotations

from typing import Any, NoReturn

from fastapi import HTTPException

from src.backend.app.core.exceptions import MedImageError, PipelineError


def raise_api_error(
    exc: Exception,
    *,
    error_cls: type[MedImageError] = PipelineError,
    message: str | None = None,
    details: dict[str, Any] | None = None,
) -> NoReturn:
    """Map unexpected route exceptions into the structured application error model."""
    if isinstance(exc, HTTPException):
        raise exc
    if isinstance(exc, MedImageError):
        raise exc

    error_details: dict[str, Any] = {"original_error": str(exc)}
    if details:
        error_details.update(details)

    raise error_cls(message or str(exc) or error_cls.default_message, details=error_details) from exc
