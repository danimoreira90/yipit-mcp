# Architecture

> Diagrams are grounded in the actual repo — every box is a real module/file. Both Mermaid
> blocks below were validated (no syntax errors). Intended to embed in the README.

## Container view — two consumers, two transports, one shared seam

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

The point of the whole design is the convergence in the middle: a human (via the React frontend
and REST) and an AI agent (via the MCP server) are **two transports that meet at one seam** —
the `KpiService` facade (ADR-003) — not two parallel stacks. Each transport is a thin wrapper
that owns no query logic and never touches the database; that "DB-free" rule is executable, not
aspirational — `backend/tests/test_architecture.py` parses every module under `backend/api` and
`backend/mcp` and fails the build if one imports SQLAlchemy or opens a session. Below the seam,
the facade delegates to the typed service functions in `companies.py` / `estimates.py`, which run
parameterized async SQLAlchemy against Postgres; the sample CSV is a one-time seed via `db/seed.py`.

## Write path — `POST /companies/{ticker}/estimates`

```mermaid
sequenceDiagram
    actor client as REST client (frontend / HTTP)
    participant rest as REST route
    participant facade as KpiService
    participant svc as estimates.publish_estimate
    participant pg as PostgreSQL

    client->>rest: POST /companies/{ticker}/estimates
    rest->>facade: publish_estimate(ticker, ...)
    facade->>svc: publish_estimate(session, ...)
    svc->>pg: INSERT ... ON CONFLICT ... RETURNING
    pg-->>svc: persisted row
    svc-->>facade: KpiEstimate
    facade->>facade: session.commit()
    facade-->>rest: KpiEstimate (read-after-write)
    rest-->>client: 201 Created
```

Publishing is the only write in the system, and it is **REST-only** — the MCP surface is read-only
by design (6 read tools, no write tool), so an AI agent cannot publish; only the REST client does.
This traces it to show it goes through the **same
seam** as every read: the REST route hands off to `KpiService.publish_estimate`, which owns the
session and commit, while `estimates.publish_estimate` does the upsert — `INSERT ... ON CONFLICT`
targeting the partial-unique index that matches the estimate type (historical vs qtd). The
`RETURNING` clause hands the persisted row straight back, so the response is a read-after-write of
exactly what landed in `kpi_estimates` — no second round-trip, no client-side guessing.
