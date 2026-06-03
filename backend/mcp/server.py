"""FastMCP server: read-only KPI tools for AI agents.

Tools are THIN wrappers over the KpiService facade — no query logic, no SQL, no DB
session here (that all lives in backend/services). Lives under backend/mcp to avoid a
name collision with the `mcp` PyPI SDK (ADR-002).
"""

from __future__ import annotations

from fastmcp import FastMCP

from backend.services.kpi_service import KpiService
from backend.services.models import Company


def build_server(service: KpiService) -> FastMCP:
    """Build the MCP server, wiring each tool to the injected service facade.

    Tools are registered via add_tool (not the decorator) so they read as ordinary
    referenced functions; descriptions come from the docstrings, schemas from the
    type-annotated signatures."""
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

    mcp.add_tool(list_sectors)
    mcp.add_tool(list_companies)
    return mcp
