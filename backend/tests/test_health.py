"""Observability baseline at the REST edge: the /health readiness probe and the
X-Request-ID response header. Both ride the DB-free transport — /health calls the
KpiService facade, never the database directly.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from backend.api.app import create_app
from backend.services.db import build_sessionmaker
from backend.services.kpi_service import KpiService


@pytest_asyncio.fixture
async def client(seeded_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(KpiService(build_sessionmaker(seeded_engine)))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


@pytest_asyncio.fixture
async def down_client() -> AsyncGenerator[AsyncClient, None]:
    # Engine pointed at a closed port: the DB is unreachable, health must report it.
    bad_engine = create_async_engine("postgresql+asyncpg://kpi:kpi@127.0.0.1:1/nope")
    app = create_app(KpiService(build_sessionmaker(bad_engine)))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client
    await bad_engine.dispose()


async def test_health_ok_when_db_reachable(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_health_unavailable_when_db_down(down_client: AsyncClient) -> None:
    response = await down_client.get("/health")
    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}


async def test_response_carries_request_id_header(client: AsyncClient) -> None:
    response = await client.get("/sectors")
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID")
