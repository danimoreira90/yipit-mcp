"""The MCP stdio composition root exposes a module-level `mcp` — the launch target for
`fastmcp run backend/mcp/main.py:mcp` and Claude Desktop. test_mcp_tools.py drives
build_server directly; nothing else exercises main.mcp.
"""

from __future__ import annotations

from fastmcp import FastMCP
from pytest import MonkeyPatch


def test_mcp_main_exposes_a_launchable_server(monkeypatch: MonkeyPatch) -> None:
    # build_engine is lazy, so importing builds the server with no live DB; a dummy
    # DATABASE_URL keeps this independent of a local .env.
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://kpi:kpi@localhost:5432/kpi")
    from backend.mcp.main import mcp

    assert isinstance(mcp, FastMCP)
