"""Company overview ("at a glance") service tests — against the seeded kpi_test DB.

get_company_overview composes, per KPI, the latest historical point and the latest qtd
snapshot — each independently nullable and never fabricated. The composition must use a
BOUNDED number of queries (no N+1): one per data shape, not one per KPI.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from backend.services.errors import UnknownTicker
from backend.services.estimates import get_company_overview
from backend.services.models import CompanyOverview, KpiOverview

_ASP = "ASP ($)"
_FIVE_KPIS = {
    "ASP ($)",
    "Global Net Added Subscribers",
    "U.S. Net Added Subscribers",
    "Total Revenue ($MM)",
    "Units Sold",
}


def _kpi(overview: CompanyOverview, name: str) -> KpiOverview:
    matches = [k for k in overview.kpis if k.kpi == name]
    assert matches, f"{name} missing from overview"
    return matches[0]


async def test_overview_acme_all_five_kpis_with_both_sides(session: AsyncSession) -> None:
    overview = await get_company_overview(session, "ACME")
    assert overview.company.ticker == "ACME"
    assert overview.company.sector == "E-commerce"
    assert {k.kpi for k in overview.kpis} == _FIVE_KPIS
    # deterministic, locale-independent ordering — consistent with list_kpis (codepoint)
    assert [k.kpi for k in overview.kpis] == sorted(k.kpi for k in overview.kpis)
    for kpi in overview.kpis:
        assert kpi.latest_history is not None
        assert kpi.latest_qtd is not None


async def test_overview_latest_history_and_qtd_are_the_latest(session: AsyncSession) -> None:
    overview = await get_company_overview(session, "ACME")
    asp = _kpi(overview, _ASP)
    assert asp.unit == "$"
    assert asp.latest_history is not None and asp.latest_history.period == "2025Q4"
    assert asp.latest_qtd is not None and asp.latest_qtd.as_of == date(2026, 3, 15)


async def test_overview_kpi_with_no_qtd_has_none_qtd_others_unaffected(
    session: AsyncSession,
) -> None:
    # Remove ACME 'ASP ($)' qtd rows in-tx: ASP keeps its history but loses qtd.
    await session.execute(
        text(
            "DELETE FROM kpi_estimates "
            "WHERE ticker = 'ACME' AND kpi = :kpi AND estimate_type = 'qtd'"
        ),
        {"kpi": _ASP},
    )
    overview = await get_company_overview(session, "ACME")

    asp = _kpi(overview, _ASP)
    assert asp.latest_qtd is None  # not fabricated
    assert asp.latest_history is not None

    other = _kpi(overview, "Units Sold")
    assert other.latest_qtd is not None


async def test_overview_unknown_ticker_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownTicker):
        await get_company_overview(session, "ZZZ")


async def test_overview_uses_bounded_query_count(
    session: AsyncSession, seeded_engine: AsyncEngine
) -> None:
    queries = 0

    def count(*args: object) -> None:
        nonlocal queries
        queries += 1

    event.listen(seeded_engine.sync_engine, "before_cursor_execute", count)
    try:
        await get_company_overview(session, "ACME")
    finally:
        event.remove(seeded_engine.sync_engine, "before_cursor_execute", count)

    # ACME has 5 KPIs; an N+1 composition would be >= 6 queries. A small constant
    # proves the query count is independent of the KPI count.
    assert 0 < queries <= 4
