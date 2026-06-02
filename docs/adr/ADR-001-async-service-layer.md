# ADR-001: Async service layer (SQLAlchemy 2.0 async + asyncpg)

**Status:** Accepted
**Date:** 2026-06-02
**Deciders:** Daniel Moreira
**Related:** `docs/specs/mcp-server.md`, `CLAUDE.md` (architecture spine), DATA-MODEL.md §7

---

## Context

The `services/` layer is the single place all query logic lives; **two transports** wrap it — FastMCP (this build) and FastAPI REST (later). The take-home is **graded on reliability and scale**, and the service is **DB-fronting**: nearly every request is I/O-bound on a single round-trip (or a few) to Postgres, not CPU-bound.

The local seed is small (2000 rows), so raw data volume does not force a choice. The choice is about the **concurrency model the same code must support under the stated stack** (FastAPI + FastMCP, both async-native) and under the grading lens (scalability).

Options considered:
1. **Sync** SQLAlchemy 2.0 + psycopg — simplest to write and test for a 2k-row local app.
2. **Async** SQLAlchemy 2.0 + asyncpg — matches FastAPI/FastMCP's native model.

## Decision

Use **async**: SQLAlchemy 2.0 async engine/session + asyncpg. Service functions are `async def`; tests use `pytest-asyncio`.

## Rationale (scalability — the graded axis)

- **I/O-bound concurrency without thread-per-request.** A DB-fronting endpoint spends almost all its wall-clock waiting on Postgres. Async lets a single worker keep many in-flight requests progressing on one event loop, instead of parking an OS thread per concurrent request. For the REST transport serving concurrent UI clients (charts + search), this is the scalability story the grading asks for.
- **No transport/data-layer impedance mismatch.** FastAPI and FastMCP are async-native. A sync data layer underneath would force `run_in_threadpool` bridging at every call — added complexity and a thread pool that becomes the real concurrency ceiling. Async end-to-end keeps **one** concurrency model from transport to driver.
- **One code path, both transports.** The spine mandates shared `services/`. Picking the transports' native model means MCP and REST call the same `async` functions directly — no duplicated sync/async variants.
- **Connection pooling is explicit.** The async engine's pool gives a clear, documentable knob for the README's scaling plan (pool size, overflow) — concrete scalability material, not hand-waving.

## Consequences

**Positive**
- Matches the stack; one concurrency model throughout; honest scalability narrative for grading.
- Async connection pool is the natural place to document horizontal-scale limits.

**Negative / costs (stated honestly)**
- Slightly more ceremony in tests (`pytest-asyncio`, async fixtures) than sync.
- asyncpg-specific behaviors (no implicit transactions sharing across tasks) require care — mitigated by a session-per-request/per-call pattern.
- For *this* 2k-row local seed, async buys no measurable speed; the justification is the stack fit + the REST path + the grading axis, **not** local performance. We are explicit that this is not premature optimization of data volume but alignment with the required concurrency model.

**Neutral**
- Datastore consistency model (Postgres = CP) is a separate decision — recorded in its own ADR (see PLAN Phase 6, ADR-005).

## Alternatives rejected

- **Sync now, async later.** Rejected: the services layer is the shared core; rewriting its concurrency model after REST is built means touching every function and every test — the exact cost the spine exists to avoid.
