"""Schema constraint tests (DATA-MODEL.md §4).

Four behaviors make the single-table design safe — all proven here against a real
Postgres (kpi_test), and each proven to *bite* (see the constraint-removed RED runs
in the session log / verification):

  1. as_of CHECK  — qtd row MUST have a non-NULL as_of
  2. as_of CHECK  — historical row MUST have a NULL as_of (the other branch)
  3. uq_hist      — one settled value per historical (ticker, kpi, period)
  4. uq_qtd       — one snapshot per qtd (ticker, kpi, period, as_of)
"""

from __future__ import annotations

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine

_COMPANY = (
    "INSERT INTO companies (ticker, company_name, sector) "
    "VALUES ('TST', 'Test Co', 'Cloud') ON CONFLICT DO NOTHING;"
)

_HISTORICAL_ROW = (
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES ('TST', 'ASP ($)', '$', '2022Q1', '2022-01-01', '2022-03-31', 'historical', 100, NULL);"
)

_HISTORICAL_ROW_WITH_AS_OF = (
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES ('TST', 'ASP ($)', '$', '2022Q1', '2022-01-01', '2022-03-31', 'historical', 100, '2022-01-15');"
)

_QTD_ROW_NULL_AS_OF = (
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES ('TST', 'ASP ($)', '$', '2026Q1', '2026-01-01', '2026-03-31', 'qtd', 100, NULL);"
)

_QTD_ROW = (
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES ('TST', 'ASP ($)', '$', '2026Q1', '2026-01-01', '2026-03-31', 'qtd', 100, '2026-01-31');"
)


async def test_as_of_check_rejects_qtd_with_null_as_of(schema_engine: AsyncEngine) -> None:
    async with schema_engine.begin() as conn:
        await conn.exec_driver_sql(_COMPANY)

    with pytest.raises(IntegrityError):
        async with schema_engine.begin() as conn:
            await conn.exec_driver_sql(_QTD_ROW_NULL_AS_OF)


async def test_as_of_check_rejects_historical_with_as_of(schema_engine: AsyncEngine) -> None:
    async with schema_engine.begin() as conn:
        await conn.exec_driver_sql(_COMPANY)

    with pytest.raises(IntegrityError):
        async with schema_engine.begin() as conn:
            await conn.exec_driver_sql(_HISTORICAL_ROW_WITH_AS_OF)


async def test_uq_hist_rejects_duplicate_historical(schema_engine: AsyncEngine) -> None:
    async with schema_engine.begin() as conn:
        await conn.exec_driver_sql(_COMPANY)
        await conn.exec_driver_sql(_HISTORICAL_ROW)

    with pytest.raises(IntegrityError):
        async with schema_engine.begin() as conn:
            await conn.exec_driver_sql(_HISTORICAL_ROW)  # duplicate (ticker, kpi, period)


async def test_uq_qtd_rejects_duplicate_snapshot(schema_engine: AsyncEngine) -> None:
    async with schema_engine.begin() as conn:
        await conn.exec_driver_sql(_COMPANY)
        await conn.exec_driver_sql(_QTD_ROW)

    with pytest.raises(IntegrityError):
        async with schema_engine.begin() as conn:
            await conn.exec_driver_sql(_QTD_ROW)  # duplicate (ticker, kpi, period, as_of)
