"""Structured-logging unit tests plus the MCP tool-call log line. The app logger has
propagate=False, so pytest's caplog (root handler) won't see it — we attach our own
capturing handler and assert the structured records directly.
"""

from __future__ import annotations

import json
import logging

import pytest_asyncio
from fastmcp import Client, FastMCP
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.mcp.server import build_server
from backend.observability import LOGGER_NAME, JsonFormatter, get_logger, log_event
from backend.services.db import build_sessionmaker
from backend.services.kpi_service import KpiService


class _CapturingHandler(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def _capture() -> _CapturingHandler:
    handler = _CapturingHandler()
    get_logger().addHandler(handler)
    return handler


def test_log_event_attaches_structured_context() -> None:
    handler = _capture()
    try:
        log_event("request", request_id="r1", method="GET", path="/sectors", status=200)
    finally:
        logging.getLogger(LOGGER_NAME).removeHandler(handler)
    assert len(handler.records) == 1
    record = handler.records[0]
    assert record.getMessage() == "request"
    assert record.context == {  # type: ignore[attr-defined]
        "request_id": "r1",
        "method": "GET",
        "path": "/sectors",
        "status": 200,
    }


def test_json_formatter_renders_one_line_of_json() -> None:
    record = logging.LogRecord(LOGGER_NAME, logging.INFO, __file__, 0, "request", None, None)
    record.context = {"request_id": "r1", "status": 200, "latency_ms": 1.5}  # type: ignore[attr-defined]
    line = JsonFormatter().format(record)
    assert "\n" not in line
    assert json.loads(line) == {
        "event": "request",
        "request_id": "r1",
        "status": 200,
        "latency_ms": 1.5,
    }


@pytest_asyncio.fixture
async def mcp_server(seeded_engine: AsyncEngine) -> FastMCP:
    return build_server(KpiService(build_sessionmaker(seeded_engine)))


async def test_mcp_tool_call_emits_structured_log(mcp_server: FastMCP) -> None:
    handler = _capture()
    try:
        async with Client(mcp_server) as client:
            await client.call_tool("list_companies", {"sector": "Cloud"})
    finally:
        logging.getLogger(LOGGER_NAME).removeHandler(handler)
    calls = [r for r in handler.records if r.getMessage() == "mcp_tool_call"]
    assert len(calls) == 1
    context = calls[0].context  # type: ignore[attr-defined]
    assert context["tool"] == "list_companies"
    assert context["call_id"]
    assert context["args"]["sector"] == "Cloud"
