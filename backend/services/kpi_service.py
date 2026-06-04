"""Application facade: a session-bound service over the query functions.

Owns session lifecycle so the transports (MCP tools, REST routes) never open a
session or run SQL — they call these session-free methods. One facade, two
transports (the spine). See docs/adr/ADR-003-kpi-service-facade.md.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from backend.services import companies, estimates
from backend.services.models import (
    Company,
    CompanyOverview,
    EstimateType,
    HistoryPoint,
    KpiEstimate,
    KpiUnit,
    QtdResult,
)


class KpiService:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def check_health(self) -> bool:
        """Readiness probe: a trivial round-trip to confirm the DB answers. Returns
        True when reachable; False on any connection or query failure (the probe
        reports unavailability, it does not raise)."""
        try:
            async with self._sessionmaker() as session:
                await session.execute(text("SELECT 1"))
            return True
        except (SQLAlchemyError, OSError):
            return False

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

    async def list_company_estimates(self, ticker: str) -> list[KpiEstimate]:
        async with self._sessionmaker() as session:
            return await estimates.list_company_estimates(session, ticker)

    async def publish_estimate(
        self,
        ticker: str,
        *,
        kpi: str,
        period: str,
        period_start: date,
        period_end: date,
        estimate_type: EstimateType,
        value: Decimal,
        as_of: date | None,
    ) -> KpiEstimate:
        async with self._sessionmaker() as session:
            estimate = await estimates.publish_estimate(
                session,
                ticker,
                kpi=kpi,
                period=period,
                period_start=period_start,
                period_end=period_end,
                estimate_type=estimate_type,
                value=value,
                as_of=as_of,
            )
            await session.commit()
            return estimate
