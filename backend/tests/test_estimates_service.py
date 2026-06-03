"""Estimate query service tests — against the seeded kpi_test database.

get_kpi_history returns only HISTORICAL rows (never qtd) as HistoryPoint, ordered by
period_start, with date-range filtering on the real period_start DATE (not the
'YYYYQn' label). ACME 'ASP ($)' has 16 historical quarters (2022Q1..2025Q4) and is
the fixture company throughout.
"""

from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.errors import InvalidDateRange, NoQtdData, UnknownKpi, UnknownTicker
from backend.services.estimates import get_kpi_history, get_qtd, list_company_estimates
from backend.services.models import EstimateType, HistoryPoint

_ASP = "ASP ($)"


async def test_history_full_series_ordered_by_period_start(session: AsyncSession) -> None:
    history = await get_kpi_history(session, "ACME", _ASP)
    assert len(history) == 16  # 16 historical quarters; proves qtd is excluded (would be 20)
    assert all(isinstance(h, HistoryPoint) for h in history)
    periods = [h.period for h in history]
    assert periods == sorted(periods)  # YYYYQn sorts chronologically == period_start order
    assert all(h.unit == "$" for h in history)


async def test_history_excludes_qtd(session: AsyncSession) -> None:
    history = await get_kpi_history(session, "ACME", _ASP)
    assert "2026Q1" not in [h.period for h in history]  # 2026Q1 is qtd-only


async def test_history_calendar_year_window_inclusive(session: AsyncSession) -> None:
    history = await get_kpi_history(
        session, "ACME", _ASP, start=date(2024, 1, 1), end=date(2024, 12, 31)
    )
    assert [h.period for h in history] == ["2024Q1", "2024Q2", "2024Q3", "2024Q4"]


async def test_history_single_quarter_boundaries_inclusive(session: AsyncSession) -> None:
    # period_start of 2025Q4 is exactly 2025-10-01 — inclusive on both ends.
    history = await get_kpi_history(
        session, "ACME", _ASP, start=date(2025, 10, 1), end=date(2025, 10, 1)
    )
    assert [h.period for h in history] == ["2025Q4"]


async def test_history_filters_on_period_start_not_label(session: AsyncSession) -> None:
    # A mid-Q1 start (2024-02-01) excludes 2024Q1 (period_start 2024-01-01) — only a real
    # DATE filter on period_start can express this; a label-string filter cannot.
    history = await get_kpi_history(
        session, "ACME", _ASP, start=date(2024, 2, 1), end=date(2024, 12, 31)
    )
    assert [h.period for h in history] == ["2024Q2", "2024Q3", "2024Q4"]


async def test_history_start_after_end_raises(session: AsyncSession) -> None:
    with pytest.raises(InvalidDateRange):
        await get_kpi_history(session, "ACME", _ASP, start=date(2025, 1, 1), end=date(2024, 1, 1))


async def test_history_valid_window_with_no_rows_returns_empty(session: AsyncSession) -> None:
    history = await get_kpi_history(
        session, "ACME", _ASP, start=date(2030, 1, 1), end=date(2030, 12, 31)
    )
    assert history == []  # empty, not an error


async def test_history_unknown_ticker_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownTicker):
        await get_kpi_history(session, "ZZZ", _ASP)


async def test_history_unknown_kpi_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownKpi):
        await get_kpi_history(session, "ACME", "Revenue")  # not one of the 5 valid KPIs


# --- get_qtd ----------------------------------------------------------------

_QTD_AS_OFS = [date(2026, 1, 31), date(2026, 2, 15), date(2026, 2, 28), date(2026, 3, 15)]


async def test_qtd_trajectory_four_points_ordered_by_as_of(session: AsyncSession) -> None:
    qtd = await get_qtd(session, "ACME", _ASP)
    as_ofs = [snap.as_of for snap in qtd.trajectory]
    assert len(as_ofs) == 4
    assert as_ofs == sorted(as_ofs)  # ordered by as_of
    assert as_ofs == _QTD_AS_OFS


async def test_qtd_latest_is_max_as_of_snapshot(session: AsyncSession) -> None:
    qtd = await get_qtd(session, "ACME", _ASP)
    assert qtd.period == "2026Q1"
    assert qtd.unit == "$"
    assert qtd.latest_as_of == date(2026, 3, 15)  # MAX(as_of)
    assert qtd.latest_value == qtd.trajectory[-1].value  # the latest snapshot's value


async def test_qtd_unknown_ticker_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownTicker):
        await get_qtd(session, "ZZZ", _ASP)


async def test_qtd_unknown_kpi_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownKpi):
        await get_qtd(session, "ACME", "Revenue")


async def test_qtd_known_pair_with_no_qtd_rows_raises_noqtddata(session: AsyncSession) -> None:
    # Remove ACME 'ASP ($)' qtd rows within this transaction: the pair still has history
    # (so ticker + kpi are valid), but no qtd snapshots -> NoQtdData, distinct from the
    # Unknown* errors.
    await session.execute(
        text(
            "DELETE FROM kpi_estimates "
            "WHERE ticker = 'ACME' AND kpi = :kpi AND estimate_type = 'qtd'"
        ),
        {"kpi": _ASP},
    )
    with pytest.raises(NoQtdData):
        await get_qtd(session, "ACME", _ASP)


# --- list_company_estimates (all estimates for a company) -------------------


async def test_list_company_estimates_returns_all_history_and_qtd(
    session: AsyncSession,
) -> None:
    rows = await list_company_estimates(session, "ACME")
    assert len(rows) == 100  # 5 KPIs x (16 historical + 4 qtd)
    assert all(r.ticker == "ACME" for r in rows)
    assert sum(r.estimate_type == EstimateType.HISTORICAL for r in rows) == 80
    assert sum(r.estimate_type == EstimateType.QTD for r in rows) == 20


async def test_list_company_estimates_unknown_ticker_raises(session: AsyncSession) -> None:
    with pytest.raises(UnknownTicker):
        await list_company_estimates(session, "ZZZ")
