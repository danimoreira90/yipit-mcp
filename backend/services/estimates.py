"""Estimate query service.

All estimate logic lives here (the spine); MCP tools and REST routes are thin
wrappers. Queries are parameterized — only static clause fragments are assembled into
the SQL text; every user value is bound (no injection surface).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.companies import require_company
from backend.services.errors import InvalidDateRange, NoQtdData, UnknownKpi
from backend.services.models import (
    Company,
    CompanyOverview,
    EstimateType,
    HistoryPoint,
    KpiEstimate,
    KpiOverview,
    LatestHistory,
    LatestQtd,
    QtdResult,
    QtdSnapshot,
)


async def _validate_ticker_and_kpi(session: AsyncSession, ticker: str, kpi: str) -> None:
    """Raise UnknownTicker if the company doesn't exist, else UnknownKpi if it does not
    report that kpi (the message lists the KPIs it does report)."""
    await require_company(session, ticker)

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


async def get_qtd(session: AsyncSession, ticker: str, kpi: str) -> QtdResult:
    """Quarter-to-date estimate for (ticker, kpi): the full intra-quarter trajectory
    (qtd snapshots ordered by as_of) plus the latest snapshot (MAX(as_of)).

    Validates ticker/kpi (UnknownTicker / UnknownKpi). A known pair that reports the
    kpi but has no qtd snapshots raises NoQtdData — distinct from an unknown pair.
    """
    await _validate_ticker_and_kpi(session, ticker, kpi)

    result = await session.execute(
        text(
            "SELECT period, as_of, value, unit FROM kpi_estimates "
            "WHERE ticker = :ticker AND kpi = :kpi AND estimate_type = 'qtd' ORDER BY as_of"
        ),
        {"ticker": ticker, "kpi": kpi},
    )
    rows = result.all()
    if not rows:
        raise NoQtdData(ticker, kpi)

    latest = rows[-1]  # rows are ordered by as_of ascending, so the last is MAX(as_of)
    return QtdResult(
        period=latest.period,
        latest_as_of=latest.as_of,
        latest_value=latest.value,
        unit=latest.unit,
        trajectory=[QtdSnapshot(as_of=r.as_of, value=r.value) for r in rows],
    )


async def get_company_overview(session: AsyncSession, ticker: str) -> CompanyOverview:
    """The 'at a glance' view: the company plus, per KPI, its latest historical point
    and its latest qtd snapshot. Each side is independently nullable and never
    fabricated (no history -> None; no qtd -> None). Raises UnknownTicker if absent.

    Bounded query count: three queries total (company, latest-per-kpi historical,
    latest-per-kpi qtd) via DISTINCT ON — independent of the number of KPIs (no N+1).
    """
    company = await require_company(session, ticker)

    history_rows = await session.execute(
        text(
            "SELECT DISTINCT ON (kpi) kpi, unit, period, value FROM kpi_estimates "
            "WHERE ticker = :ticker AND estimate_type = 'historical' "
            "ORDER BY kpi, period_start DESC"
        ),
        {"ticker": ticker},
    )
    qtd_rows = await session.execute(
        text(
            "SELECT DISTINCT ON (kpi) kpi, unit, as_of, value FROM kpi_estimates "
            "WHERE ticker = :ticker AND estimate_type = 'qtd' "
            "ORDER BY kpi, as_of DESC"
        ),
        {"ticker": ticker},
    )

    units: dict[str, str] = {}
    history: dict[str, LatestHistory] = {}
    for r in history_rows:
        units[r.kpi] = r.unit
        history[r.kpi] = LatestHistory(period=r.period, value=r.value)
    qtd: dict[str, LatestQtd] = {}
    for r in qtd_rows:
        units[r.kpi] = r.unit
        qtd[r.kpi] = LatestQtd(value=r.value, as_of=r.as_of)

    kpis = [
        KpiOverview(
            kpi=name,
            unit=units[name],
            latest_history=history.get(name),
            latest_qtd=qtd.get(name),
        )
        for name in sorted(units)
    ]
    return CompanyOverview(
        company=Company(ticker=ticker, name=company.company_name, sector=company.sector),
        kpis=kpis,
    )


async def list_company_estimates(session: AsyncSession, ticker: str) -> list[KpiEstimate]:
    """Every estimate (historical and qtd) for a company. Raises UnknownTicker if the
    company doesn't exist. Ordered deterministically in-service (codepoint kpi, then
    period_start, type, as_of) — locale-independent, like the other text orderings.
    """
    await require_company(session, ticker)

    result = await session.execute(
        text(
            "SELECT ticker, kpi, unit, period, period_start, period_end, "
            "estimate_type, value, as_of FROM kpi_estimates WHERE ticker = :ticker"
        ),
        {"ticker": ticker},
    )
    rows = [
        KpiEstimate(
            ticker=r.ticker,
            kpi=r.kpi,
            unit=r.unit,
            period=r.period,
            period_start=r.period_start,
            period_end=r.period_end,
            estimate_type=r.estimate_type,
            value=r.value,
            as_of=r.as_of,
        )
        for r in result
    ]
    rows.sort(key=lambda e: (e.kpi, e.period_start, e.estimate_type.value, e.as_of or date.min))
    return rows


async def _unit_for_kpi(session: AsyncSession, kpi: str) -> str:
    """The unit for a kpi, read from the data (unit is functionally determined by kpi).
    Raises UnknownKpi (listing the dataset's KPIs) if the kpi is not one of them."""
    unit = await session.scalar(
        text("SELECT unit FROM kpi_estimates WHERE kpi = :kpi LIMIT 1"), {"kpi": kpi}
    )
    if unit is None:
        rows = await session.execute(text("SELECT DISTINCT kpi FROM kpi_estimates"))
        raise UnknownKpi(kpi, available=sorted(r.kpi for r in rows))
    return unit


# Upsert statements. The ON CONFLICT target matches the matching partial-unique index, and
# the estimate_type / as_of literals honour the as_of_matches_type CHECK. All user values
# are bound parameters — nothing from the request is interpolated into the SQL text.
_RETURNING = (
    "RETURNING ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of"
)
_PUBLISH_HISTORICAL = text(
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES (:ticker, :kpi, :unit, :period, :period_start, :period_end, 'historical', :value, NULL) "
    "ON CONFLICT (ticker, kpi, period) WHERE estimate_type = 'historical' "
    "DO UPDATE SET value = EXCLUDED.value, created_at = now() " + _RETURNING
)
_PUBLISH_QTD = text(
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES (:ticker, :kpi, :unit, :period, :period_start, :period_end, 'qtd', :value, :as_of) "
    "ON CONFLICT (ticker, kpi, period, as_of) WHERE estimate_type = 'qtd' "
    "DO UPDATE SET value = EXCLUDED.value, created_at = now() " + _RETURNING
)


async def publish_estimate(
    session: AsyncSession,
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
    """Publish (insert-or-update) an estimate and return the persisted row.

    Validates the ticker (UnknownTicker) and kpi (UnknownKpi); derives the unit
    server-side. Upserts via INSERT ... ON CONFLICT, targeting the partial-unique index
    for the estimate_type — historical conflicts on (ticker, kpi, period); qtd on
    (ticker, kpi, period, as_of). The caller commits.
    """
    await require_company(session, ticker)
    unit = await _unit_for_kpi(session, kpi)

    params: dict[str, object] = {
        "ticker": ticker,
        "kpi": kpi,
        "unit": unit,
        "period": period,
        "period_start": period_start,
        "period_end": period_end,
        "value": value,
    }
    if estimate_type is EstimateType.HISTORICAL:
        statement = _PUBLISH_HISTORICAL
    else:
        statement = _PUBLISH_QTD
        params["as_of"] = as_of

    row = (await session.execute(statement, params)).first()
    assert row is not None  # INSERT ... RETURNING (with DO UPDATE) always yields one row
    return KpiEstimate(
        ticker=row.ticker,
        kpi=row.kpi,
        unit=row.unit,
        period=row.period,
        period_start=row.period_start,
        period_end=row.period_end,
        estimate_type=row.estimate_type,
        value=row.value,
        as_of=row.as_of,
    )
