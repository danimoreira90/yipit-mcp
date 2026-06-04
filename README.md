# YipitData KPI Portal + MCP

A portal that lets time-constrained public investors browse YipitData KPI estimates per company — settled quarterly history versus the live quarter-to-date (QTD) estimate — chart and export them, and search by sector, company, or KPI. The same data is exposed twice: as a REST API behind a React frontend for humans, and as an MCP server so an AI agent (Claude Desktop, Cursor) can answer the same investor questions directly.

The one decision the whole codebase turns on: **one typed service layer, two thin transports.** REST and MCP are wrappers; all query logic lives in `backend/services/` and runs once.

## Quick start

Prerequisites: Docker (for Postgres), [uv](https://docs.astral.sh/uv/) (Python 3.11+), Node 20.

```powershell
# 1. Config — copy the example, local dev values are filled in already
cp .env.example .env

# 2. Postgres — first init auto-creates kpi + kpi_test and applies db/schema.sql
docker compose up -d

# 3. Python deps + seed the 2000-row sample into the dev DB
uv sync
uv run python -m db.seed

# 4. REST API (http://localhost:8000)
uv run uvicorn backend.api.main:app --port 8000

# 5. Frontend (http://localhost:5173) — in a second shell
cd frontend
npm install
npm run dev
```

The schema is applied by Postgres on first container init (mounted into `/docker-entrypoint-initdb.d/`), so step 2 leaves an empty schema and step 3 fills it. The seed is idempotent (truncate-then-load), so re-running it is safe. To launch the MCP server instead of (or alongside) the API, see [MCP server](#mcp-server).

## Architecture

Two consumers, two transports, one shared seam. A human goes browser → React frontend → REST; an agent goes MCP client → MCP tools. Both transports converge on the `KpiService` facade and never touch the database themselves.

```mermaid
flowchart TD
    subgraph consumers["Consumers"]
        browser["Investor (web browser)"]
        agent["AI agent (Claude Desktop / Cursor)"]
    end

    fe["React + Vite frontend<br/>frontend/, api/client.ts"]

    subgraph transports["Transport layer - DB-free, enforced by backend/tests/test_architecture.py"]
        rest["REST API (FastAPI)<br/>backend/api/app.py, main.py"]
        mcp["MCP server (FastMCP)<br/>backend/mcp/server.py"]
    end

    subgraph seam["Shared service seam (ADR-003)"]
        facade["KpiService facade<br/>backend/services/kpi_service.py"]
    end

    subgraph services["Service layer"]
        companies["companies.py<br/>list_sectors, list_companies, list_kpis"]
        estimates["estimates.py<br/>get_kpi_history, get_qtd, get_company_overview,<br/>list_company_estimates, publish_estimate"]
        db["async SQLAlchemy engine<br/>backend/services/db.py"]
    end

    subgraph data["Data"]
        pg[("PostgreSQL 16<br/>companies, kpi_estimates")]
        csv["db/kpi_sample_2000.csv"]
        seed["db/seed.py"]
    end

    browser --> fe
    fe -->|"HTTP / JSON"| rest
    agent -->|"MCP protocol"| mcp
    rest --> facade
    mcp --> facade
    facade --> companies
    facade --> estimates
    companies --> db
    estimates --> db
    db --> pg
    csv --> seed --> pg
```

The "DB-free transport" rule is executable, not aspirational. `backend/tests/test_architecture.py` is a fitness function: it AST-scans every module under `backend/api` and `backend/mcp` and fails the build if one imports SQLAlchemy or references a session or `.execute()`. That keeps query logic from leaking into either transport and keeps the seam honest as the code grows. The facade (`KpiService`) owns session lifecycle and delegates to the typed query functions in `companies.py` / `estimates.py`; the transports depend only on the facade plus domain models and errors.

Both diagrams — the container view above and the write-path sequence for `POST /companies/{ticker}/estimates` — live in [`docs/architecture.md`](docs/architecture.md), grounded in real module paths.

## Design decisions

Non-trivial choices are recorded as ADRs in [`docs/adr/`](docs/adr/):

- [ADR-001](docs/adr/ADR-001-async-service-layer.md) — async SQLAlchemy + asyncpg. The service is DB-fronting and I/O-bound; async keeps one concurrency model from transport to driver and gives an explicit connection pool to reason about for scale. For the 2k-row local seed it buys no measurable speed; the justification is stack fit and the scalability axis, stated honestly.
- [ADR-002](docs/adr/ADR-002-mcp-package-location.md) — the MCP server lives at `backend/mcp/`, not a top-level `mcp/`. FastMCP depends on the `mcp` PyPI SDK, which installs a regular package named `mcp` that shadows any same-named project directory regardless of `sys.path` order. Namespacing under `backend` removes the collision.
- [ADR-003](docs/adr/ADR-003-kpi-service-facade.md) — the `KpiService` facade. Transports can't open sessions (the spine rule), but something must per call. One session-bound facade does it, so session plumbing lives in exactly one place instead of being duplicated across REST and MCP.

The read-only MCP surface is a deliberate design decision (recorded in the MCP spec, §8): exposing writes to arbitrary agents is unnecessary risk, so publishing is REST-only and the service has no write path reachable from a tool.

## Tech choices

Each is the lightest fit for the assignment's constraints, not a default.

- **FastAPI + Pydantic 2** — typed request/response models, async-native, OpenAPI for free. Routes stay one line because typed domain errors map to HTTP via exception handlers.
- **FastMCP** — the MCP transport. Wraps the same `KpiService` as REST, so there is no second code path to keep in sync.
- **SQLAlchemy 2.0 async + asyncpg** — parameterized queries (no string-built SQL), one async concurrency model end to end (ADR-001).
- **PostgreSQL 16** — the partial-unique indexes and the `as_of`/`estimate_type` CHECK below model the history-vs-QTD distinction at the storage layer; Postgres is the natural fit, and its ACID atomicity means a publish either lands whole or not at all, so investors never read a torn estimate.
- **Vite + React 18 + TypeScript** — the frontend is a pure client of a separate API: no SSR, SEO, or API-routes need, so Next.js machinery would be weight without benefit. Recharts for charts, TanStack Query for server state.

## Data model

Two tables ([`db/schema.sql`](db/schema.sql)). `companies(ticker, company_name, sector)` and `kpi_estimates`, which holds both estimate kinds in one table discriminated by `estimate_type IN ('historical','qtd')`. Each row carries its own `unit`, `period`, `period_start/end`, `value`, and — for QTD only — an `as_of` snapshot date.

The two kinds have different natural keys, modeled as two partial-unique indexes: `uq_hist (ticker, kpi, period) WHERE estimate_type = 'historical'` (one settled value per finished quarter) and `uq_qtd (ticker, kpi, period, as_of) WHERE estimate_type = 'qtd'` (one value per intra-quarter snapshot). A publish is an `INSERT ... ON CONFLICT` targeting whichever index matches the type. A CHECK constraint, `as_of_matches_type`, enforces that historical rows have a NULL `as_of` and QTD rows have a non-NULL one — the history/QTD distinction can't be violated even by a direct write.

The seed is `db/kpi_sample_2000.csv`: 2000 rows, 20 companies, 5 KPIs, 18 sectors; historical 2022Q1–2025Q4 and QTD for the in-progress 2026Q1 across four snapshots.

## MCP server

Six read-only tools, each a thin wrapper that calls exactly one service function and returns a typed Pydantic model with provenance (`unit`, `period`, and for QTD `as_of`) — never prose the agent might over-trust:

- `list_sectors()` — every sector in the dataset; the discovery entry point.
- `list_companies(sector?, query?)` — filter by sector and/or a case-insensitive search over name, ticker, and sector. No match returns `[]`, not an error.
- `list_kpis(ticker)` — the KPIs a company reports, each with its unit.
- `get_kpi_history(ticker, kpi, start?, end?)` — settled quarterly history, oldest-first, optionally bounded by date on the quarter start.
- `get_qtd(ticker, kpi)` — the live quarter-to-date estimate: latest snapshot plus the full intra-quarter trajectory, each point carrying its `as_of`.
- `get_company_overview(ticker)` — one-call snapshot: every KPI with its latest settled value and latest QTD value; either side is null when absent, never fabricated.

All computation (latest-snapshot selection, ordering, date filtering, distinct) happens server-side in `services/` and deterministically — the consuming model is never asked to infer it. Errors are structured and actionable so the agent self-corrects: an unknown ticker points to `list_companies()`, an unknown KPI names the valid enum and the KPIs that ticker actually reports, and `start > end` says so. Tool docstrings name the five valid KPIs verbatim so the agent doesn't guess spelling.

### Connect from an AI client

The MCP server launches over stdio (`uv run python -m backend.mcp.main`, or `fastmcp run backend/mcp/main.py:mcp`). To wire it into Claude Desktop, edit `claude_desktop_config.json` at `%APPDATA%\Claude\` (the Microsoft Store build keeps it under a packaged path like `%LOCALAPPDATA%\Packages\...\LocalCache\Roaming\Claude\` instead):

```json
{
  "mcpServers": {
    "yipit-kpi": {
      "command": "<absolute-path-to-repo>\\.venv\\Scripts\\python.exe",
      "args": ["-m", "backend.mcp.main"],
      "cwd": "<absolute-path-to-repo>",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://kpi:kpi@localhost:5432/kpi",
        "PYTHONPATH": "<absolute-path-to-repo>"
      }
    }
  }
}
```

Replace `<absolute-path-to-repo>` with the repo's absolute path (Claude Desktop does not resolve relative paths). Use the venv's Python as `command` so FastMCP and the deps resolve. Set both `DATABASE_URL` and `PYTHONPATH` to the repo root in `env` — the project isn't pip-installed (`package = false`), so `cwd` alone is not reliably enough to import `backend.mcp.main`. Gotchas: fully quit and restart Claude Desktop after editing the config (it reads it once at launch), and make sure Postgres is up and seeded first or every tool call errors on connect.

### Example session (Claude Desktop)

Wired in via the config above, an agent answers investor questions by chaining the tools itself. It shows as `running` in Claude Desktop → Settings → Developer:

![MCP server running in Claude Desktop](docs/screenshots/mcp-01-server-connected.png)

**Discovery** — *"What sectors and companies do you have KPI estimates for?"* The agent calls `list_sectors` then `list_companies` and returns the 18 sectors and 20 companies:

![Agent lists sectors and companies](docs/screenshots/mcp-02-discovery-sectors-companies.png)

**History + live QTD** — *"How has ACME's ASP trended?"* It pulls `get_kpi_history` and `get_qtd`, charts the settled quarters, and marks the in-progress 2026Q1 as a live estimate, visually distinct from settled history:

![Agent charts ASP history and QTD](docs/screenshots/mcp-03-asp-history-and-qtd.png)

**Error recovery** — *"Pull revenue for ticker ZZZZ."* The unknown-ticker error names the valid tickers, so the agent recovers, lists them, and refuses to invent a value:

![Agent recovers from an unknown ticker](docs/screenshots/mcp-04-error-recovery.png)

## Reliability, performance, scalability

What's actually true today. All SQL is parameterized via SQLAlchemy — no string-built queries. Ordering is deterministic and done in-service (Python codepoint sort) rather than relying on DB collation, so identical args give identical output. `get_company_overview` is a bounded number of queries (three), not one-per-KPI in a loop — no N+1. The async engine pools connections, which is the knob a real deployment would tune (pool size, overflow) for concurrent UI clients.

Honest limits: this runs as a single process against a single local Postgres with a 2000-row seed. There is no caching layer, no read replica, no rate limiting, and no load testing — the scalability story is the async/pooled shape and a single-node ACID datastore, documented rather than benchmarked at scale.

## Observability, monitoring, auditing

A baseline is shipped; the rest is planned. Built: structured JSON logging configured once (`backend/observability.py`, stdout); a `GET /health` readiness endpoint that checks DB reachability through the `KpiService` facade so the route itself stays DB-free; request-id middleware that sets `X-Request-ID` and emits one JSON log line per REST request (id, method, path, status, latency); and a structured log line per MCP tool call (call id, tool, arg summary — never secrets). Still planned: a metrics hook (request count, latency, error rate) exported to Prometheus, and an append-only audit trail on the one write path (`publish_estimate`) recording who published what and when. None of this changes the spine — it sits at the transport edges and around the facade.

## Testing

Test-driven throughout: a failing test (with real RED output) before each piece of production code, then the minimum to pass. 96 tests across the backend. Service correctness is tested against a real seeded `kpi_test` Postgres (never a mocked function under test) — the six query patterns plus every documented edge case. Transport tests assert each REST route and MCP tool delegates to its service function, returns the typed model with its provenance fields, and maps domain errors to the right contract. Ground-truth value guards assert specific seeded numbers, not just shapes, so a wrong query can't pass. The spine fitness function (`backend/tests/test_architecture.py`) is parametrized over every transport module, so adding a transport file adds a collected case automatically.

```powershell
uv run pytest          # backend, 96 tests
cd frontend; npm test  # frontend (vitest)
```

## Future improvements

- Collapse the small duplication between the publish and read error messaging into one shared mapping.
- The seed truncates and reloads on every run; a faster path would re-seed only changed rows for large datasets.
- Make `backend` pip-installable (drop `package = false`) so the MCP client config no longer needs `PYTHONPATH`.
- Run the MCP tool-ergonomics eval (Phase 8, Claude Haiku) and record the `pass@3` / `pass^3` signal here.
