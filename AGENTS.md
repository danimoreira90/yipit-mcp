# YipitData KPI Portal + MCP — AGENTS.md

**Generic agent rules for any AI coding assistant working on this repo.**
**Version:** 1.0 | **Date:** 2026-06-01

> For agents that don't read `CLAUDE.md` (Claude Code only). Mirrors the same rules so the project stays agent-portable.

---

## Identity

Full-stack take-home for YipitData. A web app that lets time-constrained public investors browse KPI estimates per company (historical quarterly vs quarter-to-date / QTD), chart and export them, and search by sector/company/KPI. The same data API is exposed as an **MCP server** so AI agents can query companies, KPIs, and QTD data. No auth, no streaming, daily-at-most updates. Submitted ahead of a 60-min live session where Daniel must know every detail and code follow-ups live.

**Core architecture:** one typed `services/` layer holds all DB logic; the FastAPI REST API and the FastMCP server are both thin wrappers over it. No duplicated query logic.

Owner: Daniel Moreira.

---

## Hard Rules — non-negotiable

- **HR-1 — Manual commits only.** Only Daniel runs `git add/commit/push` or any PR/merge. Agents show diffs and suggest plain-text messages. No AI attribution in git history.
- **HR-2 — Scope is locked.** Out of scope: auth/login, real-time streaming/websockets, ETL/ingestion pipelines, multi-tenancy, Kubernetes/Kafka/queues, extra data sources. Observability + scaling are documented **plans** plus a lightweight real baseline — not a full build. If a request implies an out-of-scope item, stop and flag it.
- **HR-3 — Applied migrations are immutable** (if Alembic is used; N/A for a plain schema.sql + seed).
- **HR-4 — Test integrity.** Create new tests freely. Editing/deleting tests, or adding `skip`/`xfail`/softened assertions/catch-all mocks, needs Daniel approval + a `docs/tech-debt.md` entry. Mock at the DB/network edges, never the function under test.
- **HR-5 — Grounded MCP data.** No internal LLM; the MCP server feeds external agents. Tools return structured, typed data with provenance (`as_of`, `last_updated`, history-vs-QTD marked). All computation is server-side and deterministic in `services/`. Never leave the consuming model to guess or compute.
- **HR-6 — Secrets & data discipline.** No secrets in git; creds via `.env`/env. The provided dataset is proprietary — seed only, don't publish beyond submission.
- **HR-7 — Cost guardrails — N/A** (app calls no paid API; cap spend only if an LLM eval harness is built).

---

## Stack

```
python 3.11+ (backend + mcp), node 20 LTS (frontend)
uv (python), npm (frontend)
backend: FastAPI + Pydantic 2 + SQLAlchemy 2.0 async + asyncpg
mcp: FastMCP — wraps the same services/ layer as REST
frontend: Vite + React 18 + TypeScript + Tailwind + Recharts + TanStack Query
data: PostgreSQL 16 (docker compose), seed from provided CSV
tests: pytest + httpx; vitest
lint/format: ruff; eslint + prettier
type-check: pyright/mypy strict; tsc
```
New external deps require a one-line ADR entry in `docs/adr/` first.

---

## Disciplines

- **TDD** — failing test before production code. Red → Green → Refactor.
- **SDD** — non-trivial features get `SPEC.md` before `PLAN.md` before code.
- **EDD (for MCP)** — eval the MCP tool design by running a real agent against it; `pass@3 ≥ 0.90` for tool quality, `pass^3 = 1.00` on regression.
- **Anti-Cheat** — never fake a passing state; show real output; never skip/soften/mock-the-world.

---

## Branch Roles
`feature/<name>` · `data/<name>` · `quality/<name>` · `infra/<name>` · `bugfix/issue-<n>-<name>` · `chore/<name>`

## Protected Paths
Read-only without owner approval:
```
tests/**/test_*.py (edit-forbidden), alembic/versions/*.py (if used), .env/secrets,
README.md (Daniel owns the narrative), docs/architecture-diagram.* (Daniel owns)
```

## Reporting
1. Show `git diff --cached` (full output). 2. Show the test command + FULL terminal output. 3. Coverage if relevant; MCP eval output for MCP work. 4. List Protected Paths touched. 5. Wait for Daniel to commit.
If a test fails: do not skip, soften, or mock around it. Stop, report, propose a production-code fix, wait.

## When Uncertain
Stop. Report. List 2–3 options with trade-offs. Wait for Daniel. No trial-and-error in production code.

## Pointers
- Claude Code guidance: `CLAUDE.md` · Discipline detail: `STANDARDS.md` · Review method: `REVIEW-METHOD.md` · Simplicity: `SIMPLICITY.md` · Data model + schema: `DATA-MODEL.md`
