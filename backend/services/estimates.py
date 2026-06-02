"""Estimate query service.

All estimate logic lives here (the spine); MCP tools and REST routes are thin
wrappers. Queries are parameterized — only static clause fragments are assembled into
the SQL text; every user value is bound (no injection surface).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.errors import InvalidDateRange, UnknownKpi, UnknownTicker
from backend.services.models import HistoryPoint


async def _validate_ticker_and_kpi(session: AsyncSession, ticker: str, kpi: str) -> None:
    """Raise UnknownTicker if the company doesn't exist, else UnknownKpi if it does not
    report that kpi (the message lists the KPIs it does report)."""
    exists = await session.scalar(
        text("SELECT 1 FROM companies WHERE ticker = :ticker"), {"ticker": ticker}
    )
    if not exists:
        raise UnknownTicker(ticker)

    rows = await session.execute(
        text("SELECT DISTINCT kpi FROM kpi_estimates WHERE ticker = :ticker"), {"ticker": ticker}
    )
    available = sorted(r.kpi for r in rows)
    if kpi not in available:
        raise UnknownKpi(kpi, available=available)


async def get_kpi_history(
    session: AsyncSession,
    ticker: str,
    kpi: str,
    start: date | None = None,
    end: date | None = None,
) -> list[HistoryPoint]:
    """Settled historical series for (ticker, kpi), ordered by period_start.

    Only estimate_type='historical' rows (never qtd). The optional [start, end] window
    filters on the real period_start DATE (inclusive), not the 'YYYYQn' label. An empty
    window is a valid empty result; start > end raises InvalidDateRange.
    """
    if start is not None and end is not None and start > end:
        raise InvalidDateRange(start, end)

    await _validate_ticker_and_kpi(session, ticker, kpi)

    clauses = ["ticker = :ticker", "kpi = :kpi", "estimate_type = 'historical'"]
    params: dict[str, object] = {"ticker": ticker, "kpi": kpi}
    if start is not None:
        clauses.append("period_start >= :start")
        params["start"] = start
    if end is not None:
        clauses.append("period_start <= :end")
        params["end"] = end

    result = await session.execute(
        text(
            "SELECT period, period_end, value, unit FROM kpi_estimates "
            f"WHERE {' AND '.join(clauses)} ORDER BY period_start"
        ),
        params,
    )
    return [
        HistoryPoint(period=r.period, period_end=r.period_end, value=r.value, unit=r.unit)
        for r in result
    ]
