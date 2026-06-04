"""FastMCP server: read-only KPI tools for AI agents.

Tools are THIN wrappers over the KpiService facade — no query logic, no SQL, no DB
session here (that all lives in backend/services). Typed domain errors from the service
are surfaced as clean, actionable MCP errors (ToolError), never raw tracebacks. Lives
under backend/mcp to avoid a name collision with the `mcp` PyPI SDK (ADR-002).
"""

from __future__ import annotations

import functools
from collections.abc import Callable, Coroutine
from datetime import date
from typing import Any, TypeVar
from uuid import uuid4

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from backend.observability import log_event
from backend.services.errors import (
    InvalidDateRange,
    NoQtdData,
    UnknownKpi,
    UnknownTicker,
)
from backend.services.kpi_service import KpiService
from backend.services.models import (
    Company,
    CompanyOverview,
    HistoryPoint,
    KpiUnit,
    QtdResult,
)

_T = TypeVar("_T")

# Typed domain errors that map to clean, actionable MCP errors an agent can recover from.
_SERVICE_ERRORS = (UnknownTicker, UnknownKpi, InvalidDateRange, NoQtdData)


async def _guard(coro: Coroutine[Any, Any, _T]) -> _T:
    """Await a service call, surfacing typed domain errors as ToolError (a clean,
    agent-readable message) instead of a raw traceback."""
    try:
        return await coro
    except _SERVICE_ERRORS as exc:
        raise ToolError(str(exc)) from exc


def _logged(
    tool: Callable[..., Coroutine[Any, Any, _T]],
) -> Callable[..., Coroutine[Any, Any, _T]]:
    """Wrap a tool so each call emits one structured log line (call id, tool name, arg
    summary — no secrets). functools.wraps preserves the name/signature/docstring, so
    FastMCP still derives the same schema and description from the original function."""

    @functools.wraps(tool)
    async def wrapper(*args: Any, **kwargs: Any) -> _T:
        log_event("mcp_tool_call", call_id=str(uuid4()), tool=tool.__name__, args=dict(kwargs))
        return await tool(*args, **kwargs)

    return wrapper


def build_server(service: KpiService) -> FastMCP:
    """Build the MCP server, wiring each tool to the injected service facade.

    Registered via add_tool (not the decorator) so they read as ordinary referenced
    functions; descriptions come from the docstrings, schemas from the signatures."""
    mcp: FastMCP = FastMCP("yipit-kpi")

    async def list_sectors() -> list[str]:
        """List every sector in the KPI dataset. Start here to discover sectors, then
        call list_companies(sector=...) to drill into one."""
        return await service.list_sectors()

    async def list_companies(
        sector: str | None = None, query: str | None = None
    ) -> list[Company]:
        """Find companies. `sector` is an exact sector filter; `query` is a
        case-insensitive search over company name, ticker, and sector. Both are
        optional — omit both to list all companies. Returns ticker, name, and sector."""
        return await service.list_companies(sector=sector, query=query)

    async def list_kpis(ticker: str) -> list[KpiUnit]:
        """List the KPIs a company reports, each with its unit. The five KPIs in this
        dataset are exactly: "ASP ($)", "Global Net Added Subscribers",
        "U.S. Net Added Subscribers", "Total Revenue ($MM)", "Units Sold". Returns
        {kpi, unit} pairs."""
        return await _guard(service.list_kpis(ticker))

    async def get_kpi_history(
        ticker: str, kpi: str, start: date | None = None, end: date | None = None
    ) -> list[HistoryPoint]:
        """Settled quarterly HISTORY for a company's KPI — finished past quarters, not the
        current one. `kpi` must be one of exactly: "ASP ($)", "Global Net Added
        Subscribers", "U.S. Net Added Subscribers", "Total Revenue ($MM)", "Units Sold".
        Optional `start`/`end` are ISO dates (YYYY-MM-DD) that filter on the quarter's
        start date, inclusive. Returns {period, period_end, value, unit} oldest-first.
        For the in-progress quarter use get_qtd."""
        return await _guard(service.get_kpi_history(ticker, kpi, start, end))

    async def get_qtd(ticker: str, kpi: str) -> QtdResult:
        """Quarter-to-date (QTD) estimate for a company's KPI: the live estimate for the
        in-progress quarter, revised through the quarter. `kpi` must be one of exactly:
        "ASP ($)", "Global Net Added Subscribers", "U.S. Net Added Subscribers",
        "Total Revenue ($MM)", "Units Sold". Returns the latest snapshot (latest_as_of,
        latest_value) plus the full trajectory of {as_of, value} snapshots. For settled
        past quarters use get_kpi_history."""
        return await _guard(service.get_qtd(ticker, kpi))

    async def get_company_overview(ticker: str) -> CompanyOverview:
        """One-call snapshot of a company: every KPI with its latest settled HISTORY value
        and its latest QTD value. Either side may be null when absent — values are never
        guessed. Use this to summarize a company at a glance."""
        return await _guard(service.get_company_overview(ticker))

    mcp.add_tool(_logged(list_sectors))
    mcp.add_tool(_logged(list_companies))
    mcp.add_tool(_logged(list_kpis))
    mcp.add_tool(_logged(get_kpi_history))
    mcp.add_tool(_logged(get_qtd))
    mcp.add_tool(_logged(get_company_overview))
    return mcp
