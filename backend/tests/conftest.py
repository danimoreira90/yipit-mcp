"""Test harness: apply db/schema.sql to the test database and hand back an engine.

Minimal on purpose — the production engine/session factory arrives in Phase 3
(Task 3.1). This fixture exists only so the schema tests can exercise the real
constraints against a real Postgres (never mock the thing under test).
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

load_dotenv()

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "db" / "schema.sql"

# Overridable via env; falls back to the documented local test DB (Docker Compose).
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://kpi:kpi@localhost:5432/kpi_test",
)


def _statements(sql: str) -> list[str]:
    """Split plain DDL into single statements (asyncpg rejects multi-statement
    extended-protocol queries). Our schema has no procedural bodies and no '--'
    inside string literals, so stripping each line's '--' comment (full-line or
    inline) and splitting on ';' is correct."""
    cleaned: list[str] = []
    for ln in sql.splitlines():
        idx = ln.find("--")
        cleaned.append(ln if idx == -1 else ln[:idx])
    return [s.strip() for s in "\n".join(cleaned).split(";") if s.strip()]


@pytest_asyncio.fixture
async def schema_engine() -> AsyncGenerator[AsyncEngine, None]:
    """Drop-and-recreate the schema, yield an engine. Clean state per test."""
    engine = create_async_engine(TEST_DATABASE_URL)
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    async with engine.begin() as conn:
        await conn.exec_driver_sql("DROP TABLE IF EXISTS kpi_estimates CASCADE;")
        await conn.exec_driver_sql("DROP TABLE IF EXISTS companies CASCADE;")
        for stmt in _statements(schema_sql):
            await conn.exec_driver_sql(stmt)
    try:
        yield engine
    finally:
        await engine.dispose()
