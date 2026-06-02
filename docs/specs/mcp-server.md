# Spec: MCP Server (read-only KPI tools)

**Status:** Draft — awaiting Daniel's review
**Date:** 2026-06-02
**Author:** Daniel Moreira (drafted by agent)
**Spec type:** SDD feature spec. Code-review/audit method in `REVIEW-METHOD.md`; simplicity rules in `SIMPLICITY.md`.

> **Quality bar:** open-source-ready, take-home-graded. The MCP surface is judged on *LLM ergonomics* (does an agent pick the right company / KPI / history-vs-QTD and respect date ranges). This spec is the contract the build is verified against.

---

## 1. Problem Statement

A public investor's AI assistant (Claude / Cursor / etc.) needs to query YipitData KPI estimates the same way a human uses the portal: find a company by sector/name, see which KPIs it has, read the settled quarterly history, and read the live quarter-to-date (QTD) estimate as it moves through the current quarter.

The MCP server exposes that capability to *external* agents. Per the architecture spine (`CLAUDE.md`), it is a **thin transport over the shared `services/` layer** — it contains **no query logic of its own**. The same functions back the FastAPI REST transport (built later, out of scope here).

```
 AI agent ──▶ FastMCP tools ─┐
                             ├─▶ services/ (typed, all logic) ─▶ PostgreSQL 16
 (REST, later) ──────────────┘
```

## 2. User Stories

### Primary — agent answers an investor question end-to-end
> As an **investor's AI agent**, I want to resolve a natural question ("How is Acme's ASP trending, and where is this quarter tracking?") into the right company, KPI, history series, and current QTD value, so that I can answer without guessing identifiers or computing trends myself.

**Acceptance Criteria**
- [ ] Agent can discover sectors → companies → KPIs without prior knowledge of tickers or KPI spelling.
- [ ] Agent retrieves settled quarterly history for a `(ticker, kpi)`, optionally bounded by date range.
- [ ] Agent retrieves the current-quarter QTD value **and** its intra-quarter trajectory, each carrying its `as_of` date.
- [ ] Every numeric value the agent receives carries `unit`, `period`, and (for QTD) `as_of` — the agent never infers these (HR-5).
- [ ] History vs QTD is **explicit** in every return shape; the agent cannot confuse the two.

### Secondary — "at a glance" in one call
> As an **investor's AI agent**, I want a single company overview (all KPIs, latest history value + latest QTD value each) so that I can summarize a company in one round-trip.

**Acceptance Criteria**
- [ ] `get_company_overview(ticker)` returns every KPI for the company with its latest settled-history value and latest QTD value + `as_of`.

## 3. Scope

### In Scope
- Six **read-only** MCP tools (DATA-MODEL.md §6): `list_sectors`, `list_companies`, `list_kpis`, `get_kpi_history`, `get_qtd`, `get_company_overview`.
- The `services/` functions these tools wrap (read queries only — the six query patterns in DATA-MODEL.md §5, minus "publish").
- DB schema + seed loader (DATA-MODEL.md §4) — the substrate the services query. Schema is **already specified** in DATA-MODEL.md; this build implements it, it does not redesign it.
- A small **MCP tool-ergonomics eval** (EDD, §9) gating tool-design quality.
- Lightweight observability baseline: structured JSON logs + request/tool-call id (CLAUDE.md observability scope).

### Out of Scope (HR-2 — do not scaffold or design for these)
- **Any write/publish over MCP.** "Publish new estimates" is a REST-only concern; exposing writes to arbitrary agents is an unnecessary risk (DATA-MODEL.md §7). MCP is read-only — a deliberate security decision.
- The FastAPI REST transport, the React frontend — separate features, later.
- Auth / accounts / RBAC, real-time push, ETL/ingestion, multi-tenancy, a second data source.
- A `services/` write/upsert function — not needed by any of the six read tools (YAGNI; SIMPLICITY §3).
- Full production observability/monitoring stack — **documented as a plan** in the README, not built.
- A tool-registration framework / registry — six explicit tool definitions; no registry before the rule-of-three pattern actually repeats (SIMPLICITY §5).

## 4. Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| F1 | `list_sectors() -> [sector]` — distinct sectors, sorted. | Must |
| F2 | `list_companies(sector?, query?) -> [{ticker, name, sector}]` — filter by sector and/or case-insensitive substring over name/ticker/sector. No match → `[]` (not an error). | Must |
| F3 | `list_kpis(ticker) -> [{kpi, unit}]` — distinct KPIs reported for that company, each with its unit. | Must |
| F4 | `get_kpi_history(ticker, kpi, start?, end?) -> [{period, period_end, value, unit}]` — settled `historical` series, ordered by `period_start`, optionally bounded by `[start, end]` on `period_start`. | Must |
| F5 | `get_qtd(ticker, kpi) -> {period, latest_as_of, latest_value, unit, trajectory:[{as_of, value}]}` — current-quarter QTD: latest snapshot + full intra-quarter trajectory ordered by `as_of`. | Must |
| F6 | `get_company_overview(ticker) -> {company:{ticker,name,sector}, kpis:[{kpi, unit, latest_history:{period,value}|null, latest_qtd:{value,as_of}|null}]}` — one-call "at a glance". | Must |
| F7 | All computation (latest-snapshot selection, ordering, date filtering, distinct) is done **server-side in `services/`, deterministically** — never left to the consuming model (HR-5). | Must |
| F8 | Tool docstrings name the valid `kpi` enum and explain history-vs-QTD, so the agent does not guess KPI spelling (ergonomics). | Must |
| F9 | Structured JSON log line per tool call with a generated `call_id`, tool name, and arg summary (no secrets). | Should |

**The five valid KPIs (enum, from the seed):** `ASP ($)`, `Global Net Added Subscribers`, `U.S. Net Added Subscribers`, `Total Revenue ($MM)`, `Units Sold`.

## 5. Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| Tool latency (local, seeded 2k rows) | < 50ms typical; no N+1 — `get_company_overview` is a bounded number of queries, not one-per-KPI in a loop where avoidable |
| Determinism | Identical args → identical output (no clock-dependent ordering except QTD `as_of`, which is data) |
| Type safety | mypy/pyright strict; Pydantic 2 models for every tool return |
| Provenance | Every value carries `unit` + `period`; every QTD value carries `as_of` (HR-5) |

## 6. Tool Contracts (the LLM-facing surface — graded)

Each tool is a **thin wrapper** that (a) validates inputs, (b) calls exactly one `services/` function, (c) returns a typed Pydantic model. No business logic in the tool body.

```
list_sectors() -> list[str]
list_companies(sector: str | None = None, query: str | None = None) -> list[Company]
list_kpis(ticker: str) -> list[KpiUnit]
get_kpi_history(ticker: str, kpi: str, start: date | None = None, end: date | None = None) -> list[HistoryPoint]
get_qtd(ticker: str, kpi: str) -> QtdResult
get_company_overview(ticker: str) -> CompanyOverview
```

Return models (Pydantic 2) carry the provenance fields named in F4–F6. `kpi` is documented with the enum (F8). Tools return **values + metadata only — never prose** the agent might over-trust (HR-5).

### Error contract
Errors are **structured and actionable** so the agent self-corrects rather than guesses:

| Condition | Behavior |
|-----------|----------|
| Unknown `ticker` (get_*/list_kpis) | Typed error: `"unknown ticker 'X'. Use list_companies() to discover valid tickers."` |
| Unknown / misspelled `kpi` | Typed error naming the valid KPI enum **and** which KPIs this ticker actually reports. |
| `start > end` in `get_kpi_history` | Typed error: `"start must be <= end"`. |
| `get_qtd` for a `(ticker, kpi)` with no QTD rows | Typed error stating no QTD estimate exists (only 2026Q1 has QTD). |
| `list_companies` with no matches | Return `[]` — empty is a valid answer, not an error. |

Mapping of these typed `services/` errors to FastMCP error responses is part of F7/F8.

## 7. Data Model

**Already specified** in `DATA-MODEL.md §4` (the `companies` + `kpi_estimates` tables, partial-unique indexes, the `as_of`/`estimate_type` CHECK). This feature **implements** that schema; it does not redesign it. Seed source: `db/kpi_sample_2000.csv` (2000 rows, 20 companies, 5 KPIs, 18 sectors; `historical` 2022Q1–2025Q4, `qtd` 2026Q1 × 4 snapshots).

**CAP trade-off:** PostgreSQL is **CP** — under partition it favors consistency (a read either reflects committed estimates or fails) over availability. Acceptable: investors must not see a torn/half-published estimate. (Recorded as an ADR per the PLAN.)

## 8. Security Considerations

- [x] **No auth** — explicitly out of scope (HR-2). Document that the deployed MCP server would sit behind the host's transport auth; not built here.
- [x] **Read-only** — no tool mutates data; the service layer used by MCP exposes no write function (defense in depth + the §7 decision).
- [x] **Input validation** — `ticker`/`kpi`/dates validated before any query; parameterized SQL only (SQLAlchemy 2.0 — no string-concatenated SQL).
- [x] **No secrets in code** — DB URL via `.env` / environment (HR-6); `.env` gitignored, `.env.example` committed.
- [x] **No PII** — dataset is company KPI estimates, not personal data.
- [x] **No prose leakage** — tools return typed values + metadata; error strings name remediation, never internal stack detail.

## 9. MCP tool ergonomics eval — a quality signal, not a hard gate (Daniel's decision, 2026-06-02)

The AI is an **external consumer**, so the eval targets **tool ergonomics**, not an internal model. A **real but cheap LLM (Claude Haiku)** is pointed at the MCP server with a small fixture of realistic investor questions; a grader checks it selected the right tool(s), company, KPI, and history-vs-QTD, and respected date ranges.

**Status of the eval (decided):** it is a **quality signal run once and recorded in the README — NOT a hard gate** that blocks the build or CI. When no API key is present, the eval **skips cleanly** (it does not fail the suite). This skip is explicitly approved by Daniel for this take-home and is *not* an anti-cheat violation: it is an external-LLM quality probe, not a unit/integration test of our own code, and its skip-without-key behavior is documented here.

- [ ] **Fixture size:** ~10–15 investor questions. Capability examples:
  - "What's Acme's ASP history for 2024?" → expects `get_kpi_history(ACME, "ASP ($)", 2024-01-01, 2024-12-31)`.
  - "Where is Acme's revenue tracking this quarter?" → expects `get_qtd(ACME, "Total Revenue ($MM)")`, reads `latest_value` + `as_of`.
  - "Which cloud companies are there?" → `list_companies(sector="Cloud")`.
  - "Give me a snapshot of NIMB." → `get_company_overview("NIMB")`.
  - Misspelled KPI / unknown ticker → agent recovers using the structured error.
- [ ] **Regression set** (append-only) — guards like "agent never confuses QTD with history"; "agent never invents a ticker".
- [ ] **Driver:** Claude **Haiku** (cheap), with an **HR-7 spend cap** on the harness.
- [ ] **Grader:** rule/code grader over the agent's tool-call trace (deterministic where possible); model-grader only where judgement is needed, documented per case.
- [ ] **Metrics recorded (not enforced as CI gates):** capability `pass@3` and regression `pass^3`, computed and written into the README as the reported quality signal. The CLAUDE.md targets (`pass@3 ≥ 0.90`, `pass^3 = 1.00`) are the **quality bar we report against**, not a build-blocking gate.
- [ ] **Eval file:** `.claude/evals/mcp-ergonomics.md` + fixtures (JSONL) + a runner that skips without an API key.

## 10. Edge Cases

| Case | Expected Behavior |
|------|-------------------|
| Unknown ticker | Typed error pointing to `list_companies()` (§6). |
| Misspelled KPI | Typed error naming the enum + the ticker's actual KPIs. |
| `get_kpi_history` `start > end` | Typed error `"start must be <= end"`. |
| `get_kpi_history` range with no rows in window | `[]` (valid empty series). |
| `get_qtd` where no QTD exists for the pair | Typed error: QTD only exists for the in-progress quarter (2026Q1). |
| Company with KPIs that have history but no QTD (or vice-versa) | `get_company_overview` returns `latest_history`/`latest_qtd` as `null` independently — never fabricated. |
| `list_companies(query="")` / whitespace | Treat as no query filter (return all, or sector-filtered). |
| DB unavailable | Tool fails with a clear error; no partial/silent success (anti-cheat). |

## 11. Testing Strategy

- **Service integration tests** (real seeded test Postgres — never mock the function under test, STANDARDS §2): each of the six query patterns + every §10 edge case. This is where correctness lives.
- **MCP tool tests:** each tool is thin — assert it (a) delegates to its service fn, (b) returns the typed model with required provenance fields (`unit`/`period`/`as_of`), (c) maps service errors to the §6 error contract. Run against the seeded DB.
- **Schema/seed test:** loader produces 2000 rows, 20 companies, 5 KPIs; the two partial-unique indexes and the `as_of` CHECK reject bad rows.
- **EDD gate (§9):** capability `pass@3 ≥ 0.90`, regression `pass^3 = 1.00` — shown as real runner output before "done".
- **Coverage:** services (business logic) ≥ 90%; tools ≥ 80% on changed lines (testing-requirements.md).

## 12. Resolved decisions (was: Open Questions — answered by Daniel 2026-06-02)

- [x] **Async services.** SQLAlchemy 2.0 **async** + asyncpg, to match the stack and the REST path. Justified for a DB-fronting service graded on scalability — see `docs/adr/ADR-001-async-service-layer.md`.
- [x] **Eval = cheap real LLM, signal not gate.** Claude **Haiku** on ~10–15 investor questions, HR-7 spend cap, run once and recorded in the README. **Not** a hard gate; skips cleanly without an API key (§9).
- [x] **`unit` stored on each row** (DATA-MODEL.md §4). Defer the `kpis` lookup table until a third real need (rule of three).

## 13. Quality lenses (applied while building — they raise quality, they do NOT license extra layers/services/infra; SIMPLICITY + HR-2 still bind — this stays ONE modular service)

- **Clean Code (Martin):** small intention-revealing functions, one level of abstraction per function, names over comments.
- **DDD ubiquitous language (Evans):** the domain vocabulary appears verbatim in code — `Company`, `KpiEstimate`, `EstimateType {historical, qtd}`, `as_of`, `period`. Keep the model simple; no extra aggregates.
- **Evolutionary architecture (Ford):** at least one **fitness function as a test** asserting the spine's dependency rule — MCP tools (and future REST routes) import from `services/` and **never** execute SQL or touch the DB session directly.
- **Boundaries (Newman):** clean module seams within one service. Do **not** split into microservices or add infra.

## 14. Changelog
- 2026-06-02: Initial draft (agent), pending review.
- 2026-06-02: Approved by Daniel. Open questions resolved (async / cheap-Haiku-signal / unit-on-row); §9 reframed (eval = signal, not gate); §13 quality lenses + spine fitness function added; ADR-001 (async) written.
