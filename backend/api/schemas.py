"""Request schemas for the REST API. No SQL/session here — just input validation at the
boundary (so the spine fitness function stays green for backend/api).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, model_validator

from backend.services.models import EstimateType


class PublishEstimateRequest(BaseModel):
    """Body for POST /companies/{ticker}/estimates. `ticker` comes from the path; `unit`
    is derived server-side from the kpi (HR-5 — the client never sets it)."""

    kpi: str
    period: str
    period_start: date
    period_end: date
    estimate_type: EstimateType
    value: Decimal
    as_of: date | None = None

    @model_validator(mode="after")
    def _as_of_matches_type(self) -> PublishEstimateRequest:
        # Mirrors the DB as_of_matches_type CHECK: reject the mismatch at the boundary (422)
        # rather than letting it reach the database.
        if self.estimate_type is EstimateType.HISTORICAL and self.as_of is not None:
            raise ValueError("historical estimates must not carry an as_of")
        if self.estimate_type is EstimateType.QTD and self.as_of is None:
            raise ValueError("qtd estimates require an as_of")
        return self
