"""Structured JSON logging for both transports (REST middleware + MCP tool calls).

One JSON line per request / tool call on stdout (12-factor XI): a request/call id,
the operation, and outcome metadata — never request bodies or secrets. Lives outside
backend/api and backend/mcp so it cannot affect the spine fitness function, which
forbids those transport packages from touching the DB layer.
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, cast

LOGGER_NAME = "yipit_kpi"


class JsonFormatter(logging.Formatter):
    """Render a record as one compact JSON object: the message under `event`, plus
    any structured fields attached via the `context` extra."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {"event": record.getMessage()}
        context = getattr(record, "context", None)
        if isinstance(context, dict):
            payload.update(cast("dict[str, Any]", context))
        return json.dumps(payload, default=str)


def get_logger() -> logging.Logger:
    """The app logger, configured once with a stdout JSON handler. Idempotent."""
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
    return logger


def log_event(event: str, **context: Any) -> None:
    """Emit one structured log line. Pass only non-sensitive metadata as context."""
    get_logger().info(event, extra={"context": context})
