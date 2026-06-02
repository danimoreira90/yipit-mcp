"""Engine/session factory tests — verify lazy construction, no import-time side effects."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

import backend.services.db as db_module


def test_build_engine_returns_async_engine_without_connecting() -> None:
    engine = db_module.build_engine("postgresql+asyncpg://kpi:kpi@localhost:5432/kpi_test")
    assert isinstance(engine, AsyncEngine)


def test_build_sessionmaker_returns_sessionmaker() -> None:
    engine = db_module.build_engine("postgresql+asyncpg://kpi:kpi@localhost:5432/kpi_test")
    maker = db_module.build_sessionmaker(engine)
    assert isinstance(maker, async_sessionmaker)


def test_no_eager_engine_at_module_scope() -> None:
    # SIMPLICITY §2: no framework wired at import time.
    assert not hasattr(db_module, "engine")
    assert not hasattr(db_module, "_engine")
