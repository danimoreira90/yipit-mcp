"""Seed loader: load db/kpi_sample_2000.csv into companies + kpi_estimates.

Idempotent (truncate-then-load). Empty as_of in the CSV → NULL (historical);
a date → the qtd snapshot's as_of. Dates and the numeric value are parsed to
real Python types so asyncpg binds them correctly.

Run directly to seed the dev database:  uv run python -m db.seed
"""

from __future__ import annotations

import asyncio
import csv
import os
from datetime import date
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

CSV_PATH = Path(__file__).parent / "kpi_sample_2000.csv"

_INSERT_COMPANY = text(
    "INSERT INTO companies (ticker, company_name, sector) "
    "VALUES (:ticker, :company_name, :sector) ON CONFLICT (ticker) DO NOTHING"
)
_INSERT_ESTIMATE = text(
    "INSERT INTO kpi_estimates "
    "(ticker, kpi, unit, period, period_start, period_end, estimate_type, value, as_of) "
    "VALUES (:ticker, :kpi, :unit, :period, :period_start, :period_end, "
    ":estimate_type, :value, :as_of)"
)


def _parse(csv_path: Path) -> tuple[list[dict[str, str]], list[dict[str, object]]]:
    companies: dict[str, dict[str, str]] = {}
    estimates: list[dict[str, object]] = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            companies[row["ticker"]] = {
                "ticker": row["ticker"],
                "company_name": row["company_name"],
                "sector": row["sector"],
            }
            estimates.append(
                {
                    "ticker": row["ticker"],
                    "kpi": row["kpi"],
                    "unit": row["unit"],
                    "period": row["period"],
                    "period_start": date.fromisoformat(row["period_start"]),
                    "period_end": date.fromisoformat(row["period_end"]),
                    "estimate_type": row["estimate_type"],
                    "value": Decimal(row["value"]),
                    "as_of": date.fromisoformat(row["as_of"]) if row["as_of"] else None,
                }
            )
    return list(companies.values()), estimates


async def seed(engine: AsyncEngine, csv_path: Path = CSV_PATH) -> None:
    companies, estimates = _parse(csv_path)
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE kpi_estimates, companies RESTART IDENTITY CASCADE"))
        await conn.execute(_INSERT_COMPANY, companies)
        await conn.execute(_INSERT_ESTIMATE, estimates)


async def _main() -> None:
    load_dotenv()
    url = os.environ["DATABASE_URL"]
    engine = create_async_engine(url)
    try:
        await seed(engine)
        print(f"Seeded from {CSV_PATH.name}")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(_main())
