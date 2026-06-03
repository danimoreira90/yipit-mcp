"""Test harness for DB-backed tests, against a real Postgres (kpi_test) — never mocked.

Three layered fixtures:
  - schema_engine: drops and recreates the schema from db/schema.sql (clean state per
    test; used by the schema-constraint tests).
  - seeded_engine: schema_engine + the full CSV seed loaded (for read-only service,
    MCP, and REST tests).
  - session: an AsyncSession over the seeded database.
"""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from backend.services.db import build_sessionmaker
from db.seed import seed

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


@pytest_asyncio.fixture
async def seeded_engine(schema_engine: AsyncEngine) -> AsyncEngine:
    """Clean schema + the full CSV seed loaded. For read-only service tests."""
    await seed(schema_engine)
    return schema_engine


@pytest_asyncio.fixture
async def session(seeded_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    """An AsyncSession over the seeded test database."""
    maker = build_sessionmaker(seeded_engine)
    async with maker() as db_session:
        yield db_session
