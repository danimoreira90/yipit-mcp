"""FastAPI REST API — a thin transport over the KpiService facade.

Like the MCP tools, routes carry no query logic, no SQL, and no DB session (all of
that lives in backend/services). Typed domain errors map to HTTP responses via
exception handlers, so route bodies stay one line.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.schemas import PublishEstimateRequest
from backend.services.errors import UnknownKpi, UnknownTicker
from backend.services.kpi_service import KpiService
from backend.services.models import KpiEstimate


def create_app(service: KpiService) -> FastAPI:
    """Build the API, wiring routes to the injected service facade."""
    app = FastAPI(title="YipitData KPI API")

    async def unknown_ticker_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=404, content={"error": "unknown_ticker", "detail": str(exc)}
        )

    async def unknown_kpi_handler(request: Request, exc: Exception) -> JSONResponse:
        # 422: the body is well-formed but the kpi value is not one of the dataset's KPIs
        # (a data-driven set Pydantic can't enumerate at schema-build time).
        return JSONResponse(
            status_code=422, content={"error": "unknown_kpi", "detail": str(exc)}
        )

    app.add_exception_handler(UnknownTicker, unknown_ticker_handler)
    app.add_exception_handler(UnknownKpi, unknown_kpi_handler)

    async def get_company_estimates(ticker: str) -> list[KpiEstimate]:
        return await service.list_company_estimates(ticker)

    async def publish_company_estimate(
        ticker: str, body: PublishEstimateRequest
    ) -> KpiEstimate:
        return await service.publish_estimate(
            ticker,
            kpi=body.kpi,
            period=body.period,
            period_start=body.period_start,
            period_end=body.period_end,
            estimate_type=body.estimate_type,
            value=body.value,
            as_of=body.as_of,
        )

    app.add_api_route(
        "/companies/{ticker}/estimates",
        get_company_estimates,
        methods=["GET"],
        response_model=list[KpiEstimate],
    )
    app.add_api_route(
        "/companies/{ticker}/estimates",
        publish_company_estimate,
        methods=["POST"],
        response_model=KpiEstimate,
        status_code=201,
    )
    return app
