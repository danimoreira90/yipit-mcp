# Data Model (reference)

**Owner:** Daniel Moreira
**Source:** `kpi_sample_2000.csv` (the YipitData sample seed — 2000 rows).
**Purpose:** the locked understanding of the dataset and the proposed Postgres schema. The agent building the app reads this before touching the DB layer.

---

## 1. Dataset at a glance

- **2000 rows**, each row = one KPI estimate.
- **20 companies**, **18 sectors** (sector → company is one-to-many; e.g. Cloud has CLD9, STRT, NIMB).
- **5 KPIs:** `ASP ($)`, `Global Net Added Subscribers`, `U.S. Net Added Subscribers`, `Total Revenue ($MM)`, `Units Sold`.
- **CSV columns:** `company_name, ticker, sector, kpi, period_start, period_end, period, estimate_type, value, unit, as_of`.

## 2. The grain — and the one rule that shapes everything

`estimate_type` splits the data into two kinds, and a given `(ticker, kpi, period)` is **only ever one of them**:

- **`historical`** (1600 rows): the settled estimate for a finished quarter. One row per `(ticker, kpi, period)`. `as_of` is **empty**. Covers **2022Q1 → 2025Q4** (16 quarters).
- **`qtd`** (400 rows): the live estimate for the **in-progress** quarter, **2026Q1 only**. For each `(ticker, kpi)` there are **4 snapshots** at different `as_of` dates (`2026-01-31, 2026-02-15, 2026-02-28, 2026-03-15`) — the estimate moving through the quarter.

*Plain version:* history is "what we finally believe each past quarter was." QTD is "what we believe the current quarter is *right now*," and it gets revised every couple of weeks. The chart shows the settled history, then the current quarter as a moving QTD line.

**`unit` is determined by `kpi`** ($ / $MM / subs / units). It is not independent data.

## 3. Entities

- **company** — `ticker` (id), `company_name`, `sector`.
- **kpi_estimate** — a value for a `(ticker, kpi, period)`, tagged `historical` or `qtd`, with `as_of` for QTD snapshots, plus the quarter's `period_start` / `period_end`.

## 4. Proposed schema (Postgres 16)

One table for both kinds, discriminated by `estimate_type`, with two **partial unique** indexes for the two different natural keys. This matches the CSV exactly and avoids splitting one concept across two tables (see Decisions).

```sql
CREATE TABLE companies (
    ticker        TEXT PRIMARY KEY,
    company_name  TEXT NOT NULL,
    sector        TEXT NOT NULL
);
CREATE INDEX idx_companies_sector ON companies (sector);

CREATE TABLE kpi_estimates (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    ticker        TEXT NOT NULL REFERENCES companies (ticker),
    kpi           TEXT NOT NULL,
    unit          TEXT NOT NULL,                 -- determined by kpi; stored for convenience
    period        TEXT NOT NULL,                 -- 'YYYYQn', e.g. '2026Q1'
    period_start  DATE NOT NULL,                 -- filter/sort on this
    period_end    DATE NOT NULL,
    estimate_type TEXT NOT NULL CHECK (estimate_type IN ('historical','qtd')),
    value         NUMERIC NOT NULL,
    as_of         DATE,                           -- NULL for historical, set for qtd
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT as_of_matches_type CHECK (
        (estimate_type = 'historical' AND as_of IS NULL)
     OR (estimate_type = 'qtd'        AND as_of IS NOT NULL)
    )
);

-- one settled value per finished quarter
CREATE UNIQUE INDEX uq_hist ON kpi_estimates (ticker, kpi, period)
    WHERE estimate_type = 'historical';
-- one value per intra-quarter snapshot
CREATE UNIQUE INDEX uq_qtd  ON kpi_estimates (ticker, kpi, period, as_of)
    WHERE estimate_type = 'qtd';

-- query helpers
CREATE INDEX idx_hist_series ON kpi_estimates (ticker, kpi, period_start)
    WHERE estimate_type = 'historical';
CREATE INDEX idx_qtd_latest  ON kpi_estimates (ticker, kpi, as_of DESC)
    WHERE estimate_type = 'qtd';
```

> Optional normalization: a `kpis (kpi PK, unit)` lookup, since `unit` is functionally dependent on `kpi`. Defer it (rule of three) unless KPI metadata grows — storing `unit` on the row is fine for v1.

## 5. The query patterns the app needs

- **History series (chart):** `WHERE ticker=? AND kpi=? AND estimate_type='historical' [AND period_start BETWEEN ? AND ?] ORDER BY period_start`.
- **Current QTD value:** latest snapshot — `WHERE ticker=? AND kpi=? AND estimate_type='qtd' ORDER BY as_of DESC LIMIT 1`.
- **QTD trajectory (intra-quarter line):** all `qtd` rows for the current period ordered by `as_of`.
- **"Last updated" / "as-of":** `MAX(as_of)` over the QTD rows for that `(ticker, kpi)`.
- **Search:** companies `WHERE company_name ILIKE %q% OR ticker ILIKE %q% OR sector ILIKE %q%`, plus KPI-name match.
- **Publish (backend write):** upsert — `INSERT ... ON CONFLICT` on the matching partial-unique index `DO UPDATE SET value = EXCLUDED.value, created_at = now()`.

## 6. MCP tool surface (the LLM-facing design — graded)

Tools map to how an investor-assistant would actually ask. Each returns structured data with `unit`, `period`, and `as_of` so the consuming agent never guesses (HR-5).

- `list_sectors() -> [sector]`
- `list_companies(sector?: str, query?: str) -> [{ticker, name, sector}]`
  - `query` is a case-insensitive substring over `company_name`/`ticker`/`sector` (the search box hits the sector too); `sector` is the exact drill-down filter.
- `list_kpis(ticker: str) -> [{kpi, unit}]`
- `get_kpi_history(ticker: str, kpi: str, start?: date, end?: date) -> [{period, period_end, value, unit}]`
- `get_qtd(ticker: str, kpi: str) -> {period, latest_as_of, latest_value, unit, trajectory: [{as_of, value}]}`
- `get_company_overview(ticker: str) -> {company, kpis: [{kpi, latest_history, latest_qtd, as_of}]}`  — serves the "at a glance" goal in one call.

**Tool-design rules:** clear names + one-line docstrings; `kpi` documented with its valid enum so the agent doesn't guess KPI spelling; history vs QTD always explicit in the return; never return prose the agent might over-trust — values + metadata only.

## 7. Design decisions to record (these feed the graded README)

- **Single `kpi_estimates` table, not two.** History and QTD are the same concept (an estimate) at different lifecycle stages; one table + a discriminator + partial unique indexes keeps query logic and the `services/` layer simple. Alternative (two tables) duplicates almost everything.
- **`as_of` nullability carries the history/QTD distinction**, enforced by a CHECK so bad rows can't be inserted.
- **MCP is read-only.** "Publish new estimates" is a backend/REST concern; exposing writes over MCP to arbitrary agents is an unnecessary risk for this scope. State this as a deliberate security decision.
- **Filtering/sorting on `period_start` (a real DATE)**, not on the `'2026Q1'` label string, so date-range filters and ordering are correct and index-friendly.
