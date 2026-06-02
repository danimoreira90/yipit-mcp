"""Domain models (ubiquitous language). Pydantic 2 value objects — data + provenance,
no behavior they don't need. estimate_type is the EstimateType enum; QtdResult always
carries a latest_as_of (provenance, HR-5).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel


class EstimateType(str, Enum):
    HISTORICAL = "historical"
    QTD = "qtd"


class Company(BaseModel):
    ticker: str
    name: str
    sector: str


class KpiUnit(BaseModel):
    kpi: str
    unit: str


class HistoryPoint(BaseModel):
    period: str
    period_end: date
    value: Decimal
    unit: str


class QtdSnapshot(BaseModel):
    as_of: date
    value: Decimal


class QtdResult(BaseModel):
    period: str
    latest_as_of: date
    latest_value: Decimal
    unit: str
    trajectory: list[QtdSnapshot]


class LatestHistory(BaseModel):
    period: str
    value: Decimal


class LatestQtd(BaseModel):
    value: Decimal
    as_of: date


class KpiOverview(BaseModel):
    kpi: str
    unit: str
    latest_history: LatestHistory | None = None
    latest_qtd: LatestQtd | None = None


class CompanyOverview(BaseModel):
    company: Company
    kpis: list[KpiOverview]


class KpiEstimate(BaseModel):
    ticker: str
    kpi: str
    unit: str
    period: str
    period_start: date
    period_end: date
    estimate_type: EstimateType
    value: Decimal
    as_of: date | None = None
