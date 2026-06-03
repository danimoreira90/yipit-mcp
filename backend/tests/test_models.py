"""Domain model tests (ubiquitous language: Company, KpiEstimate, EstimateType,
HistoryPoint, QtdResult, CompanyOverview).

Behavioral — they assert real validation rules, not just that the classes import.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from backend.services.errors import InvalidDateRange, NoQtdData, UnknownKpi, UnknownTicker
from backend.services.models import (
    Company,
    CompanyOverview,
    EstimateType,
    HistoryPoint,
    KpiEstimate,
    KpiOverview,
    KpiUnit,
    LatestHistory,
    QtdResult,
    QtdSnapshot,
)


def test_estimate_type_has_exactly_two_members() -> None:
    assert {e.value for e in EstimateType} == {"historical", "qtd"}


def test_estimate_type_rejects_unknown_value() -> None:
    with pytest.raises(ValueError):
        EstimateType("bogus")


def test_history_point_carries_unit_period_value() -> None:
    point = HistoryPoint(
        period="2024Q1", period_end=date(2024, 3, 31), value=Decimal("128.67"), unit="$"
    )
    assert point.period == "2024Q1"
    assert point.unit == "$"
    assert point.value == Decimal("128.67")


def test_history_point_requires_value() -> None:
    with pytest.raises(ValidationError):
        HistoryPoint.model_validate(
            {"period": "2024Q1", "period_end": date(2024, 3, 31), "unit": "$"}  # no value
        )


def test_qtd_result_requires_latest_as_of() -> None:
    with pytest.raises(ValidationError):
        QtdResult.model_validate(
            {"period": "2026Q1", "latest_value": Decimal("1"), "unit": "$", "trajectory": []}
        )


def test_qtd_result_round_trips_trajectory() -> None:
    result = QtdResult(
        period="2026Q1",
        latest_as_of=date(2026, 3, 15),
        latest_value=Decimal("5"),
        unit="$",
        trajectory=[QtdSnapshot(as_of=date(2026, 1, 31), value=Decimal("4"))],
    )
    assert result.latest_as_of == date(2026, 3, 15)
    assert result.trajectory[0].value == Decimal("4")


def test_kpi_estimate_rejects_unknown_estimate_type() -> None:
    with pytest.raises(ValidationError):
        KpiEstimate.model_validate(
            {
                "ticker": "ACME",
                "kpi": "ASP ($)",
                "unit": "$",
                "period": "2026Q1",
                "period_start": date(2026, 1, 1),
                "period_end": date(2026, 3, 31),
                "estimate_type": "bogus",
                "value": Decimal("1"),
                "as_of": date(2026, 1, 31),
            }
        )


def test_kpi_estimate_coerces_valid_estimate_type_to_enum() -> None:
    estimate = KpiEstimate.model_validate(
        {
            "ticker": "ACME",
            "kpi": "ASP ($)",
            "unit": "$",
            "period": "2022Q1",
            "period_start": date(2022, 1, 1),
            "period_end": date(2022, 3, 31),
            "estimate_type": "historical",
            "value": Decimal("128.67"),
            "as_of": None,
        }
    )
    assert estimate.estimate_type is EstimateType.HISTORICAL


def test_company_overview_allows_independent_null_sides() -> None:
    overview = CompanyOverview(
        company=Company(ticker="ACME", name="Acme E-commerce", sector="E-commerce"),
        kpis=[
            KpiOverview(
                kpi="ASP ($)",
                unit="$",
                latest_history=LatestHistory(period="2025Q4", value=Decimal("9")),
                latest_qtd=None,
            )
        ],
    )
    assert overview.kpis[0].latest_history is not None
    assert overview.kpis[0].latest_qtd is None


def test_kpi_unit_pairs_kpi_with_unit() -> None:
    ku = KpiUnit(kpi="Units Sold", unit="units")
    assert ku.kpi == "Units Sold"
    assert ku.unit == "units"


def test_unknown_ticker_carries_value() -> None:
    err = UnknownTicker("ZZZ")
    assert isinstance(err, Exception)
    assert "ZZZ" in str(err)


def test_unknown_kpi_lists_available_when_given() -> None:
    err = UnknownKpi("Revenue", available=["ASP ($)", "Units Sold"])
    assert "ASP ($)" in str(err)


def test_invalid_date_range_and_no_qtd_are_exceptions() -> None:
    assert isinstance(InvalidDateRange(date(2025, 1, 1), date(2024, 1, 1)), Exception)
    assert "ACME" in str(NoQtdData("ACME", "ASP ($)"))
