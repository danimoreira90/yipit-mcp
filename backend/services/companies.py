"""Company query service.

All company discovery logic lives here (the spine); MCP tools and REST routes are
thin wrappers. Queries are parameterized — only static clause fragments are assembled
into the SQL text; every user value is bound (no injection surface).
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.models import Company


async def list_sectors(session: AsyncSession) -> list[str]:
    """Distinct sectors, sorted."""
    result = await session.execute(text("SELECT DISTINCT sector FROM companies ORDER BY sector"))
    return [row.sector for row in result]


async def list_companies(
    session: AsyncSession, sector: str | None = None, query: str | None = None
) -> list[Company]:
    """Companies, optionally filtered by an exact sector and/or a case-insensitive
    substring over company_name/ticker/sector. Blank/absent filters are ignored.

    `sector` is the exact drill-down filter; `query` is the search-box free text
    (the assessment lets users search the sector, company, or KPI)."""
    clauses: list[str] = []
    params: dict[str, str] = {}

    if sector:
        clauses.append("sector = :sector")
        params["sector"] = sector

    term = (query or "").strip()
    if term:
        clauses.append(
            "(company_name ILIKE :pattern OR ticker ILIKE :pattern OR sector ILIKE :pattern)"
        )
        params["pattern"] = f"%{term}%"

    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    result = await session.execute(
        text(f"SELECT ticker, company_name, sector FROM companies{where} ORDER BY ticker"),
        params,
    )
    return [Company(ticker=r.ticker, name=r.company_name, sector=r.sector) for r in result]
