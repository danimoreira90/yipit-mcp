"""FastMCP tool tests — invoke the tools through an in-memory FastMCP Client against the
seeded kpi_test DB, and assert each tool's structured output matches its service function.

This exercises the real MCP path (registration, schema, structured serialization) an agent
would see — the tool is proven to be a faithful thin wrapper over services/.
"""

from __future__ import annotations

import pytest_asyncio
from fastmcp import Client, FastMCP
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.mcp.server import build_server
from backend.services.companies import list_companies as svc_list_companies
from backend.services.companies import list_sectors as svc_list_sectors
from backend.services.db import build_sessionmaker
from backend.services.kpi_service import KpiService


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
