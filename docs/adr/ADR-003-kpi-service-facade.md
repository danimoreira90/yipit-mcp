# ADR-003: A session-bound KpiService facade between transports and queries

**Status:** Accepted
**Date:** 2026-06-02
**Deciders:** Daniel Moreira
**Related:** `CLAUDE.md` (architecture spine), `docs/specs/mcp-server.md`, ADR-001 (async), the spine fitness function (`backend/tests/test_architecture.py`)

---

## Context

The spine is "one typed service layer, two thin transports." The query functions in
`backend/services/companies.py` and `estimates.py` take an `AsyncSession` as their first
argument (dependency injection — tests pass a session bound to `kpi_test`).

A hard constraint emerged while building the MCP transport (Task 4.1): **transports must
not open sessions or run SQL.** The reasons are (a) it keeps the spine's dependency rule
crisp and enforceable, and (b) the FastMCP tool modules must not even import `sqlalchemy`
— a top-level `mcp`-package collision aside (ADR-002), keeping the tool layer free of DB
types makes it trivially testable and the fitness function trivially expressible.

That left a gap: if the transport can't hold a session, *something* must open one per call
and pass it to the query function. Putting that in each transport would duplicate session
plumbing across MCP and REST and re-introduce DB handling into the transport layer.

## Decision

Introduce one **session-bound application facade**, `KpiService`
(`backend/services/kpi_service.py`), constructed with a `sessionmaker`. It exposes
**session-free** async methods (`list_sectors()`, `get_qtd(ticker, kpi)`, …); each opens a
session via `async with self._sessionmaker() as session:` and delegates to the
corresponding query function. Both transports depend only on `KpiService` (plus domain
models/errors) — never on `sqlalchemy`.

```
MCP tools  ─┐                                 ┌─ companies.* (session, …)
            ├─▶ KpiService(sessionmaker) ─────┤
REST routes ┘   (owns session lifecycle)      └─ estimates.*  (session, …)
```

## Consequences

**Positive**
- Transports are genuinely DB-free, enforced by `test_architecture.py` (the fitness
  function scans `backend/mcp` and `backend/api` for any `sqlalchemy`/`session`/`.execute`).
- Session lifecycle lives in exactly one place; the two transports share it (one facade,
  two callers — it earns its keep today, not speculatively).
- Query functions stay session-injected, so they remain directly unit-testable against a
  test session without going through a transport.

**Negative / trade-off**
- A third layer (transport → facade → query fn) the original SPEC diagram didn't show; this
  ADR is the record, and the README diagram (Phase 9) will be updated to match.
- The facade methods are mechanically uniform (open session, delegate). That repetition is
  accepted in favour of explicit, individually-typed methods over a generic
  "run-in-session" helper; the duplication is plumbing, not logic.

## Alternatives rejected

- **Transports take a session via DI and call query fns directly.** Rejected: it forces the
  transport layer to import `sqlalchemy` and manage sessions — exactly what the spine
  constraint (and the fitness function) forbid.
- **Query functions manage their own sessions (no session arg).** Rejected: it removes the
  injection seam the integration tests rely on (they run many calls inside one seeded
  session/transaction).
