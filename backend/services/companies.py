"""Company query service.

All company discovery logic lives here (the spine); MCP tools and REST routes are
thin wrappers. Queries are parameterized — only static clause fragments are assembled
into the SQL text; every user value is bound (no injection surface).

Ordering is done in-service with Python's codepoint sort on these small, bounded
reference lists. That is deterministic and independent of the database locale's
collation (a Postgres ORDER BY would order by the server locale, which varies by
environment); for ≤20-row lists the cost is irrelevant.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import Row, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.errors import UnknownTicker
from backend.services.models import Company, KpiUnit


async def require_company(session: AsyncSession, ticker: str) -> Row[Any]:
    """Fetch a company's (company_name, sector), raising UnknownTicker if it doesn't
    exist. The single existence guard shared by every ticker-scoped query."""
    row = (
        await session.execute(
            text("SELECT company_name, sector FROM companies WHERE ticker = :ticker"),
            {"ticker": ticker},
        )
    ).first()
    if row is None:
        raise UnknownTicker(ticker)
    return row


async def list_sectors(session: AsyncSession) -> list[str]:
    """Distinct sectors, sorted."""
    result = await session.execute(text("SELECT DISTINCT sector FROM companies"))
    return sorted(row.sector for row in result)


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
        text(f"SELECT ticker, company_name, sector FROM companies{where}"), params
    )
    companies = [Company(ticker=r.ticker, name=r.company_name, sector=r.sector) for r in result]
    return sorted(companies, key=lambda c: c.ticker)


async def list_kpis(session: AsyncSession, ticker: str) -> list[KpiUnit]:
    """Distinct (kpi, unit) pairs reported by a company, ordered by kpi.

    Raises UnknownTicker if the ticker does not exist — an unknown company is the
    error-contract path, distinct from a known company that simply has no rows.
    """
    await require_company(session, ticker)

    result = await session.execute(
        text("SELECT DISTINCT kpi, unit FROM kpi_estimates WHERE ticker = :ticker"),
        {"ticker": ticker},
    )
    kpis = [KpiUnit(kpi=r.kpi, unit=r.unit) for r in result]
    return sorted(kpis, key=lambda k: k.kpi)
