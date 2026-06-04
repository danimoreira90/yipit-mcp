"""Production composition root for the MCP server (mirrors backend/api/main.py).

`build_server(service)` stays a DI factory (tests inject a test-bound service); this module
builds the real engine/sessionmaker/service once and exposes the module-level `mcp` — the
launch target for stdio.

Run (stdio):  uv run python -m backend.mcp.main   |   fastmcp run backend/mcp/main.py:mcp
"""

from __future__ import annotations

from backend.mcp.server import build_server
from backend.services.db import build_engine, build_sessionmaker
from backend.services.kpi_service import KpiService

mcp = build_server(KpiService(build_sessionmaker(build_engine())))

if __name__ == "__main__":
    mcp.run()  # stdio by default
