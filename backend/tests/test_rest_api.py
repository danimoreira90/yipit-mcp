"""REST API tests — drive the FastAPI app with httpx AsyncClient against the seeded
kpi_test DB. The app is built over a KpiService bound to the test engine; the route
layer stays DB-free (all access via the service facade).
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from decimal import Decimal

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.api.app import create_app
from backend.services.db import build_sessionmaker
from backend.services.kpi_service import KpiService


@pytest_asyncio.fixture
async def client(seeded_engine: AsyncEngine) -> AsyncGenerator[AsyncClient, None]:
    app = create_app(KpiService(build_sessionmaker(seeded_engine)))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as http_client:
        yield http_client


async def test_get_company_estimates_success(client: AsyncClient) -> None:
    response = await client.get("/companies/ACME/estimates")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 100  # all estimates for the company (history + qtd)
    required = {"ticker", "kpi", "unit", "period", "estimate_type", "value", "as_of"}
    assert all(required <= row.keys() for row in data)
    assert all(row["ticker"] == "ACME" for row in data)
    # Ground truth: deterministic ordering puts ASP ($) 2022Q1 historical (128.67) first.
    first = data[0]
    assert first["kpi"] == "ASP ($)"
    assert first["period"] == "2022Q1"
    assert Decimal(str(first["value"])) == Decimal("128.67")


async def test_get_company_estimates_unknown_ticker_returns_404(client: AsyncClient) -> None:
    response = await client.get("/companies/ZZZ/estimates")
    assert response.status_code == 404
    body = response.json()
    assert body["error"] == "unknown_ticker"
    assert "ZZZ" in body["detail"]
