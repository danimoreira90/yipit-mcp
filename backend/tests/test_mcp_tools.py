"""FastMCP tool tests — invoke the tools through an in-memory FastMCP Client against the
seeded kpi_test DB, and assert each tool's structured output matches its service function.

This exercises the real MCP path (registration, schema, structured serialization) an agent
would see — the tool is proven to be a faithful thin wrapper over services/.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.mcp.server import build_server
from backend.services.companies import list_companies as svc_list_companies
from backend.services.companies import list_kpis as svc_list_kpis
from backend.services.companies import list_sectors as svc_list_sectors
from backend.services.db import build_sessionmaker
from backend.services.estimates import get_company_overview as svc_get_company_overview
from backend.services.estimates import get_kpi_history as svc_get_kpi_history
from backend.services.estimates import get_qtd as svc_get_qtd
from backend.services.kpi_service import KpiService

_ASP = "ASP ($)"


@pytest_asyncio.fixture
async def mcp_server(seeded_engine: AsyncEngine) -> FastMCP:
    return build_server(KpiService(build_sessionmaker(seeded_engine)))


async def test_list_sectors_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_list_sectors(session)
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_sectors", {})
    assert result.structured_content is not None
    assert result.structured_content["result"] == expected


async def test_list_companies_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_list_companies(session)
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_companies", {})
    assert result.structured_content is not None
    assert result.structured_content["result"] == [c.model_dump() for c in expected]
    assert len(result.structured_content["result"]) == 20


async def test_list_companies_tool_passes_filters_to_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_list_companies(session, sector="E-commerce")
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_companies", {"sector": "E-commerce"})
    assert result.structured_content is not None
    assert result.structured_content["result"] == [c.model_dump() for c in expected]


async def test_tools_are_registered_with_docstrings_and_typed_params(
    mcp_server: FastMCP,
) -> None:
    async with Client(mcp_server) as client:
        tools = {t.name: t for t in await client.list_tools()}
    assert tools["list_sectors"].description
    assert tools["list_companies"].description
    assert set(tools["list_companies"].inputSchema["properties"]) == {"sector", "query"}


async def test_list_kpis_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_list_kpis(session, "ACME")
    async with Client(mcp_server) as client:
        result = await client.call_tool("list_kpis", {"ticker": "ACME"})
    assert result.structured_content is not None
    assert result.structured_content["result"] == [k.model_dump(mode="json") for k in expected]
    assert len(result.structured_content["result"]) == 5


async def test_get_kpi_history_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_get_kpi_history(session, "ACME", _ASP)
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_kpi_history", {"ticker": "ACME", "kpi": _ASP})
    assert result.structured_content is not None
    assert result.structured_content["result"] == [h.model_dump(mode="json") for h in expected]


async def test_get_qtd_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_get_qtd(session, "ACME", _ASP)
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_qtd", {"ticker": "ACME", "kpi": _ASP})
    # single-model return: structured_content is the model dump (not wrapped in 'result')
    assert result.structured_content == expected.model_dump(mode="json")


async def test_get_company_overview_tool_matches_service(
    mcp_server: FastMCP, session: AsyncSession
) -> None:
    expected = await svc_get_company_overview(session, "ACME")
    async with Client(mcp_server) as client:
        result = await client.call_tool("get_company_overview", {"ticker": "ACME"})
    assert result.structured_content == expected.model_dump(mode="json")


async def test_get_qtd_unknown_ticker_returns_actionable_toolerror(
    mcp_server: FastMCP,
) -> None:
    async with Client(mcp_server) as client:
        with pytest.raises(ToolError) as exc:
            await client.call_tool("get_qtd", {"ticker": "ZZZ", "kpi": _ASP})
    message = str(exc.value)
    assert "ZZZ" in message  # names the bad ticker
    assert "Traceback" not in message  # not a raw traceback


async def test_get_kpi_history_start_after_end_returns_toolerror(
    mcp_server: FastMCP,
) -> None:
    async with Client(mcp_server) as client:
        with pytest.raises(ToolError) as exc:
            await client.call_tool(
                "get_kpi_history",
                {"ticker": "ACME", "kpi": _ASP, "start": "2025-01-01", "end": "2024-01-01"},
            )
    assert "start must be <= end" in str(exc.value)


async def test_get_kpi_history_unknown_kpi_returns_toolerror_naming_valid_kpis(
    mcp_server: FastMCP,
) -> None:
    async with Client(mcp_server) as client:
        with pytest.raises(ToolError) as exc:
            await client.call_tool("get_kpi_history", {"ticker": "ACME", "kpi": "Revenue"})
    message = str(exc.value)
    assert "Revenue" in message  # the bad value
    assert _ASP in message  # names valid KPIs the company reports
