# Plan: YipitData KPI Portal + MCP (full assessment)

**Spec (MCP feature):** `docs/specs/mcp-server.md` — **Approved** by Daniel 2026-06-02.
**Scope:** the full take-home — shared `services/` core, **two transports** (FastMCP + FastAPI REST), and a React frontend. MCP-first sequencing; `services/` is the shared spine.
**Status:** Approved. Executing **one task at a time**, TDD throughout, stopping at each green step for Daniel to commit (HR-1).

> **For agentic workers:** REQUIRED: Use subagent-driven-development for every task.
> Each task = one fresh subagent. Spec compliance review → code quality review → ✅ done.
> No task is "done" without: passing verification command (real output shown), reviewer sign-off, and Daniel's commit (HR-1 — agents never commit).

---

## Resolved decisions (folded in from Daniel's approval)
- **Async** services (SQLAlchemy 2.0 async + asyncpg) — ADR-001 written.
- **Eval = quality signal, not a hard gate.** Claude **Haiku**, ~10–15 questions, HR-7 cap, run once, recorded in README; **skips cleanly without an API key**. See SPEC §9.
- **`unit` stored on row**; defer `kpis` lookup table (rule of three).
- **Local dev creds:** Postgres `kpi`/`kpi` (approved, local only).
- **MCP stays read-only.** The **write/publish** path is REST-only — its upsert service fn is built in the REST phase, not the MCP feature (DATA-MODEL.md §5/§7).

## Quality lenses binding every task (raise quality only — SIMPLICITY + HR-2 still bind; ONE modular service, no extra layers/services/infra)
- **Clean Code:** small intention-revealing functions, one level of abstraction, names over comments.
- **DDD ubiquitous language in code:** `Company`, `KpiEstimate`, `EstimateType {historical, qtd}`, `as_of`, `period`.
- **Evolutionary architecture:** the **spine fitness function** (Task 6.1) is a real test asserting **both** transports (MCP tools **and** REST routes) never execute SQL or touch the DB session — only `services/` does.
- **Boundaries:** clean module seams within the single service; no microservices, no infra sprawl.

## EDD Preamble (MCP ergonomics — repurposed per CLAUDE.md)
The EDD target is **tool ergonomics** of an external agent, not an internal model. The eval (`.claude/evals/mcp-ergonomics.md` + JSONL + runner) is authored in Phase 8 and run **once** with Claude Haiku; its `pass@3` / `pass^3` numbers are **reported in the README** against the CLAUDE.md bar — a signal, **not** a CI gate, and the runner **skips without an API key**. Regression fixtures are append-only.

---

## Dependency graph
```
P1 scaffold ─▶ P2 schema+seed ─▶ P3 services/ read layer (TDD)
                                        │
                          ┌─────────────┼──────────────┐
                          ▼             ▼               │
                     P4 MCP tools   P5 REST API         │   (both wrap services/, MCP-first)
                          │             │               │
                          └──────┬──────┘               │
                                 ▼                       │
            P6 spine fitness fn (MCP+REST) + observability (both transports)
                                 │
                                 ▼
                          P7 frontend (Vite+React+TS) ─▶ consumes REST
                                 │
                                 ▼
                          P8 ergonomics eval (signal, Haiku)
                                 │
                                 ▼
                          P9 README + architecture diagram (final)
```
Phases sequential as drawn; tasks within a phase mostly sequential (noted per task). P4 and P5 both depend only on P3.

---

## Phase 1 — Scaffold (one-time substrate; no production logic)
*Editable-with-review paths only. **GO given by Daniel** — manifest below is exactly what is built.*

#### Task 1.1: Python project + deps
- **Files:** `pyproject.toml`, `uv.lock`, `.env.example`, `.gitignore` (add `.env`, `__pycache__/`, `*.pyc`, `.venv/`)
- **Action:** one `uv` project covering `/backend` (services + tests + evals) and `/mcp`. Runtime: `fastmcp`, `sqlalchemy[asyncio]`, `asyncpg`, `pydantic>=2`, `python-dotenv`. Dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`, `pyright`. Optional `eval` extra (isolated): `anthropic`.
- **Verification:** `uv sync`; `uv run python -c "import fastmcp, sqlalchemy, asyncpg, pydantic; print('ok')"` → `ok`. Paste.
- **Exit:** deps resolve; `.env` gitignored; `.env.example` has `DATABASE_URL` + `ANTHROPIC_API_KEY=` placeholders (HR-6).
- **Protected paths:** `pyproject.toml`, `.gitignore` (editable-with-review — show diff).
- **Risk:** Low.

#### Task 1.2: Local Postgres via Docker Compose
- **File:** `docker-compose.yml`
- **Action:** Postgres 16, healthcheck, env-driven creds (`kpi`/`kpi` local), dev DB `kpi` + test DB `kpi_test`.
- **Verification:** `docker compose up --wait`; `pg_isready` + `SELECT 1`. Paste.
- **Exit:** DB reachable; no hardcoded secret (HR-6).
- **Protected paths:** `docker-compose.yml` (editable-with-review).
- **Risk:** Low.

---

## Phase 2 — DB schema + seed
*Implements DATA-MODEL.md §4 (implement, don't redesign).*

#### Task 2.1: Schema
- **File:** `db/schema.sql` — transcribe DATA-MODEL.md §4 verbatim.
- **TDD:** RED — `backend/tests/test_schema.py`: `as_of` CHECK rejects qtd row with NULL `as_of`; partial-unique index rejects duplicate historical `(ticker,kpi,period)`. Confirm fails. GREEN — apply schema.
- **Verification:** `uv run pytest backend/tests/test_schema.py -q` → green; paste.
- **Protected paths:** `db/schema.sql` (editable-with-review).
- **Risk:** Low.

#### Task 2.2: Seed loader
- **File:** `db/seed.py` — idempotent loader from `db/kpi_sample_2000.csv`; empty `as_of` → NULL (historical), date → qtd.
- **TDD:** RED — `backend/tests/test_seed.py`: 2000 rows, 20 companies, 5 KPIs, 18 sectors; historical `as_of` NULL, qtd non-NULL. Confirm fails. GREEN.
- **Verification:** `uv run pytest backend/tests/test_seed.py -q` → green; paste counts.
- **Dependencies:** 2.1.
- **Risk:** Low.

---

## Phase 3 — `services/` read layer (async, typed; TDD)
*Implements F1–F7. Integration tests vs the real seeded test DB — never mock the fn under test (STANDARDS §2). Read fns only here; the write/upsert fn is in Phase 5 with its REST caller. DDD names throughout.*

#### Task 3.1: Async engine/session + domain models + typed errors
- **Files:** `backend/services/db.py` (lazy async engine/session, no import-time side effects), `backend/services/models.py` (Pydantic 2: `Company`, `KpiUnit`, `HistoryPoint`, `QtdResult`, `CompanyOverview`, `KpiEstimate`; `EstimateType` enum), `backend/services/errors.py` (`UnknownTicker`, `UnknownKpi`, `InvalidDateRange`, `NoQtdData`).
- **TDD:** RED — `backend/tests/test_models.py`: shapes + provenance fields (`unit`,`period`,`as_of`); `EstimateType` values. GREEN.
- **Verification:** `uv run pytest backend/tests/test_models.py -q` + `pyright backend/services` clean. Paste.
- **Risk:** Low.

#### Task 3.2: `list_sectors` + `list_companies` (F1, F2)
- **File:** `backend/services/companies.py`
- **TDD:** RED — `backend/tests/test_companies_service.py`: sectors distinct+sorted; filter by sector / substring (ci over name/ticker/sector) / both; no match → `[]`; empty query → no filter. GREEN — parameterized SQL.
- **Verification:** `uv run pytest backend/tests/test_companies_service.py -q` → green; paste.
- **Dependencies:** 3.1, Phase 2. **Risk:** Low.

#### Task 3.3: `list_kpis` (F3)
- **File:** `backend/services/companies.py` (append)
- **TDD:** RED — distinct `(kpi,unit)` for ticker; unknown ticker → `UnknownTicker`. GREEN.
- **Verification:** same module → green; paste.
- **Dependencies:** 3.2. **Risk:** Low.

#### Task 3.4: `get_kpi_history` (F4)
- **File:** `backend/services/estimates.py`
- **TDD:** RED — `backend/tests/test_estimates_service.py`: historical series ordered by `period_start`; `[start,end]` bounds; empty window → `[]`; `start>end` → `InvalidDateRange`; unknown ticker/kpi → typed errors. GREEN.
- **Verification:** `uv run pytest backend/tests/test_estimates_service.py -q` → green; paste.
- **Exit:** date filter on the DATE column, not the label.
- **Dependencies:** 3.1, Phase 2. **Risk:** Med.

#### Task 3.5: `get_qtd` (F5)
- **File:** `backend/services/estimates.py` (append)
- **TDD:** RED — latest by `MAX(as_of)`; trajectory ordered by `as_of`; no QTD → `NoQtdData`. GREEN.
- **Verification:** same module → green; paste.
- **Dependencies:** 3.4. **Risk:** Med.

#### Task 3.6: `get_company_overview` (F6)
- **File:** `backend/services/estimates.py` (append) — composes 3.3/3.4/3.5 without N+1.
- **TDD:** RED — `backend/tests/test_overview_service.py`: every KPI with latest_history + latest_qtd; missing side → `null` (never fabricated); unknown ticker → `UnknownTicker`. GREEN — bounded query count.
- **Verification:** `uv run pytest backend/tests/test_overview_service.py -q` → green; paste + note query count.
- **Dependencies:** 3.3, 3.5. **Risk:** Med.

---

## Phase 4 — FastMCP tools (thin wrappers; TDD)
*Implements F8 + §6 error contract. Each tool: validate → call one service fn → return typed model. No logic in tool body. Six explicit defs — no registry (rule of three).*

#### Task 4.1: Server bootstrap + `list_sectors`, `list_companies`
- **Files:** `backend/mcp/server.py`, `backend/tests/test_mcp_tools.py`
- **TDD:** RED — call tool fns directly (vs seeded DB): return typed model; docstrings exist. GREEN.
- **Verification:** `uv run pytest backend/tests/test_mcp_tools.py -q` → green; paste. Imports side-effect-free.
- **Dependencies:** Phase 3. **Risk:** Low.

#### Task 4.2: Remaining tools + error mapping (`list_kpis`, `get_kpi_history`, `get_qtd`, `get_company_overview`)
- **Files:** `backend/mcp/server.py` (append), `backend/tests/test_mcp_tools.py` (append)
- **TDD:** RED — typed models with provenance; service errors → §6 structured errors; docstrings name the kpi enum (F8). GREEN.
- **Verification:** `uv run pytest backend/tests/test_mcp_tools.py -q` → green; paste. Smoke: launch server, list tools, call one. Paste.
- **Exit:** six tools live; error contract = §6; enum documented.
- **Dependencies:** 4.1. **Risk:** Med.

---

## Phase 5 — FastAPI REST API (thin wrappers over the same spine; TDD)
*Parallels Phase 4. Same rule: routes validate → call a service fn → return a typed model. No query logic in routes. Two endpoints required by the assessment.*
*Security note (security-guardian lens): the POST is data-mutating + takes external input → strict Pydantic validation, parameterized SQL only, clear 4xx on bad input. No auth (HR-2) — documented as a deliberate scope decision, not an oversight.*

#### Task 5.1: FastAPI app + `GET /companies/{ticker}/estimates` (all KPI estimates for a company)
- **Files:** `backend/services/estimates.py` (append read fn `list_company_estimates(ticker) -> list[KpiEstimate]` — all historical + qtd rows with provenance), `backend/api/app.py`, `backend/api/routes.py`, `backend/tests/test_estimates_service.py` (append), `backend/tests/test_rest_api.py`
- **TDD:** RED — service test: `list_company_estimates` returns all rows for a ticker (history + qtd), unknown ticker → `UnknownTicker`. API test (httpx): `GET /companies/ACME/estimates` → 200 + typed payload with `estimate_type`/`unit`/`period`/`as_of`; unknown ticker → 404 structured error. Confirm fails. GREEN.
- **Verification:** `uv run pytest backend/tests/test_estimates_service.py backend/tests/test_rest_api.py -q` → green; paste. Smoke: `uvicorn` up + `curl GET`. Paste.
- **Exit:** GET endpoint is a thin wrapper; full estimate listing typed.
- **Dependencies:** Phase 3. **Risk:** Low.

#### Task 5.2: `POST /companies/{ticker}/estimates` (publish a new estimate) + upsert service fn
- **Files:** `backend/services/estimates.py` (append write fn `publish_estimate(...)` — `INSERT ... ON CONFLICT` on the matching partial-unique index, `DO UPDATE`), `backend/api/routes.py` (append), `backend/api/schemas.py` (request model), `backend/tests/test_estimates_service.py` (append), `backend/tests/test_rest_api.py` (append)
- **TDD:** RED — service test: publishing a new `(ticker,kpi,period[,as_of])` inserts; republishing the same key updates value (idempotent upsert), respects the historical-vs-qtd `as_of` rule. API test: `POST` valid body → 201/200 + echoed row; invalid body (bad estimate_type, qtd without as_of, unknown ticker) → 422/404 structured error; SQL is parameterized. Confirm fails. GREEN.
- **Verification:** `uv run pytest backend/tests/test_estimates_service.py backend/tests/test_rest_api.py -q` → green; paste. Smoke: `curl POST` new + republish (update). Paste.
- **Exit:** publish upserts correctly; validation rejects malformed input; MCP remains untouched/read-only.
- **Dependencies:** 5.1. **Risk:** Med (write path + validation — security-sensitive).

---

## Phase 6 — Spine fitness function (MCP + REST) + observability

#### Task 6.1: Spine fitness function (evolutionary architecture)
- **File:** `backend/tests/test_architecture.py`
- **TDD:** RED — a test that statically scans **both** `backend/mcp/` **and** `backend/api/` and **fails** if any transport module references SQL execution / a DB session / asyncpg directly (only `services/` may). Prove it can fail against a deliberate violation, then assert the real tree is clean. GREEN.
- **Verification:** `uv run pytest backend/tests/test_architecture.py -q` → green; paste.
- **Exit:** the spine dependency rule is enforced for **both transports** in CI from now on.
- **Dependencies:** Phases 4 + 5. **Risk:** Low.

#### Task 6.2: Structured logging + call_id, wired into both entrypoints (F9)
- **File:** `backend/services/logging.py` (or equiv), wired into the MCP entrypoint **and** the FastAPI app (request id middleware).
- **TDD:** RED — `backend/tests/test_logging.py`: a tool call and a REST request each emit one JSON log line with an id, name/route, arg summary, **no secrets**. GREEN.
- **Verification:** `uv run pytest backend/tests/test_logging.py -q` → green; paste sample lines (one MCP, one REST).
- **Dependencies:** 6.1. **Risk:** Low.

---

## Phase 7 — Frontend (Vite + React + TS; consumes REST; TDD with vitest)
*A pure client of the FastAPI backend (no SSR — see SIMPLICITY). Scaffold Vite at phase start. Tests: vitest + @testing-library/react; mock the REST client at the network edge (never the component under test).*

#### Task 7.1: Scaffold Vite app + typed API client + data layer
- **Files:** `frontend/` (Vite + React 18 + TS5 + Tailwind), `frontend/src/api/client.ts` (typed fetch over the REST contract), TanStack Query provider, Recharts + Vitest config.
- **TDD:** RED — `frontend/src/api/client.test.ts`: client typing + a fetch call shaped to the REST contract (mocked transport). GREEN.
- **Verification:** `npm --prefix frontend run test` → green; `npm --prefix frontend run build` succeeds; `tsc --noEmit` clean. Paste.
- **Protected paths:** `package.json` (editable-with-review).
- **Dependencies:** Phase 5. **Risk:** Med (scaffold).

#### Task 7.2: Navigation — sectors → companies → KPIs + search
- **Files:** `frontend/src/features/browse/*`, tests alongside.
- **TDD:** RED — component tests: sector list renders, selecting a sector loads companies, selecting a company loads KPIs; search box filters companies (by name/ticker/sector). GREEN.
- **Verification:** `npm --prefix frontend run test` → green; paste.
- **Dependencies:** 7.1. **Risk:** Med.

#### Task 7.3: Chart — history + QTD with as-of / last-updated
- **Files:** `frontend/src/features/chart/*`, tests alongside.
- **TDD:** RED — tests: chart renders the settled history series and the current-quarter QTD as a distinct moving line; the QTD `as_of` / "last updated" timestamp is shown; history vs QTD is visually/labelled distinct (mirrors HR-5 — no ambiguity). GREEN.
- **Verification:** `npm --prefix frontend run test` → green; paste.
- **Dependencies:** 7.2. **Risk:** Med.

#### Task 7.4: Date-range filter + export current view
- **Files:** `frontend/src/features/chart/*` (append), export util + tests.
- **TDD:** RED — tests: date-range control re-queries history within `[start,end]`; export produces the current view (CSV of the displayed series). GREEN.
- **Verification:** `npm --prefix frontend run test` → green; paste. Manual smoke: `npm run dev`, click through nav → chart → filter → export. Paste/screenshot note.
- **Dependencies:** 7.3. **Risk:** Med.

---

## Phase 8 — Ergonomics eval (signal, Haiku)

#### Task 8.1: Eval definition + fixtures + runner (skips without key)
- **Files:** `.claude/evals/mcp-ergonomics.md`, `.claude/evals/fixtures/*.jsonl`, `backend/evals/run_ergonomics.py`
- **Action:** ~10–15 §9 capability questions + append-only regression guards; rule/code grader over the tool-call trace (model-grader only where needed, documented). Driver = Claude **Haiku**, HR-7 cap. Runner **skips** if `ANTHROPIC_API_KEY` unset.
- **Verification:** with key — run once, paste `pass@3`/`pass^3`. Without key — show clean skip.
- **Exit:** eval non-vacuous; numbers captured for README.
- **Dependencies:** 4.2. **Risk:** Med.

---

## Phase 9 — Final: README + architecture diagram

#### Task 9.1: ADRs (the decisions feeding the README)
- **Files:** `docs/adr/ADR-003-single-kpi_estimates-table.md`, `ADR-004-mcp-read-only.md`, `ADR-005-services-layer-two-transports.md` (spine + fitness fn), `ADR-006-postgres-cp.md`. (ADR-001 async + ADR-002 mcp-package-location already written.)
- **Action:** short context → decision → consequences each (STANDARDS §6).
- **Verification:** ADRs consistent with SPEC + code.
- **Risk:** Low.

#### Task 9.2: Architecture diagram
- **File:** `docs/architecture-diagram.md` (Mermaid source) — the spine + two transports + frontend + Postgres.
- **Action:** draft the diagram; validate via the Mermaid Chart MCP. **Protected Path — Daniel owns the final.**
- **Verification:** diagram validates/renders.
- **Risk:** Low.

#### Task 9.3: README (graded narrative)
- **File:** `README.md` — **Protected Path; agent drafts, Daniel owns the final.**
- **Action:** run instructions (docker compose → seed → backend → mcp → frontend), key architecture/design decisions (link ADRs + diagram), observability/scaling **as a documented plan** (HR-2 — not built), the eval `pass@3`/`pass^3` signal, and future improvements.
- **Verification:** Daniel reviews; instructions reproduce a working local run.
- **Dependencies:** all prior. **Risk:** Low.

---

## Verification summary (what "done" requires)
- Every code task: RED shown → GREEN real output shown → `pyright`/`ruff` (py) or `tsc`/vitest (fe) clean.
- Phases 3/4/5: integration tests vs the **real seeded test DB** (never mock the fn under test).
- Phase 6: spine fitness function green for **both** transports.
- Phase 8: eval runs once (Haiku) → numbers recorded in README; skips without a key — a signal, not a gate.
- Before each commit: full `git diff --cached`, full test output, coverage where relevant, Protected Paths touched → **Daniel commits** (HR-1).

## Protected Paths this plan touches
- Editable-with-review (show diff): `pyproject.toml`, `.gitignore`, `docker-compose.yml`, `db/schema.sql`, `db/seed.py`, `package.json`.
- Daniel owns (agent drafts only): `README.md`, `docs/architecture-diagram.md`.
- Free within scope: `backend/**` (non-test, includes `backend/mcp/**`), `frontend/src/**` (non-test), `docs/specs/**`, `docs/adr/**` (new).
- New tests created freely (HR-4); no existing test edited/skipped/softened.
