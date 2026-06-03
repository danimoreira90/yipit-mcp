# ADR-002: MCP server lives under backend/mcp (not a top-level mcp/)

**Status:** Accepted
**Date:** 2026-06-02
**Deciders:** Daniel Moreira
**Related:** `CLAUDE.md` (layout), `PLAN.md` (Phase 4), `docs/specs/mcp-server.md`

---

## Context

The plan called for the FastMCP server to live in a top-level `mcp/` package (`mcp/server.py`, imported as `mcp.server`). FastMCP depends on the **`mcp` PyPI SDK** (`mcp==1.27.2`), which installs a **regular package** named `mcp` (with `__init__.py`) into the environment — and that SDK already ships a `mcp.server` submodule.

Python resolves the import name `mcp` to that installed regular package process-wide. A top-level project directory named `mcp/` therefore cannot be imported as `mcp.*`: the SDK always wins. Verified empirically — even with the project root first on `sys.path`, `import mcp.server` resolves to `site-packages/mcp/server/__init__.py`, not our file:

```
import mcp.server  ->  .venv/.../site-packages/mcp/server/__init__.py   (the SDK)
                       our marker absent, even with "." at sys.path[0]
```

Consequence of ignoring this: tests and `fastmcp run` would **silently load the SDK** instead of our server. There is no `sys.path` ordering trick — a regular package shadows a same-named namespace directory regardless of order.

## Decision

Place the FastMCP server at **`backend/mcp/`**, imported as **`backend.mcp`** (e.g. `backend.mcp.server`). Namespacing it under our `backend` package gives it a fully-qualified name distinct from the top-level `mcp` SDK, so there is no collision. Drop the planned top-level `mcp/` package.

## Consequences

**Positive**
- Imports are unambiguous (`from backend.mcp.server import build_server`); tests and `python -m backend.mcp.server` load our code, never the SDK.
- No fragile `sys.path` manipulation.

**Negative / trade-off**
- The "two transports" diagram shows MCP as a sibling of `backend`; physically it now lives *under* `backend/`. The architecture is unchanged (both transports are still thin wrappers over `backend/services/`); only the file location differs. The README diagram notes this.

**Neutral**
- `pyright` `include` drops the stale top-level `mcp` entry (now covered by `backend`).
- The spine fitness function (PLAN Task 6.1) scans `backend/mcp/` (and `backend/api/`) instead of a top-level `mcp/`.

## Alternatives rejected

- **Top-level `mcp_server/` or `kpi_mcp/`.** Both avoid the collision, but Daniel preferred keeping the name "mcp" (namespaced under `backend`) for readability.
- **Keep `mcp/` and import by file path** (importlib from path). Fragile, breaks normal tooling (`fastmcp run`, pyright, test discovery). Rejected.
