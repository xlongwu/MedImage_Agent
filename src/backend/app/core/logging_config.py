from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Small structured formatter for backend infrastructure logs."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        context = getattr(record, "medimage", None)
        if isinstance(context, dict):
            payload.update(context)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logging(level: str | None = None) -> None:
    """Configure structured logging for src.backend.app loggers."""

    raw_level = (level or os.environ.get("MEDIMAGE_LOG_LEVEL") or "INFO").upper()
    log_level = getattr(logging, raw_level, logging.INFO)
    logger = logging.getLogger("src.backend.app")
    logger.setLevel(log_level)
    logger.propagate = False

    for handler in logger.handlers:
        if getattr(handler, "_medimage_json_handler", False):
            handler.setLevel(log_level)
            return

    handler = logging.StreamHandler()
    handler.setLevel(log_level)
    handler.setFormatter(JsonLogFormatter())
    handler._medimage_json_handler = True
    logger.addHandler(handler)
