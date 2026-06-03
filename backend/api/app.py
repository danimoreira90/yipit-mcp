"""FastAPI REST API — a thin transport over the KpiService facade.

Like the MCP tools, routes carry no query logic, no SQL, and no DB session (all of
that lives in backend/services). Typed domain errors map to HTTP responses via
exception handlers, so route bodies stay one line.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.services.errors import UnknownTicker
from backend.services.kpi_service import KpiService
from backend.services.models import KpiEstimate


def create_app(service: KpiService) -> FastAPI:
    """Build the API, wiring routes to the injected service facade."""
    app = FastAPI(title="YipitData KPI API")

    async def unknown_ticker_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": "unknown_ticker", "detail": str(exc)}
        )

    app.add_exception_handler(UnknownTicker, unknown_ticker_handler)

    async def get_company_estimates(ticker: str) -> list[KpiEstimate]:
        return await service.list_company_estimates(ticker)

    app.add_api_route(
        "/companies/{ticker}/estimates",
        get_company_estimates,
        methods=["GET"],
        response_model=list[KpiEstimate],
    )
    return app
