# YipitData KPI Portal + MCP — Project CLAUDE.md

**Version:** 1.0
**Date:** 2026-06-01
**Owner:** Daniel Moreira
**Context:** YipitData Senior Software Engineer take-home. Full-stack app + MCP server. Submitted ahead of a 60-min live session where Daniel must know every implementation detail and code follow-ups live.

> **Read this file FIRST.** It is the operating contract for any agent working in this repo.
> Detailed protocols: `STANDARDS.md`. Code-review/audit method: `REVIEW-METHOD.md`. Simplicity rules: `SIMPLICITY.md`. Portable copy for non-Claude agents: `AGENTS.md`.

---

## Project Identity

```yaml
name: YipitData KPI Portal + MCP server
type: full-stack take-home assessment
goal: >
  Let time-constrained public investors browse YipitData KPI estimates per company
  (historical quarterly vs quarter-to-date), chart and export them, and search by
  sector/company/KPI. The same data API is exposed as an MCP server so AI agents can
  query companies, KPIs, and QTD data.
status: kickoff
grading: architecture + diagram + tech-choice justification + reliability/scale +
         observability PLANS + MCP tool quality (LLM ergonomics)
```

**Architecture spine (the one decision that matters most):**
**One typed service layer, two transports.** A single `services/` layer holds all query and "publish estimate" logic against Postgres. The FastAPI REST endpoints and the FastMCP tools are both **thin wrappers** over those same functions — no query logic is duplicated between them. This is the project's core answer to the "architecture effectiveness" and "MCP quality" criteria.

```
            ┌──────────────┐        ┌──────────────┐
 React UI → │  FastAPI REST│ ─┐     │  FastMCP     │ ← AI agent (Claude/Cursor)
            └──────────────┘  │     └──────────────┘
                              ▼            ▼
                        ┌───────────────────────┐
                        │   services/ (typed)   │  ← all logic lives here
                        └───────────────────────┘
                              ▼
                          PostgreSQL 16
```

## Stack

```yaml
runtime: python 3.11+ (backend + mcp); node 20 LTS (frontend)
package_manager: uv (python); npm (frontend)
layout: light monorepo — /backend (FastAPI + services), /mcp (FastMCP), /frontend (Vite+React), /db (schema + seed)

backend: FastAPI + Pydantic 2 + SQLAlchemy 2.0 (async) + asyncpg
mcp: FastMCP (python) — wraps the SAME services/ layer as REST
frontend: Vite + React 18 + TypeScript 5 + Tailwind + Recharts (charts) + TanStack Query (data)  # shadcn/ui optional
data: PostgreSQL 16 via Docker Compose (local); seed from the provided sample CSV
tests: pytest + httpx (backend/mcp); vitest (frontend)
lint_format: ruff (python); eslint + prettier (frontend)
type_check: pyright/mypy strict (python); tsc (frontend)
observability: structured JSON logging + request IDs + /health + a metrics hook (lightweight, real); full prod stack = a documented PLAN, not built
dev_environment:
  os_target: windows 11 (primary), powershell
  postgres: docker compose
```

> These are the proposed choices; override any in this block and the rest of the doc follows.
> Vite (not Next.js) is deliberate: the frontend is a pure client of a separate FastAPI backend — no SSR/SEO/API-routes need, so Next.js machinery would be weight without benefit (see `SIMPLICITY.md`).

New external dependencies require a one-line ADR entry in `docs/adr/` first.

---

## Disciplines (always active)

Short here. Full protocol in `STANDARDS.md`.

- **TDD** — failing test before production code. RED (show the failing output) → GREEN → REFACTOR.
- **SDD** — non-trivial features get a `SPEC.md` (what + why) before a `PLAN.md` (order) before code.
- **EDD (repurposed for MCP)** — the AI is an *external consumer*, so evals target **MCP tool ergonomics**: run a real agent against the MCP server with realistic investor questions and check it picks the right company, KPI, and history-vs-QTD, and respects date ranges. Small suite, `pass@3 ≥ 0.90` to call the tool design good; `pass^3 = 1.00` on a regression set.
- **Anti-Cheat** — never fake a passing state. Show real output. Never skip/soften/`xfail`. Mock the DB/network at the edges, never the function under test. (This matters doubly here: the live session means Daniel must understand every line — no green that isn't real.)

---

## Hard Rules — non-negotiable

### HR-1 — Manual commits only
All `git add/commit/push` and any PR/merge are run **by Daniel**, never by an agent. No `Co-Authored-By`, no AI attribution anywhere in git history. The assignment encourages AI agents but Daniel must own and understand the whole codebase.
**Agents may:** show `git status`, show `git diff --cached`, suggest a plain-text commit message, run read-only git.

### HR-2 — Scope is locked
Build only the frontend, backend, and MCP features the assignment lists. **Out of scope — do not scaffold, design for, or partially build:**
- Authentication, login, user accounts, RBAC (explicitly not required).
- Real-time streaming / websockets / live push (QTD updates daily at most).
- ETL / ingestion / data-cleaning pipelines (data arrives clean in Postgres; the CSV is a one-time seed).
- Multi-tenancy or per-user saved state.
- Kubernetes, Kafka, message queues, multi-service deployment — scaling is a **documented plan**, not built.
- A second data source or external API integration.

Observability, monitoring, and scaling are graded as **plans**: implement a lightweight real baseline (JSON logs, request IDs, `/health`, a metrics hook) and **document** the production plan in the README. Out of scope to fully build; in scope to document well.

If a request implies any out-of-scope item, **stop, flag it per HR-2, and wait.**

### HR-3 — Applied migrations are immutable *(if Alembic is used)*
A migration applied to the dev DB is not edited. New behavior = new migration. If the project uses a plain `schema.sql` + seed instead, this rule is N/A.

### HR-4 — Test integrity
CREATE new tests freely. EDIT/DELETE existing tests, add `skip`/`xfail`/`skipif`, soften an assertion, or swap a specific mock for a catch-all: **forbidden** without explicit Daniel approval **plus** a `docs/tech-debt.md` entry with an id.

### HR-5 — Grounded MCP data (reframed for this project)
The app contains **no internal LLM**; the MCP server feeds *external* agents. The discipline:
- MCP tools return **structured, typed data with provenance** — every estimate carries its `as_of` (QTD) and `last_updated` timestamps and clearly marks history vs QTD.
- All computation (trends, deltas, filtering) happens **server-side and deterministically** in `services/`, never left for the consuming model to infer.
- Tools never return vague prose an agent might over-trust; they return values + metadata. Make it impossible for the agent to guess.

### HR-6 — Secrets & data discipline
- No secrets in git. DB credentials and any config via `.env` (gitignored) / environment.
- The provided YipitData dataset is proprietary product data — keep it in the repo only as the take-home seed; do not publish it beyond the submission.

### HR-7 — Cost guardrails — N/A
The app calls no paid API. Only relevant if Daniel builds an LLM-driven eval harness for tool quality; if so, cap its spend. Otherwise ignore.

---

## Verification & Reporting

Before asking Daniel to commit:
1. Show `git diff --cached` (full output, not a summary).
2. Show the test command and its **FULL** terminal output — no paraphrasing.
3. Show coverage output if relevant.
4. For MCP work: show the tool-ergonomics eval output (`pass@3` / `pass^3`).
5. List which Protected Paths you touched, if any.
6. Wait for Daniel to commit.

If a test fails: do **not** skip, soften, or mock around it. Stop, report, propose a fix to **production code**, wait.
Verify before you claim. "Done" means you ran it and showed the output.

---

## When Uncertain

Stop. Report the uncertainty. List 2–3 options with trade-offs. Wait for Daniel.
Trial-and-error in production code is forbidden.

---

## Conventions

- **Commits:** Conventional Commits — `feat / fix / chore / docs / refactor / test / perf / ci`, scope in parentheses. TDD pair: `test:` then `feat:`. No AI attribution.
- **Branches:** `feature/<name>`, `data/<name>`, `quality/<name>`, `infra/<name>`, `bugfix/issue-<n>-<name>`, `chore/<name>`.
- **Decisions:** non-trivial choices get an ADR in `docs/adr/` (these feed the README's "architectural decisions" section, which is graded). Known debt goes in `docs/tech-debt.md` as `TD-NNN`.
- **Language:** English throughout — UI strings, code, schema, docs (US-facing assessment).
- **Windows commit pattern** (avoids PowerShell `>>` placeholder bugs):
  ```powershell
  @"
  <commit message>
  "@ | Out-File -FilePath commit-msg.txt -Encoding utf8
  git commit -F commit-msg.txt
  Remove-Item commit-msg.txt
  ```

---

## Protected Paths

Read-only without Daniel approval:
```
tests/**/test_*.py          # edit-forbidden (HR-4); creation permitted
backend/**/test_*.py
alembic/versions/*.py        # immutable once applied (HR-3), if Alembic is used
.env / any secrets           # never committed
README.md                    # Daniel owns the final architecture/decisions narrative (graded)
docs/architecture-diagram.*  # diagram source — Daniel owns the final
```
Editable with diff review:
```
pyproject.toml / package.json, lockfiles, ruff/eslint/tsconfig, docker-compose.yml, .gitignore
db/schema.sql, db/seed.*     # schema and seed — review before applying
```
Free to edit within role scope:
```
backend/** (except tests), mcp/** (except tests), frontend/src/** (except tests)
docs/sessions/**, docs/specs/**, docs/adr/** (new ADRs)
```

---

## Quick Reference

```
Before any task:
  1. Read this file
  2. Read the spec/plan for the current task
  3. Map the codebase before acting

Before any commit (DANIEL ONLY):
  1. git diff --cached
  2. lint, typecheck, tests (+ MCP eval if MCP work)
  3. real output, no summaries
  4. Daniel runs git manually

When uncertain:
  Stop. Report. 2-3 options + trade-offs. Wait.
```

## Pointers
- Full discipline protocols: `STANDARDS.md`
- Code-review / audit method: `REVIEW-METHOD.md`
- Simplicity / anti-overengineering: `SIMPLICITY.md`
- Dataset shape + schema + MCP tool surface: `DATA-MODEL.md`
- Portable rules for other agents: `AGENTS.md`
