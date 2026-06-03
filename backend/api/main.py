"""Production composition root: wire the real engine into the app for `uvicorn`.

`create_app(service)` stays a DI factory (tests inject a test-bound service); this module
builds the real engine/sessionmaker/service once and exposes the ASGI `app`.

Run:  uvicorn backend.api.main:app --port 8000
"""

from __future__ import annotations

from backend.api.app import create_app
from backend.services.db import build_engine, build_sessionmaker
from backend.services.kpi_service import KpiService

app = create_app(KpiService(build_sessionmaker(build_engine())))
