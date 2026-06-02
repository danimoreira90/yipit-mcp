"""Typed domain errors (ubiquitous language).

These carry the offending value so the transport layer (MCP/REST) can render the
structured, remediation-oriented messages from the SPEC error contract. Computation
and context stay server-side (HR-5) — the consumer never has to guess.
"""

from __future__ import annotations


class UnknownTicker(Exception):
    def __init__(self, ticker: str) -> None:
        self.ticker = ticker
        super().__init__(f"unknown ticker '{ticker}'")


class UnknownKpi(Exception):
    def __init__(self, kpi: str, available: list[str] | None = None) -> None:
        self.kpi = kpi
        self.available = available
        message = f"unknown kpi '{kpi}'"
        if available:
            message += f". This company reports: {', '.join(available)}"
        super().__init__(message)


class InvalidDateRange(Exception):
    def __init__(self, start: object, end: object) -> None:
        self.start = start
        self.end = end
        super().__init__(f"start must be <= end (got start={start}, end={end})")


class NoQtdData(Exception):
    def __init__(self, ticker: str, kpi: str) -> None:
        self.ticker = ticker
        self.kpi = kpi
        super().__init__(
            f"no QTD estimate for {ticker} / {kpi} "
            "(QTD exists only for the in-progress quarter)"
        )
