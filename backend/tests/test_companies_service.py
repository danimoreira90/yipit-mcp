"""Company query service tests — against the SEEDED kpi_test database (real Postgres,
real data; never mocked).

Search semantics per DATA-MODEL §6 + Daniel's task brief:
  list_sectors()                  -> distinct, sorted sectors (18)
  list_companies(sector?, query?) -> filter by sector; case-insensitive substring
                                     on company_name/ticker; combinable; no match -> [];
                                     empty/no args -> all companies (20)
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.companies import list_companies, list_kpis, list_sectors
from backend.services.errors import UnknownTicker
from backend.services.models import KpiUnit

_FIVE_KPIS = {
    "ASP ($)",
    "Global Net Added Subscribers",
    "U.S. Net Added Subscribers",
    "Total Revenue ($MM)",
    "Units Sold",
}


async def test_list_sectors_distinct_sorted_18(session: AsyncSession) -> None:
    sectors = await list_sectors(session)
    assert len(sectors) == 18
    assert len(set(sectors)) == 18
    assert sectors == sorted(sectors)


async def test_list_companies_no_args_returns_all_20(session: AsyncSession) -> None:
    companies = await list_companies(session)
    assert len(companies) == 20


async def test_list_companies_filter_by_sector(session: AsyncSession) -> None:
    companies = await list_companies(session, sector="E-commerce")
    assert companies
    assert all(c.sector == "E-commerce" for c in companies)
    assert any(c.ticker == "ACME" for c in companies)


async def test_list_companies_substring_on_name_case_insensitive(session: AsyncSession) -> None:
    companies = await list_companies(session, query="acme")  # lower-case hits "Acme E-commerce"
    assert any(c.ticker == "ACME" for c in companies)
    assert all("acme" in c.name.lower() or "acme" in c.ticker.lower() for c in companies)


async def test_list_companies_substring_on_ticker(session: AsyncSession) -> None:
    companies = await list_companies(session, query="acm")
    assert any(c.ticker == "ACME" for c in companies)


async def test_list_companies_substring_on_sector(session: AsyncSession) -> None:
    # 'Cybersecurity' appears in no company_name/ticker — matchable only via the sector
    # column, so this isolates the free-text sector clause (assessment: search the sector).
    companies = await list_companies(session, query="cybersecurity")
    assert any(c.ticker == "SHLD" for c in companies)
    assert all(c.sector == "Cybersecurity" for c in companies)


async def test_list_companies_sector_and_query_together(session: AsyncSession) -> None:
    companies = await list_companies(session, sector="E-commerce", query="acme")
    assert companies
    assert all(c.sector == "E-commerce" for c in companies)
    assert any(c.ticker == "ACME" for c in companies)


async def test_list_companies_no_match_returns_empty(session: AsyncSession) -> None:
    companies = await list_companies(session, query="zzz-no-such-company")
    assert companies == []


async def test_list_companies_blank_query_returns_all(session: AsyncSession) -> None:
    companies = await list_companies(session, query="   ")
    assert len(companies) == 20


async def test_list_kpis_returns_five_pairs_for_acme(session: AsyncSession) -> None:
    kpis = await list_kpis(session, "ACME")
    assert len(kpis) == 5
    assert all(isinstance(k, KpiUnit) for k in kpis)
    assert {k.kpi for k in kpis} == _FIVE_KPIS


async def test_list_kpis_distinct_and_sorted(session: AsyncSession) -> None:
    kpis = await list_kpis(session, "ACME")
    pairs = [(k.kpi, k.unit) for k in kpis]
    assert len(pairs) == len(set(pairs))
    assert [k.kpi for k in kpis] == sorted(k.kpi for k in kpis)


async def test_list_kpis_unknown_ticker_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownTicker):
        await list_kpis(session, "ZZZ")  # error-contract path: raise, not []
