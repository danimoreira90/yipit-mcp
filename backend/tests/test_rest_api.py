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


# --- POST /companies/{ticker}/estimates (publish) ---------------------------


def _qtd_body(value: str, as_of: str, kpi: str = "ASP ($)") -> dict[str, str]:
    return {
        "kpi": kpi,
        "period": "2026Q1",
        "period_start": "2026-01-01",
        "period_end": "2026-03-31",
        "estimate_type": "qtd",
        "value": value,
        "as_of": as_of,
    }


async def _estimates(client: AsyncClient) -> list[dict[str, object]]:
    return (await client.get("/companies/ACME/estimates")).json()


async def test_post_estimate_persists_and_round_trips(client: AsyncClient) -> None:
    # A brand-new qtd snapshot (as_of not in the seed).
    response = await client.post("/companies/ACME/estimates", json=_qtd_body("170.00", "2026-03-31"))
    assert response.status_code == 201
    created = response.json()
    assert created["unit"] == "$"  # derived server-side from the kpi

    rows = await _estimates(client)
    match = [
        r
        for r in rows
        if r["kpi"] == "ASP ($)" and r["estimate_type"] == "qtd" and r["as_of"] == "2026-03-31"
    ]
    assert len(match) == 1
    assert Decimal(str(match[0]["value"])) == Decimal("170.00")
    assert match[0]["unit"] == "$"


async def test_post_estimate_upserts_on_conflict_key(client: AsyncClient) -> None:
    # ACME ASP 2026Q1 qtd @ 2026-01-31 already exists in the seed (162.95) -> UPDATE, not insert.
    before = await _estimates(client)
    response = await client.post("/companies/ACME/estimates", json=_qtd_body("999.99", "2026-01-31"))
    assert response.status_code == 201
    after = await _estimates(client)

    assert len(after) == len(before)  # updated in place, no duplicate row
    match = [
        r
        for r in after
        if r["kpi"] == "ASP ($)" and r["estimate_type"] == "qtd" and r["as_of"] == "2026-01-31"
    ]
    assert len(match) == 1
    assert Decimal(str(match[0]["value"])) == Decimal("999.99")


async def test_post_estimate_malformed_body_returns_422(client: AsyncClient) -> None:
    response = await client.post("/companies/ACME/estimates", json={"kpi": "ASP ($)"})  # missing fields
    assert response.status_code == 422


async def test_post_estimate_unknown_ticker_returns_404(client: AsyncClient) -> None:
    response = await client.post("/companies/ZZZ/estimates", json=_qtd_body("100", "2026-01-31"))
    assert response.status_code == 404
    assert response.json()["error"] == "unknown_ticker"


async def test_post_estimate_unknown_kpi_returns_422(client: AsyncClient) -> None:
    response = await client.post(
        "/companies/ACME/estimates", json=_qtd_body("100", "2026-01-31", kpi="Revenue")
    )
    assert response.status_code == 422
    body = response.json()
    assert body["error"] == "unknown_kpi"
    assert "ASP ($)" in body["detail"]  # names valid KPIs


async def test_post_estimate_as_of_type_mismatch_returns_422(client: AsyncClient) -> None:
    # historical with an as_of set -> violates as_of_matches_type; rejected at the boundary.
    body = {
        "kpi": "ASP ($)",
        "period": "2022Q1",
        "period_start": "2022-01-01",
        "period_end": "2022-03-31",
        "estimate_type": "historical",
        "value": "100",
        "as_of": "2022-01-15",
    }
    response = await client.post("/companies/ACME/estimates", json=body)
    assert response.status_code == 422
