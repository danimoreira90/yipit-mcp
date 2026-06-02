"""Seed loader tests (DATA-MODEL.md §1).

Reuse the kpi_test schema harness: schema_engine gives a clean schema, then seed()
loads db/kpi_sample_2000.csv. Assertions are exact (non-vacuous) — they fail loudly
against an unloaded / mis-loaded database.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from db.seed import seed


async def _scalar(engine: AsyncEngine, sql: str) -> int:
    async with engine.begin() as conn:
        result = await conn.execute(text(sql))
        return int(result.scalar_one())


async def test_seed_row_and_type_counts(schema_engine: AsyncEngine) -> None:
    await seed(schema_engine)
    assert await _scalar(schema_engine, "SELECT count(*) FROM kpi_estimates") == 2000
    assert (
        await _scalar(
            schema_engine,
            "SELECT count(*) FROM kpi_estimates WHERE estimate_type = 'historical'",
        )
        == 1600
    )
    assert (
        await _scalar(
            schema_engine,
            "SELECT count(*) FROM kpi_estimates WHERE estimate_type = 'qtd'",
        )
        == 400
    )


async def test_seed_entity_counts(schema_engine: AsyncEngine) -> None:
    await seed(schema_engine)
    assert await _scalar(schema_engine, "SELECT count(*) FROM companies") == 20
    assert await _scalar(schema_engine, "SELECT count(DISTINCT kpi) FROM kpi_estimates") == 5
    assert await _scalar(schema_engine, "SELECT count(DISTINCT sector) FROM companies") == 18


async def test_seed_as_of_nullability(schema_engine: AsyncEngine) -> None:
    await seed(schema_engine)
    historical_with_as_of = await _scalar(
        schema_engine,
        "SELECT count(*) FROM kpi_estimates WHERE estimate_type = 'historical' AND as_of IS NOT NULL",
    )
    qtd_without_as_of = await _scalar(
        schema_engine,
        "SELECT count(*) FROM kpi_estimates WHERE estimate_type = 'qtd' AND as_of IS NULL",
    )
    assert historical_with_as_of == 0
    assert qtd_without_as_of == 0


async def test_seed_acme_asp_has_four_qtd_snapshots(schema_engine: AsyncEngine) -> None:
    await seed(schema_engine)
    snapshots = await _scalar(
        schema_engine,
        "SELECT count(*) FROM kpi_estimates "
        "WHERE ticker = 'ACME' AND kpi = 'ASP ($)' AND period = '2026Q1' AND estimate_type = 'qtd'",
    )
    assert snapshots == 4
