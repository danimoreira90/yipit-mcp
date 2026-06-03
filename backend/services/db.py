"""Async engine/session factories.

Lazy on purpose (SIMPLICITY §2): importing this module has NO side effects — no
engine, no connection. The entrypoints (MCP server, FastAPI app) build a single
engine + sessionmaker at startup; tests inject their own against kpi_test.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)


def build_engine(url: str | None = None) -> AsyncEngine:
    """Does not connect until first use (lazy)."""
    if url is None:
        load_dotenv()
        url = os.environ["DATABASE_URL"]
    return create_async_engine(url)


def build_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)
