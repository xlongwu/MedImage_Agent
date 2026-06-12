from __future__ import annotations

from typing import Any

from src.backend.app.core.error_codes import ErrorCode


def _code_value(code: ErrorCode | str) -> str:
    if isinstance(code, ErrorCode):
        return code.value
    return str(code)


class MedImageError(Exception):
    """Base application error with a stable code and HTTP status."""

    code: ErrorCode | str = ErrorCode.INTERNAL_SERVER_ERROR
    status_code: int = 500
    default_message: str = "An internal server error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: ErrorCode | str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = _code_value(code or self.code)
        self.status_code = status_code or self.status_code
        self.message = message or self.default_message
        self.details = details or {}
        super().__init__(self.message)


class ConfigError(MedImageError):
    code = ErrorCode.CONFIG_ERROR
    status_code = 400
    default_message = "Invalid configuration."


class PipelineError(MedImageError):
    code = ErrorCode.PIPELINE_ERROR
    status_code = 400
    default_message = "Pipeline request failed."


class SafetyError(MedImageError):
    code = ErrorCode.SAFETY_ERROR
    status_code = 403
    default_message = "The requested operation was rejected by safety policy."


class NotFoundError(MedImageError):
    code = ErrorCode.NOT_FOUND
    status_code = 404
    default_message = "The requested resource was not found."


class StateStoreError(MedImageError):
    code = ErrorCode.STATE_STORE_ERROR
    status_code = 500
    default_message = "State store operation failed."


class ExternalServiceError(MedImageError):
    code = ErrorCode.EXTERNAL_SERVICE_ERROR
    status_code = 502
    default_message = "External service operation failed."
