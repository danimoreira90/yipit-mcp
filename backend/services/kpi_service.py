"""Application facade: a session-bound service over the query functions.

Owns session lifecycle so the transports (MCP tools, REST routes) never open a
session or run SQL — they call these session-free methods. One facade, two
transports (the spine). RED stub: methods return [] until GREEN.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.services import companies, estimates
from backend.services.models import (
    Company,
    CompanyOverview,
    HistoryPoint,
    KpiUnit,
    QtdResult,
)


class KpiService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def list_sectors(self) -> list[str]:
        async with self._sessionmaker() as session:
            return await companies.list_sectors(session)

    async def list_companies(
        self, sector: str | None = None, query: str | None = None
    ) -> list[Company]:
        async with self._sessionmaker() as session:
            return await companies.list_companies(session, sector, query)

    async def list_kpis(self, ticker: str) -> list[KpiUnit]:
        async with self._sessionmaker() as session:
            return await companies.list_kpis(session, ticker)

    async def get_kpi_history(
        self, ticker: str, kpi: str, start: date | None = None, end: date | None = None
    ) -> list[HistoryPoint]:
        async with self._sessionmaker() as session:
            return await estimates.get_kpi_history(session, ticker, kpi, start, end)

    async def get_qtd(self, ticker: str, kpi: str) -> QtdResult:
        async with self._sessionmaker() as session:
            return await estimates.get_qtd(session, ticker, kpi)

    async def get_company_overview(self, ticker: str) -> CompanyOverview:
        async with self._sessionmaker() as session:
            return await estimates.get_company_overview(session, ticker)
